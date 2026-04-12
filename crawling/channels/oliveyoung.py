from config import CHANNEL_PATHS
from core.runner import run_channel


URL = "https://www.oliveyoung.co.kr/store/main/getBestList.do?dispCatNo=900000100100001&fltDispCatNo=10000020001"


def parse_oliveyoung(soup, today):
    data = []
    ranking = soup.select("li:has(a.prd_thumb):has(.prd_info)")

    for idx, item in enumerate(ranking, start=1):
        a_tag = item.select_one("a.prd_thumb")
        info_tag = item.select_one(".prd_info")

        code = a_tag.get("data-ref-goodsno", "N/A") if a_tag else "N/A"

        brand_tag = info_tag.select_one(".tx_brand") if info_tag else None
        product_tag = info_tag.select_one(".tx_name") if info_tag else None
        price_tag = info_tag.select_one(".prd_price") if info_tag else None

        brand = brand_tag.text.strip().split()[0] if brand_tag else "N/A"
        product = product_tag.text.strip() if product_tag else "N/A"

        if price_tag:
            price_text = price_tag.text.strip()
            price = (
                price_text
                .replace(",", "")
                .replace("원", "")
                .replace("~", "")
                .split()[-1]
            )
        else:
            price = "N/A"

        data.append({
            "date": today,
            "code": code,
            "rank": idx,
            "brand": brand,
            "product": product,
            "price": price
        })

    return data


def run():
    return run_channel(
        channel_name="oliveyoung",
        url=URL,
        base_dir=CHANNEL_PATHS["oliveyoung"],
        parse_func=parse_oliveyoung,
        image_selector=".prd_thumb img",
    )


if __name__ == "__main__":
    run()