"""
generate_html_trend.py
-----------------------
채널별 급상승/급하락 그리드 카드 HTML 생성 모듈

단독 실행:
    python generate_html_trend.py
    python generate_html_trend.py --date 20250403
    python generate_html_trend.py --date 20250403 --output ./result --account my_instagram
"""

import logging
import os
from datetime import datetime

import pandas as pd

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

PATHS = {
    "excel_template": "../data/report/{today}_ranking.xlsx",
    "css":            "./css/style.css",
    "instagram_icon": "./images/instagram.png",
    "no_image":       "./images/no-image.png",
}

MAX_ITEMS = 12

# ──────────────────────────────────────────────
# 채널 설정
# ──────────────────────────────────────────────
TREND_CHANNEL_CONFIG = {
    "naver": {
        "channel_label":       "네이버",
        "logo_path":           "./images/naver.png",
        "image_path_template": "../data/raw/naver/{today}/{rank:02d}",
        "hot_sheet":           "naver_hot",
        "down_sheet":          "naver_down",
        "cool_filename":        "01_naver_cool",
        "down_filename":       "01_naver_down",
    },
    "coupang": {
        "channel_label":       "쿠팡",
        "logo_path":           "./images/coupang.png",
        "image_path_template": "../data/raw/coupang/{today}/{rank:02d}",
        "hot_sheet":           "coupang_hot",
        "down_sheet":          "coupang_down",
        "cool_filename":        "02_coupang_cool",
        "down_filename":       "02_coupang_down",
    },
    "oliveyoung": {
        "channel_label":       "올리브영",
        "logo_path":           "./images/oliveyoung.png",
        "image_path_template": "../data/raw/oliveyoung/{today}/{rank:02d}",
        "hot_sheet":           "oliveyoung_hot",
        "down_sheet":          "oliveyoung_down",
        "cool_filename":        "03_oliveyoung_cool",
        "down_filename":       "03_oliveyoung_down",
    },
    "kakao": {
        "channel_label":       "카카오",
        "logo_path":           "./images/kakao.png",
        "image_path_template": "../data/raw/kakao/{today}/{rank:02d}",
        "hot_sheet":           "kakao_hot",
        "down_sheet":          "kakao_down",
        "cool_filename":        "04_kakao_cool",
        "down_filename":       "04_kakao_down",
    },
    "daiso": {
        "channel_label":       "다이소",
        "logo_path":           "./images/daiso.png",
        "image_path_template": "../data/raw/daiso/{today}/{rank:02d}",
        "hot_sheet":           "daiso_hot",
        "down_sheet":          "daiso_down",
        "cool_filename":        "05_daiso_cool",
        "down_filename":       "05_daiso_down",
    },
}


# ──────────────────────────────────────────────
# 색상 규칙
# ──────────────────────────────────────────────
def get_card_bg(rank_diff: float, trend_type: str) -> str | None:
    """배경색 반환. 기본값(#F2F2F2)이면 None 반환 → CSS에 위임"""
    diff = abs(rank_diff)
    if trend_type == "hot":
        if diff > 40: return "#FF595C80"
        if diff > 20: return "#FFA7A880"
    else:  # down
        if diff > 40: return "#1F22FF80"
        if diff > 20: return "#A7A8FF80"
    return None


# ──────────────────────────────────────────────
# 경로 유틸
# ──────────────────────────────────────────────
def abs_to_rel(abs_path: str, from_dir: str) -> str:
    return os.path.relpath(abs_path, start=from_dir).replace("\\", "/")


def resolve_asset(relative_to_base: str, from_dir: str) -> str:
    abs_path = os.path.abspath(os.path.join(BASE_DIR, relative_to_base))
    return abs_to_rel(abs_path, from_dir)


def get_image_path(channel_key: str, today: str, rank: int, from_dir: str) -> str:
    tmpl = TREND_CHANNEL_CONFIG[channel_key]["image_path_template"]
    base_path = tmpl.format(today=today, rank=rank)
    for ext in ("jpg", "png", "jpeg", "webp"):
        abs_path = os.path.abspath(os.path.join(BASE_DIR, f"{base_path}.{ext}"))
        if os.path.exists(abs_path):
            return abs_to_rel(abs_path, from_dir)
    return resolve_asset(PATHS["no_image"], from_dir)


# ──────────────────────────────────────────────
# HTML 빌더
# ──────────────────────────────────────────────
def build_mini_card(
    df: pd.DataFrame,
    i: int,
    channel_key: str,
    today: str,
    trend_type: str,
    from_dir: str,
) -> str:
    rank          = int(df["rank"].iloc[i])
    rank_diff_val = df["rank_diff"].iloc[i]
    brand         = str(df["brand"].iloc[i]).strip()
    image_path    = get_image_path(channel_key, today, rank, from_dir)

    if pd.isna(rank_diff_val):
        diff_text = "New"
        bg_color  = None
    else:
        diff_abs  = abs(int(rank_diff_val))
        arrow     = "▲" if trend_type == "hot" else "▼"
        diff_text = f"{arrow}{diff_abs}"
        bg_color  = get_card_bg(rank_diff_val, trend_type)

    diff_cls   = "mini-diff-hot" if trend_type == "hot" else "mini-diff-down"
    bg_style   = f' style="background-color:{bg_color};"' if bg_color else ""

    return f"""
    <div class="mini-card"{bg_style}>
      <div class="mini-rank-row">
        <span class="mini-rank-num">{rank}위</span><span class="mini-diff {diff_cls}">{diff_text}</span>
      </div>
      <div class="mini-image-wrap">
        <img src="{image_path}" alt="{rank}위 상품" class="mini-product-img" />
      </div>
      <div class="mini-brand">{brand}</div>
    </div>
    """


def build_trend_card_html(
    df: pd.DataFrame,
    trend_type: str,
    today: str,
    today1: str,
    channel_key: str,
    from_dir: str,
    instagram_account: str = "RANKING_NAM",
) -> str:
    config = TREND_CHANNEL_CONFIG[channel_key]

    items_html = "".join(
        build_mini_card(df, i, channel_key, today, trend_type, from_dir)
        for i in range(min(MAX_ITEMS, len(df)))
    )

    css_rel   = resolve_asset(PATHS["css"], from_dir)
    insta_rel = resolve_asset(PATHS["instagram_icon"], from_dir)
    logo_rel  = resolve_asset(config["logo_path"], from_dir)

    if trend_type == "hot":
        title_type = "급상승"
        arrow_sym  = "▲"
        arrow_cls  = "trend-arrow-hot"
    else:
        title_type = "급하락"
        arrow_sym  = "▼"
        arrow_cls  = "trend-arrow-down"

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{config['channel_label']} {title_type} 브랜드</title>
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
        <div class="hero-right trend-hero-right">
          <div class="trend-title-lines">
            <p class="trend-title-type">{title_type}</p>
            <p class="trend-title-brand">브랜드</p>
          </div>
          <span class="trend-arrow-symbol {arrow_cls}">{arrow_sym}</span>
        </div>
      </div>

      <div class="trend-grid">
        {items_html}
      </div>

    </section>
  </div>
</body>
</html>
"""


# ──────────────────────────────────────────────
# 저장 / 로딩
# ──────────────────────────────────────────────
def save_trend_card(
    df: pd.DataFrame,
    trend_type: str,
    today: str,
    today1: str,
    channel_key: str,
    filepath: str,
    instagram_account: str = "RANKING_NAM",
) -> None:
    from_dir = os.path.dirname(os.path.abspath(filepath))
    os.makedirs(from_dir, exist_ok=True)

    html = build_trend_card_html(
        df, trend_type, today, today1,
        channel_key, from_dir, instagram_account,
    )
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)
    logger.info(f"저장 완료: {filepath}")


def load_trend_sheets(today: str) -> dict[str, pd.DataFrame]:
    excel_path = os.path.abspath(
        os.path.join(BASE_DIR, PATHS["excel_template"].format(today=today))
    )
    if not os.path.exists(excel_path):
        raise FileNotFoundError(f"랭킹 파일을 찾을 수 없습니다: {excel_path}")

    logger.info(f"Excel 로드: {excel_path}")
    result = {}
    for key, cfg in TREND_CHANNEL_CONFIG.items():
        result[f"{key}_hot"]  = pd.read_excel(excel_path, sheet_name=cfg["hot_sheet"])
        result[f"{key}_down"] = pd.read_excel(excel_path, sheet_name=cfg["down_sheet"])
    return result


# ──────────────────────────────────────────────
# 단독 실행 진입점
# ──────────────────────────────────────────────
def run(today: str, output_dir: str, instagram_account: str) -> dict[str, int]:
    """
    트렌드 HTML 카드 일괄 생성.
    반환값: {"success": N, "fail": N}
    """
    today1 = datetime.strptime(today, "%Y%m%d").strftime("%Y년 %m월 %d일")
    logger.info(f"[TREND HTML] 실행 날짜: {today1}")

    sheets = load_trend_sheets(today)
    success, fail = 0, 0

    for channel_key, cfg in TREND_CHANNEL_CONFIG.items():
        for trend_type, sheet_key, filename_key in [
            ("hot",  f"{channel_key}_hot",  "cool_filename"),
            ("down", f"{channel_key}_down", "down_filename"),
        ]:
            df       = sheets[sheet_key]
            filename = cfg[filename_key]
            filepath = os.path.join(output_dir, today, f"{filename}.html")
            try:
                save_trend_card(
                    df=df,
                    trend_type=trend_type,
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

    logger.info(f"[TREND HTML] 완료 — 성공 {success}개 / 실패 {fail}개")
    return {"success": success, "fail": fail}


if __name__ == "__main__":
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    parser = argparse.ArgumentParser(description="급상승/급하락 트렌드 HTML 카드 생성")
    parser.add_argument("--date",    default=None,           help="날짜 YYYYMMDD (기본값: 오늘)")
    parser.add_argument("--output",  default="./result",     help="결과 저장 루트 디렉토리")
    parser.add_argument("--account", default="RANKING_NAM", help="인스타그램 계정명")
    args = parser.parse_args()

    today = args.date or datetime.today().strftime("%Y%m%d")
    run(today=today, output_dir=args.output, instagram_account=args.account)
