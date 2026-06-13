# 멀티 케이스 이미지 생성/편집 + 비용 비교 — 설계

- 날짜: 2026-06-13
- 상태: 승인됨(설계) → 구현 계획 대기
- 성격: **간단한 학습용 테스트**. 구조는 최소한만 바꾼다.

## 1. 목표 / 문제

지금은 입력 이미지 1장과 프롬프트 1개가 `generate_sample.py`·`make_montage.py`에
**하드코딩**되어 있다. 테스트 이미지·프롬프트를 더 늘리고 싶은데, 현재 구조에는 두 가지 문제가 있다.

1. **출력 충돌** — 결과가 `outputs/<model>.png` 로만 저장되어, 케이스를 하나 더 추가하면
   기존 결과를 **덮어쓴다**. (이게 반드시 고쳐야 하는 유일한 구조적 문제다.)
2. 프롬프트·이미지가 코드 상수라서, 케이스를 추가하려면 코드를 고쳐야 한다.

목표: **여러 케이스(이미지+프롬프트)** 를 데이터 파일로 관리하고, 3개 모델로 돌려
케이스별로 결과·비용·뫽타주를 비교한다. prd.md 의 목표(생성 + 편집, 품질·비용 비교)를 유지한다.

## 2. 범위

- 파일 구조는 **기존 2개 파일 유지**(`generate_sample.py`, `make_montage.py`). 모듈 분리 안 함.
- 케이스 목록은 루트 `cases.toml` (stdlib `tomllib` 로 읽음 — **새 의존성 없음**, Python ≥3.11).
- 출력은 **케이스별 하위 폴더** `outputs/<case-id>/` 로 분리.

### 범위 밖 (YAGNI)
`summary.json` 집계 파일, `outputs/index.md` 자동 생성, 비용 회귀 테스트, `--skip-existing`
플래그, 비동기/병렬 호출, 이미지 품질 *수치* 지표, 새 런타임 의존성 — **전부 하지 않는다.**

## 3. `cases.toml` (루트)

각 `[[case]]` = 하나의 작업. `id` 가 `outputs/` 하위 폴더 이름이 되므로 파일시스템 안전 문자만 사용하고 중복 금지.

| 필드 | 필수 | 설명 |
|---|---|---|
| `id` | ✓ | 케이스 식별자 = 출력 폴더 이름 (예: `cat-fullbody`) |
| `type` | ✓ | `"edit"` (입력 이미지 필요) 또는 `"generate"` (텍스트만) |
| `prompt` | ✓ | 프롬프트 |
| `image` | edit 시 ✓ | 입력 이미지 경로(루트 기준). `generate` 면 생략 |
| `models` | ✗ | 돌릴 모델 ID 목록. 생략 시 기본 3종 전부 (비용 줄이려면 일부만) |

```toml
# 현재 동작하는 케이스 (기존 결과와 동일)
[[case]]
id = "cat-fullbody"
type = "edit"
image = "test_data/cat-scratch.png"
prompt = "A full-body cute cat based on this simple smiling cat sketch. High-resolution."

# 새 이미지 케이스 예시 — 프롬프트는 사용자가 실제 값으로 채운다.
# [[case]]
# id = "woman-book-edit"
# type = "edit"
# image = "test_data/woman-masking-book.jpg"
# prompt = "<여기에 편집 프롬프트>"
# models = ["gemini-3.1-flash-image"]   # 예: 비용 줄이려고 한 모델만
```

## 4. 출력 폴더 구조

```
outputs/
  cat-fullbody/
    gpt-image-2.png  gemini-3-pro-image.png  gemini-3.1-flash-image.png
    usage.json       # 이 케이스의 모델별 토큰/비용 목록
    montage.png      # 이 케이스 비교 뫽타주
  <다른-케이스>/      # 실행해야 생성됨 (실행 1셀 = 실제 과금 1회)
```

## 5. 코드 변경

### `src/generate_sample.py`
- 모듈 상수 `PROMPT`, `INPUT_IMAGE` **제거**. `OPENAI_RATES`/`GEMINI_RATES`/모델 ID/
  `_get_key`/`_fmt_cost`/`_load_input_rgb` 는 유지.
- `tomllib` 로 `cases.toml` 읽는 `load_cases()` 추가.
- 모델 → 제공자 매핑을 env 3개 슬롯(`OPENAI_IMAGE_MODEL` / `GEMINI_PRO_IMAGE_MODEL` /
  `GEMINI_FLASH_IMAGE_MODEL`)에서 구성. 케이스 `models` 에 알 수 없는 ID 가 있으면
  **API 호출 전에** 명확히 에러.
- 제공자 함수를 파라미터화:
  - `generate_openai(model, prompt, image_path | None, out_dir)` — `image_path` 있으면
    `client.images.edit`, 없으면 `client.images.generate`. 비용 계산 로직은 동일.
    결과를 `out_dir/<model>.png` 에 저장.
  - `generate_gemini(model, prompt, image_path | None, out_dir)` — `contents` 를
    `[prompt, 입력이미지]` 또는 `[prompt]` 로. 나머지 동일.
- `main()`:
  - 인자 파싱(가볍게): 선택적 위치 인자 `case`(생략=전체), `--list`(케이스 목록만 출력).
  - 선택된 케이스마다 `outputs/<id>/` 생성 → `case.models or 기본3종` 반복 →
    제공자 디스패치 → 셀 단위 `try/except`(한 셀 실패해도 나머지 진행, 현재 동작 유지).
  - 케이스별 `outputs/<id>/usage.json` 기록, 콘솔에 케이스·모델·토큰·비용 표 출력.

### `src/make_montage.py`
- 하드코딩 `PROMPT`/`INPUT` 제거. `cases.toml` 를 읽어 케이스마다:
  - `edit`: `[입력 | 모델1 | 모델2 | 모델3]`
  - `generate`: `[모델1 | 모델2 | 모델3]` (입력 패널 없음, 배너에 생성임을 표기)
  - 결과 png 없으면 기존 "no output" 플레이스홀더 그대로
  - 캡션 = `usage.json` 의 비용·토큰, 배너 = 프롬프트(+ case id)
  - `outputs/<id>/montage.png` 저장
- 선택적 위치 인자 `case` 로 한 케이스만 그릴 수 있게(생성 스크립트와 대칭).

> 참고: `cases.toml` 로딩(약 5줄)은 두 파일에 가볍게 중복 허용 — 2파일 구조 유지를 위해 공용 모듈은 만들지 않는다.

## 6. 기존 결과 마이그레이션 (재과금 없음)

```bash
mkdir -p outputs/cat-fullbody
git mv outputs/gpt-image-2.png outputs/gemini-3-pro-image.png \
       outputs/gemini-3.1-flash-image.png outputs/montage.png \
       outputs/usage.json outputs/cat-fullbody/
# montage.png 까지 함께 옮겨 최상위 orphan 을 남기지 않는다.
# 그 후 make_montage.py cat-fullbody 로 새 배너의 montage.png 재생성(무과금)하여 덮어쓴다.
```

## 7. 문서 업데이트

- **README.md**: 폴더 구조·명령(케이스 단일 실행, `cases.toml`)·뫽타주 임베드 경로
  (`outputs/cat-fullbody/montage.png`) 갱신. 더 많은 케이스는 `outputs/<id>/` 아래 생긴다고 명시.
  + 기존에 잘못된 줄 수정: "`usage.json` 이 루트 `.gitignore` 의 `*.json` 규칙으로 제외" → 이 저장소엔
  그 규칙이 없고 추적된다 (이전 `/init` 점검에서 발견).
- **CLAUDE.md**: Layout(`cases.toml`, `outputs/<id>/`)·명령·현재 상태(멀티 케이스, `type` 으로
  생성/편집 모두 1급) 갱신.

## 8. 에러 처리 / 동작
- 셀(케이스×모델) 단위 `try/except` 로 실패 격리(현재 동작 유지).
- `edit` 케이스인데 `image` 누락/없음 → 그 케이스 건너뛰고 메시지.
- `models` 에 미등록 모델 ID → API 호출 전에 즉시 에러(돈 낭비 방지).
- API 키 없음 → 기존 `_get_key` 의 안내 메시지.

## 9. 검증 (수동, 무과금 우선)
- `uv run python src/generate_sample.py --list` → 키 없이 케이스 목록 출력 확인.
- 마이그레이션 후 `uv run python src/make_montage.py cat-fullbody` → 커밋된 png 로
  뫽타주 생성(무과금 end-to-end 확인).
- 실제 모델 호출은 사용자가 키·결제 활성화 후 직접 실행(셀당 실제 과금).
