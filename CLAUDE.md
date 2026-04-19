# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 프로젝트 개요

건강식품 쇼핑몰 랭킹(네이버, 쿠팡, 올리브영, 카카오, 다이소)을 매일 자동 수집하고, 인스타그램용 랭킹 카드 이미지(PNG 1080×1350)를 생성하는 파이프라인.

---

## 실행 명령어

```bash
# 전체 파이프라인 (루트에서 실행)
python run.py
python run.py --date 20250403                  # 특정 날짜
python run.py --channel naver                  # 특정 채널만 크롤링 후 전체 진행
python run.py --channel naver coupang          # 복수 채널 지정
python run.py --skip-crawl                     # 크롤링 건너뜀
python run.py --skip-crawl-report              # 카드 생성만 (HTML→PNG)
python run.py --account MY_ACCOUNT             # 인스타그램 계정명

# 단계별 개별 실행 (반드시 해당 디렉토리 안에서 실행)
cd crawling && python main.py                  # 전체 크롤링
cd crawling && python main.py naver            # 특정 채널만
cd crawling && python report.py                # 엑셀 리포트
cd generate && python main.py                  # HTML + PNG
cd generate && python html2png.py              # PNG 변환만
```

---

## 일별 파이프라인 구조 (`run.py`)

```
1단계: crawling/main.py   → data/raw/{channel}/{YYYYMMDD}.csv
                            data/raw/{channel}/{YYYYMMDD}/{rank:02d}.jpg|png
2단계: crawling/report.py → data/report/{YYYYMMDD}_ranking.xlsx
3단계: generate/main.py   → data/output/{YYYYMMDD}/*.html + *.png
```

---

## 월간 파이프라인 구조 (`run_monthly.py`)

매월 첫째주 일요일 윈도우 스케줄러로 실행. 전월 데이터를 집계해 히어로 제품을 선발한다.

```
1단계: monthly/aggregate.py → data/monthly/{YYYY_MM}_monthly.xlsx
2단계: monthly/hero.py      → 동일 파일에 {channel}_hero 시트 추가
3단계: monthly/export.py    → data/hero/{YYYY_MM}/{channel}.xlsx
4단계: generate/generate_html_hero.py + generate_html_trend_monthly.py → HTML
5단계: generate/html2png.py → PNG
```

```bash
python run_monthly.py                        # 전월 자동 실행
python run_monthly.py --month 2026-04        # 특정 월
python run_monthly.py --skip-aggregate       # 집계 건너뜀
python run_monthly.py --skip-hero            # 히어로 선발 건너뜀
python run_monthly.py --skip-export          # 상세 파일 생성 건너뜀
python run_monthly.py --skip-cards           # 카드 HTML 생성 건너뜀
python run_monthly.py --skip-png             # PNG 변환 건너뜀

# 단계별 개별 실행 (monthly/ 디렉토리 안에서 실행)
cd monthly && python aggregate.py --month 2026-04
cd monthly && python hero.py      --month 2026-04
cd monthly && python export.py    --month 2026-04
```

**주의**: `run_monthly.py`는 generate 관련 모듈(`generate_html_hero`, `generate_html_trend_monthly`, `html2png`)을 lazy import로 처리한다. 해당 단계를 skip해도 import 오류 없이 실행된다.

### 월간 파이프라인 모듈 역할

| 파일 | 역할 | 입력 | 출력 |
|---|---|---|---|
| `monthly/aggregate.py` | 월간 CSV 집계 + 제품별 통계 계산 | `data/raw/{channel}/*.csv` | `data/monthly/YYYY_MM_monthly.xlsx` |
| `monthly/hero.py` | 점수 기반 히어로 제품 선발 (채널별 1개) | monthly.xlsx | 동일 파일에 `{channel}_hero` 시트 추가 |
| `monthly/export.py` | 히어로 제품 상세 파일 생성 | monthly.xlsx | `data/hero/YYYY_MM/{channel}.xlsx` |

### `data/hero/{YYYY_MM}/{channel}.xlsx` 시트 구성

| 시트 | 내용 |
|---|---|
| `summary` | 히어로 제품 요약 1행 (brand, product, url, avg_rank, best_rank, rank_change, total_score 등) |
| `weekly` | 주차별 rank / price / review·star (or like) |
| `reviews` | 빈 템플릿 — 리뷰 크롤링 기능 추가 예정 |

### 히어로 점수 기준 (100점 만점)

| 항목 | 기본 가중치 | 예외 |
|---|---|---|
| 순위 안정성 | 30pt | oliveyoung: 50pt |
| 최고 순위 | 25pt | oliveyoung: 50pt |
| 순위 상승폭 | 25pt | oliveyoung: 0pt |
| 참여도 성장 (리뷰/좋아요 증가율) | 20pt | oliveyoung: 0pt |

---

## 데이터 경로 구조

```
data/
├── raw/      ← 크롤링 원본 CSV + 이미지
├── report/   ← 일별 ranking.xlsx  (crawling/report.py)
├── output/   ← 인스타그램 카드 HTML + PNG
├── monthly/  ← 월간 집계 monthly.xlsx
└── hero/     ← 히어로 제품 상세 파일
    └── YYYY_MM/
        ├── naver.xlsx
        ├── coupang.xlsx
        ├── oliveyoung.xlsx
        ├── kakao.xlsx
        └── daiso.xlsx
```

---

## CSV 데이터 규칙

### `period_ym` 컬럼
모든 CSV에 `period_ym` 컬럼이 포함된다. 쇼핑몰 랭킹은 "과거 7일" 기준이므로 크롤링 날짜와 실제 데이터 귀속 월이 다를 수 있다.

**규칙**: `period_ym = (크롤링 날짜 - 4일)의 YYYYMM`
- 4월 5일 크롤링 → 4월 1일 → `202604`
- 3월 1일 크롤링 → 2월 25일 → `202602`

`runner.py`가 CSV 저장 시 자동 계산해 추가한다. `monthly/aggregate.py`는 파일명 prefix 대신 이 컬럼으로 월별 필터링한다.

### 채널별 CSV 컬럼

| 채널 | 공통 컬럼 | 추가 컬럼 |
|---|---|---|
| naver | date, code, rank, brand, product, price, period_ym, url | star, review |
| coupang | date, code, rank, brand, product, price, period_ym, url | star, review |
| oliveyoung | date, code, rank, brand, product, price, period_ym, url | — |
| kakao | date, code, rank, brand, product, price, period_ym, url | like, img_url |
| daiso | date, code, rank, brand, product, price, period_ym, url | star, review |

---

## 크롤링 아키텍처 (`crawling/`)

### `core/runner.py` — 공통 실행 흐름

모든 채널은 `run_channel()`을 통해 실행된다. 직접 드라이버를 조작하거나 별도 흐름을 만들지 않는다.

```python
run_channel(
    channel_name: str,        # 로그 표시용 이름
    url: str,                 # 크롤링 대상 URL
    base_dir: Path,           # data/raw/{channel}/ 경로
    parse_func,               # BeautifulSoup → list[dict] 반환 함수
    wait_selector: str,       # 페이지 로드 확인용 CSS 셀렉터 (필수)
    image_selector: str,      # 이미지 img 태그 셀렉터 (없으면 img_url 컬럼 사용)
    pre_actions=None,         # 파싱 전 브라우저 조작 콜백 (스크롤, 버튼 클릭 등)
    post_process_func=None,   # 파싱 후 데이터 후처리 콜백
    max_retries: int = 2,     # 봇 감지 시 최대 재시도 횟수
    popup_selectors: list = None,  # 채널 전용 팝업 닫기 셀렉터
)
```

**내부 실행 순서 (변경 금지):**
1. `driver.get(url)`
2. `WebDriverWait(20초)` — `wait_selector` 요소 대기. 타임아웃 시 재시도 (15초 → 30초 간격, 최대 2회)
3. `dismiss_popups()` — 팝업 자동 제거
4. `pre_actions(driver)` — 채널별 커스텀 조작
5. BeautifulSoup 파싱 → CSV 저장 → 이미지 저장

### `core/browser.py` — 드라이버 및 팝업 유틸리티

**`create_driver()`**: `undetected_chromedriver` + 번들 드라이버(`driver/chromedriver-win64/chromedriver.exe`, version_main=146) 사용. Chrome 버전 업데이트 시 `version_main` 값을 함께 갱신해야 한다.

**`safe_click(driver, css_selector, timeout=5, label=None)`**: 알려진 버튼을 안전하게 클릭. 요소가 없거나 타임아웃 시 `False` 반환. `label` 지정 시 실패 경고를 콘솔에 출력한다. `pre_actions` 내 모든 버튼 클릭은 반드시 이 함수를 사용한다.

**`dismiss_popups(driver, extra_selectors=None, timeout=1)`**: 페이지 로드 후 자동 호출. 아래 순서로 팝업을 탐색·제거한다.
1. **별도 창** — 메인 핸들 외 창이 열려 있으면 닫고 메인으로 복귀
2. **메인 문서** — 공통 셀렉터 + `extra_selectors` (JS click으로 오버레이 우회)
3. **iframe** — 페이지 내 모든 `<iframe>`에 진입 후 셀렉터 시도, 완료 후 `default_content` 복귀

---

## 새 채널 추가 시 필수 체크리스트

### 1. `crawling/channels/{name}.py` 생성

반드시 아래 구조를 준수한다:

```python
from config import CHANNEL_PATHS
from core.browser import safe_click          # pre_actions 있을 경우
from core.runner import run_channel

URL = "https://..."

# 채널 전용 팝업 닫기 셀렉터 (없으면 빈 리스트 유지)
_{NAME}_POPUP_SELECTORS = []

def {name}_pre_actions(driver):              # 필요할 때만 정의
    safe_click(driver, "...", label="{name} 버튼명")
    # 직접 find_element().click() 금지 — safe_click 사용 필수

def parse_{name}(soup, today) -> list[dict]:
    # 반환 dict는 반드시 date, code, rank, brand, product, price 포함
    ...

def run():
    return run_channel(
        channel_name="{name}",
        url=URL,
        base_dir=CHANNEL_PATHS["{name}"],
        parse_func=parse_{name},
        wait_selector="...",                 # 상품 목록 대표 셀렉터 (생략 금지)
        image_selector="...",
        pre_actions={name}_pre_actions,      # 없으면 생략
        popup_selectors=_{NAME}_POPUP_SELECTORS,
    )
```

### 2. `crawling/config.py`

`CHANNEL_PATHS`와 `RANKING_COMPARE_COLUMNS`에 신규 채널 항목 추가.

### 3. `crawling/main.py`

`JOBS` 딕셔너리에 `"{name}": {name}.run` 등록.

### 4. `crawling/report.py`

`PLATFORMS` 딕셔너리에 신규 채널과 `diff_cols` 추가.

### 5. `generate/generate_html.py`

`CHANNEL_CONFIG`에 채널 설정 추가:
```python
"{name}": {
    "channel_label": "...",
    "logo_path": "./images/{name}.png",
    "image_path_template": "../data/raw/{name}/{today}/{rank:02d}",
    "meta_fields": [...],          # price / review / star / like 중 선택
    "sheet_name": "{name}_10",
    "filename_prefix": "0N_{name}",
}
```

### 6. `generate/html2png.py`

`HTML_FILE_NAMES` 목록에 아래 항목 추가 (번호 순서 유지):
```python
"0N_{name} (1).html",
"0N_{name} (2).html",
"0N_{name}_hot.html",
"0N_{name}_down.html",
```

### 7. `generate/images/`

채널 로고 이미지(`{name}.png`) 추가.

---

## 팝업 셀렉터 추가 방법

채널별 팝업이 공통 패턴으로 닫히지 않을 때:

1. 브라우저 개발자 도구(F12)에서 팝업 닫기 버튼의 CSS 셀렉터 확인
2. 클래스에 `/`가 포함된 경우(Tailwind 등) Python raw string 사용: `r"div.top-1\/2 > button"`
3. 셀렉터는 `<p>` 등 내부 텍스트 요소가 아닌 **클릭 가능한 `button` 또는 `a` 태그**를 가리켜야 함
4. 해당 채널 파일의 `_{NAME}_POPUP_SELECTORS` 리스트에 추가

`dismiss_popups`는 별도 창 → 메인 문서 → iframe 순으로 탐색하므로 팝업이 어느 컨텍스트에 있든 처리된다.

---

## 경로 규칙

- `crawling/` 스크립트는 `../data/...` 상대 경로를 사용하므로 **반드시 `crawling/` 디렉토리 안에서 실행**.
- `generate/` 스크립트도 동일하게 `generate/` 디렉토리 안에서 실행.
- `run.py`는 `subprocess`로 각 스크립트를 `cwd=CRAWLING_DIR` / `cwd=GENERATE_DIR`로 실행하므로 루트에서 실행해도 안전.
- 루트 `config.py`는 전역 경로 상수 모음 (현재 `run.py`에서는 미사용).

## ChromeDriver

- **크롤링**: `driver/chromedriver-win64/chromedriver.exe` 번들 + `undetected_chromedriver` (version_main=146)
- **PNG 변환**: `webdriver_manager`가 Chrome 버전에 맞는 드라이버 자동 설치 (크롤링과 다른 드라이버)
- Chrome 업데이트 시 번들 드라이버 교체 + `core/browser.py`의 `version_main` 갱신 필요
