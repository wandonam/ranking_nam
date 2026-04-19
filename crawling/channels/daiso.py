import re
import time
from urllib.parse import urlparse, parse_qs

from config import CHANNEL_PATHS
from core.browser import safe_click
from core.runner import run_channel

URL = "https://www.daisomall.co.kr/ds/rank/C105"

def daiso_pre_actions(driver):
    safe_click(
        driver,
        "#__layout > section > div.wrap.scrollArea > div > div > div.section.section-top > div.prod-category > div > div > div > div > button:nth-child(9)",
        label="daiso 카테고리 버튼",
    )
    time.sleep(2)

    safe_click(
        driver,
        "#__layout > section > div.wrap.scrollArea > div > div > div.section.section-top > div:nth-child(2) > div > div.add-ons > ul > li:nth-child(3) > button > span > span",
        label="daiso 정렬 버튼",
    )
    time.sleep(2)

    driver.execute_script("document.body.style.zoom='50%'")

    last_height = driver.execute_script("return document.body.scrollHeight")
    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)

        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

def parse_daiso(soup, today):
    data = []
    ranking = soup.select(".product-info")

    for idx, item in enumerate(ranking, start=1):
        a_tag = item.find_previous("a", class_="prod-thumb__link") or item.select_one("a.prod-thumb__link")
        href = a_tag.get("href", "") if a_tag else ""

        parsed = urlparse(href)
        params = parse_qs(parsed.query)
        code = params.get("pdNo", ["N/A"])[0]
        url = ("https://www.daisomall.co.kr" + parsed.path + ("?" + parsed.query if parsed.query else "")) if parsed.path else href

        brand = item.select_one(".product-title").text.split()[0]
        product = item.select_one(".product-title").text
        price = int(item.select_one(".value").text.replace(",", "").replace("원", ""))

        star_tag = item.select_one(".rating-star .hiddenText")
        if star_tag:
            star_text = star_tag.text.strip()
            star_match = re.search(r"\d+(\.\d+)?", star_text)
            star = float(star_match.group()) if star_match else None
        else:
            star = None

        review_tag = item.select_one(".star-detail")
        if review_tag:
            review_match = re.search(r"[\d,]+", review_tag.text)
            review = int(review_match.group().replace(",", "")) if review_match else 0
        else:
            review = 0

        data.append({
            "date": today,
            "code": code,
            "rank": idx,
            "brand": brand,
            "product": product,
            "price": price,
            "star": star,
            "review": review,
            "url": url,
        })

    return data

# 다이소 전용 팝업 닫기 셀렉터 (팝업 HTML 확인 후 추가)
_DAISO_POPUP_SELECTORS = [r"body > div > div.absolute.top-1\/2.flex.w-full.-translate-y-1\/2.justify-center > div > div > button:nth-child(2)"]

def run():
    return run_channel(
        channel_name="daiso",
        url=URL,
        base_dir=CHANNEL_PATHS["daiso"],
        parse_func=parse_daiso,
        wait_selector=".product-info",
        image_selector=".thumb-img",
        pre_actions=daiso_pre_actions,
        popup_selectors=_DAISO_POPUP_SELECTORS,
    )

if __name__ == "__main__":
    run()
