import time
import random
from bs4 import BeautifulSoup

from core.browser import create_driver, close_driver
from core.io import get_today, ensure_dir, save_csv
from core.image import save_images

def run_channel(
    channel_name: str,
    url: str,
    base_dir,
    parse_func,
    image_selector: str = None,
    pre_actions=None,
    post_process_func=None,
):
    today = get_today()
    img_dir = ensure_dir(base_dir / today)
    csv_path = base_dir / f"{today}.csv"

    driver = create_driver()

    try:
        driver.get(url)
        time.sleep(random.uniform(6.2, 13.2))

        if pre_actions:
            pre_actions(driver)

        soup = BeautifulSoup(driver.page_source, "html.parser")
        data = parse_func(soup, today)

        if post_process_func:
            data = post_process_func(data)

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