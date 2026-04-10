from config import CHANNEL_PATHS
from core.runner import run_channel

URL = "https://snxbest.naver.com/product/best/buy?categoryId=50000023&sortType=PRODUCT_BUY&periodType=WEEKLY"

def parse_naver(soup, today):
    data = []
    ranking = soup.select(".productCardResponsive_information__CD_1n")

    for idx, item in enumerate(ranking, start=1):
        parent = item.find_parent("li")
        code = parent.get("data-shp-contents-id", "N/A") if parent else "N/A"

        brand_tag = item.select_one(".productCardResponsive_store__GaHMN")
        product_tag = item.select_one(".productCardResponsive_title__n77mU")
        price_tag = item.select_one(".productCardResponsive_number__cAjPl")
        star_tag = item.select_one(".productCardResponsive_rating___br2h")
        review_tag = item.select_one(".productCardResponsive_review__LkeRC")

        data.append({
            "date": today,
            "code": code,
            "rank": idx,
            "brand": brand_tag.text.strip() if brand_tag else "N/A",
            "product": product_tag.text.strip() if product_tag else "N/A",
            "price": price_tag.text.strip().replace(",", "") if price_tag else "N/A",
            "star": star_tag.text.strip().replace("별점", "") if star_tag else "N/A",
            "review": review_tag.text.strip().replace(",", "").replace("리뷰", "").replace("+", "") if review_tag else "N/A"
        })

    return data

def run():
    return run_channel(
        channel_name="naver",
        url=URL,
        base_dir=CHANNEL_PATHS["naver"],
        parse_func=parse_naver,
        image_selector=".productCardResponsive_thumbnail__ZDZh3 img",
    )

if __name__ == "__main__":
    run()