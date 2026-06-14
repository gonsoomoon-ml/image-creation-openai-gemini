"""세 모델 이미지 생성/편집(generate·edit) + 토큰 사용량/비용 비교.

cases.toml 에 정의된 테스트 케이스를 읽어, 각 케이스를 지정 모델들로 실행하고
응답의 토큰 사용량으로 예상 비용(USD)을 계산해 표로 출력한다.
결과 이미지/사용량은 outputs/<case-id>/ 아래에 저장된다.

실행:
    uv sync
    cp .env.example .env                              # 그리고 실제 API 키 입력
    uv run python src/generate_sample.py             # 모든 케이스
    uv run python src/generate_sample.py cat-fullbody  # 한 케이스만
    uv run python src/generate_sample.py --list      # 케이스 목록만 (API 호출 없음)
"""
from __future__ import annotations

import base64
import json
import os
import sys
import time
import tomllib
from io import BytesIO
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types
from openai import OpenAI
from PIL import Image

# --- 경로 / 환경 ---
PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = PROJECT_ROOT / "outputs"
CASES_FILE = PROJECT_ROOT / "cases.toml"
load_dotenv(PROJECT_ROOT / ".env")

# 모델 ID 는 .env 에서 읽고, 미설정 시 검증된 기본값(핵심 테스트 세트)을 사용
OPENAI_IMAGE_MODEL = os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-2")
GEMINI_PRO_IMAGE_MODEL = os.getenv("GEMINI_PRO_IMAGE_MODEL", "gemini-3-pro-image")
GEMINI_FLASH_IMAGE_MODEL = os.getenv("GEMINI_FLASH_IMAGE_MODEL", "gemini-3.1-flash-image")

# 케이스에 models 미지정 시 쓰는 기본 세트, 그리고 모델→제공자 매핑
DEFAULT_MODELS = [OPENAI_IMAGE_MODEL, GEMINI_PRO_IMAGE_MODEL, GEMINI_FLASH_IMAGE_MODEL]
MODEL_PROVIDER = {
    OPENAI_IMAGE_MODEL: "openai",
    GEMINI_PRO_IMAGE_MODEL: "gemini",
    GEMINI_FLASH_IMAGE_MODEL: "gemini",
}

# --- 가격표 (USD, per 1M tokens; design/research_models_api.md 참고) ---
OPENAI_RATES = {
    "gpt-image-2": {"text_in": 5.0, "image_in": 8.0, "image_out": 30.0, "text_out": 0.0},
}
GEMINI_RATES = {
    "gemini-3-pro-image": {"input": 2.0, "image_out": 120.0},
    "gemini-3.1-flash-image": {"input": 0.5, "image_out": 60.0},
}


def _get_key(*names: str) -> str:
    """환경 변수에서 API 키를 읽는다. 비어 있거나 플레이스홀더면 안내 후 예외."""
    for name in names:
        value = os.getenv(name, "").strip()
        if value and not value.startswith("your_"):
            return value
    raise ValueError(
        f"환경 변수 {' 또는 '.join(names)} 가 설정되지 않았습니다. "
        ".env 파일에 실제 키를 넣어주세요 (.env.example 참고)."
    )


def _fmt_cost(cost: float | None) -> str:
    """예상 비용을 표시 문자열로. 단가표에 없는 모델이면 'n/a'."""
    return f"${cost:.4f}" if cost is not None else "n/a (단가표 없음)"


def _load_input_rgb(path: Path) -> Image.Image:
    """입력 이미지를 RGB(흰 배경 합성)로 로드. 편집 시 alpha 가 마스크로 오인되는 것 방지."""
    im = Image.open(path).convert("RGBA")
    bg = Image.new("RGB", im.size, "white")
    bg.paste(im, mask=im.split()[3])
    return bg


def load_cases() -> list[dict]:
    """cases.toml 을 읽어 케이스 목록을 반환. 기본 검증 포함(호출 전 fail-fast)."""
    if not CASES_FILE.exists():
        raise FileNotFoundError(f"{CASES_FILE} 가 없습니다. cases.toml 을 만들어 주세요.")
    cases = tomllib.loads(CASES_FILE.read_text(encoding="utf-8")).get("case", [])
    seen: set[str] = set()
    for c in cases:
        cid = c.get("id")
        if not cid:
            raise ValueError("각 [[case]] 에는 id 가 필요합니다.")
        if cid in seen:
            raise ValueError(f"중복된 case id: {cid}")
        seen.add(cid)
        if c.get("type") not in ("edit", "generate"):
            raise ValueError(f"[{cid}] type 은 'edit' 또는 'generate' 여야 합니다.")
        if not c.get("prompt"):
            raise ValueError(f"[{cid}] prompt 가 필요합니다.")
        if c["type"] == "edit" and not c.get("image"):
            raise ValueError(f"[{cid}] edit 케이스에는 image 가 필요합니다.")
        for m in c.get("models", DEFAULT_MODELS):
            if m not in MODEL_PROVIDER:
                raise ValueError(
                    f"[{cid}] 알 수 없는 모델 '{m}'. 사용 가능: {list(MODEL_PROVIDER)}"
                )
    return cases


def generate_openai(model: str, prompt: str, image_path: Path | None, out_dir: Path,
                    quality: str = "high", label: str | None = None) -> dict:
    """OpenAI 이미지. image_path 있으면 편집(images.edit), 없으면 생성(images.generate).
    quality(low|medium|high)는 출력 토큰 수를 바꿔 비용·소요시간을 함께 좌우한다.
    label 을 주면 그 이름으로 저장(품질 변형 비교용, 예: gpt-image-2-low)."""
    client = OpenAI(api_key=_get_key("OPENAI_API_KEY"))
    if image_path is not None:
        buf = BytesIO()
        _load_input_rgb(image_path).save(buf, format="png")
        buf.name = "input.png"   # SDK 가 파일명/MIME 추론하도록
        buf.seek(0)
        resp = client.images.edit(
            model=model, image=buf, prompt=prompt,
            size="1024x1024",   # gpt-image-2: 1024x1024 / 1536x1024 / 1024x1536 / auto
            quality=quality,    # low | medium | high (출력 토큰=비용=속도)
            # 주의: gpt-image-2 에는 input_fidelity 를 쓰지 말 것
        )
    else:
        resp = client.images.generate(
            model=model, prompt=prompt, size="1024x1024", quality=quality,
        )
    out_name = label or model
    out_path = out_dir / f"{out_name}.png"
    out_path.write_bytes(base64.b64decode(resp.data[0].b64_json))

    u = resp.usage  # GPT image 모델에만 존재
    out_det = getattr(u, "output_tokens_details", None)
    image_out = getattr(out_det, "image_tokens", None) if out_det else None
    text_out = getattr(out_det, "text_tokens", 0) if out_det else 0
    if image_out is None:
        image_out, text_out = u.output_tokens, 0  # 상세 없으면 전부 이미지로 근사
    in_det = getattr(u, "input_tokens_details", None)
    text_in = getattr(in_det, "text_tokens", u.input_tokens) if in_det else u.input_tokens
    image_in = getattr(in_det, "image_tokens", 0) if in_det else 0

    r = OPENAI_RATES.get(model)
    cost = None
    if r is not None:
        cost = round(
            (
                text_in * r["text_in"]
                + image_in * r["image_in"]
                + image_out * r["image_out"]
                + text_out * r["text_out"]
            )
            / 1e6,
            4,
        )
    return {
        "provider": "openai",
        "model": out_name,
        "quality": quality,
        "path": str(out_path.relative_to(PROJECT_ROOT)),
        "input_tokens": u.input_tokens,
        "output_tokens": u.output_tokens,
        "total_tokens": u.total_tokens,
        "est_cost_usd": cost,
    }


def generate_gemini(model: str, prompt: str, image_path: Path | None, out_dir: Path) -> dict:
    """Gemini 이미지. image_path 있으면 편집(프롬프트+이미지), 없으면 생성(프롬프트만)."""
    client = genai.Client(api_key=_get_key("GOOGLE_API_KEY", "GEMINI_API_KEY"))
    contents = [prompt] if image_path is None else [prompt, _load_input_rgb(image_path)]
    resp = client.models.generate_content(
        model=model,
        contents=contents,
        config=types.GenerateContentConfig(
            response_modalities=["TEXT", "IMAGE"],
            image_config=types.ImageConfig(aspect_ratio="1:1", image_size="1K"),
        ),
    )
    out_path = out_dir / f"{model}.png"
    for part in resp.parts:
        if part.inline_data is not None:
            Image.open(BytesIO(part.inline_data.data)).save(out_path)
            break

    um = resp.usage_metadata
    prompt_tokens = um.prompt_token_count or 0
    cand_tokens = um.candidates_token_count or 0
    # candidates 중 IMAGE 모달리티 토큰만 (상세 없으면 candidates 전체로 근사)
    image_out_tokens = cand_tokens
    for d in getattr(um, "candidates_tokens_details", None) or []:
        mod = getattr(d, "modality", None)
        if getattr(mod, "name", str(mod)) == "IMAGE":
            image_out_tokens = d.token_count

    r = GEMINI_RATES.get(model)
    cost = None
    if r is not None:
        cost = round((prompt_tokens * r["input"] + image_out_tokens * r["image_out"]) / 1e6, 4)
    return {
        "provider": "gemini",
        "model": model,
        "path": str(out_path.relative_to(PROJECT_ROOT)),
        "prompt_tokens": prompt_tokens,
        "candidates_tokens": cand_tokens,
        "total_tokens": um.total_token_count,
        "est_cost_usd": cost,
    }


PROVIDERS = {"openai": generate_openai, "gemini": generate_gemini}


def _run_case(case: dict) -> list[dict]:
    """한 케이스를 모델별로 실행하고 결과 목록을 반환. outputs/<id>/usage.json 저장."""
    cid = case["id"]
    out_dir = OUT_DIR / cid
    out_dir.mkdir(parents=True, exist_ok=True)

    image_path = None
    if case["type"] == "edit":
        image_path = PROJECT_ROOT / case["image"]
        if not image_path.exists():
            print(f"  [건너뜀] {cid}: 입력 이미지 없음 {image_path}")
            return []

    results = []
    for model in case.get("models", DEFAULT_MODELS):
        fn = PROVIDERS[MODEL_PROVIDER[model]]
        print(f"  [{case['type']}] {cid} · {model} ...")
        try:
            t0 = time.perf_counter()
            res = fn(model, case["prompt"], image_path, out_dir)
            res["elapsed_sec"] = round(time.perf_counter() - t0, 2)  # API 호출 포함 전체 소요(초)
            results.append(res)
            print(f"    → {res['path']}  (비용 {_fmt_cost(res['est_cost_usd'])}, {res['elapsed_sec']}s)")
        except Exception as e:  # noqa: BLE001 - 샘플이므로 셀 단위 실패 격리
            print(f"    [건너뜀] {model}: {e}")

    if results:
        (out_dir / "usage.json").write_text(
            json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    return results


OPENAI_QUALITIES = ("low", "medium", "high")


def _merge_usage(out_dir: Path, new_results: list[dict]) -> None:
    """새 결과를 outputs/<id>/usage.json 에 라벨(model) 기준으로 병합(기존 항목 보존)."""
    path = out_dir / "usage.json"
    merged: dict[str, dict] = {}
    if path.exists():
        for row in json.loads(path.read_text(encoding="utf-8")):
            merged[row["model"]] = row
    for res in new_results:
        merged[res["model"]] = res
    path.write_text(json.dumps(list(merged.values()), indent=2, ensure_ascii=False), encoding="utf-8")


def _run_quality_sweep(cases: list[dict], qualities: list[str]) -> None:
    """gpt-image-2 를 여러 quality 로만 돌려 비용·속도를 비교(라벨 <model>-<quality>).
    다른 모델/기존 결과는 건드리지 않고 usage.json 에 병합한다(재과금 최소화)."""
    bad = [q for q in qualities if q not in OPENAI_QUALITIES]
    if bad:
        print(f"알 수 없는 quality: {bad} (사용 가능: {list(OPENAI_QUALITIES)})")
        return
    rows: list[tuple[str, dict]] = []
    for case in cases:
        out_dir = OUT_DIR / case["id"]
        out_dir.mkdir(parents=True, exist_ok=True)
        image_path = None
        if case["type"] == "edit":
            image_path = PROJECT_ROOT / case["image"]
            if not image_path.exists():
                print(f"  [건너뜀] {case['id']}: 입력 이미지 없음 {image_path}")
                continue
        new: list[dict] = []
        for q in qualities:
            label = f"{OPENAI_IMAGE_MODEL}-{q}"
            print(f"  [openai {q}] {case['id']} · {label} ...")
            try:
                t0 = time.perf_counter()
                res = generate_openai(OPENAI_IMAGE_MODEL, case["prompt"], image_path, out_dir, quality=q, label=label)
                res["elapsed_sec"] = round(time.perf_counter() - t0, 2)
                new.append(res)
                rows.append((case["id"], res))
                print(f"    → {res['path']}  (비용 {_fmt_cost(res['est_cost_usd'])}, {res['elapsed_sec']}s)")
            except Exception as e:  # noqa: BLE001 - 셀 단위 실패 격리
                print(f"    [건너뜀] {label}: {e}")
        if new:
            _merge_usage(out_dir, new)

    if not rows:
        print("\n생성된 결과가 없습니다. .env 의 API 키/케이스 설정을 확인하세요.")
        return
    print(f"\n{'case':16}{'quality':9}{'total_tokens':>14}{'est_cost_usd':>14}{'elapsed_sec':>13}")
    print("-" * 66)
    for cid, r in rows:
        print(f"{cid:16}{r.get('quality', ''):9}{r['total_tokens']:>14}{_fmt_cost(r['est_cost_usd']):>14}{r['elapsed_sec']:>13.2f}")


def main() -> None:
    args = sys.argv[1:]
    cases = load_cases()

    if "--list" in args:
        print("사용 가능한 케이스:")
        for c in cases:
            n = len(c.get("models", DEFAULT_MODELS))
            print(f"  - {c['id']:20} [{c['type']:8}] 모델 {n}종")
        return

    wanted = [a for a in args if not a.startswith("-")]
    if wanted:
        ids = {c["id"] for c in cases}
        for w in wanted:
            if w not in ids:
                print(f"알 수 없는 케이스: {w} (사용 가능: {sorted(ids)})")
                return
        cases = [c for c in cases if c["id"] in wanted]

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # --quality=low,medium : gpt-image-2 만 해당 quality 들로 추가 실행(기존 결과에 병합)
    quality_csv = next((a.split("=", 1)[1] for a in args if a.startswith("--quality=")), None)
    if quality_csv:
        _run_quality_sweep(cases, [q.strip() for q in quality_csv.split(",") if q.strip()])
        return

    rows: list[tuple[str, dict]] = []
    for case in cases:
        print(f"[케이스] {case['id']}")
        rows.extend((case["id"], r) for r in _run_case(case))

    if not rows:
        print("\n생성된 결과가 없습니다. .env 의 API 키/케이스 설정을 확인하세요.")
        return

    print(f"\n{'case':20}{'model':28}{'total_tokens':>14}{'est_cost_usd':>16}{'elapsed_sec':>14}")
    print("-" * 92)
    for cid, r in rows:
        print(f"{cid:20}{r['model']:28}{r['total_tokens']:>14}{_fmt_cost(r['est_cost_usd']):>16}{r['elapsed_sec']:>14.2f}")


if __name__ == "__main__":
    main()
