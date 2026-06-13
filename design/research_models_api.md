# lab/28 리서치 리포트: OpenAI vs Gemini 이미지 생성/편집 (2026년 중반 기준)

> 2026-06-13 작성. 6개 리서치 영역에 대한 실시간 웹 조사 + 공식 문서 대조 검증(adversarial verification) 결과를 종합했습니다. 검증 단계에서 1차 조사 결과가 수정된 경우 수정된 값을 사용했습니다. 끝까지 **불확실(uncertain)**로 남은 항목은 본문에 표시했습니다. 모델 ID와 가격은 빠르게 바뀌므로, 고정(pin)하기 전에 링크된 공식 페이지에서 다시 확인하세요.

## 1. TL;DR

- **OpenAI** 이미지 작업은 **GPT Image** 제품군이며 **토큰 단위** 과금(텍스트 입력 / 이미지 입력 / 이미지 출력)입니다. 장기적으로 쓸 수 있는 선택지는 **`gpt-image-2`**(GA, 기본값, 2026-04-21 출시) 하나뿐입니다. 나머지 GPT-image 모델(`gpt-image-1.5`, `gpt-image-1-mini`, `gpt-image-1`, `chatgpt-image-latest`)은 모두 **지원 종료(deprecated)** 상태입니다 — `gpt-image-1`은 **2026-10-23**, 나머지는 **2026-12-01**에 종료됩니다. DALL·E 2/3는 **2026-05-12**에 폐기되었습니다.
- **Gemini**는 통합 `google-genai` SDK를 통해 두 제품군을 제공합니다: `generate_content`로 **생성과 편집을 모두** 처리하는 네이티브 **"Nano Banana"** 모델(`gemini-3-pro-image`, `gemini-3.1-flash-image`, `gemini-2.5-flash-image`), 그리고 `generate_images`로 호출하는 **Imagen 4** 디퓨전 모델(생성 전용). Nano Banana의 `-preview` ID는 **2026-06-25**에 종료되므로 GA(비-preview) ID를 사용하세요.
- **이 lab에 권장하는 모델 ID:**
  - **생성:** OpenAI `gpt-image-2` vs Gemini `gemini-3-pro-image`(최고 품질) 또는 `gemini-2.5-flash-image`(가장 저렴, 토큰 스토리가 가장 깔끔).
  - **편집 / 배경 변경:** OpenAI `gpt-image-2`(투명 컷아웃이나 명시적 fidelity 제어가 필요하면 `gpt-image-1.5`) vs 입력 이미지를 전달한 동일 Gemini Nano Banana 모델.
- **품질은 작업별로 갈립니다.** 생성: GPT Image 2가 이미지 내 텍스트 렌더링 / 레이아웃 / 프롬프트 충실도에서 앞섭니다; Gemini는 사실감(photorealism)과 속도에서 우세합니다. 편집: 최상위권은 거의 동률이며(Artificial Analysis 기준 GPT Image가 근소하게 앞섬), 대화형/반복 편집과 정체성(identity) 일관성에서는 Gemini가 선호됩니다.
- **비용/사용량 정합(reconciliation)이 이 lab의 핵심 산출물입니다.** OpenAI는 토큰 분해 정보가 담긴 `usage` 객체(텍스트/이미지, 입력/출력)를 반환하고, Gemini는 `usage_metadata`(prompt/candidates 토큰 수)를 반환합니다. Imagen은 토큰 사용량이 없는 이미지당 정액제입니다. 두 제공자 모두 이제 출처 신호(provenance)를 삽입합니다(Gemini: SynthID 상시 적용; OpenAI: 2026-05-19부터 API 이미지에 SynthID + C2PA).

---

## 2. OpenAI

### 모델

| Name | Model ID | Status | Notes |
|---|---|---|---|
| GPT Image 2 | `gpt-image-2` | **GA (default/recommended)** | Flagship, released 2026-04-21. Reasoning step, strong photorealism + text rendering, image-to-image. Always processes inputs at high fidelity (you **cannot** set `input_fidelity`). **Does NOT support `background="transparent"`**. |
| GPT Image 1.5 | `gpt-image-1.5` | **Deprecated** (announced 2026-06-02, shutdown **2026-12-01**) | Still callable. Supports `input_fidelity` (high/low) and **transparent background**. Use only when you need those features. |
| GPT Image 1 Mini | `gpt-image-1-mini` | **Deprecated** (shutdown 2026-12-01) | Cheapest GPT-image model. No `input_fidelity`. |
| GPT Image 1 | `gpt-image-1` | **Deprecated** (shutdown **2026-10-23**) | First GPT-image model. Migrate to `gpt-image-2`. |
| ChatGPT Image (alias) | `chatgpt-image-latest` | **Deprecated** (shutdown 2026-12-01) | Rolling alias; do not pin for a lab. |
| DALL·E 3 / DALL·E 2 | `dall-e-3` / `dall-e-2` | **Retired 2026-05-12** | Do not build on these. *(Uncertain at the doc level: the live generate/edit reference enums still list them despite the past shutdown date — treat as unavailable regardless.)* |

> **검증 수정 적용:** 1차 조사 결과는 `gpt-image-1.5`, `gpt-image-1-mini`, `chatgpt-image-latest`를 "GA"로 표기했습니다. 공식 deprecations 페이지(2026-06-02 공지)에 따르면 이들은 모두 **2026-12-01 종료 예정으로 지원 종료(deprecated)** 상태입니다. lab의 수명을 위해 **`gpt-image-2`**로 표준화하세요.

> **스냅샷 주의(불확실):** 스냅샷 문자열 `gpt-image-2-2026-04-21`은 한 영역에서는 모델 페이지에 나타났지만, 다른 영역의 공식 changelog에서는 **확인되지 않았습니다**. 출시 **날짜**(2026-04-21)와 기본 ID `gpt-image-2`는 확인되었습니다.

### 생성 API + 코드

GPT-image 모델은 **항상 `data[].b64_json`에 base64를 반환**합니다(`response_format`/`url` 없음; 그건 DALL·E 전용이었습니다).

```python
import base64
from openai import OpenAI

client = OpenAI()  # reads OPENAI_API_KEY

gen = client.images.generate(
    model="gpt-image-2",
    prompt="A studio product photo of a ceramic coffee mug on a plain white "
           "seamless background, soft daylight, photorealistic.",
    size="1024x1024",        # also 1536x1024 / 1024x1536 / auto / custom WxH
    quality="high",          # low | medium | high | auto
    n=1,
    output_format="png",     # png | jpeg | webp
    background="opaque",     # gpt-image-2: opaque | auto only (NO transparent)
)
with open("mug.png", "wb") as f:
    f.write(base64.b64decode(gen.data[0].b64_json))
print("usage:", gen.usage)
```

커스텀 `WxH` 크기 제약: 양쪽 변이 16으로 나누어떨어져야 하고, 종횡비 1:3–3:1, 최대 변 **3840 px**(4096 아님), 총 픽셀 655,360–8,294,400. 에이전트형 플로우를 위한 Responses API 경로(`tools=[{"type":"image_generation"}]`, gpt-5 이상이 오케스트레이션)도 있지만, 키만 사용하는 lab 노트북에서는 범위를 벗어납니다.

### 편집 API + 코드

`client.images.edit()`가 전용 편집 엔드포인트입니다. 최대 **16개**의 입력 이미지, 선택적 **PNG 마스크**(완전 투명한 `alpha=0` 픽셀 = 재생성할 영역 — 직관과 반대), 그리고 (`gpt-image-1.5`/`1`/mini의 경우) `input_fidelity`를 받습니다.

```python
import base64
from openai import OpenAI
client = OpenAI()

edit = client.images.edit(
    model="gpt-image-2",
    image=open("mug.png", "rb"),
    prompt="Replace the white background with a solid pastel-blue background. "
           "Keep the mug, its shape, colors and reflections exactly the same.",
    size="1024x1024",
    quality="high",
    # mask=open("bg_mask.png", "rb"),  # optional: PNG, alpha=0 = edit region, SAME dims as image, <4MB
    # NOTE: do NOT pass input_fidelity with gpt-image-2 — the API rejects it.
)
with open("mug_blue_bg.png", "wb") as f:
    f.write(base64.b64decode(edit.data[0].b64_json))
print("edit usage:", edit.usage)
```

> **검증 수정 적용:** 1차 조사 결과의 편집 예제는 `gpt-image-2`에 `input_fidelity="high"`를 전달했습니다. 이는 **유효하지 않습니다** — `gpt-image-2`에서는 `input_fidelity`를 **생략**해야 합니다(항상 high-fidelity로 동작). `input_fidelity`(high/low)는 `gpt-image-1.5` / `gpt-image-1` / `gpt-image-1-mini`에서만 유효합니다. `model`을 생략하면 편집 엔드포인트는 **`gpt-image-1.5`를 기본값**으로 사용하므로, 항상 `model`을 명시적으로 전달하세요.

### 가격 (100만 토큰당, standard tier)

| Model | Text in | Image in | Cached image in | Image out | Text out |
|---|---|---|---|---|---|
| `gpt-image-2` | $5.00 | $8.00 | $2.00 | $30.00 | — (no separate text-out rate) |
| `gpt-image-1.5` | $5.00 | $8.00 | $2.00 | $32.00 | **$10.00** |
| `gpt-image-1` | $5.00 | $10.00 | $2.50 | $40.00 | — |
| `gpt-image-1-mini` | $2.00 (cached $0.20) | $2.50 (cached $0.25) | — | $8.00 | — |

Batch API는 약 50% 할인. `gpt-image-2`의 1024×1024 이미지당 추정치: **low ~$0.006, medium ~$0.053, high ~$0.211**(세로/가로는 *더 저렴*: high ~$0.165). gpt-image-2에서는 1024×1024가 가장 비싼 종횡비입니다.

> **검증 수정 적용:** 한 1차 조사 결과는 gpt-image-2 high 1024²를 ~$0.28로 주장했지만 이는 과대평가이며, 토큰 기반 수치는 **~$0.211**입니다.

### 사용량 리포팅

모든 생성/편집 응답에는 `usage` 객체가 담깁니다(`"For the GPT image models only."`):

```json
{ "usage": {
    "total_tokens": 1597,
    "input_tokens": 29,
    "output_tokens": 1568,
    "input_tokens_details": { "text_tokens": 29, "image_tokens": 0 }
    /* output_tokens_details {image_tokens, text_tokens} appears for newer
       models but is NOT in the formal images-object schema — access with getattr() */
}}
```

Python: dict 키가 아니라 속성으로 접근합니다(`gen.usage.input_tokens`, `gen.usage.input_tokens_details.image_tokens`, …). **편집**의 경우 `input_tokens_details.image_tokens`가 소스 이미지 비용을 담습니다.

> **중요한 비용 공식 수정(검증):** *모든* 출력 토큰에 이미지 출력 단가를 곱하지 **마세요**. `gpt-image-1.5`(및 `gpt-image-2`)는 이미지 출력 토큰 외에 **추론(reasoning) 텍스트 출력 토큰**을 방출하며, 이를 **끄는 문서화된 방법은 없습니다**. `gpt-image-1.5`의 경우 이 텍스트 토큰은 $32/1M 이미지 출력 단가가 아니라 **$10/1M 텍스트 출력 단가**로 과금됩니다. `output_tokens_details`로 출력을 분리하세요:
>
> `cost = (text_in×text_in_rate + image_in×image_in_rate + image_out×image_out_rate + text_out×text_out_rate) / 1e6`
>
> `gpt-image-2`는 가격 페이지에 별도의 텍스트 출력 단가가 없으므로, 그 모델에 한해서는 `output_tokens` 전체에 단일 이미지 출력 단가를 적용하는 것이 합리적인 근사입니다.

---

## 3. Gemini

### 모델

| Name | Model ID | Status | Notes |
|---|---|---|---|
| Gemini 3 Pro Image (Nano Banana Pro) | `gemini-3-pro-image` | **GA** (2026-05-28) | Best quality, thinking/reasoning, SOTA text rendering, up to **14** reference inputs, 1K/2K/4K, Google Search grounding. Generation **and** editing via `generate_content`. |
| Gemini 3.1 Flash Image (Nano Banana 2) | `gemini-3.1-flash-image` | **GA** (2026-05-28) | Fast/high-volume, near-Pro quality, 0.5K/1K/2K/4K, widest aspect-ratio set, video-to-image input. |
| Gemini 2.5 Flash Image (original Nano Banana) | `gemini-2.5-flash-image` | **GA** (2025-10-02) | Cheapest native model, cleanest token story (1290 tokens/1K image). *(Uncertain: secondary sources cite a 2026-10-02 Gemini-API shutdown with replacement `gemini-3.1-flash-image`; not confirmed on the primary changelog — verify the models page before pinning.)* |
| Imagen 4 Standard | `imagen-4.0-generate-001` | GA | Text-to-image diffusion via `generate_images`. **Generate-only** (no native edit in the Developer API). |
| Imagen 4 Fast | `imagen-4.0-fast-generate-001` | GA | Cheapest tier ($0.02/image). |
| Imagen 4 Ultra | `imagen-4.0-ultra-generate-001` | GA | Highest-fidelity Imagen tier. |
| Imagen 3 | `imagen-3.0-generate-002` | Deprecated | Use Imagen 4. |

> **참고:** Nano Banana의 `-preview` ID(`gemini-3-pro-image-preview`, `gemini-3.1-flash-image-preview`)는 **지원 종료, 2026-06-25 종료**입니다 — GA 비-preview ID를 사용하세요. **별도의 "-edit" 모델은 없습니다**; 편집은 `contents`에 이미지를 넣은 `generate_content`입니다.

### 생성 + 편집 API + 코드

```python
from google import genai
from google.genai import types
from PIL import Image
from io import BytesIO

client = genai.Client()  # reads GEMINI_API_KEY (or GOOGLE_API_KEY)
MODEL = "gemini-3-pro-image"   # or "gemini-2.5-flash-image" (cheapest native)

# (1) TEXT-TO-IMAGE
gen = client.models.generate_content(
    model=MODEL,
    contents="A photorealistic red ceramic coffee mug on a white studio background, soft lighting",
    config=types.GenerateContentConfig(
        response_modalities=["TEXT", "IMAGE"],     # canonical form; include TEXT
        image_config=types.ImageConfig(aspect_ratio="1:1", image_size="2K"),
    ),
)
for part in gen.parts:
    if part.inline_data is not None:
        Image.open(BytesIO(part.inline_data.data)).save("generated.png")  # or part.as_image()
print("usage:", gen.usage_metadata)

# (2) IMAGE EDIT (background change) — mask-free, prompt-only; pass the image in contents
edit = client.models.generate_content(
    model=MODEL,
    contents=[
        "Change ONLY the background to a solid deep-teal color. "
        "Keep the mug, its shape, color, and position exactly the same.",
        Image.open("generated.png"),
    ],
    config=types.GenerateContentConfig(response_modalities=["TEXT", "IMAGE"]),
)
for part in edit.parts:
    if part.inline_data is not None:
        Image.open(BytesIO(part.inline_data.data)).save("edited.png")

# (3) IMAGEN 4 (generate-only, cheapest flat per-image)
imagen = client.models.generate_images(
    model="imagen-4.0-generate-001",
    prompt="A red ceramic coffee mug on a white studio background, product photography",
    config=types.GenerateImagesConfig(
        number_of_images=1,
        aspect_ratio="1:1",
        image_size="1K",          # NOTE: image_size, NOT sample_image_size (1K/2K; Standard+Ultra only)
        person_generation="allow_adult",
        output_mime_type="image/png",
    ),
)
imagen.generated_images[0].image.save("imagen4.png")
```

> **Imagen에 적용된 검증 수정:** (1) config 필드는 `sample_image_size`가 아니라 **`image_size`**('1K'/'2K')입니다(전자는 레거시 이름). (2) Imagen Ultra는 이미지 1개로 제한되지 **않습니다** — 모든 Imagen 4 변형이 `number_of_images` **1–4**를 지원합니다. (3) `generate_content`에서는 `response_modalities=["TEXT","IMAGE"]`가 문서화된 표준 형식입니다(`["IMAGE"]` 단독은 피하세요).

### 가격 (Gemini Developer API, standard tier)

| Model | Input ($/1M) | Image output | Per-image | Batch |
|---|---|---|---|---|
| `gemini-2.5-flash-image` | $0.30 | $30/1M | **$0.039** (1290 tok @1K) | $0.0195/image |
| `gemini-3.1-flash-image` | $0.50 | $60/1M | $0.045 (0.5K) / **$0.067 (1K)** / $0.101 (2K) / $0.151 (4K) | ~50% off ($30/1M) |
| `gemini-3-pro-image` | $2.00 | $120/1M | **$0.134 (1K/2K)** / $0.24 (4K) | $0.067 (1K/2K) / $0.12 (4K) |
| `imagen-4.0-fast-generate-001` | — | flat | **$0.02/image** | — |
| `imagen-4.0-generate-001` | — | flat | $0.04/image | — |
| `imagen-4.0-ultra-generate-001` | — | flat | $0.06/image | — |

이 중 어떤 모델도 이미지 출력에 **무료 tier가 없습니다**(Imagen은 명시적으로 "Not available"; 네이티브 모델도 무료 이미지 출력 할당량을 명시하지 않음). 2025-11-04에 `gemini-2.5-flash-image`의 *입력* 이미지 토큰이 1290 → **258**로 인하되었습니다(편집이 더 저렴해짐).

### 사용량 리포팅 + SynthID

네이티브(`generate_content`) 응답에는 `response.usage_metadata`가 담깁니다: `prompt_token_count`, `candidates_token_count`(생성된 이미지의 토큰 비용, 예: 2.5-flash의 1K 이미지에서 ~1290), `total_token_count`, 그리고 `prompt_tokens_details` / `candidates_tokens_details`(각각 `.modality` ∈ {TEXT, IMAGE, …}와 `.token_count`를 가진 `ModalityTokenCount`), thinking 모델에서는 `thoughts_token_count`도 포함됩니다. 이미지 비용은 `candidates_tokens_details`의 IMAGE 모달리티 항목 × 100만당 이미지 출력 단가로 계산하세요.

**Imagen은 토큰 사용량을 보고하지 않습니다** — 이미지당 정액제이므로 `cost = number_of_images × per_image_price`입니다.

**SynthID:** 모든 Gemini/Imagen 출력에는 보이지 않는 SynthID 워터마크가 자동으로(플래그 없이) 들어갑니다. 이는 과금/사용량 항목이 아닙니다.

---

## 4. 이미지 편집 / 배경색 변경 (두 제공자)

| Aspect | OpenAI | Gemini (Developer API) |
|---|---|---|
| Endpoint | `client.images.edit()` (dedicated) | `client.models.generate_content(contents=[prompt, image])` |
| Mask / inpainting | **Yes** — PNG mask, `alpha=0` = region to edit, same dims, <4MB | **No mask** — "masking" is semantic (prompt "change only X, keep the rest unchanged") |
| Fidelity control | `input_fidelity` high/low on `gpt-image-1.5`/`1`/mini; `gpt-image-2` is always high | None explicit; rely on instruction + multi-turn; `gemini-3-pro-image` for max fidelity |
| Transparent cutout | `gpt-image-1.5` + `background="transparent"` (gpt-image-2 cannot) | n/a (no transparent-background flag) |
| Multi-reference | up to 16 images | up to 14 (Nano Banana Pro) |
| Trade-off | Pixel-precise edit boundary, guaranteed subject-pixel preservation, but you must build a mask | Fast, conversational, strong identity consistency; boundary is model-decided and can drift over many iterations |

**OpenAI 배경 변경 — 두 가지 방법:**
1. *프롬프트만:* `image` + "배경을 단색 파스텔 그린으로 바꾸고 피사체는 그대로 유지" 같은 프롬프트 전달.
2. *마스크 인페인팅:* 배경 위에 투명한 PNG `mask`를 추가해 해당 영역만 재생성(정밀; 피사체 픽셀 보존).

```python
# OpenAI masked background swap
res = client.images.edit(
    model="gpt-image-2",
    image=open("subject.png", "rb"),
    mask=open("background_mask.png", "rb"),   # alpha=0 == edit here; same dims as image
    prompt="Replace the background with a warm sunset gradient.",
    size="1024x1024", quality="high",
)
```

**Gemini 배경 변경 — 프롬프트만:**
```python
edit = client.models.generate_content(
    model="gemini-3.1-flash-image",
    contents=["Change ONLY the background to a solid pastel-green studio backdrop. "
              "Keep the subject, pose, lighting and composition unchanged.",
              Image.open("subject.png")],
    config=types.GenerateContentConfig(response_modalities=["TEXT", "IMAGE"]),
)
```

**Google 스택에서의 진짜 마스크 기반 인페인팅**은 **Vertex AI Imagen**(`imagen-3.0-capability-001`, `edit_mode="inpainting-insert"` / `INPAINT_INSERTION`, `mask_mode="background"` 자동 마스크 또는 직접 공급한 raw 마스크)이 필요합니다. 여기에는 Vertex 인증 + 실제 리전(`us-central1`; `global` 미지원)이 필요하며 — 다른 곳에서 쓰는 `GOOGLE_API_KEY`와는 **다른 SDK/과금 경로**입니다. 키만 쓰는 노트북에서는 범위를 벗어날 가능성이 높으니 사이드바로만 언급하세요.

---

## 5. 비용 비교

권장 모델, 단일 1024×1024 / 1K 이미지, **standard tier**:

| Provider | Model | Billing unit | Approx $ / generated image (high/1K) | Notes |
|---|---|---|---|---|
| OpenAI | `gpt-image-2` | tokens (text-in/image-in/image-out) | **~$0.211** (high); ~$0.053 medium; ~$0.006 low | Square is priciest aspect; portrait/landscape high ~$0.165. Reasoning text-out tokens also billed. |
| Gemini | `gemini-3-pro-image` | tokens (image-out $120/1M) | **~$0.134** (1K/2K) | Top-quality Gemini; ~$0.24 at 4K. |
| Gemini | `gemini-2.5-flash-image` | tokens (image-out $30/1M) | **~$0.039** (1290 tok) | Cheapest native model that can also edit; cleanest token→cost mapping. |
| Gemini | `imagen-4.0-fast-generate-001` | **flat per image** | **$0.02** | Generate-only; flat-rate baseline. |

**서로 다른 과금 단위 — lab이 드러내야 할 정합:**
- **OpenAI**는 입력 vs 출력 **그리고** 텍스트 vs 이미지 토큰을 분리합니다. Cost = `text_in×text_in_rate + image_in×image_in_rate + image_out×image_out_rate + text_out×text_out_rate`, 모두 ÷ 1e6. 편집의 경우 소스 이미지는 `input_tokens_details.image_tokens`에 나타납니다.
- **Gemini 네이티브**는 입력 이미지를 `prompt_token_count`에, 출력 이미지를 `candidates_token_count`에 합산합니다(모달리티 상세 배열을 읽지 않는 한 텍스트/이미지 입력 구분 없음). Cost = `prompt_token_count×input_rate + candidates_image_tokens×image_out_rate`.
- **Imagen**은 토큰을 보고하지 않습니다 — cost = `number_of_images × per_image_price`.

**나란히 비교(side-by-side) 표를 위한 매핑:** OpenAI `(입력 텍스트 + 입력 이미지 토큰)` ↔ Gemini `prompt_token_count`; OpenAI `출력 이미지 토큰` ↔ Gemini `candidates_token_count` IMAGE 모달리티. 호출마다 원시 `response.usage` / `response.usage_metadata`를 JSON으로 로깅하고 비용은 클라이언트 측에서 계산하세요(두 API 모두 달러 금액을 반환하지 않음). **편집은 생성보다 비쌉니다** — 소스 이미지가 입력 토큰을 추가하기 때문입니다(`gpt-image-2`에서는 항상 high fidelity).

---

## 6. 품질 비교

블라인드 Elo 아레나 두 곳이 주도합니다: **Artificial Analysis Image Arena**와 **LMArena**. 두 곳의 수치를 **절대 섞지 마세요**(프롬프트 풀, 투표자, 척도가 다름).

**생성 (text-to-image):**
- **GPT Image 2 (high)가 선두** — Artificial Analysis Elo ~**1339**(#1); 2026년 4월 데뷔 시 LMArena 1위(~Elo 1512, 기록적인 ~+242점 격차 — *웹 검색을 켠 Nano Banana 2 대비이며, Nano Banana Pro 대비가 아님*). **이미지 내 텍스트 렌더링, 구조적 레이아웃/UI/인포그래픽, 프롬프트 + 공간 충실도**에서 우세.
- **Gemini Nano Banana Pro / 2가 우세**한 영역: 사실감, 피부/재질/조명의 "촬영된 듯한" 충실도, 그리고 **훨씬 빠른 속도**(Flash ~850 ms vs GPT Image ~4,200 ms).

**편집 — 최상위권 거의 동률**(Artificial Analysis 편집 리더보드):

| Model | Editing Elo |
|---|---|
| GPT Image 1.5 (high) | ~1262 (#1) |
| GPT Image 2 (high) | ~1259 |
| Nano Banana Pro (`gemini-3-pro-image`) | ~1250 |
| Nano Banana 2 (`gemini-3.1-flash-image`) | ~1247 |

GPT Image가 Elo에서 근소하게 앞서지만, 정성적으로는 대화형/반복 편집, 국소 인페인팅, 멀티 레퍼런스(최대 14개), 그리고 순차 편집에 걸친 **캐릭터/정체성 일관성**에서 **Gemini가 선호**됩니다; GPT Image는 구조적/텍스트 포함 편집에서 앞섭니다.

**lab이 공정하게 평가하는 방법:**
- 프롬프트, 종횡비/해상도, 그리고 (가능하면) 시드/temperature를 **고정**하고, **동일 품질 tier**를 요청(OpenAI `quality="high"`).
- 프롬프트당 **N = 3–4 샘플**을 돌리고 분산을 보고하세요(샘플링 노이즈는 실재함).
- 작은 블라인드 채점 **루브릭** 사용: 프롬프트 충실도, 텍스트 가독성, 사실감, 편집 정밀도 / 정체성 보존, 아티팩트.
- **텍스트 위주 프롬프트 하나와 사실적/인물 프롬프트 하나**를 유지 — 카테고리에 따라 승자가 뒤바뀝니다.
- **편집 비대칭성을 공개**하세요: OpenAI는 명시적 마스크를 받을 수 있고, Gemini는 언어적 국소화에 의존합니다. 숨기지 마세요.
- **tier에 주의**: 일부 서드파티 "벤치마크"는 GPT Image 2를 *최저* 품질(흐릿함)로 테스트했습니다 — 불공정. `quality="high"`로 맞추세요.
- **출처(provenance):** 이제 두 제공자 모두 신호를 넣습니다(Gemini SynthID 상시; OpenAI는 2026-05-19부터 API 이미지에 SynthID + C2PA). C2PA 메타데이터는 다시 저장하면 제거될 수 있지만 SynthID는 많은 변형을 견딥니다.

---

## 7. lab/28 권장 사항

> **lab 결정(2026-06-13): 핵심 테스트 세트 = `gpt-image-2` + `gemini-3-pro-image` + `gemini-3.1-flash-image`** — OpenAI 플래그십 1개 + Gemini 2개 tier(Pro & Flash); 각각 생성과 편집을 모두 수행. 이로써 3포인트 품질/비용 곡선(고해상도 이미지당 ~$0.21 / ~$0.13 / ~$0.067)이 나옵니다. `gemini-2.5-flash-image`(가장 저렴한 네이티브)와 `imagen-4.0-*`(이미지당 정액)는 아래에 참고/베이스라인으로 문서화되어 있으나 핵심 세트에는 **포함되지 않습니다**.

**`pyproject.toml` 의존성 항목**(최소 버전 고정; 빌드 시점에 최신 버전 확인 — 버전 변동 잦음):

```toml
dependencies = [
    "openai>=2.0.0",        # GPT Image family (client.images.generate / .edit)
    "google-genai>=1.0.0",  # unified Gemini SDK: `from google import genai`
    "python-dotenv>=1.0.0", # load .env
    "pillow>=11.0.0",       # PIL: pass/save images for editing
]
```
> 정확한 패치 버전은 리서치 데이터에서 **불확실**합니다 — 빌드 시점에 최신 `openai`(2.x) 및 `google-genai`(1.x)로 고정하세요. 레거시 `google-generativeai` 패키지는 **사용하지 마세요**; `google-genai`를 사용하세요.

**환경 변수(`.env`):**
```
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=...        # google-genai also accepts GEMINI_API_KEY
```

**표준화할 모델 ID:**

| Task | OpenAI | Gemini |
|---|---|---|
| **Generation** | `gpt-image-2` | `gemini-3-pro-image` (top quality) — or `gemini-2.5-flash-image` for the cheapest, cleanest token-cost demo |
| **Editing / background change** | `gpt-image-2` (prompt or mask). Switch to `gpt-image-1.5` only for a transparent cutout or explicit `input_fidelity` — and note its 2026-12-01 sunset | Same Nano Banana model as generation, with the source image in `contents` (prompt-only) |
| **Flat-rate cost baseline (optional)** | — | `imagen-4.0-fast-generate-001` ($0.02/image) |

**선정 이유:** `gpt-image-2`는 유일하게 **지원 종료되지 않은** GPT-image 모델입니다(나머지는 2026-10-23 / 2026-12-01에 종료). Gemini Nano Banana GA ID는 `-preview` 종료(2026-06-25)를 피합니다. 비용 비교 서사를 위해 `gemini-2.5-flash-image`는 OpenAI의 토큰 단위 리포팅과 대비되는 가장 깔끔한 "1 이미지 = 1290 토큰 = $0.039" 스토리를 제공합니다.

**노트북에 반영할 함정들:** `gpt-image-2`에 `input_fidelity`를 전달하지 말 것; `gpt-image-2`는 투명 배경 불가; GPT-image는 base64만 반환; OpenAI 마스크 `alpha=0` = 편집 영역; Gemini는 Developer API에 마스크 없음; `output_tokens_details`는 `getattr()`로 방어적으로 접근; 비용 표를 위해 원시 usage 객체를 JSON으로 로깅.

---

## 8. 출처 (Sources)

**OpenAI (공식)**
- Image generation guide — https://developers.openai.com/api/docs/guides/image-generation
- Create image (generate) reference — https://developers.openai.com/api/reference/resources/images/methods/generate
- Create image edit reference — https://developers.openai.com/api/reference/resources/images/methods/edit
- Images object (usage) reference — https://developers.openai.com/api/docs/api-reference/images/object
- Image generation tool (Responses API) — https://developers.openai.com/api/docs/guides/tools-image-generation
- Pricing — https://developers.openai.com/api/docs/pricing
- Deprecations — https://developers.openai.com/api/docs/deprecations
- Model pages: gpt-image-2 — https://developers.openai.com/api/docs/models/gpt-image-2 · gpt-image-1.5 — https://developers.openai.com/api/docs/models/gpt-image-1.5 · gpt-image-1 — https://developers.openai.com/api/docs/models/gpt-image-1 · gpt-image-1-mini — https://developers.openai.com/api/docs/models/gpt-image-1-mini
- Changelog — https://developers.openai.com/api/docs/changelog
- Content provenance (SynthID + C2PA) — https://openai.com/index/advancing-content-provenance/ · https://help.openai.com/en/articles/8912793-c2pa-and-synthid-in-openai-generated-images

**Google / Gemini (공식)**
- Image generation (Nano Banana) — https://ai.google.dev/gemini-api/docs/image-generation
- Imagen — https://ai.google.dev/gemini-api/docs/imagen
- Pricing — https://ai.google.dev/gemini-api/docs/pricing
- Changelog — https://ai.google.dev/gemini-api/docs/changelog
- Counting tokens / usage_metadata — https://ai.google.dev/gemini-api/docs/tokens
- generateContent / UsageMetadata reference — https://ai.google.dev/api/generate-content
- Nano Banana Pro developer blog — https://blog.google/innovation-and-ai/technology/developers-tools/gemini-3-pro-image-developers/
- Gemini 2.5 Flash Image launch — https://developers.googleblog.com/en/introducing-gemini-2-5-flash-image/
- Prompting Flash Image for edits — https://developers.googleblog.com/en/how-to-prompt-gemini-2-5-flash-image-generation-for-the-best-results/
- Vertex AI pricing — https://cloud.google.com/vertex-ai/generative-ai/pricing
- Vertex AI Imagen mask inpainting — https://docs.cloud.google.com/vertex-ai/generative-ai/docs/samples/generativeaionvertexai-imagen-edit-image-inpainting-insert-mask-mode
- Firebase AI Logic — replace background with Imagen — https://firebase.google.com/docs/ai-logic/edit-images-imagen-replace-background
- SynthID — https://deepmind.google/models/synthid/

**벤치마크 / 아레나**
- Artificial Analysis — Text-to-Image — https://artificialanalysis.ai/image/leaderboard/text-to-image
- Artificial Analysis — Image Editing — https://artificialanalysis.ai/image/leaderboard/editing
- LM Arena text-to-image rankings 2026 — https://wavespeed.ai/blog/posts/lm-arena-text-to-image-rankings-2026/

**2차 자료 / 가격 계산기 (주의해서 사용; 공식과 대조 검증):**
- https://costgoat.com/pricing/openai-images · https://www.aifreeapi.com/en/posts/openai-image-generation-api-pricing · https://wavespeed.ai/blog/posts/gpt-image-2-pricing-2026/ · OpenAI dev community threads on gpt-image-1.5 text-output tokens

---

## 사실로 단정하지 말 것 — 표시된 불확실 항목

1. **DALL·E 가용성** — 명시된 종료일 2026-05-12는 지났지만, 라이브 generate/edit 레퍼런스 enum에는 여전히 `dall-e-2`/`dall-e-3`가 나열되어 있습니다. 문서-실제 충돌; 어느 쪽이든 사용 불가로 간주하세요.
2. **`gpt-image-2-2026-04-21` 스냅샷 문자열** — 출시 날짜는 확인됨, 정확한 스냅샷 문자열은 공식 changelog에서 미확인.
3. **`gemini-2.5-flash-image` 2026-10-02 폐기** — 2차 자료로만 뒷받침되며 primary changelog에는 없음. 고정 전에 모델 페이지를 확인하세요.
4. **`output_tokens_details` (OpenAI)** — 최신 모델에서는 실제로 존재하지만 공식 images-object 스키마에는 없음; `getattr()`로 접근.
5. **SDK 패치 버전** — 빌드 시점에 최신 `openai` 2.x / `google-genai` 1.x로 고정; 정확한 버전은 리서치 데이터에 없음.
