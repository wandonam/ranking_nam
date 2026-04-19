"""
generate_html_hero.py
----------------------
월간 히어로 제품 발표 카드 HTML 생성 모듈 (Card 1)

채널별 히어로 제품 1개를 대형 이미지 + 선정 이유 형식으로 카드화합니다.
출력: data/output/{YYYY_MM_monthly}/hero_{channel}.html/.png

단독 실행:
    python generate_html_hero.py --month 2026-04
    python generate_html_hero.py --month 2026-04 --output ../data/output --account my_instagram
"""

import logging
import os
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

PATHS = {
    "monthly_excel":  "../data/report/{year_month}_monthly.xlsx",
    "css":            "./css/style.css",
    "instagram_icon": "./images/instagram.png",
    "no_image":       "./images/no-image.png",
}

HERO_CHANNEL_CONFIG = {
    "naver": {
        "channel_label":       "네이버",
        "logo_path":           "./images/naver.png",
        "image_path_template": "../data/raw/naver/{date}/{rank:02d}",
        "has_review": True,  "has_star": True,  "has_like": False,
        "filename":            "hero_naver",
        "prefix_num":          "01",
    },
    "coupang": {
        "channel_label":       "쿠팡",
        "logo_path":           "./images/coupang.png",
        "image_path_template": "../data/raw/coupang/{date}/{rank:02d}",
        "has_review": True,  "has_star": True,  "has_like": False,
        "filename":            "hero_coupang",
        "prefix_num":          "02",
    },
    "oliveyoung": {
        "channel_label":       "올리브영",
        "logo_path":           "./images/oliveyoung.png",
        "image_path_template": "../data/raw/oliveyoung/{date}/{rank:02d}",
        "has_review": False, "has_star": False, "has_like": False,
        "filename":            "hero_oliveyoung",
        "prefix_num":          "03",
    },
    "kakao": {
        "channel_label":       "카카오",
        "logo_path":           "./images/kakao.png",
        "image_path_template": "../data/raw/kakao/{date}/{rank:02d}",
        "has_review": False, "has_star": False, "has_like": True,
        "filename":            "hero_kakao",
        "prefix_num":          "04",
    },
    "daiso": {
        "channel_label":       "다이소",
        "logo_path":           "./images/daiso.png",
        "image_path_template": "../data/raw/daiso/{date}/{rank:02d}",
        "has_review": True,  "has_star": True,  "has_like": False,
        "filename":            "hero_daiso",
        "prefix_num":          "05",
    },
}


# ──────────────────────────────────────────────
# 경로 유틸 (generate_html.py 와 동일 패턴)
# ──────────────────────────────────────────────

def abs_to_rel(abs_path: str, from_dir: str) -> str:
    return os.path.relpath(abs_path, start=from_dir).replace("\\", "/")


def resolve_asset(relative_to_base: str, from_dir: str) -> str:
    abs_path = os.path.abspath(os.path.join(BASE_DIR, relative_to_base))
    return abs_to_rel(abs_path, from_dir)


def get_product_image(channel_key: str, date: str, rank: int, from_dir: str) -> str:
    tmpl = HERO_CHANNEL_CONFIG[channel_key]["image_path_template"]
    base = tmpl.format(date=date, rank=rank)
    for ext in ("jpg", "png", "jpeg", "webp"):
        abs_path = os.path.abspath(os.path.join(BASE_DIR, f"{base}.{ext}"))
        if os.path.exists(abs_path):
            return abs_to_rel(abs_path, from_dir)
    return resolve_asset(PATHS["no_image"], from_dir)


# ──────────────────────────────────────────────
# 포맷 헬퍼
# ──────────────────────────────────────────────

def _val(row: pd.Series, col: str, default=None):
    v = row.get(col, default)
    return default if pd.isna(v) else v


def build_meta_html(row: pd.Series, cfg: dict) -> str:
    items = []
    price = _val(row, "price")
    if price is not None:
        items.append(f'<div class="hero-meta-item"><strong>판매가:</strong> {int(price):,}원</div>')
    if cfg["has_star"]:
        star = _val(row, "avg_star")
        if star is not None:
            items.append(f'<div class="hero-meta-item"><strong>평균 별점:</strong> &#11088; {star}</div>')
    if cfg["has_review"]:
        rev = _val(row, "last_review")
        if rev is not None:
            items.append(f'<div class="hero-meta-item"><strong>리뷰 수:</strong> {int(rev):,}개</div>')
    if cfg["has_like"]:
        like = _val(row, "last_like")
        if like is not None:
            items.append(f'<div class="hero-meta-item"><strong>좋아요:</strong> {int(like):,}개</div>')
    return "\n".join(items)


def build_reasons(row: pd.Series, cfg: dict) -> list[str]:
    reasons = []

    # 1. 평균 순위
    avg_rank = _val(row, "avg_rank")
    if avg_rank is not None:
        reasons.append(f"월간 평균 순위: <strong>{float(avg_rank):.1f}위</strong>")

    # 2. 출현 일관성
    appearances = _val(row, "appearances", 0)
    total_weeks = _val(row, "total_weeks", 0)
    if total_weeks and appearances:
        if int(appearances) >= int(total_weeks):
            reasons.append(f"전 기간 TOP 랭킹 유지: <strong>{int(total_weeks)}주 연속</strong>")
        else:
            reasons.append(f"TOP 랭킹 진입: <strong>{int(appearances)}주 / {int(total_weeks)}주</strong>")

    # 3. 순위 상승 or 참여도 성장
    rank_change = _val(row, "rank_change", 0)
    if rank_change and int(rank_change) > 0:
        reasons.append(f"순위 상승폭: <strong>&#9650;{int(rank_change)}</strong>")

    if cfg["has_review"]:
        r_growth = _val(row, "review_growth", 0)
        r_pct    = _val(row, "review_growth_pct", 0)
        if r_growth and int(r_growth) > 0:
            reasons.append(f"리뷰 증가: <strong>+{int(r_growth):,}개 (+{float(r_pct):.1f}%)</strong>")
    elif cfg["has_like"]:
        l_growth = _val(row, "like_growth", 0)
        l_pct    = _val(row, "like_growth_pct", 0)
        if l_growth and int(l_growth) > 0:
            reasons.append(f"좋아요 증가: <strong>+{int(l_growth):,}개 (+{float(l_pct):.1f}%)</strong>")

    return reasons[:3]  # 최대 3개


# ──────────────────────────────────────────────
# HTML 빌더
# ──────────────────────────────────────────────

def build_hero_card_html(
    row: pd.Series,
    channel_key: str,
    year_month_label: str,
    from_dir: str,
    instagram_account: str = "RANKING_NAM",
) -> str:
    cfg       = HERO_CHANNEL_CONFIG[channel_key]
    css_rel   = resolve_asset(PATHS["css"], from_dir)
    insta_rel = resolve_asset(PATHS["instagram_icon"], from_dir)
    logo_rel  = resolve_asset(cfg["logo_path"], from_dir)

    last_date = str(_val(row, "last_date", ""))
    last_rank = int(_val(row, "last_rank", 1))
    img_rel   = get_product_image(channel_key, last_date, last_rank, from_dir)

    brand   = str(_val(row, "brand", "")).strip()
    product = str(_val(row, "product", "")).strip()

    meta_html    = build_meta_html(row, cfg)
    reasons      = build_reasons(row, cfg)
    reasons_html = "\n".join(
        f'<li class="hero-reason-item">'
        f'<span class="hero-reason-bullet">&#9679;</span>'
        f'<span>{r}</span>'
        f'</li>'
        for r in reasons
    )

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{cfg['channel_label']} 이달의 히어로 제품</title>
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
          출처: {cfg['channel_label']} ({year_month_label} ver.)
        </div>
      </div>

      <div class="hero-section">
        <div class="hero-left">
          <img src="{logo_rel}" alt="{cfg['channel_label']}" class="hero-logo" />
        </div>
        <div class="hero-right">
          <p class="title-main">이달의</p>
          <p class="title-sub">히어로</p>
        </div>
      </div>

      <div class="hero-monthly-body">

        <div class="hero-product-section">
          <div class="hero-product-img-wrap">
            <img src="{img_rel}" alt="히어로 제품 이미지" class="hero-product-img" />
          </div>
          <div class="hero-product-info">
            <span class="hero-badge">&#127942; 이달의 히어로</span>
            <div class="hero-brand">{brand}</div>
            <div class="hero-product-name">{product}</div>
            <div class="hero-meta-row">
              {meta_html}
            </div>
          </div>
        </div>

        <div class="hero-reason-box">
          <p class="hero-reason-title">&#127942; 선정 이유</p>
          <ul class="hero-reason-list">
            {reasons_html}
          </ul>
        </div>

      </div>

    </section>
  </div>
</body>
</html>
"""


# ──────────────────────────────────────────────
# 저장 / 로딩
# ──────────────────────────────────────────────

def save_hero_card(
    row: pd.Series,
    channel_key: str,
    year_month_label: str,
    filepath: str,
    instagram_account: str = "RANKING_NAM",
) -> None:
    from_dir = os.path.dirname(os.path.abspath(filepath))
    os.makedirs(from_dir, exist_ok=True)

    html = build_hero_card_html(row, channel_key, year_month_label, from_dir, instagram_account)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)
    logger.info(f"저장 완료: {filepath}")


def load_hero_rows(year_month: str) -> dict[str, pd.Series]:
    """월간 Excel에서 채널별 히어로 1행을 읽어 반환."""
    excel_path = os.path.abspath(
        os.path.join(BASE_DIR, PATHS["monthly_excel"].format(year_month=year_month))
    )
    if not os.path.exists(excel_path):
        raise FileNotFoundError(f"월간 파일 없음: {excel_path}")

    result = {}
    for channel in HERO_CHANNEL_CONFIG:
        sheet = f"{channel}_hero"
        try:
            df = pd.read_excel(excel_path, sheet_name=sheet)
            result[channel] = df.iloc[0]
        except Exception as e:
            logger.warning(f"[{channel}] hero 시트 로드 실패: {e}")
    return result


# ──────────────────────────────────────────────
# 진입점
# ──────────────────────────────────────────────

def run(
    year: int,
    month: int,
    output_dir: str,
    instagram_account: str = "RANKING_NAM",
) -> dict[str, int]:
    year_month       = f"{year}_{month:02d}"
    year_month_label = f"{year}년 {month:02d}월"
    folder_name      = f"{year_month}_monthly"

    logger.info(f"[HERO CARD] {year_month_label}")

    heroes = load_hero_rows(year_month)
    success, fail = 0, 0

    for channel_key, row in heroes.items():
        cfg      = HERO_CHANNEL_CONFIG[channel_key]
        filename = cfg["filename"]
        filepath = os.path.join(output_dir, folder_name, f"{filename}.html")
        try:
            save_hero_card(row, channel_key, year_month_label, filepath, instagram_account)
            success += 1
        except Exception as e:
            logger.error(f"저장 실패 [{filepath}]: {e}")
            fail += 1

    logger.info(f"[HERO CARD] 완료 - 성공 {success}개 / 실패 {fail}개")
    return {"success": success, "fail": fail}


if __name__ == "__main__":
    import argparse
    from datetime import datetime

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    parser = argparse.ArgumentParser(description="월간 히어로 제품 카드 생성")
    parser.add_argument("--month",   default=None,                        help="YYYY-MM (기본값: 이번 달)")
    parser.add_argument("--output",  default="../data/output",            help="결과 저장 루트 디렉토리")
    parser.add_argument("--account", default="RANKING_NAM",              help="인스타그램 계정명")
    args = parser.parse_args()

    if args.month:
        y, m = map(int, args.month.split("-"))
    else:
        now = datetime.now()
        y, m = now.year, now.month

    output = os.path.abspath(os.path.join(BASE_DIR, args.output))
    run(year=y, month=m, output_dir=output, instagram_account=args.account)
