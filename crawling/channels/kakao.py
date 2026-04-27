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
    # 1) 무한스크롤로 전체 상품 로드
    last_height = driver.execute_script("return document.body.scrollHeight")

    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)

        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

    # 2) zoom 적용
    driver.execute_script("document.body.style.zoom='50%'")
    time.sleep(2)

    # 3) zoom 후 점진적 재스크롤 — lazy loading 옵저버 트리거
    driver.execute_script("window.scrollTo(0, 0);")
    time.sleep(0.5)
    scroll_height = driver.execute_script("return document.body.scrollHeight")
    current = 0
    while current < scroll_height:
        current += 500
        driver.execute_script(f"window.scrollTo(0, {current});")
        time.sleep(0.3)
    time.sleep(1)


def find_card(item):
    for parent in item.parents:
        if parent.select_one("gc-link") or parent.select_one(".inner_thumb") or parent.select_one("img"):
            return parent
    return item


def get_img_url(card):
    selectors = [".inner_thumb img", ".inner_thumb", "img"]

    for selector in selectors:
        img_tag = card.select_one(selector)
        if not img_tag:
            continue

        img_url = (
            img_tag.get("data-src")
            or img_tag.get("data-original")
            or img_tag.get("data-lazy-src")
            or img_tag.get("src")
        )

        if img_url:
            return img_url

    return None


def parse_kakao(soup, today):
    data = []
    ranking = soup.select(".link_prdunit")

    for item in ranking:
        card = find_card(item)

        gc_tag = card.select_one("gc-link")
        tiara_code = gc_tag.get("data-tiara-area-code", "") if gc_tag else ""

        if "product_ad" in tiara_code or "product_ad" in str(card):
            continue

        href = item.get("href", "")

        match = re.search(r"/product/(\d+)", href)
        code = match.group(1) if match else None

        brand_tag = card.select_one(".area_prdbrand")
        product_tag = card.select_one(".txt_prdname")
        price_tag = card.select_one(".num_price")
        like_tag = card.select_one(".num_wish")

        if not code or not product_tag or not price_tag:
            continue

        brand = brand_tag.get_text(strip=True).split()[0] if brand_tag else "N/A"
        product = product_tag.get_text(strip=True)

        price_text = price_tag.get_text(strip=True) if price_tag else ""
        price = int(re.sub(r"[^\d]", "", price_text)) if price_text else 0

        like_text = like_tag.get_text(strip=True) if like_tag else ""
        like = parse_like(like_text)

        url = ("https://gift.kakao.com" + href) if href.startswith("/") else href

        data.append({
            "date": today,
            "code": str(code),
            "brand": brand,
            "product": product,
            "price": price,
            "like": like,
            "img_url": get_img_url(card),
            "url": url,
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
            "price": row["price"],
            "like": row["like"],
            "img_url": row["img_url"],
            "url": row["url"],
        })
    return ordered


def run():
    return run_channel(
        channel_name="kakao",
        url=URL,
        base_dir=CHANNEL_PATHS["kakao"],
        parse_func=parse_kakao,
        wait_selector=".link_prdunit",
        image_selector=None,
        pre_actions=kakao_pre_actions,
        post_process_func=post_process_kakao,
    )


if __name__ == "__main__":
    run()