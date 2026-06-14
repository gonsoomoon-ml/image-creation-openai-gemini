"""케이스별 비교 뫽타주 생성 (2단 레이아웃).

각 케이스의 outputs/<id>/usage.json 과 결과 png 를 읽어, 패널을 두 줄로 배치한다:
  - 윗줄: (편집이면 입력 +) OpenAI gpt-image-2 의 quality 변형들(low/medium/high)
  - 아랫줄: Gemini 모델들
상단에는 제목/프롬프트 배너, 각 패널 아래에는 비용·토큰·소요시간 캡션을 단다.

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

OPENAI_MODEL = os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-2")
# 케이스에 models 미지정 시(미실행 케이스 placeholder 용) 기본 모델 세트
DEFAULT_MODELS = [
    OPENAI_MODEL,
    os.getenv("GEMINI_PRO_IMAGE_MODEL", "gemini-3-pro-image"),
    os.getenv("GEMINI_FLASH_IMAGE_MODEL", "gemini-3.1-flash-image"),
]
QUALITY_ORDER = {"low": 0, "medium": 1, "high": 2}

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


def _provider_of(row: dict) -> str:
    return row.get("provider") or ("openai" if row["model"].startswith("gpt") else "gemini")


def _quality_of(row: dict) -> str | None:
    """결과의 quality 를 반환. 명시 필드 없으면 라벨 접미사로, 그래도 없으면 OpenAI 는 high 로 추정."""
    if row.get("quality"):
        return row["quality"]
    for q in QUALITY_ORDER:
        if row["model"].endswith(f"-{q}"):
            return q
    return "high" if _provider_of(row) == "openai" else None


def _label_of(row: dict) -> str:
    if _provider_of(row) == "openai":
        return f"{OPENAI_MODEL} ({_quality_of(row)})"
    return row["model"]


def _caption_of(row: dict) -> str:
    if row.get("est_cost_usd") is None:
        return "비용 정보 없음"
    s = f"${row['est_cost_usd']:.4f} · {row['total_tokens']:,} tok"
    if row.get("elapsed_sec") is not None:
        s += f" · {row['elapsed_sec']:.1f}s"
    return s


def build_montage(case: dict) -> None:
    cid = case["id"]
    case_dir = OUT_DIR / cid
    case_dir.mkdir(parents=True, exist_ok=True)

    # usage.json 의 각 행 = 한 결과 패널. 없으면(미실행) models 로 placeholder 행 구성.
    usage_path = case_dir / "usage.json"
    if usage_path.exists():
        rows = json.loads(usage_path.read_text(encoding="utf-8"))
    else:
        rows = [{"model": m} for m in case.get("models", DEFAULT_MODELS)]

    openai_rows = sorted(
        [r for r in rows if _provider_of(r) == "openai"],
        key=lambda r: QUALITY_ORDER.get(_quality_of(r), 9),
    )
    gemini_rows = [r for r in rows if _provider_of(r) == "gemini"]

    def panel(r: dict) -> tuple[Path, str, str]:
        return (case_dir / f"{r['model']}.png", _label_of(r), _caption_of(r))

    # 윗줄: (편집이면 입력 +) OpenAI quality 변형들 / 아랫줄: Gemini 모델들
    top: list[tuple[Path, str, str]] = []
    if case["type"] == "edit":
        img = PROJECT_ROOT / case["image"]
        iw, ih = Image.open(img).size if img.exists() else (0, 0)
        top.append((img, "입력 (INPUT)", f"{iw}×{ih} · input"))
    top += [panel(r) for r in openai_rows]
    bottom = [panel(r) for r in gemini_rows]
    grid = [r for r in (top, bottom) if r]

    max_cols = max(len(r) for r in grid)
    row_h = CELL + CAPTION_H + PAD
    width = PAD + max_cols * (CELL + PAD)
    height = HEADER_H + PAD + len(grid) * row_h
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

    # 패널들(좌측 정렬, 줄마다 차례로)
    label_font, sub_font = _font(22, bold=True), _font(19)
    y = HEADER_H + PAD
    for row_panels in grid:
        for i, (path, label, sub) in enumerate(row_panels):
            x = PAD + i * (CELL + PAD)
            canvas.paste(_fit_square(path, CELL), (x, y))
            draw.rectangle([x, y, x + CELL, y + CELL], outline=LINE, width=2)
            cx = x + CELL // 2
            _centered(draw, label, label_font, cx, y + CELL + 10, INK)
            _centered(draw, sub, sub_font, cx, y + CELL + 42, SUB)
        y += row_h

    out = case_dir / "montage.png"
    canvas.save(out)
    rows_desc = "+".join(str(len(r)) for r in grid)
    print(f"뫽타주 저장: {out.relative_to(PROJECT_ROOT)}  ({width}×{height}, 패널 {rows_desc})")


def main() -> None:
    cases = load_cases()
    wanted = [a for a in sys.argv[1:] if not a.startswith("-")]
    if wanted:
        cases = [c for c in cases if c["id"] in wanted]
    for case in cases:
        build_montage(case)


if __name__ == "__main__":
    main()
