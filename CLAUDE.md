# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

Standalone study repo: **OpenAI vs Google Gemini image generation/editing + token-based cost comparison**. Working and verified end-to-end (2026-06-13). Extracted from the `Self-Study-Generative-AI` monorepo (originally `lab/28`); public repo: https://github.com/gonsoomoon-ml/image-creation-openai-gemini

The maintainer (Gonsoo Moon) works in Korean — see **Writing language** below.

## Layout

```
src/
  generate_sample.py   # 3-model image EDIT (image-to-image) + token→cost
  make_montage.py      # comparison montage (input sketch + prompt + 3 results → 1 png)
test_data/cat-scratch.png   # input sketch
outputs/                # results + montage.png + usage.json (created on run; *.png committed)
design/                 # prd.md (source of truth, Korean) + research_models_api.md (model/pricing research)
README.md               # beginner-friendly cost-calculation walkthrough (Korean)
.env.example            # API keys + model-ID template
pyproject.toml          # uv project (package = false)
```

**Read `design/prd.md` first** — it is the source of truth (Korean).

## Goal (from `design/prd.md`)

Compare image work across the **OpenAI** and **Google Gemini** APIs:

1. **Image generation** — text-to-image.
2. **Image editing** — image-to-image (current test: a cat sketch → full-body cat).
3. **Quality comparison** — compare the providers' visual results.
4. **Cost comparison** — derive price from each response's reported **token usage**.

Note on (4): the two APIs report usage in different shapes (OpenAI → `usage`; Gemini → `usage_metadata`) and bill on different units. Reconciling them is *the* deliverable. Neither API returns a dollar amount — cost is computed client-side from tokens × rates. `src/generate_sample.py` does this.

Current state: `generate_sample.py` runs the **edit** path (image input). Switching to plain generation = drop the input image (`client.images.generate` / `generate_content` with text only).

## Writing language

Write **Korean-friendly** content so the maintainer reads it naturally:

- **Markdown (`.md`) files**, **Python docstrings**, and **inline comments** → **Korean** (English technical terms inline are fine).
- Keep in **English**: code identifiers, model IDs (`gpt-image-2`, …), API/SDK names, dict keys, and required string literals.
- Rasterized image labels: prefer Korean too, but only with a CJK-capable font (`make_montage.py` uses NanumGothic) — DejaVu renders Hangul as tofu.

(This file, `CLAUDE.md`, stays in English — guidance for Claude, not project content.)

## Environment & commands

Uses **`uv`**. Deps (verified mid-2026): `openai>=2.0.0`, `google-genai>=1.0.0` (the unified Gemini SDK — **not** legacy `google-generativeai`), `python-dotenv>=1.0.0`, `pillow>=11.0.0`. `requires-python = ">=3.11"`; non-package project (`[tool.uv] package = false`).

```bash
uv sync                              # create .venv and install deps
cp .env.example .env                 # then fill in OPENAI_API_KEY + GOOGLE_API_KEY
uv run python src/generate_sample.py # edit with all 3 models + print usage/cost → outputs/
uv run python src/make_montage.py    # build outputs/montage.png
uv add <package>                     # add a dependency
```

## `.env` (keys + model IDs)

Gitignored `.env` for real values; committed `.env.example` template; loaded via `python-dotenv`. Keys:

- `OPENAI_API_KEY`
- `GOOGLE_API_KEY` (Gemini; `google-genai` also accepts `GEMINI_API_KEY`)

Model IDs are also read from `.env` (defaults = the core set if unset):
`OPENAI_IMAGE_MODEL`, `GEMINI_PRO_IMAGE_MODEL`, `GEMINI_FLASH_IMAGE_MODEL`.

> ⚠️ Gemini image models have **no free tier** — billing (paid tier) must be enabled or calls fail `429 RESOURCE_EXHAUSTED` (`limit: 0`).

## Models & APIs (verified 2026-06-13)

Full details, code, pricing, benchmarks: **`design/research_models_api.md`**.

**Core test set (3 models):**

| Provider | Model ID | Tier | Per-1M-token rates (verified) |
|---|---|---|---|
| OpenAI | `gpt-image-2` | flagship | text-in \$5 · image-in \$8 · image-out \$30 (no separate text-out) |
| Gemini | `gemini-3-pro-image` | Pro | input \$2 · image-out \$120 |
| Gemini | `gemini-3.1-flash-image` | Flash | input \$0.5 · image-out \$60 |

Prices re-verified against official pages (2026-06-13). Real edit-run costs: `gpt-image-2` $0.2139, `gemini-3-pro-image` $0.1350, `gemini-3.1-flash-image` $0.0673.

**Cost computation gotchas (already handled in code):**
- OpenAI: read `response.usage` — split via `input_tokens_details` / `output_tokens_details` (access with `getattr`, schema not guaranteed).
- Gemini: read `response.usage_metadata` — use the **IMAGE-modality** entry of `candidates_tokens_details` (~1,120 tok for a 1K image), *not* the full `candidates_token_count` (which includes text + thinking tokens on Pro).
- `gpt-image-2` rejects `input_fidelity` and can't do transparent backgrounds; GPT-image returns base64 only (`data[0].b64_json`); all other GPT-image models are deprecated. Editing input that is RGBA should be flattened to RGB-on-white first (avoid alpha being read as an edit mask) — `_load_input_rgb()` does this.

## `.gitignore` / outputs

This repo's own `.gitignore` excludes `.env`, `.venv/`, `__pycache__/`, `.claude/`. Generated `outputs/*.png` and `outputs/usage.json` **are** tracked (README embeds `outputs/montage.png`). The real-key `.env` is intentionally never committed.
