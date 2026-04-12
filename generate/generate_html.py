"""
generate_html.py
-----------------
채널별 건강식품 TOP10 랭킹 HTML 카드 생성 모듈

단독 실행:
    python generate_html.py
    python generate_html.py --date 20250403
    python generate_html.py --date 20250403 --output ./result --account my_instagram
"""

import logging
import os
from datetime import datetime

import pandas as pd

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# 경로 상수
# ──────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

PATHS = {
    "excel_template": "../data/report/{today}_ranking.xlsx",
    "css":            "./css/style.css",
    "instagram_icon": "./images/instagram.png",
    "no_image":       "./images/no-image.png",
}

# ──────────────────────────────────────────────
# 채널 설정
# ──────────────────────────────────────────────
CHANNEL_CONFIG = {
    "naver": {
        "channel_label":       "네이버",
        "logo_path":           "./images/naver.png",
        "image_path_template": "../data/raw/naver/{today}/{rank:02d}",
        "meta_fields":         ["price", "review", "star"],
        "sheet_name":          "naver_10",
        "filename_prefix":     "01_naver",
    },
    "coupang": {
        "channel_label":       "쿠팡",
        "logo_path":           "./images/coupang.png",
        "image_path_template": "../data/raw/coupang/{today}/{rank:02d}",
        "meta_fields":         ["price", "review", "star"],
        "sheet_name":          "coupang_10",
        "filename_prefix":     "02_coupang",
    },
    "oliveyoung": {
        "channel_label":       "올리브영",
        "logo_path":           "./images/oliveyoung.png",
        "image_path_template": "../data/raw/oliveyoung/{today}/{rank:02d}",
        "meta_fields":         ["price"],
        "sheet_name":          "oliveyoung_10",
        "filename_prefix":     "03_oliveyoung",
    },
    "kakao": {
        "channel_label":       "카카오",
        "logo_path":           "./images/kakao.png",
        "image_path_template": "../data/raw/kakao/{today}/{rank:02d}",
        "meta_fields":         ["price", "like"],
        "sheet_name":          "kakao_10",
        "filename_prefix":     "04_kakao",
    },
    "daiso": {
        "channel_label":       "다이소",
        "logo_path":           "./images/daiso.png",
        "image_path_template": "../data/raw/daiso/{today}/{rank:02d}",
        "meta_fields":         ["price", "review", "star"],
        "sheet_name":          "daiso_10",
        "filename_prefix":     "05_daiso",
    },
}

# 카드 분할 구간 (start_idx, end_idx)
CARD_SPLITS = [(0, 5), (5, 10)]


# ──────────────────────────────────────────────
# 포맷 헬퍼
# ──────────────────────────────────────────────
def format_rank_diff(x) -> tuple[str, str]:
    if pd.isna(x):
        return "New", "new"
    if x == 0:
        return "", ""
    if x > 0:
        return f"▲{int(x)}", "up"
    return f"▼{abs(int(x))}", "down"


def format_price(x)  -> str: return f"{int(x):,}원" if not pd.isna(x) else ""
def format_review(x) -> str: return f"{int(x):,}개" if not pd.isna(x) else ""
def format_star(x)   -> str: return str(x)           if not pd.isna(x) else ""
def format_like(x)   -> str: return f"{int(x):,}개"  if not pd.isna(x) else ""


# ──────────────────────────────────────────────
# 경로 유틸
# ──────────────────────────────────────────────
def abs_to_rel(abs_path: str, from_dir: str) -> str:
    return os.path.relpath(abs_path, start=from_dir).replace("\\", "/")


def resolve_asset(relative_to_base: str, from_dir: str) -> str:
    abs_path = os.path.abspath(os.path.join(BASE_DIR, relative_to_base))
    return abs_to_rel(abs_path, from_dir)


def get_image_path(channel_key: str, today: str, rank: int, from_dir: str) -> str:
    config    = CHANNEL_CONFIG[channel_key]
    base_path = config["image_path_template"].format(today=today, rank=rank)

    for ext in ("jpg", "png", "jpeg", "webp"):
        abs_path = os.path.abspath(os.path.join(BASE_DIR, f"{base_path}.{ext}"))
        if os.path.exists(abs_path):
            return abs_to_rel(abs_path, from_dir)

    return resolve_asset(PATHS["no_image"], from_dir)


# ──────────────────────────────────────────────
# HTML 빌더
# ──────────────────────────────────────────────
def build_meta_html(df: pd.DataFrame, i: int, channel_key: str) -> str:
    meta_fields = CHANNEL_CONFIG[channel_key]["meta_fields"]
    field_map = {
        "price":  lambda: f'<span class="meta-item"><strong>판매가:</strong> {format_price(df["price"].iloc[i])}</span>',
        "review": lambda: f'<span class="meta-item"><strong>리뷰:</strong> {format_review(df["review"].iloc[i])}</span>',
        "star":   lambda: f'<span class="meta-item star-score">⭐ {format_star(df["star"].iloc[i])}</span>',
        "like":   lambda: f'<span class="meta-item star-score">❤️ {format_like(df["like"].iloc[i])}</span>',
    }
    return "".join(
        renderer()
        for field, renderer in field_map.items()
        if field in meta_fields and field in df.columns
    )


def build_rank_row(
    df: pd.DataFrame,
    i: int,
    today: str,
    channel_key: str,
    from_dir: str,
    is_first_row: bool = False,
) -> str:
    rank_text, rank_cls  = format_rank_diff(df["rank_diff"].iloc[i])
    rank_col_classes     = ["rank-col"]
    if is_first_row:    rank_col_classes.append("rank-first")
    if i + 1 >= 10:     rank_col_classes.append("rank-last")

    brand      = str(df["brand"].iloc[i]).strip()
    product    = str(df["product"].iloc[i]).strip()
    image_path = get_image_path(channel_key, today, i + 1, from_dir)
    meta_html  = build_meta_html(df, i, channel_key)

    return f"""
    <div class="rank-row">
      <div class="{' '.join(rank_col_classes)}">{i + 1}위</div>
      <div class="image-col">
        <img src="{image_path}" alt="{i + 1}위 상품" class="product-image" />
      </div>
      <div class="info-col">
        <div class="brand-row">
          <span class="brand-name">{brand}</span>
          <span class="rank-change {rank_cls}">{rank_text}</span>
        </div>
        <div class="product-name">{product}</div>
        <div class="meta-row">{meta_html}</div>
      </div>
    </div>
    """


def build_card_html(
    df: pd.DataFrame,
    start_idx: int,
    end_idx: int,
    today: str,
    today1: str,
    channel_key: str,
    from_dir: str,
    instagram_account: str = "RANKING_NAM",
) -> str:
    config    = CHANNEL_CONFIG[channel_key]
    rows_html = "".join(
        build_rank_row(df, i, today, channel_key, from_dir, is_first_row=(i == 0))
        for i in range(start_idx, min(end_idx, len(df)))
    )
    css_rel   = resolve_asset(PATHS["css"], from_dir)
    insta_rel = resolve_asset(PATHS["instagram_icon"], from_dir)
    logo_rel  = resolve_asset(config["logo_path"], from_dir)

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{config['channel_label']} 건강식품 TOP10</title>
  <link rel="stylesheet" href="{css_rel}" />
</head>
<body>
  <div class="canvas">
    <section class="card">

      <div class="top-bar">
        <div class="top-left">
          <img src="{insta_rel}" alt="instagram" class="insta-logo" />
          <span class="ranking-name">{instagram_account}</span>
        </div>
        <div class="top-right">
          출처: {config['channel_label']} ({today1} ver.)
        </div>
      </div>

      <div class="hero-section">
        <div class="hero-left">
          <img src="{logo_rel}" alt="{config['channel_label']}" class="hero-logo" />
        </div>
        <div class="hero-right">
          <p class="title-main">건강식품</p>
          <p class="title-sub">판매 순위</p>
        </div>
      </div>

      <div class="ranking-table">
        {rows_html}
      </div>

    </section>
  </div>
</body>
</html>
"""


# ──────────────────────────────────────────────
# 저장 / 로딩
# ──────────────────────────────────────────────
def save_card(
    df: pd.DataFrame,
    start_idx: int,
    end_idx: int,
    today: str,
    today1: str,
    channel_key: str,
    filepath: str,
    instagram_account: str = "RANKING_NAM",
) -> None:
    from_dir = os.path.dirname(os.path.abspath(filepath))
    os.makedirs(from_dir, exist_ok=True)

    html = build_card_html(
        df, start_idx, end_idx,
        today, today1,
        channel_key, from_dir,
        instagram_account,
    )
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)

    logger.info(f"저장 완료: {filepath}")


def load_all_sheets(today: str) -> dict[str, pd.DataFrame]:
    excel_path = os.path.abspath(
        os.path.join(BASE_DIR, PATHS["excel_template"].format(today=today))
    )
    if not os.path.exists(excel_path):
        raise FileNotFoundError(f"랭킹 파일을 찾을 수 없습니다: {excel_path}")

    logger.info(f"Excel 로드: {excel_path}")
    return {
        key: pd.read_excel(excel_path, sheet_name=cfg["sheet_name"])
        for key, cfg in CHANNEL_CONFIG.items()
    }


# ──────────────────────────────────────────────
# 단독 실행 진입점
# ──────────────────────────────────────────────
def run(today: str, output_dir: str, instagram_account: str) -> dict[str, int]:
    """
    HTML 카드 일괄 생성.
    반환값: {"success": N, "fail": N}
    """
    today1 = datetime.strptime(today, "%Y%m%d").strftime("%Y년 %m월 %d일")
    logger.info(f"[HTML] 실행 날짜: {today1}")

    dfs = load_all_sheets(today)

    success, fail = 0, 0
    for channel_key, cfg in CHANNEL_CONFIG.items():
        df     = dfs[channel_key]
        prefix = cfg["filename_prefix"]

        for part, (start, end) in enumerate(CARD_SPLITS, start=1):
            filepath = os.path.join(output_dir, today, f"{prefix} ({part}).html")
            try:
                save_card(
                    df=df,
                    start_idx=start,
                    end_idx=end,
                    today=today,
                    today1=today1,
                    channel_key=channel_key,
                    filepath=filepath,
                    instagram_account=instagram_account,
                )
                success += 1
            except Exception as e:
                logger.error(f"저장 실패 [{filepath}]: {e}")
                fail += 1

    logger.info(f"[HTML] 완료 — 성공 {success}개 / 실패 {fail}개")
    return {"success": success, "fail": fail}


if __name__ == "__main__":
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    parser = argparse.ArgumentParser(description="랭킹 HTML 카드 생성")
    parser.add_argument("--date",    default=None,           help="날짜 YYYYMMDD (기본값: 오늘)")
    parser.add_argument("--output",  default="./result",     help="결과 저장 루트 디렉토리")
    parser.add_argument("--account", default="RANKING_NAM", help="인스타그램 계정명")
    args = parser.parse_args()

    today = args.date or datetime.today().strftime("%Y%m%d")
    run(today=today, output_dir=args.output, instagram_account=args.account)
