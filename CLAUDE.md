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
1단계: monthly/aggregate.py      → data/monthly/{YYYY_MM}_monthly.xlsx
2단계: monthly/hero.py           → 동일 파일에 {channel}_hero 시트 추가
3단계: monthly/export.py         → data/hero/{YYYY_MM}/{channel}.xlsx
4단계: monthly/crawl_reviews.py  → data/hero/{YYYY_MM}/{channel}.xlsx reviews 시트
5단계: generate/generate_html_hero.py
       generate/generate_html_trend_monthly.py
       generate/generate_html_hero_review.py
       generate/generate_html_weekly_trend.py  → HTML 카드
6단계: generate/html2png.py      → PNG
```

```bash
python run_monthly.py                        # 이번 달 전체 실행
python run_monthly.py --month 2026-04        # 특정 월
python run_monthly.py --skip-aggregate       # 집계 건너뜀
python run_monthly.py --skip-hero            # 히어로 선발 건너뜀
python run_monthly.py --skip-export          # 상세 파일 생성 건너뜀
python run_monthly.py --skip-reviews         # 리뷰 크롤링 건너뜀
python run_monthly.py --skip-cards           # 카드 HTML 생성 건너뜀
python run_monthly.py --skip-png             # PNG 변환 건너뜀

# 단계별 개별 실행 (monthly/ 디렉토리 안에서 실행)
cd monthly && python aggregate.py  --month 2026-04
cd monthly && python hero.py       --month 2026-04
cd monthly && python export.py     --month 2026-04
cd monthly && python crawl_reviews.py --month 2026-04

# 리뷰 카드 단독 생성 (generate/ 디렉토리 안에서 실행)
cd generate && python generate_html_hero_review.py --month 2026-04

# 주간 순위 추이 카드 단독 생성 (generate/ 디렉토리 안에서 실행)
cd generate && python generate_html_weekly_trend.py --month 2026-04
```

**주의**: `run_monthly.py`는 generate 관련 모듈을 lazy import로 처리한다. 해당 단계를 skip해도 import 오류 없이 실행된다.

### 월간 파이프라인 모듈 역할

| 파일 | 역할 | 입력 | 출력 |
|---|---|---|---|
| `monthly/aggregate.py` | 월간 CSV 집계 + 제품별 통계 계산 | `data/raw/{channel}/*.csv` | `data/monthly/YYYY_MM_monthly.xlsx` |
| `monthly/hero.py` | 점수 기반 히어로 제품 선발 (채널별 1개) | monthly.xlsx | 동일 파일에 `{channel}_hero` 시트 추가 |
| `monthly/export.py` | 히어로 제품 상세 파일 생성 | monthly.xlsx | `data/hero/YYYY_MM/{channel}.xlsx` |
| `monthly/crawl_reviews.py` | 히어로 제품 리뷰 크롤링 | hero xlsx summary.url | hero xlsx reviews 시트 갱신 |
| `generate/generate_html_hero.py` | 히어로 선정 이유 카드 | monthly.xlsx hero 시트 | `hero_{channel}.html` |
| `generate/generate_html_trend_monthly.py` | 월간 순위 추이 차트 카드 | monthly.xlsx daily 시트 | `trend_{channel}.html` |
| `generate/generate_html_hero_review.py` | 히어로 리뷰 수 추이 차트 카드 | hero xlsx weekly 시트 + monthly daily 시트 | `hero_review_{channel}.html` |
| `generate/generate_html_weekly_trend.py` | 히어로 주간 순위+리뷰 추이 듀얼 차트 카드 | hero xlsx weekly + summary 시트 | `weekly_trend_{channel}.html` |

---

## 히어로 제품 파일 구조 (`data/hero/{YYYY_MM}/{channel}.xlsx`)

| 시트 | 내용 |
|---|---|
| `summary` | 히어로 제품 요약 1행. 컬럼: code, brand, product, price, url, appearances, total_weeks, avg_rank, best_rank, first_rank, last_rank, first_date, last_date, rank_change, first_review, last_review, review_growth, review_growth_pct, avg_star, total_score 등 |
| `weekly` | 주차별 스냅샷. 컬럼: week, date, rank, price, review(or like), star |
| `reviews` | 리뷰 크롤링 결과. 컬럼: review_date, rating, reviewer, content |

**summary.url**: `aggregate.py`의 `compute_stats()`에서 해당 월 마지막 스냅샷의 `url` 컬럼 값을 그대로 저장. `crawl_reviews.py`가 이 url로 리뷰를 크롤링한다.

### 히어로 점수 기준 (100점 만점)

| 항목 | 기본 가중치 | 예외 |
|---|---|---|
| 순위 안정성 | 30pt | oliveyoung: 50pt |
| 최고 순위 | 25pt | oliveyoung: 50pt |
| 순위 상승폭 | 25pt | oliveyoung: 0pt |
| 참여도 성장 (리뷰/좋아요 증가율) | 20pt | oliveyoung: 0pt |

---

## 리뷰 크롤링 (`monthly/crawl_reviews.py`)

### 개요

`data/hero/YYYY_MM/{channel}.xlsx`의 summary 시트에서 url을 읽어 채널별 셀렉터로 리뷰를 파싱하고 reviews 시트를 갱신한다. 로그는 `run_monthly.txt`에 기록된다.

### 실행 모드

```bash
# 월별 전체 실행
cd monthly && python crawl_reviews.py --month 2026-04

# 단일 URL 직접 테스트
cd monthly && python crawl_reviews.py --channel naver --url https://smartstore.naver.com/...

# 쿠키 저장 (최초 1회 또는 만료 시)
cd monthly && python crawl_reviews.py --save-cookies naver
```

### 쿠키 관리 (`monthly/cookies/`)

네이버 등 로그인이 필요한 채널은 쿠키를 pickle 파일로 저장해 재사용한다.

| 파일 | 용도 |
|---|---|
| `monthly/cookies/naver.pkl` | 네이버 로그인 쿠키 |

**최초 설정**: `--save-cookies naver` 실행 → 브라우저 팝업 → 직접 로그인 → Enter → 쿠키 저장

**만료 감지**: 리뷰 0건 수집 시 로그에 아래 경고가 출력된다.
```
[naver] 수집된 리뷰 0건 — 쿠키 만료 또는 봇 차단 가능성.
쿠키 갱신: python crawl_reviews.py --save-cookies naver
```

**갱신 주기**: 네이버 쿠키는 통상 30일 내외. 매월 파이프라인 실행 전 갱신 권장.
`cookies/` 디렉토리는 `.gitignore`에 추가 (개인 로그인 정보 포함).

### 셀렉터 설정 (`monthly/review_config.py`)

`REVIEW_SELECTORS` 딕셔너리에 채널별 CSS 셀렉터를 직접 입력한다.
`wait_selector`가 비어있는 채널은 자동으로 건너뜀.

**네이버 셀렉터 (검증 완료)**:

```python
"naver": {
    "review_btn":       "#content > div > div.fUgLLODhD8 > div:nth-child(1) > div > div > div.PSOcMLEJuY > button",
    "wait_selector":    "#MODAL_ROOT_ID > div > div.qc8qCgj4u2.b3VJJSdlmJ > div > div > div.ckqgS03UN6 > div > div > div:nth-child(1) > div > div.ZDSfEuYSzZ > strong",
    "container":        ".PYRRKjHPB6",
    "date":             ".dgOMiF9qbL span:nth-child(2)",
    "rating":           ".F6N7Rr56mQ",
    "reviewer":         ".dgOMiF9qbL span:nth-child(1)",
    "content":          "p.Uv4T3VkhKU",
    "scroll_container": "div.ckqgS03UN6",   # 리뷰 모달 스크롤 컨테이너
    "next_btn":         "",                  # 무한스크롤이므로 불필요
    "max_pages":        1,
}
```

### 네이버 리뷰 크롤링 동작 원리 (`naver_pre_actions`)

네이버 스마트스토어는 봇 감지가 강해 아래 순서를 반드시 지킨다.

1. **zoom 50% 먼저** — `document.body.style.zoom='50%'`  
   zoom 적용 전에 scrollIntoView하면 좌표계가 틀어져 클릭 실패.
2. **scrollIntoView** — 리뷰전체보기 버튼을 뷰포트 중앙으로 이동
3. **JS click** — `arguments[0].click()` 사용. zoom으로 좌표 기반 클릭 불가.
4. **모달 로드 대기** — `wait_selector` 요소 presence 대기 (최대 20초)
5. **무한스크롤** — `div.ckqgS03UN6` 컨테이너 기준 `scrollTop = scrollHeight`  
   `window.scrollTo`는 모달 내부 스크롤에 무효. 반드시 컨테이너 직접 스크롤.

### 단계별 테스트

`monthly/review_test.ipynb` — 네이버 리뷰 크롤링을 셀 단위로 테스트하는 주피터 노트북. 드라이버를 열린 상태로 유지하며 각 단계를 순서대로 확인할 수 있다.

---

## 히어로 카드 생성 (`generate/`)

### 카드 종류

| 파일 | 출력 파일명 | 내용 |
|---|---|---|
| `generate_html_hero.py` | `hero_{channel}.html` | 히어로 선정 이유 + 제품 정보 텍스트 카드 |
| `generate_html_trend_monthly.py` | `trend_{channel}.html` | 주간 순위 추이 꺾은선 차트 |
| `generate_html_hero_review.py` | `hero_review_{channel}.html` | 리뷰(또는 좋아요) 수 주간 추이 차트 + 비교 라인 |
| `generate_html_weekly_trend.py` | `weekly_trend_{channel}.html` | 순위+리뷰 정규화 듀얼 꺾은선 차트 (월간 히어로 1p) |

### 주간 순위+리뷰 추이 카드 (`generate_html_weekly_trend.py`)

**레이아웃 (1080×1350)**:
- 상단 바: 인스타그램 아이콘 + 계정명 / 출처 텍스트
- 헤더: 채널 로고 이미지(`hero-logo`) / `trend-title-lines` — `{월}월` + `HERO`
- 메인: 제품 원형 이미지(좌상단) + 브랜드명 + matplotlib 듀얼 꺾은선 차트 (base64 PNG)

**차트 (`build_chart_b64`)** — 1080×1050px (`figsize=(10.8, 10.5), dpi=100`):
- **순위선**: `#EF402F`, 두께 8, scipy cubic spline 곡선, 속빈 원 마커, 그림자, 레이블 항상 위
  - Y정규화: `0.1 + (max_rank - rank) / range * 0.8` → 1위=0.9, 낮은순위=0.1
- **리뷰선**: `#4590CA`, 두께 8, scipy cubic spline 곡선, 속빈 원 마커, 그림자, 레이블 항상 아래
  - Y정규화: `(review - min) / range * 0.8` → min=0, max=0.8
  - oliveyoung(리뷰 컬럼 없음) 등 데이터 없을 시 자동 생략
- **공통**: Y축 숨김, X축 MM/DD 날짜 표시, X축 하단선 검은색, Y축 수평 점선 그리드
- **범례**: X축 우측 하단 — 순위(빨강) / 리뷰수 or 좋아요(파랑)
- **스플라인**: `scipy.interpolate.make_interp_spline`, `k=min(3, n-1)` (데이터 수 자동 적응)
- **레이블 path_effects**: `pe.withStroke(linewidth=2, foreground=각색)` — 외곽선으로 가독성 강화

**데이터 소스**: `data/hero/YYYY_MM/{channel}.xlsx` → `weekly` 시트 + `summary` 시트

**헤더 구조**: `generate_html_trend.py`와 동일 CSS 클래스 사용
- `hero-left`: `<img class="hero-logo">` (채널 로고)
- `hero-right trend-hero-right` > `trend-title-lines` > `trend-title-type`(월) + `trend-title-brand`(HERO)

---

### 히어로 리뷰 추이 카드 (`generate_html_hero_review.py`)

**레이아웃 (1080×1350)**:
- 상단 바: 인스타그램 아이콘 + 계정명 / 출처 텍스트
- 헤더: 채널명 대형 컬러 텍스트(좌) + `{월}월 / HERO` (우, HERO는 빨강)
- 메인: matplotlib 꺾은선 차트 (base64 PNG 임베드)
  - 히어로 제품: 채널 색상 굵은 선 + 면적 채우기 (alpha=0.25)
  - 비교 제품들: 회색 얇은 선 (naver_daily 시트에서 로드, 최대 20개)
- 제품 이미지: 원형 오버레이 (차트 좌상단, border-radius 50%)

**데이터 소스**:
- `data/hero/YYYY_MM/{channel}.xlsx` → `weekly` 시트: 히어로 제품 주간 metric
- `data/monthly/YYYY_MM_monthly.xlsx` → `{channel}_daily` 시트: 비교 라인용

**지원 채널**: naver(review), coupang(review), daiso(review), kakao(like)  
oliveyoung은 review/like 컬럼 없으므로 미지원.

**채널 색상** (`CHANNEL_COLORS`):

| 채널 | 색상 |
|---|---|
| naver | #03C75A |
| coupang | #FF4C00 |
| oliveyoung | #00A651 |
| kakao | #F7D300 |
| daiso | #E60012 |

### 차트 생성 공통 패턴

모든 generate 모듈은 matplotlib으로 차트를 생성하고 base64 PNG로 HTML에 임베드한다.
CDN 의존성 없이 오프라인에서 동작해야 한다.

```python
buf = io.BytesIO()
fig.savefig(buf, format="png", dpi=100, bbox_inches="tight", facecolor="#ffffff")
plt.close(fig)
buf.seek(0)
chart_b64 = base64.b64encode(buf.read()).decode("utf-8")
# HTML에 삽입: <img src="data:image/png;base64,{chart_b64}" />
```

---

## 데이터 경로 구조

```
data/
├── raw/      ← 크롤링 원본 CSV + 이미지
│   └── {channel}/
│       ├── {YYYYMMDD}.csv
│       └── {YYYYMMDD}/{rank:02d}.jpg|png
├── report/   ← 일별 ranking.xlsx  (crawling/report.py)
├── output/   ← 인스타그램 카드 HTML + PNG
│   └── {YYYY_MM}_monthly/
│       ├── hero_{channel}.html
│       ├── trend_{channel}.html
│       └── hero_review_{channel}.html
├── monthly/  ← 월간 집계 (aggregate.py 출력)
│   └── {YYYY_MM}_monthly.xlsx
└── hero/     ← 히어로 제품 상세 파일 (export.py 출력)
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

### 카카오 이미지 크롤링 (`crawling/channels/kakao.py`)

#### 이미지 URL 구조

카카오 채널의 이미지 URL은 두 가지 패턴이 존재한다.

| 패턴 | URL 예시 | 설명 |
|---|---|---|
| CDN URL (정상) | `https://img1.kakaocdn.net/thumb/C175x175@2x.fwebp.q82/?fname=https%3A%2F%2Fst.kakaocdn.net%2F...{파일}.jpg` | CDN이 원본(jpg/png)을 webp로 변환하여 서빙. URL path에 확장자 없어 `.jpg`로 저장됨 (정상 동작) |
| Fallback URL (비정상) | `https://st.kakaocdn.net/commerce_ui/static/common_module/default_fallback_thumbnail.png` | 974 bytes 크기의 placeholder 이미지. lazy loading 미로드 시 발생 |

점진적 재스크롤로 실제 CDN URL이 로드되므로 정상 운영 시 발생하지 않는다. 만약 발생하면 `kakao_pre_actions`의 스크롤 대기 시간을 늘릴 것.

#### 카카오 img 태그 구조

카카오 제품 카드의 실제 img 태그: `<img cuimg="" uselazyloading="" alt="" class="img_thumb" src="CDN URL">`
`uselazyloading` 속성이 카카오 자체 JS lazy loading을 트리거. `data-src` 등 별도 속성 없이 `src` 자체가 lazy loading 대상.

#### `get_img_url()` 탐색 로직

카드 내 이미지를 **셀렉터 → 속성** 2단계로 탐색한다.

1. **셀렉터 순서**: `.inner_thumb img` → `.inner_thumb` → `img` (첫 매칭에서 중단)
2. **속성 우선순위**: `data-src` > `data-original` > `data-lazy-src` > `src`

`src`에 fallback이 들어있을 수 있으므로 lazy loading 속성을 우선한다.

#### lazy loading 처리 순서 (`kakao_pre_actions`)

순서 변경 시 수집 수량이 500개 → 20개로 급감하므로 반드시 아래 순서를 유지한다.

1. **스크롤 먼저** — `window.scrollTo(0, scrollHeight)` 반복으로 무한스크롤 트리거 (500개 목표)
2. **zoom 50% 적용** — `document.body.style.zoom='50%'`  
   zoom을 스크롤보다 먼저 하면 레이아웃 재계산으로 무한스크롤이 충분히 트리거되지 않음
3. **점진적 재스크롤** — zoom 적용으로 lazy loading이 리셋되므로 맨 위(0)부터 500px 간격, 0.3초 대기로 점진적 스크롤. 한 번에 점프하면 lazy loading 옵저버가 트리거되지 않음

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

### 8. `monthly/review_config.py`

review 또는 like 컬럼이 있는 채널이라면 `REVIEW_SELECTORS`에 셀렉터 추가.

### 9. `generate/generate_html_hero_review.py`

`REVIEW_CHANNEL_CONFIG`에 채널 설정 추가 (metric: "review" 또는 "like").

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
- `monthly/` 스크립트도 동일하게 `monthly/` 디렉토리 안에서 실행.
- `run.py` / `run_monthly.py`는 `subprocess` 또는 import로 각 스크립트를 적절한 cwd에서 실행하므로 루트에서 실행해도 안전.

## ChromeDriver

- **크롤링**: `driver/chromedriver-win64/chromedriver.exe` 번들 + `undetected_chromedriver` (version_main=146)
- **PNG 변환**: `webdriver_manager`가 Chrome 버전에 맞는 드라이버 자동 설치 (크롤링과 다른 드라이버)
- Chrome 업데이트 시 번들 드라이버 교체 + `core/browser.py`의 `version_main` 갱신 필요

## 로그

- 일별 파이프라인: `run.txt`
- 월간 파이프라인 + 리뷰 크롤링: `run_monthly.txt`  
  (`crawl_reviews.py`는 run_monthly.py와 동일한 파일에 append 기록)
