from urllib.parse import urlparse, parse_qs

from config import CHANNEL_PATHS
from core.runner import run_channel

URL = "https://www.coupang.com/np/categories/196076?listSize=120&filterType=&rating=0&isPriceRange=false&minPrice=&maxPrice=&component=&sorter=saleCountDesc"

def parse_coupang(soup, today):
    data = []
    ranking = soup.select("li.ProductUnit_productUnit__Qd6sv")

    for idx, item in enumerate(ranking, start=1):
        a_tag = item.select_one("a")
        href = a_tag["href"] if a_tag else ""

        query = urlparse(href).query
        params = parse_qs(query)
        vendor_id = params.get("vendorItemId", ["N/A"])[0]

        product_tag = item.select_one(".ProductUnit_productNameV2__cV9cw")
        price_tag = item.select_one(".Price_priceValue__A4KOr")
        star_tag = item.select_one(".ProductRating_star__RGSlV")
        review_tag = item.select_one(".ProductRating_ratingCount__R0Vhz")

        product = product_tag.text.strip() if product_tag else "N/A"

        data.append({
            "date": today,
            "code": vendor_id,
            "rank": idx,
            "brand": product.split()[0] if product != "N/A" else "N/A",
            "product": product,
            "price": price_tag.text.strip().replace(",", "").replace("원", "") if price_tag else "N/A",
            "star": star_tag.text.strip() if star_tag else "N/A",
            "review": review_tag.text.strip().replace("(", "").replace(")", "").replace(",", "") if review_tag else "N/A",
        })

    return data

def run():
    return run_channel(
        channel_name="coupang",
        url=URL,
        base_dir=CHANNEL_PATHS["coupang"],
        parse_func=parse_coupang,
        image_selector=".ProductUnit_productImage__Mqcg1 img",
    )

if __name__ == "__main__":
    run()