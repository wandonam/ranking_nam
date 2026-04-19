import time
import random
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException

from core.browser import create_driver, close_driver, dismiss_popups
from core.io import get_today, ensure_dir, save_csv
from core.image import save_images

_WAIT_TIMEOUT = 20   # 페이지 주요 요소 대기 최대 시간(초)
_RETRY_DELAYS = [15, 30]  # 재시도 간 대기 시간(초)


def run_channel(
    channel_name: str,
    url: str,
    base_dir,
    parse_func,
    wait_selector: str = None,
    image_selector: str = None,
    pre_actions=None,
    post_process_func=None,
    max_retries: int = 2,
    popup_selectors: list = None,
):
    today = get_today()
    img_dir = ensure_dir(base_dir / today)
    csv_path = base_dir / f"{today}.csv"

    for attempt in range(max_retries + 1):
        driver = create_driver()
        try:
            driver.get(url)

            # 페이지 유효성 검증: 주요 요소가 로드될 때까지 대기
            if wait_selector:
                try:
                    WebDriverWait(driver, _WAIT_TIMEOUT).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, wait_selector))
                    )
                except TimeoutException:
                    print(f"[경고] {channel_name}: 페이지 로드 실패 (봇 감지 의심) — 시도 {attempt + 1}/{max_retries + 1}")
                    close_driver(driver)
                    if attempt < max_retries:
                        delay = _RETRY_DELAYS[min(attempt, len(_RETRY_DELAYS) - 1)]
                        print(f"[재시도] {channel_name}: {delay}초 후 재시도")
                        time.sleep(delay)
                        continue
                    else:
                        print(f"[실패] {channel_name}: 최대 재시도 횟수 초과")
                        return None
            else:
                time.sleep(random.uniform(6.2, 13.2))

            # 랜덤 팝업 제거 (채널별 셀렉터 우선 시도)
            dismiss_popups(driver, extra_selectors=popup_selectors)

            if pre_actions:
                pre_actions(driver)

            soup = BeautifulSoup(driver.page_source, "html.parser")
            data = parse_func(soup, today)

            if post_process_func:
                data = post_process_func(data)

            if data:
                period_ym = (
                    datetime.strptime(str(today), "%Y%m%d") - timedelta(days=4)
                ).strftime("%Y%m")
                for row in data:
                    row["period_ym"] = period_ym

            save_csv(data, csv_path)

            if image_selector:
                img_tags = soup.select(image_selector)
                save_images(img_tags, img_dir, current_url=driver.current_url)
            elif data:
                img_urls = [row["img_url"] for row in data if row.get("img_url")]
                save_images(img_urls, img_dir)

            print(f"[완료] {channel_name}")
            return data

        except Exception as e:
            print(f"[실패] {channel_name}: {e}")
            return None

        finally:
            close_driver(driver)
