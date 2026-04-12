import re
import time
from urllib.parse import urljoin

from config import CHANNEL_PATHS
from core.runner import run_channel

URL = "https://gift.kakao.com/ranking/category/8"


def parse_like(text):
    if text is None:
        return 0

    text = str(text).strip().replace(",", "").replace("+", "")

    if not text:
        return 0

    if "만" in text:
        return int(float(text.replace("만", "")) * 10000)

    match = re.search(r"\d+", text)
    return int(match.group()) if match else 0


def kakao_pre_actions(driver):
    
    last_height = driver.execute_script("return document.body.scrollHeight")

    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)

        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

    driver.execute_script("window.scrollTo(0, 0);")
    time.sleep(2)

    driver.execute_script("document.body.style.zoom='50%'")
    time.sleep(2)


def find_card(item):
    for parent in item.parents:
        if parent.select_one("gc-link") or parent.select_one(".img_thumb") or parent.select_one("img"):
            return parent
    return item


def get_img_url(card):
    selectors = [".img_thumb img", ".img_thumb", "img"]

    for selector in selectors:
        img_tag = card.select_one(selector)
        if not img_tag:
            continue

        img_url = (
            img_tag.get("src")
            or img_tag.get("data-src")
            or img_tag.get("data-original")
            or img_tag.get("data-lazy-src")
        )

        if img_url:
            return img_url  # urljoin 불필요 (save_images에서 처리 안 하므로 절대 URL 그대로 사용)

    return None


def parse_kakao(soup, today):
    data = []
    ranking = soup.select(".info_prd")

    for item in ranking:
        card = find_card(item)

        gc_tag = card.select_one("gc-link")
        tiara_code = gc_tag.get("data-tiara-area-code", "") if gc_tag else ""

        if "product_ad" in tiara_code or "product_ad" in str(card):
            continue

        a_tag = item.select_one("a.link_info")
        href = a_tag["href"] if a_tag and a_tag.has_attr("href") else ""

        match = re.search(r"/product/(\d+)", href)
        code = match.group(1) if match else None

        brand_tag = item.select_one(".txt_brand")
        product_tag = item.select_one(".txt_prdname")
        price_tag = item.select_one(".num_price")
        like_tag = item.select_one(".num_wsh")

        if not code or not product_tag or not price_tag:
            continue

        brand = brand_tag.get_text(strip=True).split()[0] if brand_tag else "N/A"
        product = product_tag.get_text(strip=True)

        price_text = price_tag.get_text(strip=True) if price_tag else ""
        price = int(re.sub(r"[^\d]", "", price_text)) if price_text else 0

        like_text = like_tag.get_text(strip=True) if like_tag else ""
        like = parse_like(like_text)

        data.append({
            "date": today,
            "code": str(code),
            "brand": brand,
            "product": product,
            "price": price,
            "like": like,
            "img_url": get_img_url(card),
        })

    return data


def post_process_kakao(data):
    ordered = []
    for idx, row in enumerate(data, start=1):
        ordered.append({
            "date": row["date"],
            "code": row["code"],
            "rank": idx,
            "brand": row["brand"],
            "product": row["product"],
            "price": row["price"],   # CSV엔 있지만 순서 뒤로
            "like": row["like"],
            "img_url": row["img_url"],
        })
    return ordered


def run():
    return run_channel(
        channel_name="kakao",
        url=URL,
        base_dir=CHANNEL_PATHS["kakao"],
        parse_func=parse_kakao,
        image_selector=None,
        pre_actions=kakao_pre_actions,
        post_process_func=post_process_kakao,
    )


if __name__ == "__main__":
    run()