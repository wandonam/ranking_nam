# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 프로젝트 개요

건강식품 쇼핑몰 랭킹(네이버, 쿠팡, 올리브영, 카카오, 다이소)을 매일 자동 수집하고, 인스타그램용 랭킹 카드 이미지(PNG 1080×1350)를 생성하는 파이프라인.

## 실행 명령어

```bash
# 전체 파이프라인 실행 (루트에서)
python run.py

# 옵션
python run.py --date 20250403          # 특정 날짜
python run.py --channel naver          # naver만 크롤링 후 리포트+카드 전체 진행
python run.py --channel naver coupang # 여러 채널만 크롤링 후 전체 진행
python run.py --skip-crawl             # 크롤링 건너뜀 (리포트+카드만)
python run.py --skip-crawl-report      # 카드 생성만 (HTML→PNG)
python run.py --account MY_ACCOUNT     # 카드에 표시할 인스타그램 계정명

# 각 단계 개별 실행 (반드시 해당 디렉토리 안에서 실행)
cd crawling && python main.py          # 크롤링 전체
cd crawling && python main.py naver    # 특정 채널만
cd crawling && python report.py        # 엑셀 리포트 생성
cd generate && python main.py          # HTML 생성 + PNG 변환
cd generate && python html2png.py      # PNG 변환만
```

## 의존성 설치

```bash
pip install -r requirements.txt
```

## 3단계 파이프라인 구조

```
1단계: crawling/main.py   → data/raw/{channel}/{YYYYMMDD}.csv
                            data/raw/{channel}/{YYYYMMDD}/{rank:02d}.jpg
2단계: crawling/report.py → data/report/{YYYYMMDD}_ranking.xlsx
3단계: generate/main.py   → data/output/{YYYYMMDD}/*.html + *.png
```

### 1단계: 크롤링 (`crawling/`)

- `channels/{channel}.py` 각 채널별 파싱 로직 담당. `run_channel()`을 호출하는 `run()` 함수를 노출.
- `core/runner.py`의 `run_channel()` — Selenium으로 페이지 로드 후 BeautifulSoup 파싱 → CSV 저장 → 이미지 저장의 공통 흐름.
- `core/browser.py` — `undetected_chromedriver` 사용, 번들된 `driver/chromedriver-win64/chromedriver.exe` (version_main=146) 고정 사용.
- 새 채널 추가 시: `channels/{name}.py` 생성 → `crawling/main.py`의 `JOBS` 딕셔너리에 등록.

### 2단계: 리포트 (`crawling/report.py`)

- `data/raw/{channel}/` 폴더에서 최신 CSV 2개를 읽어 rank_diff(이전 순위 - 현재 순위, 양수=상승) 계산.
- Excel 시트 구성: `{channel}_10` (TOP10), `{channel}_hot` (급상승 ≥10), `{channel}_down` (급하락 ≤-10).

### 3단계: 카드 생성 (`generate/`)

- `generate_html.py` — Excel에서 채널별 시트를 읽어 각 5개씩 2장 분할된 HTML 카드 생성. `CHANNEL_CONFIG` 딕셔너리에서 채널별 레이블, 로고, 이미지 경로 템플릿, 표시 필드 관리.
- `generate_html_trend.py` — 급상승/급하락 카드 생성 (`{prefix}_hot.html`, `{prefix}_down.html`).
- `html2png.py` — headless Chrome으로 `.card` CSS 요소를 크롭하여 1080×1350 PNG 저장. `webdriver_manager`로 드라이버 자동 설치(crawling 단계와 다름).
- `HTML_FILE_NAMES` 목록(html2png.py)과 `CHANNEL_CONFIG`(generate_html.py)가 동기화되어야 함 — 채널 추가 시 양쪽 모두 수정 필요.

## 경로 규칙

- `crawling/config.py`와 `crawling/report.py`는 `../data/...` 상대 경로 사용 → **반드시 `crawling/` 디렉토리 안에서 실행**.
- 루트의 `config.py`는 전역 경로 상수 (현재 `run.py`에서는 미사용, 향후 참조용).
- `run.py`는 subprocess로 각 스크립트를 `cwd=CRAWLING_DIR` / `cwd=GENERATE_DIR`로 실행하므로 경로 문제 없음.

## ChromeDriver

- 크롤링: `driver/chromedriver-win64/chromedriver.exe` 번들 사용 (`undetected_chromedriver`, version_main=146).
- PNG 변환: `webdriver_manager`가 자동으로 Chrome 버전에 맞는 드라이버 설치.
- Chrome 브라우저 버전이 바뀌면 `core/browser.py`의 `version_main` 값 갱신 필요.
