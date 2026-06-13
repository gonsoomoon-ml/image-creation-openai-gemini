"""세 모델 이미지 편집(image-to-image) + 토큰 사용량/비용 비교 샘플.

대상 모델 (design/research_models_api.md 의 핵심 테스트 세트):
  - OpenAI: gpt-image-2          (client.images.edit)
  - Gemini: gemini-3-pro-image (Pro), gemini-3.1-flash-image (Flash)  (generate_content)

입력 스케치 한 장(test_data/cat-scratch.png)과 동일 프롬프트로 세 모델에서
이미지를 편집/생성하고, 응답의 토큰 사용량을 읽어 예상 비용(USD)을 계산해
표로 출력합니다. 결과 이미지는 outputs/ 에 저장됩니다.

실행:
    uv sync
    cp .env.example .env          # 그리고 실제 API 키 입력
    uv run python src/generate_sample.py
"""
from __future__ import annotations

import base64
import json
import os
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
load_dotenv(PROJECT_ROOT / ".env")

# 입력 스케치를 바탕으로 한 이미지 편집(image-to-image) — 세 모델 동일 입력/프롬프트
PROMPT = "A full-body cute cat based on this simple smiling cat sketch. High-resolution."
INPUT_IMAGE = PROJECT_ROOT / "test_data" / "cat-scratch.png"

# 모델 ID 는 .env 에서 읽고, 미설정 시 검증된 기본값(핵심 테스트 세트)을 사용
OPENAI_IMAGE_MODEL = os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-2")
GEMINI_PRO_IMAGE_MODEL = os.getenv("GEMINI_PRO_IMAGE_MODEL", "gemini-3-pro-image")
GEMINI_FLASH_IMAGE_MODEL = os.getenv("GEMINI_FLASH_IMAGE_MODEL", "gemini-3.1-flash-image")

# --- 가격표 (USD, 2026-06 기준; design/research_models_api.md 참고) ---
# OpenAI: 100만 토큰당 단가. gpt-image-2 는 별도 text-out 단가가 없어 0 으로 둔다.
OPENAI_RATES = {
    "gpt-image-2": {"text_in": 5.0, "image_in": 8.0, "image_out": 30.0, "text_out": 0.0},
}
# Gemini: 100만 토큰당 단가 (input = prompt, image_out = candidates 의 IMAGE 토큰)
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
    """입력 이미지를 RGB(흰 배경 합성)로 로드. 편집 시 alpha 채널이 마스크로 오인되는 것 방지."""
    im = Image.open(path).convert("RGBA")
    bg = Image.new("RGB", im.size, "white")
    bg.paste(im, mask=im.split()[3])
    return bg


def generate_openai(model: str) -> dict:
    """OpenAI 이미지 편집(images.edit). 입력 스케치 + 프롬프트 → 새 이미지. 응답은 base64."""
    client = OpenAI(api_key=_get_key("OPENAI_API_KEY"))
    buf = BytesIO()
    _load_input_rgb(INPUT_IMAGE).save(buf, format="png")
    buf.name = "input.png"   # SDK 가 파일명/MIME 을 추론하도록
    buf.seek(0)
    resp = client.images.edit(
        model=model,
        image=buf,
        prompt=PROMPT,
        size="1024x1024",   # gpt-image-2: 1024x1024 / 1536x1024 / 1024x1536 / auto
        quality="high",     # low | medium | high | auto
        # 주의: gpt-image-2 에는 input_fidelity 를 쓰지 말 것
    )
    out_path = OUT_DIR / f"{model}.png"
    out_path.write_bytes(base64.b64decode(resp.data[0].b64_json))

    u = resp.usage  # GPT image 모델에만 존재
    # 출력 토큰을 이미지/텍스트로 분리 (스키마 미보장 → getattr 로 방어적 접근)
    out_det = getattr(u, "output_tokens_details", None)
    image_out = getattr(out_det, "image_tokens", None) if out_det else None
    text_out = getattr(out_det, "text_tokens", 0) if out_det else 0
    if image_out is None:
        image_out, text_out = u.output_tokens, 0  # 상세가 없으면 전부 이미지로 근사
    in_det = getattr(u, "input_tokens_details", None)
    text_in = getattr(in_det, "text_tokens", u.input_tokens) if in_det else u.input_tokens
    image_in = getattr(in_det, "image_tokens", 0) if in_det else 0

    # 단가표에 없는 모델(env 로 교체한 경우)은 비용을 None 으로 둔다
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
        "model": model,
        "path": str(out_path.relative_to(PROJECT_ROOT)),
        "input_tokens": u.input_tokens,
        "output_tokens": u.output_tokens,
        "total_tokens": u.total_tokens,
        "est_cost_usd": cost,
    }


def generate_gemini(model: str) -> dict:
    """Gemini 이미지 편집 (generate_content). 프롬프트 + 입력 스케치를 contents 로 전달."""
    client = genai.Client(api_key=_get_key("GOOGLE_API_KEY", "GEMINI_API_KEY"))
    resp = client.models.generate_content(
        model=model,
        contents=[PROMPT, _load_input_rgb(INPUT_IMAGE)],
        config=types.GenerateContentConfig(
            response_modalities=["TEXT", "IMAGE"],
            image_config=types.ImageConfig(aspect_ratio="1:1", image_size="1K"),
        ),
    )
    out_path = OUT_DIR / f"{model}.png"
    for part in resp.parts:
        if part.inline_data is not None:
            Image.open(BytesIO(part.inline_data.data)).save(out_path)
            break

    um = resp.usage_metadata
    prompt_tokens = um.prompt_token_count or 0
    cand_tokens = um.candidates_token_count or 0
    # candidates 중 IMAGE 모달리티 토큰만 추출 (상세가 없으면 candidates 전체로 근사)
    image_out_tokens = cand_tokens
    for d in getattr(um, "candidates_tokens_details", None) or []:
        mod = getattr(d, "modality", None)
        if getattr(mod, "name", str(mod)) == "IMAGE":
            image_out_tokens = d.token_count

    # 단가표에 없는 모델(env 로 교체한 경우)은 비용을 None 으로 둔다
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


# 핵심 테스트 세트: (모델 ID, 호출 함수)
CALLS = [
    ("gpt-image-2", generate_openai),
    ("gemini-3-pro-image", generate_gemini),
    ("gemini-3.1-flash-image", generate_gemini),
]


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    results = []
    for model, fn in CALLS:
        print(f"[편집 중] {model} ...")
        try:
            res = fn(model)
            results.append(res)
            print(f"  → 저장: {res['path']}  (예상 비용 {_fmt_cost(res['est_cost_usd'])})")
        except Exception as e:  # noqa: BLE001 - 샘플이므로 모델 단위로 실패를 격리
            print(f"  [건너뜀] {model}: {e}")

    if not results:
        print("\n생성된 결과가 없습니다. .env 의 API 키 설정을 확인하세요.")
        return

    # 비교 표 출력
    print(f"\n{'model':28}{'total_tokens':>14}{'est_cost_usd':>16}")
    print("-" * 58)
    for r in results:
        print(f"{r['model']:28}{r['total_tokens']:>14}{_fmt_cost(r['est_cost_usd']):>16}")

    # 원시 결과를 JSON 으로 저장 (루트 .gitignore 가 *.json 제외 → 추적하려면 git add -f)
    usage_path = OUT_DIR / "usage.json"
    usage_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n사용량/비용 상세 저장: {usage_path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
