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
