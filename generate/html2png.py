"""
html2png.py
------------
HTML 카드 → PNG 일괄 변환 모듈 (1080×1350)
.card 요소를 정확히 크롭하여 저장합니다.

단독 실행:
    python html2png.py
    python html2png.py --date 20250403
    python html2png.py --date 20250403 --input ./result
"""

import logging
import os
import time
from datetime import datetime
from io import BytesIO

from PIL import Image
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# 설정
# ──────────────────────────────────────────────
TARGET_W, TARGET_H = 1080, 1350
PAGE_LOAD_WAIT     = 1.5   # 초 — 페이지 렌더링 대기
RESIZE_WAIT        = 0.3   # 초 — 윈도우 리사이즈 후 대기

# 변환 대상 파일 목록 (generate_html.py의 CHANNEL_CONFIG·CARD_SPLITS와 동기화)
HTML_FILE_NAMES = [
    "01_naver (1).html",
    "01_naver (2).html",
    "02_coupang (1).html",
    "02_coupang (2).html",
    "03_oliveyoung (1).html",
    "03_oliveyoung (2).html",
    "04_kakao (1).html",
    "04_kakao (2).html",
    "05_daiso (1).html",
    "05_daiso (2).html",
    # 트렌드 카드 (급상승 / 급하락)
    "01_naver_hot.html",
    "01_naver_down.html",
    "02_coupang_hot.html",
    "02_coupang_down.html",
    "03_oliveyoung_hot.html",
    "03_oliveyoung_down.html",
    "04_kakao_hot.html",
    "04_kakao_down.html",
    "05_daiso_hot.html",
    "05_daiso_down.html",
]


# ──────────────────────────────────────────────
# 드라이버
# ──────────────────────────────────────────────
def make_driver() -> webdriver.Chrome:
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--hide-scrollbars")
    options.add_argument("--force-device-scale-factor=1")
    options.add_argument(f"--window-size={TARGET_W + 200},{TARGET_H + 500}")
    return webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options,
    )


# ──────────────────────────────────────────────
# 캡처
# ──────────────────────────────────────────────
def capture_html(driver: webdriver.Chrome, html_path: str) -> str:
    """
    HTML 파일을 렌더링하고 .card 요소를 PNG로 저장.
    반환값: 저장된 PNG 경로
    """
    base_name   = os.path.splitext(os.path.basename(html_path))[0]
    output_path = os.path.join(os.path.dirname(html_path), base_name + ".png")
    abs_path    = os.path.abspath(html_path)

    driver.get(f"file:///{abs_path}")
    time.sleep(PAGE_LOAD_WAIT)

    try:
        card = driver.find_element(By.CLASS_NAME, "card")
        rect = driver.execute_script(
            """
            const r = arguments[0].getBoundingClientRect();
            return {x: r.left, y: r.top, w: r.width, h: r.height};
            """,
            card,
        )

        x, y, w, h = int(rect["x"]), int(rect["y"]), int(rect["w"]), int(rect["h"])
        logger.debug(f"  .card rect → x={x}, y={y}, w={w}, h={h}")

        driver.set_window_size(w + 200, max(y + h + 10, TARGET_H + 200))
        time.sleep(RESIZE_WAIT)

        img = Image.open(BytesIO(driver.get_screenshot_as_png())).crop((x, y, x + w, y + h))

    except Exception as e:
        logger.warning(f"  .card 탐색 실패 ({e}) → 전체 화면 캡처 사용")
        img = Image.open(BytesIO(driver.get_screenshot_as_png()))

    if img.size != (TARGET_W, TARGET_H):
        img = img.resize((TARGET_W, TARGET_H), Image.LANCZOS)

    img.save(output_path, "PNG", optimize=True)
    return output_path


# ──────────────────────────────────────────────
# 일괄 실행
# ──────────────────────────────────────────────
def run(today: str, input_dir: str) -> dict[str, int]:
    """
    HTML → PNG 일괄 변환.
    반환값: {"success": N, "fail": N}
    """
    folder = os.path.join(input_dir, today)
    logger.info(f"[PNG] 대상 폴더: {folder}")

    driver  = make_driver()
    success, fail = 0, 0

    try:
        for fname in HTML_FILE_NAMES:
            html_path = os.path.join(folder, fname)

            if not os.path.exists(html_path):
                logger.warning(f"파일 없음: {fname}")
                fail += 1
                continue

            try:
                out = capture_html(driver, html_path)
                logger.info(f"✅ {fname} → {os.path.basename(out)}")
                success += 1
            except Exception as e:
                logger.error(f"❌ {fname} 실패: {e}")
                fail += 1
    finally:
        driver.quit()

    logger.info(f"[PNG] 완료 — 성공 {success}개 / 실패 {fail}개")
    return {"success": success, "fail": fail}


def run_folder(folder: str) -> dict[str, int]:
    """
    지정된 폴더 내 모든 HTML 파일을 PNG로 변환.
    월간 파이프라인(run_monthly.py)에서 사용.
    반환값: {"success": N, "fail": N}
    """
    html_files = sorted(f for f in os.listdir(folder) if f.endswith(".html"))
    logger.info(f"[PNG] 대상 폴더: {folder} ({len(html_files)}개)")

    driver = make_driver()
    success, fail = 0, 0

    try:
        for fname in html_files:
            html_path = os.path.join(folder, fname)
            try:
                out = capture_html(driver, html_path)
                logger.info(f"✅ {fname} → {os.path.basename(out)}")
                success += 1
            except Exception as e:
                logger.error(f"❌ {fname} 실패: {e}")
                fail += 1
    finally:
        driver.quit()

    logger.info(f"[PNG] 완료 — 성공 {success}개 / 실패 {fail}개")
    return {"success": success, "fail": fail}


# ──────────────────────────────────────────────
# 단독 실행 진입점
# ──────────────────────────────────────────────
if __name__ == "__main__":
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    parser = argparse.ArgumentParser(description="HTML 카드 → PNG 변환")
    parser.add_argument("--date",  default=None,       help="날짜 YYYYMMDD (기본값: 오늘)")
    parser.add_argument("--input", default="./result", help="HTML 파일이 있는 루트 디렉토리")
    args = parser.parse_args()

    today = args.date or datetime.today().strftime("%Y%m%d")
    run(today=today, input_dir=args.input)
