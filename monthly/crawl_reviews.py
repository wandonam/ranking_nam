"""
monthly/crawl_reviews.py
-------------------------
히어로 제품 리뷰 크롤링 모듈

data/hero/YYYY_MM/{channel}.xlsx 의 summary 시트에서 url 을 읽어
채널별 셀렉터로 리뷰를 파싱하고 reviews 시트를 갱신한다.

단독 실행:
    python crawl_reviews.py
    python crawl_reviews.py --month 2026-04
    python crawl_reviews.py --month 2026-04 --interactive
"""

import argparse
import logging
import pickle
import sys
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

ROOT         = Path(__file__).parent.parent
CRAWLING_DIR = ROOT / "crawling"
HERO_DIR     = ROOT / "data" / "hero"
COOKIES_DIR  = Path(__file__).parent / "cookies"
LOG_FILE     = ROOT / "run_monthly.txt"

# ──────────────────────────────────────────────
# 로깅 설정 (run_monthly.py 와 동일 파일에 기록)
# ──────────────────────────────────────────────
_fmt     = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
_console = logging.StreamHandler()
_console.setFormatter(_fmt)
_file    = logging.FileHandler(LOG_FILE, encoding="utf-8")
_file.setFormatter(_fmt)
logging.basicConfig(level=logging.INFO, handlers=[_console, _file])
logger = logging.getLogger(__name__)

# 채널별 쿠키 저장 시 먼저 방문할 도메인
COOKIE_DOMAIN = {
    "naver": "https://www.naver.com",
}

sys.path.insert(0, str(CRAWLING_DIR))
from core.browser import create_driver, dismiss_popups, safe_click  # noqa: E402

from review_config import REVIEW_SELECTORS  # noqa: E402

CHANNELS = ["naver", "coupang", "oliveyoung", "kakao", "daiso"]


# ──────────────────────────────────────────────
# 쿠키 저장 / 로드
# ──────────────────────────────────────────────

def save_cookies(channel: str) -> None:
    """브라우저를 열고 직접 로그인한 뒤 쿠키를 저장한다. 최초 1회 실행."""
    domain = COOKIE_DOMAIN.get(channel)
    if not domain:
        logger.warning(f"[{channel}] COOKIE_DOMAIN 미등록 채널")
        return

    COOKIES_DIR.mkdir(exist_ok=True)
    driver = create_driver()
    try:
        driver.get(domain)
        logger.info(f"[{channel}] 브라우저에서 로그인 후 Enter를 누르세요...")
        input()
        cookie_path = COOKIES_DIR / f"{channel}.pkl"
        with open(cookie_path, "wb") as f:
            pickle.dump(driver.get_cookies(), f)
        logger.info(f"[{channel}] 쿠키 저장 완료: {cookie_path}")
    finally:
        driver.quit()


def load_cookies(driver, channel: str) -> bool:
    """저장된 쿠키를 드라이버에 주입한다. 쿠키 파일 없으면 False 반환."""
    cookie_path = COOKIES_DIR / f"{channel}.pkl"
    if not cookie_path.exists():
        return False

    domain = COOKIE_DOMAIN.get(channel)
    if domain:
        driver.get(domain)   # 쿠키 도메인 맞추기 위해 먼저 방문

    with open(cookie_path, "rb") as f:
        for cookie in pickle.load(f):
            try:
                driver.add_cookie(cookie)
            except Exception:
                pass
    return True


# ──────────────────────────────────────────────
# 채널별 pre_actions
# ──────────────────────────────────────────────

def naver_pre_actions(driver, sel: dict) -> None:
    """
    1. 배율 50% 축소
    2. review_btn scrollIntoView → JS 클릭
    3. wait_selector로 모달 로드 대기
    4. 컨테이너 기반 무한스크롤
    """
    # 1. zoom 먼저
    driver.execute_script("document.body.style.zoom='50%'")
    time.sleep(0.5)

    # 2. scrollIntoView 후 JS 클릭
    if sel.get("review_btn"):
        try:
            btn = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, sel["review_btn"]))
            )
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
            time.sleep(0.5)
            driver.execute_script("arguments[0].click();", btn)
            logger.info("[naver] 리뷰전체보기 클릭")
        except Exception as e:
            logger.error(f"[naver] 리뷰전체보기 버튼 처리 실패: {e}")
            return

    # 3. 모달 로드 대기
    if sel.get("wait_selector"):
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, sel["wait_selector"]))
        )

    # 4. 컨테이너 기반 무한스크롤
    container_sel = sel.get("scroll_container", "")
    last_height = 0
    while True:
        if container_sel:
            driver.execute_script(
                f"var el=document.querySelector('{container_sel}'); if(el) el.scrollTop=el.scrollHeight;"
            )
            time.sleep(2)
            new_height = driver.execute_script(
                f"var el=document.querySelector('{container_sel}'); return el ? el.scrollHeight : 0;"
            )
        else:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(2)
            new_height = driver.execute_script("return document.body.scrollHeight")

        if new_height == last_height:
            break
        last_height = new_height


# 채널명 → pre_actions 함수 매핑 (구현된 채널만 등록)
PRE_ACTIONS: dict = {
    "naver": naver_pre_actions,
}


def _extract_text(element, selector: str) -> str:
    """soup 요소에서 셀렉터로 텍스트 추출. 없으면 빈 문자열."""
    if not selector:
        return ""
    found = element.select_one(selector)
    return found.get_text(strip=True) if found else ""


def wait_for_manual_intervention(url: str, reason: str) -> bool:
    """
    사용자에게 수동 개입을 요청하고 Enter 대기.

    Returns:
        True  → 현재 브라우저 상태에서 파싱 계속
        False → 해당 채널 건너뜀
    """
    print(f"\n{'='*60}")
    print(f"[수동 개입 필요] {reason}")
    print(f"URL: {url}")
    print(f"브라우저에서 해당 페이지를 준비한 후 Enter 누르세요.")
    print(f"건너뛰려면 'skip' 입력.")
    print(f"{'='*60}")
    resp = input("> ").strip().lower()
    return resp != "skip"


def _parse_reviews(driver, sel: dict) -> list[dict]:
    """현재 driver 상태에서 리뷰를 파싱해 반환. crawl_channel_reviews의 재시도에서도 호출 가능."""
    reviews = []
    max_pages = int(sel.get("max_pages", 1))

    for page in range(max_pages):
        soup = BeautifulSoup(driver.page_source, "html.parser")
        blocks = soup.select(sel["container"])

        for block in blocks:
            reviews.append({
                "review_date": _extract_text(block, sel["date"]),
                "rating":      _extract_text(block, sel["rating"]),
                "reviewer":    _extract_text(block, sel["reviewer"]),
                "content":     _extract_text(block, sel["content"]),
            })

        if page < max_pages - 1 and sel.get("next_btn"):
            clicked = safe_click(driver, sel["next_btn"])
            if not clicked:
                break

    return reviews


def crawl_channel_reviews(
    channel: str, url: str, sel: dict, interactive: bool = False
) -> list[dict]:
    """
    브라우저로 url 접속 → 리뷰 파싱 → list[dict] 반환.

    sel 키: wait_selector, container, date, rating, reviewer,
            content, next_btn, max_pages

    interactive=True: 크롤링 시작 전 사용자가 브라우저를 직접 준비하는 proactive 모드.
                      False(기본): 실패 시에만 수동 개입을 요청하는 reactive 모드.
    """
    driver = None
    try:
        driver = create_driver()

        # 쿠키 로드 (파일 있을 때만, 없으면 비로그인으로 진행)
        loaded = load_cookies(driver, channel)
        if loaded:
            logger.info(f"[{channel}] 쿠키 로드 완료")
        else:
            logger.warning(f"[{channel}] 쿠키 파일 없음 — 비로그인 상태로 진행 (봇 차단 가능성 있음)")

        if interactive:
            # Proactive 모드: 자동 접속 없이 사용자가 먼저 페이지 준비
            if not wait_for_manual_intervention(url, f"[{channel}] 크롤링 준비 — 브라우저에서 페이지를 열어주세요"):
                return []
            # 사용자가 이미 준비한 상태 → driver.get() 생략, pre_actions만 실행
        else:
            # Reactive 모드: 자동 접속 시도
            try:
                driver.get(url)
                time.sleep(3)
                dismiss_popups(driver)
            except Exception as e:
                logger.error(f"[{channel}] 페이지 로드 실패: {e}")
                if not wait_for_manual_intervention(url, f"페이지 로드 실패: {e}"):
                    return []
                # 사용자가 수동으로 준비 → 현재 상태에서 계속

        # pre_actions: 버튼 클릭 + 모달 대기 + 스크롤 등 채널별 처리
        pre_actions = PRE_ACTIONS.get(channel)
        if pre_actions:
            pre_actions(driver, sel)

        reviews = _parse_reviews(driver, sel)

        # 0건 수집 시 재시도 기회 제공 (reactive 모드에서도 동작)
        if len(reviews) == 0:
            logger.warning(f"[{channel}] 리뷰 0건 — 쿠키 만료 또는 봇 차단 가능성")
            if wait_for_manual_intervention(url, f"[{channel}] 리뷰 0건 — 페이지 상태를 확인하고 준비되면 Enter"):
                if pre_actions:
                    pre_actions(driver, sel)
                reviews = _parse_reviews(driver, sel)

        return reviews

    except Exception as e:
        logger.error(f"[{channel}] 리뷰 크롤링 오류: {e}")
        return []
    finally:
        if driver is not None:
            driver.quit()


def run(year: int, month: int, interactive: bool = False) -> None:
    """
    채널별 hero xlsx에서 url 읽어 리뷰 크롤링 후 reviews 시트 갱신.

    interactive=True 시 각 채널 크롤링 전 사용자가 브라우저를 직접 준비하는 proactive 모드.
    """
    hero_dir = HERO_DIR / f"{year}_{month:02d}"

    for channel in CHANNELS:
        xlsx_path = hero_dir / f"{channel}.xlsx"

        if not xlsx_path.exists():
            logger.info(f"[{channel}] 파일 없음, 건너뜀: {xlsx_path}")
            continue

        sel = REVIEW_SELECTORS.get(channel, {})
        if not sel.get("wait_selector"):
            logger.info(f"[{channel}] 셀렉터 미설정, 건너뜀")
            continue

        # summary 시트에서 url 읽기
        try:
            summary_df = pd.read_excel(xlsx_path, sheet_name="summary")
        except Exception as e:
            logger.error(f"[{channel}] summary 시트 읽기 실패: {e}")
            continue

        if "url" not in summary_df.columns or summary_df.empty:
            logger.warning(f"[{channel}] url 컬럼 없음, 건너뜀")
            continue

        url = str(summary_df.iloc[0]["url"]).strip()
        if not url.startswith("http"):
            logger.warning(f"[{channel}] 유효하지 않은 url, 건너뜀: {url}")
            continue

        logger.info(f"[{channel}] 리뷰 크롤링 시작: {url}")
        reviews = crawl_channel_reviews(channel, url, sel, interactive=interactive)

        reviews_df = pd.DataFrame(
            reviews,
            columns=["review_date", "rating", "reviewer", "content"],
        )

        try:
            with pd.ExcelWriter(
                xlsx_path,
                engine="openpyxl",
                mode="a",
                if_sheet_exists="replace",
            ) as writer:
                reviews_df.to_excel(writer, sheet_name="reviews", index=False)
            logger.info(f"[{channel}] 리뷰 {len(reviews_df)}건 저장 완료")
        except Exception as e:
            logger.error(f"[{channel}] reviews 시트 저장 실패: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="히어로 제품 리뷰 크롤링")
    parser.add_argument("--month",       default=None, help="YYYY-MM (기본값: 전월)")
    parser.add_argument("--channel",     default=None, help="단일 채널 테스트 (예: naver)")
    parser.add_argument("--url",         default=None, help="직접 URL 지정 (--channel 필수)")
    parser.add_argument("--save-cookies",dest="save_cookies", default=None,
                        metavar="CHANNEL", help="쿠키 저장 (예: --save-cookies naver)")
    parser.add_argument("--interactive", action="store_true",
                        help="채널별 크롤링 전 수동 페이지 준비 대기 (proactive 모드)")
    args = parser.parse_args()

    # 쿠키 저장 모드
    if args.save_cookies:
        save_cookies(args.save_cookies)

    # 단일 URL 테스트 모드
    elif args.url:
        if not args.channel:
            logger.warning("--url 사용 시 --channel 을 함께 지정해야 합니다.")
        else:
            sel = REVIEW_SELECTORS.get(args.channel, {})
            reviews = crawl_channel_reviews(args.channel, args.url, sel, interactive=args.interactive)
            logger.info(f"수집된 리뷰 {len(reviews)}건:")
            for i, r in enumerate(reviews[:5], 1):
                logger.info(f"  [{i}] {r['reviewer']} | {r['rating']} | {r['review_date']}")
                logger.info(f"       {r['content'][:60]}")
    # 전체 또는 월별 실행 모드
    else:
        if args.month:
            y, m = map(int, args.month.split("-"))
        else:
            now = datetime.now()
            m = now.month - 1 or 12
            y = now.year if now.month > 1 else now.year - 1

        run(y, m, interactive=args.interactive)
