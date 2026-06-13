"""비교 몽타주 생성: 입력 스케치 + 프롬프트 + 세 모델 결과를 한 장으로 합친다.

generate_sample.py 실행 후의 outputs/{model}.png 와 outputs/usage.json 을 읽어
[입력 스케치 | gpt-image-2 | gemini-3-pro-image | gemini-3.1-flash-image] 한 줄과
상단 프롬프트 배너를 그려 outputs/montage.png 로 저장한다.

실행:
    uv run python src/make_montage.py
"""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = PROJECT_ROOT / "outputs"
INPUT_IMAGE = PROJECT_ROOT / "test_data" / "cat-scratch.png"
PROMPT = "A full-body cute cat based on this simple smiling cat sketch. High-resolution."

# 한글+라틴을 한 폰트로 렌더링 (tofu 방지)
NANUM = "/usr/share/fonts/truetype/nanum/NanumGothic.ttf"
NANUM_BOLD = "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf"

# 레이아웃 상수 (px)
CELL = 460        # 셀당 이미지 정사각 크기
PAD = 28          # 여백
HEADER_H = 150    # 상단 프롬프트 배너 높이
CAPTION_H = 82    # 셀 하단 캡션 높이
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
    """이미지를 box×box 흰 정사각형 안에 비율 유지하며 중앙 배치."""
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


def main() -> None:
    # usage.json 에서 모델별 비용/토큰 로드
    usage = {}
    usage_path = OUT_DIR / "usage.json"
    if usage_path.exists():
        for row in json.loads(usage_path.read_text(encoding="utf-8")):
            usage[row["model"]] = row

    def sub_for(model: str) -> str:
        u = usage.get(model)
        if not u or u.get("est_cost_usd") is None:
            return "비용 정보 없음"
        return f"${u['est_cost_usd']:.4f} · {u['total_tokens']:,} tok"

    iw, ih = Image.open(INPUT_IMAGE).size
    panels = [
        (INPUT_IMAGE, "입력 스케치 (INPUT)", f"{iw}×{ih} · sketch"),
        (OUT_DIR / "gpt-image-2.png", "gpt-image-2 (OpenAI)", sub_for("gpt-image-2")),
        (OUT_DIR / "gemini-3-pro-image.png", "gemini-3-pro-image (Pro)", sub_for("gemini-3-pro-image")),
        (OUT_DIR / "gemini-3.1-flash-image.png", "gemini-3.1-flash-image (Flash)", sub_for("gemini-3.1-flash-image")),
    ]

    n = len(panels)
    width = PAD + n * (CELL + PAD)
    height = HEADER_H + PAD + CELL + CAPTION_H + PAD
    canvas = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(canvas)

    # 상단 배너 (프롬프트)
    draw.rectangle([0, 0, width, HEADER_H], fill=(243, 243, 246))
    draw.line([0, HEADER_H, width, HEADER_H], fill=LINE, width=2)
    draw.text((PAD, 20), "lab/28 · 스케치 → 이미지 편집 비교 (image-to-image)", font=_font(30, bold=True), fill=INK)
    prompt_font = _font(24)
    for i, ln in enumerate(_wrap(draw, f'프롬프트: "{PROMPT}"', prompt_font, width - 2 * PAD)):
        draw.text((PAD, 66 + i * 32), ln, font=prompt_font, fill=(70, 70, 78))

    # 셀 (입력 + 결과 3장)
    y_img = HEADER_H + PAD
    label_font, sub_font = _font(24, bold=True), _font(20)
    for i, (path, label, sub) in enumerate(panels):
        x = PAD + i * (CELL + PAD)
        canvas.paste(_fit_square(path, CELL), (x, y_img))
        draw.rectangle([x, y_img, x + CELL, y_img + CELL], outline=LINE, width=2)
        cx = x + CELL // 2
        _centered(draw, label, label_font, cx, y_img + CELL + 12, INK)
        _centered(draw, sub, sub_font, cx, y_img + CELL + 46, SUB)

    # 입력(0번)과 결과(1~) 사이 구분선
    div_x = PAD + (CELL + PAD) - PAD // 2
    draw.line([div_x, HEADER_H + PAD // 2, div_x, height - PAD // 2], fill=(180, 180, 188), width=2)

    out = OUT_DIR / "montage.png"
    canvas.save(out)
    print(f"몽타주 저장: {out.relative_to(PROJECT_ROOT)}  ({width}×{height})")


if __name__ == "__main__":
    main()
