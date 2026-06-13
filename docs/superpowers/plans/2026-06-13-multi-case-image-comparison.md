# 멀티 케이스 이미지 생성/편집 비교 — 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 하드코딩된 단일 케이스를 `cases.toml` 기반 다중 케이스로 바꿔, 케이스별 폴더에 결과를 저장하고 비용·뫽타주를 비교한다.

**Architecture:** 기존 2개 스크립트 유지(`generate_sample.py`, `make_montage.py`). 루트 `cases.toml`(stdlib `tomllib`)에서 케이스 목록을 읽어 케이스×모델로 반복하고, 결과를 `outputs/<case-id>/` 에 분리 저장한다. 모듈 분리·집계 파일·테스트 스위트는 만들지 않는다.

**Tech Stack:** Python ≥3.11, `tomllib`(stdlib), `openai`, `google-genai`, `pillow`, `python-dotenv`, `uv`.

**테스트 정책:** 이 저장소는 "간단한 테스트"이고 실제 동작은 **유료** 이미지 API 호출이라, TDD 실패-테스트 단계 대신 **실행 검증**을 쓴다. 무과금 검증을 우선한다: `--list`(키 불필요), 커밋된 PNG로 뫽타주 재생성. 실제 모델 호출 검증은 사용자가 키·결제 활성화 후 직접 1회 수행.

**시작 전 (git 정책):** 현재 `main` 브랜치이고 이 저장소 정책은 "요청 시에만 커밋, 기본 브랜치면 먼저 분기"다. 실행 시작 시 먼저 브랜치를 만든다:
```bash
git checkout -b feat/multi-case-cases-toml
```

---

## 파일 구조

| 파일 | 역할 | 변경 |
|---|---|---|
| `cases.toml` | 테스트 케이스 메니페스트 | **생성** |
| `src/generate_sample.py` | 케이스 로드 → 케이스×모델 실행 → `outputs/<id>/{model}.png`+`usage.json` → 표 | **재작성** |
| `src/make_montage.py` | 케이스별 `outputs/<id>/montage.png` 렌더 | **재작성** |
| `outputs/cat-fullbody/` | 기존 고양이 결과 이전 위치 | **마이그레이션(git mv)** |
| `README.md` | 폴더/명령/뫽타주 경로/gitignore 줄 수정 | **수정** |
| `CLAUDE.md` | Layout/명령/현재 상태 갱신 | **수정** |

---

## Task 1: `cases.toml` 생성

**Files:**
- Create: `cases.toml`

- [ ] **Step 1: `cases.toml` 작성**

루트(`pyproject.toml` 옆)에 다음 내용으로 생성한다. `cat-fullbody` 는 현재 동작하는 실제 케이스이고, 두 번째는 새 이미지용 주석 처리된 예시다(프롬프트는 사용자가 채움).

```toml
# 테스트 케이스 메니페스트 (generate_sample.py / make_montage.py 가 읽음)
# 각 [[case]] = 한 작업. id 는 outputs/<id>/ 폴더 이름이 되므로 파일시스템 안전 문자만, 중복 금지.
#   type   = "edit" (입력 이미지 필요) | "generate" (텍스트만)
#   image  = 입력 이미지 경로(루트 기준). edit 필수 / generate 생략
#   models = 돌릴 모델 ID 목록(생략 시 기본 3종 전부). 비용 줄이려면 일부만.

[[case]]
id = "cat-fullbody"
type = "edit"
image = "test_data/cat-scratch.png"
prompt = "A full-body cute cat based on this simple smiling cat sketch. High-resolution."

# 새 이미지 케이스 예시 — 프롬프트를 실제 값으로 채우고 주석을 해제하세요.
# [[case]]
# id = "woman-book-edit"
# type = "edit"
# image = "test_data/woman-masking-book.jpg"
# prompt = "<여기에 편집 프롬프트>"
# models = ["gemini-3.1-flash-image"]   # 예: 비용 줄이려고 한 모델만
```

- [ ] **Step 2: TOML 파싱 확인 (무과금)**

Run: `uv run python -c "import tomllib,pathlib; d=tomllib.loads(pathlib.Path('cases.toml').read_text()); print([c['id'] for c in d['case']])"`
Expected: `['cat-fullbody']` (주석 처리된 예시는 파싱되지 않음)

- [ ] **Step 3: Commit**

```bash
git add cases.toml
git commit -m "feat: add cases.toml test-case manifest"
```

---

## Task 2: 기존 고양이 결과 마이그레이션 (재과금 없음)

**Files:**
- Move: `outputs/{gpt-image-2,gemini-3-pro-image,gemini-3.1-flash-image,montage}.png`, `outputs/usage.json` → `outputs/cat-fullbody/`

- [ ] **Step 1: 케이스 폴더로 git mv**

```bash
mkdir -p outputs/cat-fullbody
git mv outputs/gpt-image-2.png outputs/gemini-3-pro-image.png \
       outputs/gemini-3.1-flash-image.png outputs/montage.png \
       outputs/usage.json outputs/cat-fullbody/
```

- [ ] **Step 2: 결과 확인**

Run: `ls outputs/cat-fullbody/`
Expected: `gemini-3-pro-image.png  gemini-3.1-flash-image.png  gpt-image-2.png  montage.png  usage.json`

Run: `ls outputs/`
Expected: `cat-fullbody` 만 (최상위에 떠도는 png/json 없음)

- [ ] **Step 3: usage.json 의 path 갱신**

`outputs/cat-fullbody/usage.json` 의 `"path"` 값 3개를 새 위치로 바꾼다(뫽타주는 path 를 쓰지 않지만 정합성 유지).

`outputs/gpt-image-2.png` → `outputs/cat-fullbody/gpt-image-2.png`
`outputs/gemini-3-pro-image.png` → `outputs/cat-fullbody/gemini-3-pro-image.png`
`outputs/gemini-3.1-flash-image.png` → `outputs/cat-fullbody/gemini-3.1-flash-image.png`

Run: `uv run python -c "import json; d=json.load(open('outputs/cat-fullbody/usage.json')); print([r['path'] for r in d])"`
Expected: 세 경로 모두 `outputs/cat-fullbody/...` 로 시작

- [ ] **Step 4: Commit**

```bash
git add -A outputs/
git commit -m "chore: migrate cat outputs into outputs/cat-fullbody/"
```

---

## Task 3: `src/generate_sample.py` 재작성 (케이스 구동)

**Files:**
- Modify(전체 교체): `src/generate_sample.py`

- [ ] **Step 1: 파일 전체를 아래 내용으로 교체**

```python
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


def generate_openai(model: str, prompt: str, image_path: Path | None, out_dir: Path) -> dict:
    """OpenAI 이미지. image_path 있으면 편집(images.edit), 없으면 생성(images.generate). 응답은 base64."""
    client = OpenAI(api_key=_get_key("OPENAI_API_KEY"))
    if image_path is not None:
        buf = BytesIO()
        _load_input_rgb(image_path).save(buf, format="png")
        buf.name = "input.png"   # SDK 가 파일명/MIME 추론하도록
        buf.seek(0)
        resp = client.images.edit(
            model=model, image=buf, prompt=prompt,
            size="1024x1024",   # gpt-image-2: 1024x1024 / 1536x1024 / 1024x1536 / auto
            quality="high",     # low | medium | high | auto
            # 주의: gpt-image-2 에는 input_fidelity 를 쓰지 말 것
        )
    else:
        resp = client.images.generate(
            model=model, prompt=prompt, size="1024x1024", quality="high",
        )
    out_path = out_dir / f"{model}.png"
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
        "model": model,
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
            res = fn(model, case["prompt"], image_path, out_dir)
            results.append(res)
            print(f"    → {res['path']}  (예상 비용 {_fmt_cost(res['est_cost_usd'])})")
        except Exception as e:  # noqa: BLE001 - 샘플이므로 셀 단위 실패 격리
            print(f"    [건너뜀] {model}: {e}")

    if results:
        (out_dir / "usage.json").write_text(
            json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    return results


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
    rows: list[tuple[str, dict]] = []
    for case in cases:
        print(f"[케이스] {case['id']}")
        rows.extend((case["id"], r) for r in _run_case(case))

    if not rows:
        print("\n생성된 결과가 없습니다. .env 의 API 키/케이스 설정을 확인하세요.")
        return

    print(f"\n{'case':20}{'model':28}{'total_tokens':>14}{'est_cost_usd':>16}")
    print("-" * 78)
    for cid, r in rows:
        print(f"{cid:20}{r['model']:28}{r['total_tokens']:>14}{_fmt_cost(r['est_cost_usd']):>16}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: `--list` 무과금 검증**

Run: `uv run python src/generate_sample.py --list`
Expected: `사용 가능한 케이스:` 와 `- cat-fullbody         [edit    ] 모델 3종`

- [ ] **Step 3: 알 수 없는 케이스 처리 확인**

Run: `uv run python src/generate_sample.py nope`
Expected: `알 수 없는 케이스: nope (사용 가능: ['cat-fullbody'])`

- [ ] **Step 4: (선택, 유료) 실제 호출 1셀 검증**

`.env` 에 키가 있고 결제가 활성화된 경우에만. 비용 최소화를 위해 한 케이스만:
Run: `uv run python src/generate_sample.py cat-fullbody`
Expected: `outputs/cat-fullbody/{model}.png` 갱신, 마지막에 case/model/토큰/비용 표 출력. 키 없으면 각 셀이 `[건너뜀]` 로 격리됨(크래시 없음).

- [ ] **Step 5: Commit**

```bash
git add src/generate_sample.py
git commit -m "feat: drive generate_sample.py from cases.toml (per-case outputs, --list, generate+edit)"
```

---

## Task 4: `src/make_montage.py` 재작성 (케이스별 뫽타주)

**Files:**
- Modify(전체 교체): `src/make_montage.py`

- [ ] **Step 1: 파일 전체를 아래 내용으로 교체**

```python
"""케이스별 비교 뫽타주 생성.

cases.toml 의 각 케이스에 대해 outputs/<id>/{model}.png 와 outputs/<id>/usage.json 을 읽어
[입력(편집 시) | 모델별 결과] 한 줄과 상단 프롬프트 배너를 그려 outputs/<id>/montage.png 로 저장.

실행:
    uv run python src/make_montage.py              # 모든 케이스
    uv run python src/make_montage.py cat-fullbody # 한 케이스만
"""
from __future__ import annotations

import json
import os
import sys
import tomllib
from pathlib import Path

from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = PROJECT_ROOT / "outputs"
CASES_FILE = PROJECT_ROOT / "cases.toml"
load_dotenv(PROJECT_ROOT / ".env")

# generate_sample.py 와 동일한 기본 모델 세트(케이스에 models 미지정 시 열로 표시)
DEFAULT_MODELS = [
    os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-2"),
    os.getenv("GEMINI_PRO_IMAGE_MODEL", "gemini-3-pro-image"),
    os.getenv("GEMINI_FLASH_IMAGE_MODEL", "gemini-3.1-flash-image"),
]

# 한글+라틴을 한 폰트로 렌더링 (tofu 방지)
NANUM = "/usr/share/fonts/truetype/nanum/NanumGothic.ttf"
NANUM_BOLD = "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf"

# 레이아웃 상수 (px)
CELL = 460
PAD = 28
HEADER_H = 150
CAPTION_H = 82
INK = (30, 30, 34)
SUB = (110, 110, 120)
LINE = (205, 205, 212)


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(NANUM_BOLD if bold else NANUM, size)
    except OSError:
        return ImageFont.load_default(size=size)


def _wrap(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_w: int) -> list[str]:
    """폰트 폭을 측정해 단어 단위로 줄바꿈."""
    lines, cur = [], ""
    for word in text.split():
        test = f"{cur} {word}".strip()
        if draw.textlength(test, font=font) <= max_w:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def _fit_square(path: Path, box: int) -> Image.Image:
    """이미지를 box×box 흰 정사각형 안에 비율 유지하며 중앙 배치. 없으면 'no output'."""
    canvas = Image.new("RGB", (box, box), "white")
    if not path.exists():
        d = ImageDraw.Draw(canvas)
        d.text((box // 2, box // 2), "no output", font=_font(24), fill=SUB, anchor="mm")
        return canvas
    im = Image.open(path).convert("RGB")
    im.thumbnail((box, box), Image.LANCZOS)
    canvas.paste(im, ((box - im.width) // 2, (box - im.height) // 2))
    return canvas


def _centered(draw, text, font, cx, y, fill):
    draw.text((cx - draw.textlength(text, font=font) / 2, y), text, font=font, fill=fill)


def load_cases() -> list[dict]:
    return tomllib.loads(CASES_FILE.read_text(encoding="utf-8")).get("case", [])


def build_montage(case: dict) -> None:
    cid = case["id"]
    case_dir = OUT_DIR / cid
    case_dir.mkdir(parents=True, exist_ok=True)
    models = case.get("models", DEFAULT_MODELS)

    # usage.json(있으면) 로드 → 모델별 비용/토큰 캡션
    usage = {}
    usage_path = case_dir / "usage.json"
    if usage_path.exists():
        for row in json.loads(usage_path.read_text(encoding="utf-8")):
            usage[row["model"]] = row

    def sub_for(model: str) -> str:
        u = usage.get(model)
        if not u or u.get("est_cost_usd") is None:
            return "비용 정보 없음"
        return f"${u['est_cost_usd']:.4f} · {u['total_tokens']:,} tok"

    # 패널: 편집이면 입력 1장 + 모델들, 생성이면 모델들만
    panels = []
    if case["type"] == "edit":
        img = PROJECT_ROOT / case["image"]
        iw, ih = Image.open(img).size if img.exists() else (0, 0)
        panels.append((img, "입력 (INPUT)", f"{iw}×{ih} · input"))
    for m in models:
        panels.append((case_dir / f"{m}.png", m, sub_for(m)))

    n = len(panels)
    width = PAD + n * (CELL + PAD)
    height = HEADER_H + PAD + CELL + CAPTION_H + PAD
    canvas = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(canvas)

    # 상단 배너 (제목 + 프롬프트)
    draw.rectangle([0, 0, width, HEADER_H], fill=(243, 243, 246))
    draw.line([0, HEADER_H, width, HEADER_H], fill=LINE, width=2)
    kind = "image-to-image" if case["type"] == "edit" else "text-to-image"
    draw.text((PAD, 20), f"{cid} · {case['type']} ({kind})", font=_font(30, bold=True), fill=INK)
    prompt_font = _font(24)
    for i, ln in enumerate(_wrap(draw, f'프롬프트: "{case["prompt"]}"', prompt_font, width - 2 * PAD)):
        draw.text((PAD, 66 + i * 32), ln, font=prompt_font, fill=(70, 70, 78))

    # 셀
    y_img = HEADER_H + PAD
    label_font, sub_font = _font(24, bold=True), _font(20)
    for i, (path, label, sub) in enumerate(panels):
        x = PAD + i * (CELL + PAD)
        canvas.paste(_fit_square(path, CELL), (x, y_img))
        draw.rectangle([x, y_img, x + CELL, y_img + CELL], outline=LINE, width=2)
        cx = x + CELL // 2
        _centered(draw, label, label_font, cx, y_img + CELL + 12, INK)
        _centered(draw, sub, sub_font, cx, y_img + CELL + 46, SUB)

    # 편집 케이스만 입력(0번)과 결과 사이 구분선
    if case["type"] == "edit":
        div_x = PAD + (CELL + PAD) - PAD // 2
        draw.line([div_x, HEADER_H + PAD // 2, div_x, height - PAD // 2], fill=(180, 180, 188), width=2)

    out = case_dir / "montage.png"
    canvas.save(out)
    print(f"뫽타주 저장: {out.relative_to(PROJECT_ROOT)}  ({width}×{height})")


def main() -> None:
    cases = load_cases()
    wanted = [a for a in sys.argv[1:] if not a.startswith("-")]
    if wanted:
        cases = [c for c in cases if c["id"] in wanted]
    for case in cases:
        build_montage(case)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 무과금 end-to-end 검증 (마이그레이션된 커밋 PNG 사용)**

Run: `uv run python src/make_montage.py cat-fullbody`
Expected: `뫽타주 저장: outputs/cat-fullbody/montage.png  (1980×748)` (4패널: 입력+3모델). 캡션에 `$0.2139`, `$0.1350`, `$0.0673` 비용이 보임.

- [ ] **Step 3: 생성된 뫽타주 육안 확인**

Read(이미지 보기): `outputs/cat-fullbody/montage.png`
Expected: 왼쪽에 입력 스케치, 구분선, 그 뒤 3개 모델 결과 + 비용 캡션. 배너에 프롬프트.

- [ ] **Step 4: Commit**

```bash
git add src/make_montage.py outputs/cat-fullbody/montage.png
git commit -m "feat: per-case montage driven by cases.toml (handles edit/generate, not-yet-run)"
```

---

## Task 5: 문서 갱신 (README.md, CLAUDE.md)

**Files:**
- Modify: `README.md`
- Modify: `CLAUDE.md`

- [ ] **Step 1: README — 빠른 시작 블록 교체**

기존(33–38행 부근):
```bash
uv sync                               # 의존성 설치
cp .env.example .env                  # OPENAI_API_KEY, GOOGLE_API_KEY 입력
uv run python src/generate_sample.py  # 3개 모델로 편집 + 비용 표 출력
uv run python src/make_montage.py     # 위 비교 몽타주(outputs/montage.png) 생성
```
교체:
```bash
uv sync                                       # 의존성 설치
cp .env.example .env                          # OPENAI_API_KEY, GOOGLE_API_KEY 입력
uv run python src/generate_sample.py --list   # 케이스 목록 (API 호출 없음)
uv run python src/generate_sample.py          # 모든 케이스 × 3개 모델 + 비용 표
uv run python src/generate_sample.py cat-fullbody  # 한 케이스만 (비용 절약)
uv run python src/make_montage.py             # 케이스별 비교 뫽타주 생성
```

- [ ] **Step 2: README — 입력/프롬프트 안내 문장 교체**

기존(40행 부근): `입력 이미지·프롬프트는 \`src/generate_sample.py\` 상단의 \`INPUT_IMAGE\`, \`PROMPT\`에서 바꿉니다.`
교체: `테스트 케이스(입력 이미지·프롬프트·모델)는 루트 \`cases.toml\` 에서 추가/수정합니다. \`id\` 가 \`outputs/<id>/\` 폴더 이름이 됩니다.`

- [ ] **Step 3: README — 뫽타주 임베드 경로 수정**

기존(19행): `![입력 스케치 + 프롬프트 + 세 모델 결과 비교 몽타주](outputs/montage.png)`
교체: `![고양이 케이스 비교 몽타주](outputs/cat-fullbody/montage.png)`

- [ ] **Step 4: README — 폴더 구조 블록 교체**

기존(101–112행 부근)을 아래로 교체:
```
.
├── cases.toml                 # 테스트 케이스 메니페스트 (id/type/image/prompt/models)
├── src/
│   ├── generate_sample.py     # 케이스 로드 → 케이스×모델 실행 + 토큰→비용 계산
│   └── make_montage.py        # 케이스별 비교 뫽타주 생성
├── test_data/                 # 입력 이미지들 (cat-scratch.png, woman-masking-book.jpg …)
├── outputs/
│   └── <case-id>/             # 케이스별 결과 png + usage.json + montage.png (실행 시 생성)
├── design/                    # PRD + 모델/가격 리서치 + specs/plans
├── .env.example               # API 키 + 모델 ID 템플릿
└── pyproject.toml
```

- [ ] **Step 5: README — 잘못된 gitignore 줄 수정**

기존(114행 부근): `> \`outputs/usage.json\`은 루트 \`.gitignore\`의 \`*.json\` 규칙 때문에 git 추적에서 제외됩니다 (추적하려면 \`git add -f\`). 결과 \`*.png\`는 추적됩니다.`
교체: `> 결과 \`*.png\` 와 \`outputs/<case-id>/usage.json\` 은 git 에 추적됩니다 (README 가 뫽타주를 임베드). 이 저장소 \`.gitignore\` 에는 \`*.json\` 규칙이 없습니다.`

- [ ] **Step 6: CLAUDE.md — Layout 블록 교체**

`## Layout` 의 코드 블록을 아래로 교체:
```
cases.toml             # 테스트 케이스 메니페스트 (tomllib 로 로드)
src/
  generate_sample.py   # cases.toml 구동: 케이스×모델 generate/edit + token→cost
  make_montage.py      # 케이스별 montage (input + N model results → 1 png)
test_data/             # 입력 이미지들 (cat-scratch.png, woman-masking-book.jpg)
outputs/<case-id>/     # per-case: {model}.png + usage.json + montage.png (created on run; committed)
design/                # prd.md (source of truth) + research_models_api.md + superpowers specs/plans
README.md              # beginner-friendly cost-calculation walkthrough (Korean)
.env.example           # API keys + model-ID template
pyproject.toml         # uv project (package = false)
```

- [ ] **Step 7: CLAUDE.md — 명령 블록 갱신**

`## Environment & commands` 의 실행 예시를 아래로 교체:
```bash
uv sync                                            # create .venv and install deps
cp .env.example .env                               # then fill in OPENAI_API_KEY + GOOGLE_API_KEY
uv run python src/generate_sample.py --list        # list cases (no API calls)
uv run python src/generate_sample.py               # run ALL cases × models + cost table
uv run python src/generate_sample.py <case-id>     # run a single case (saves money)
uv run python src/make_montage.py                  # build per-case outputs/<id>/montage.png
uv add <package>                                   # add a dependency
```

- [ ] **Step 8: CLAUDE.md — 현재 상태 문장 갱신**

`## Goal` 섹션의 `Current state:` 문장을 교체:
기존: `Current state: \`generate_sample.py\` runs the **edit** path (image input). Switching to plain generation = drop the input image (\`client.images.generate\` / \`generate_content\` with text only).`
교체: `Current state: cases are defined in \`cases.toml\` (\`type = "edit" | "generate"\`); \`generate_sample.py\` runs every case × its models. **edit** sends the input image; **generate** is text-only (no image). Outputs are isolated per case under \`outputs/<case-id>/\`.`

- [ ] **Step 9: 문서 정합성 확인**

Run: `grep -rn "outputs/montage.png\|INPUT_IMAGE\|루트 .gitignore" README.md CLAUDE.md`
Expected: 출력 없음(옛 경로/상수/문구가 모두 갱신됨).

- [ ] **Step 10: Commit**

```bash
git add README.md CLAUDE.md
git commit -m "docs: update README + CLAUDE.md for cases.toml / per-case outputs; fix stale gitignore note"
```

---

## Self-Review (작성자 점검 결과)

**1. 스펙 커버리지:** cases.toml(Task 1) · 출력 폴더 분리(Task 3 `_run_case`) · 2파일 유지(Task 3·4) · generate+edit(Task 3 제공자 분기) · 단일 케이스 실행/--list(Task 3 main) · 마이그레이션(Task 2) · 뫽타주 edit/generate/no-output(Task 4) · 문서+gitignore 수정(Task 5) · 범위 밖 항목 미포함 → 스펙 전 항목 매핑됨.

**2. 플레이스홀더 스캔:** 코드 단계는 전부 완전한 내용. `cases.toml` 의 `<여기에 편집 프롬프트>` 는 의도된 주석 예시(실행 안 됨). 계획 자체엔 TBD/TODO 없음.

**3. 타입/이름 일관성:** `load_cases()`/`DEFAULT_MODELS`/`MODEL_PROVIDER`/`PROVIDERS`/`_run_case`/`build_montage` 가 두 파일에서 일관. 제공자 시그니처 `(model, prompt, image_path|None, out_dir)` 가 호출부와 일치. usage 딕셔너리 키(`model`,`total_tokens`,`est_cost_usd`)가 생성·뫽타주에서 동일.

**검증 가능성:** Task 1·3·4 는 무과금 검증 단계 포함(파싱, --list, 커밋 PNG 로 뫽타주 재생성). 유료 경로는 Task 3 Step 4 로 선택·격리.
