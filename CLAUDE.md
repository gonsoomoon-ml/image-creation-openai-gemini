# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Status & layout

Design docs live in `design/` (`prd.md`, `research_models_api.md`). The lab is a `uv` project: `pyproject.toml` + `.env.example` at the root, sample code in `src/` (`generate_sample.py` — generates with all 3 models and prints usage/cost). **Read `design/prd.md` first** — it is the source of truth, written in Korean.

## Goal (from `design/prd.md`)

A side-by-side comparison of image work across the **OpenAI** and **Google Gemini** APIs:

1. **Image generation** — text-to-image with both providers.
2. **Image editing** — modify an existing image with both providers (the PRD's example: change the background color).
3. **Quality comparison** — compare the two providers' visual results.
4. **Cost comparison** — derive price from each response's reported **token usage** and compare OpenAI vs. Gemini.

Note on (4): the two APIs report usage in different shapes (OpenAI image responses carry a `usage` block; Gemini carries `usage_metadata`), and they bill on different units. Reconcile them explicitly rather than assuming parity — that reconciliation *is* the deliverable.

The maintainer (Gonsoo Moon) works in Korean — see **Writing language** below.

## Writing language

Write **Korean-friendly** content in this lab so the maintainer reads it naturally:

- **Markdown (`.md`) files**, **Python docstrings**, and **inline comments** → write in **Korean** (English technical terms inline are fine).
- Keep in **English**: code identifiers, function/variable names, model IDs (`gpt-image-2`, …), API/SDK names, dict keys, and any string literals the APIs require.
- Notebook markdown cells → Korean; code follows the rule above.

(This file, `CLAUDE.md`, stays in English — it is guidance for Claude, not lab content.)

## Environment & commands

The PRD mandates **`uv`**. `pyproject.toml` is at the lab root with the verified deps (`openai>=2.0.0`, `google-genai>=1.0.0` — the unified Gemini SDK, **not** legacy `google-generativeai` — `python-dotenv>=1.0.0`, `pillow>=11.0.0`); `requires-python = ">=3.11"`; non-package project (`[tool.uv] package = false`).

```bash
uv sync                              # create .venv and install deps
cp .env.example .env                 # then fill in OPENAI_API_KEY + GOOGLE_API_KEY
uv run python src/generate_sample.py # generate with all 3 models + print usage/cost
uv add <package>                     # add a dependency
```

If delivered as notebooks, env vars load two ways (see `../../vscode_environment_tips/README.md`): the `%env KEY=value` cell magic, or a `.env` file + `load_dotenv()`.

## API keys

Both providers need keys. Follow the repo convention: a gitignored `.env` for real values plus a committed `.env.example` template, loaded via `python-dotenv`'s `load_dotenv()`.

- `OPENAI_API_KEY`
- `GOOGLE_API_KEY` (Gemini; `google-genai` also accepts `GEMINI_API_KEY`)

## Models & APIs (verified mid-2026)

Full details, code, pricing, and benchmarks are in **`design/research_models_api.md`**.

**Core test set for this lab (3 models, decided 2026-06-13):**

| Provider | Model ID | Tier | Does |
|---|---|---|---|
| OpenAI | `gpt-image-2` | flagship | generation + editing (`client.images.generate` / `.edit`) |
| Gemini | `gemini-3-pro-image` | Pro | generation + editing (`generate_content`) |
| Gemini | `gemini-3.1-flash-image` | Flash | generation + editing (`generate_content`) |

It's 1 OpenAI + 2 Gemini tiers — a flagship-vs-Gemini-tiers comparison, giving a 3-point quality/cost curve (~$0.21 / ~$0.13 / ~$0.067 per high-res image). The two Gemini models share one code path — swap the model ID only. Editing/background-swap uses these same models: OpenAI via `client.images.edit()` (prompt, or PNG mask where `alpha=0` = edit region); Gemini by passing the source image in `contents` (prompt-only; no mask in the Developer API). `gemini-2.5-flash-image` (cheapest native) and `imagen-4.0-*` (flat per-image) are references/baselines, not in the core set.

Gotchas to respect: `gpt-image-2` rejects `input_fidelity` and can't do transparent backgrounds (use `gpt-image-1.5` for those, but it sunsets 2026-12-01); GPT-image returns base64 only (`data[0].b64_json`); all other GPT-image models are deprecated. For the cost-comparison deliverable, read OpenAI's `response.usage` (split text/image, in/out tokens) vs Gemini's `response.usage_metadata` (`prompt_token_count` / `candidates_token_count`) — different billing units, and neither returns a dollar amount, so compute cost client-side. Imagen (`imagen-4.0-*`) is flat per-image with no token usage.

## Root `.gitignore` gotchas

The repo-root `../../.gitignore` applies here and affects this lab's outputs:

- **`*.json` is ignored repo-wide** — token-usage / cost-comparison results saved as JSON will not be tracked unless you `git add -f`.
- `.env` and `.venv/` are ignored (intended).
- Image files (`*.png` / `*.jpg`) are **not** ignored, so generated images get tracked by default. Decide whether to commit sample outputs or add a local ignore for them.

## Monorepo context

This is lab 28 in the `Self-Study-Generative-AI` self-study series. Each `lab/NN_*` directory is **self-contained** — its own `pyproject.toml`, `.env`, and README. Don't reach across labs for shared code; mirror the conventions of recent siblings (`20`–`27`) instead.
