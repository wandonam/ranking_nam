"""
monthly/export.py
------------------
히어로 제품 상세 파일 생성 모듈

aggregate.py → hero.py 실행 후 만들어진 monthly.xlsx에서
채널별 히어로 제품 1개의 상세 데이터를 뽑아
data/hero/YYYY_MM/{channel}.xlsx 로 저장합니다.

시트 구성:
  summary : 히어로 제품 요약 1행 (url 포함)
  weekly  : 주차별 rank / price / review(or like) / star
  reviews : 빈 템플릿 (리뷰 크롤링 추가 예정)

단독 실행:
    python export.py
    python export.py --month 2026-04
"""

import argparse
from datetime import datetime
from pathlib import Path

import pandas as pd

ROOT        = Path(__file__).parent.parent
MONTHLY_DIR = ROOT / "data" / "monthly"
HERO_DIR    = ROOT / "data" / "hero"

CHANNELS = ["naver", "coupang", "oliveyoung", "kakao", "daiso"]

WEEKLY_COLS = {
    "naver":      ["week", "date", "rank", "price", "review", "star"],
    "coupang":    ["week", "date", "rank", "price", "review", "star"],
    "oliveyoung": ["week", "date", "rank", "price"],
    "kakao":      ["week", "date", "rank", "price", "like"],
    "daiso":      ["week", "date", "rank", "price", "review", "star"],
}

REVIEWS_COLS = ["review_date", "rating", "reviewer", "content"]

URL_FROM_CODE = {
    "coupang":    lambda c: f"https://www.coupang.com/vp/products/search?vendorItemId={c}",
    "oliveyoung": lambda c: f"https://www.oliveyoung.co.kr/store/goods/getGoodsDetail.do?goodsNo={c}",
    "kakao":      lambda c: f"https://gift.kakao.com/product/{c}",
    "daiso":      lambda c: f"https://www.daisomall.co.kr/ds/product/detail?pdNo={c}",
    "naver":      lambda c: "",
}


def resolve_url(channel: str, hero_row: pd.Series) -> str:
    url = hero_row.get("url", "")
    if url and str(url).startswith("http"):
        return str(url)
    return URL_FROM_CODE[channel](hero_row["code"])


def build_weekly_df(daily_df: pd.DataFrame, hero_code, channel: str) -> pd.DataFrame:
    filtered = daily_df[daily_df["code"].astype(str) == str(hero_code)].copy()
    filtered = filtered.sort_values("date").reset_index(drop=True)
    filtered.insert(0, "week", range(1, len(filtered) + 1))

    cols = [c for c in WEEKLY_COLS[channel] if c in filtered.columns]
    return filtered[cols]


def run(year: int, month: int) -> dict:
    monthly_path = MONTHLY_DIR / f"{year}_{month:02d}_monthly.xlsx"
    if not monthly_path.exists():
        raise FileNotFoundError(
            f"월간 집계 파일 없음: {monthly_path}\naggregate.py → hero.py 를 먼저 실행하세요."
        )

    out_dir = HERO_DIR / f"{year}_{month:02d}"
    out_dir.mkdir(parents=True, exist_ok=True)

    results = {}

    for channel in CHANNELS:
        try:
            hero_df  = pd.read_excel(monthly_path, sheet_name=f"{channel}_hero")
            daily_df = pd.read_excel(monthly_path, sheet_name=f"{channel}_daily")
        except Exception:
            print(f"  [{channel}] 시트 없음, 건너뜀")
            continue

        hero_row  = hero_df.iloc[0]
        hero_code = hero_row["code"]

        url = resolve_url(channel, hero_row)
        summary_df = hero_df.iloc[[0]].copy()
        summary_df["url"] = url

        weekly_df  = build_weekly_df(daily_df, hero_code, channel)
        reviews_df = pd.DataFrame(columns=REVIEWS_COLS)

        out_path = out_dir / f"{channel}.xlsx"
        with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
            summary_df.to_excel(writer, sheet_name="summary", index=False)
            weekly_df.to_excel(writer, sheet_name="weekly",  index=False)
            reviews_df.to_excel(writer, sheet_name="reviews", index=False)

        results[channel] = out_path
        print(f"  [{channel}] {hero_row['brand']} | {str(hero_row['product'])[:25]} → {out_path.name}")

    print(f"\n저장 완료: {out_dir}")
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="히어로 제품 상세 파일 생성")
    parser.add_argument("--month", default=None, help="YYYY-MM (기본값: 전월)")
    args = parser.parse_args()

    if args.month:
        y, m = map(int, args.month.split("-"))
    else:
        now = datetime.now()
        m = now.month - 1 or 12
        y = now.year if now.month > 1 else now.year - 1

    run(y, m)
