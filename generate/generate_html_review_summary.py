"""
generate/generate_html_review_summary.py
-----------------------------------------
히어로 제품 리뷰 써머리 카드뉴스 HTML 생성 모듈 (3장 시리즈)

  Page 1: 리뷰 Overview (별점 분포 + 키워드 + 대표 리뷰)
  Page 2: 구매자 프로필 (누가, 언제, 왜 사는가)
  Page 3: 기회와 리스크 (강화 포인트 + 맛 선호도 + 개선 시그널)

단독 실행:
    cd generate
    python generate_html_review_summary.py
    python generate_html_review_summary.py --month 2026-04
    python generate_html_review_summary.py --month 2026-04 --output ../data/output --account RANKING_NAM

출력 경로:
    data/output/{YYYY_MM}_monthly/review_summary_{channel}_1.html
    data/output/{YYYY_MM}_monthly/review_summary_{channel}_2.html
    data/output/{YYYY_MM}_monthly/review_summary_{channel}_3.html

데이터 소스:
    data/hero/{YYYY_MM}/{channel}.xlsx
        summary 시트: brand, product, avg_star, first_review, last_review, review_growth_pct ...
        reviews 시트: review_date, rating, reviewer, content
        weekly  시트: week, date, rank, price, review/like, star
"""

import base64
import io
import logging
import os
import re
from datetime import datetime

import matplotlib
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import pandas as pd

matplotlib.use("Agg")

_KOREAN_FONTS = ["Malgun Gothic", "NanumGothic", "AppleGothic", "Noto Sans KR"]
for _font in _KOREAN_FONTS:
    if any(f.name == _font for f in fm.fontManager.ttflist):
        matplotlib.rc("font", family=_font)
        break
matplotlib.rc("axes", unicode_minus=False)

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

PATHS = {
    "hero_excel":     "../data/hero/{year_month}/{channel}.xlsx",
    "product_image":  "../data/raw/{channel}/{date}/{rank:02d}",
    "css":            "./css/style.css",
    "instagram_icon": "./images/instagram.png",
    "no_image":       "./images/no-image.png",
}

REVIEW_CHANNELS = ["naver", "coupang", "daiso", "kakao"]

CHANNEL_CONFIG = {
    "naver":   {"label": "네이버",   "logo_path": "./images/naver.png",   "color": "#03C75A"},
    "coupang": {"label": "쿠팡",     "logo_path": "./images/coupang.png", "color": "#FF4C00"},
    "daiso":   {"label": "다이소",   "logo_path": "./images/daiso.png",   "color": "#E60012"},
    "kakao":   {"label": "카카오",   "logo_path": "./images/kakao.png",   "color": "#F7D300"},
}

# ──────────────────────────────────────────────
# 분류 패턴
# ──────────────────────────────────────────────

KEYWORD_RULES = [
    ("수험생/시험기간", r"수험|시험|고3|공부|중간고사|기말|입시"),
    ("효과/집중력",     r"효과|집중|도움|좋아"),
    ("재구매",          r"재구매|재재|또 구매|또구매"),
]

BUYER_PATTERNS = {
    "학부모 (자녀 구매)": r"아이|아들|딸|자녀|애들|우리애|아이들",
    "본인 구매":          r"제가|저는|나는|본인|회사에서|직접",
    "선물/추천":          r"선물|지인|친구에게|추천해",
}

MOTIVE_PATTERNS = [
    ("효과/집중력 기대", r"효과|집중|도움|카페인"),
    ("자녀 건강 관리",   r"아이|아들|딸|자녀|애들|건강"),
    ("먹기 편한 형태",   r"젤리|식감|먹기 편|간편|씹"),
    ("재구매/충성",      r"재구매|재재|또 구매|또구매|계속"),
    ("맛",               r"맛있|맛이|오렌지|샤인|머스캣"),
]

FLAVOR_PATTERNS = {
    "오렌지":     r"오렌지|주황",
    "샤인머스캣":  r"샤인|머스캣|머스켓|연두",
}

NEGATIVE_CATEGORIES = [
    ("효과 체감 불확실", r"못 느끼|모르겠|글쎄|잘 모르"),
    ("맛/식감 호불호",   r"텁텁|쓰다|목이 말|맛없|아쉽"),
    ("유통기한/포장",    r"유통기한|포장|부서|파손"),
]


# ──────────────────────────────────────────────
# 경로 유틸
# ──────────────────────────────────────────────

def abs_to_rel(abs_path: str, from_dir: str) -> str:
    return os.path.relpath(abs_path, start=from_dir).replace("\\", "/")


def resolve_asset(relative_to_base: str, from_dir: str) -> str:
    abs_path = os.path.abspath(os.path.join(BASE_DIR, relative_to_base))
    return abs_to_rel(abs_path, from_dir)


def get_image_path(channel: str, date_str: str, rank: int, from_dir: str) -> str:
    tmpl = PATHS["product_image"]
    base = tmpl.format(channel=channel, date=date_str, rank=rank)
    for ext in ("jpg", "png", "jpeg", "webp"):
        abs_path = os.path.abspath(os.path.join(BASE_DIR, f"{base}.{ext}"))
        if os.path.exists(abs_path):
            return abs_to_rel(abs_path, from_dir)
    return resolve_asset(PATHS["no_image"], from_dir)


def get_product_image_path(channel: str, df_weekly: pd.DataFrame, from_dir: str) -> str:
    within_100 = df_weekly[df_weekly["rank"].astype(int) <= 100]
    if not within_100.empty:
        row = within_100.iloc[-1]
    else:
        row = df_weekly.iloc[-1]
    date_str = str(int(row["date"]))
    rank     = int(row["rank"])
    return get_image_path(channel, date_str, rank, from_dir)


# ──────────────────────────────────────────────
# 공통 데이터 로드
# ──────────────────────────────────────────────

def _load_hero_data(channel: str, year_month: str) -> dict:
    """채널 hero xlsx에서 summary, reviews, weekly를 한번에 로드."""
    excel_path = os.path.abspath(
        os.path.join(BASE_DIR, PATHS["hero_excel"].format(year_month=year_month, channel=channel))
    )
    return {
        "excel_path": excel_path,
        "summary":    pd.read_excel(excel_path, sheet_name="summary"),
        "reviews":    pd.read_excel(excel_path, sheet_name="reviews"),
        "weekly":     pd.read_excel(excel_path, sheet_name="weekly"),
    }


def extract_star(rating_val) -> int | None:
    m = re.match(r"(\d+)", str(rating_val).strip())
    return int(m.group(1)) if m else None


# ──────────────────────────────────────────────
# Page 1 분석: 리뷰 Overview
# ──────────────────────────────────────────────

def analyze_reviews(df: pd.DataFrame) -> dict:
    df = df.copy()
    df["star"] = df["rating"].apply(extract_star)
    df_valid  = df.dropna(subset=["star"])
    total     = len(df_valid)
    avg_star  = round(df_valid["star"].mean(), 2) if total > 0 else 0.0

    dist = {s: 0 for s in [5, 4, 3, 2, 1]}
    for s, cnt in df_valid["star"].value_counts().items():
        if s in dist:
            dist[s] = int(cnt)

    keywords = []
    for label, pattern in KEYWORD_RULES:
        count = int(df["content"].str.contains(pattern, na=False).sum())
        pct   = round(count / len(df) * 100) if len(df) > 0 else 0
        keywords.append({"label": label, "count": count, "pct": pct})

    five_star = df_valid[df_valid["star"] == 5].copy()
    five_star["len"] = five_star["content"].str.len()
    five_star = five_star[five_star["len"] >= 30]

    def pick_review(pattern: str) -> dict | None:
        sub = five_star[five_star["content"].str.contains(pattern, na=False)]
        if sub.empty:
            sub = five_star
        if sub.empty:
            return None
        row = sub.sample(1).iloc[0]
        return {
            "star":     int(row["star"]),
            "reviewer": str(row["reviewer"]),
            "date":     str(row["review_date"]),
            "content":  str(row["content"])[:90].replace("\n", " "),
        }

    rep_reviews = [
        pick_review(r"수험|시험|고3|공부"),
        pick_review(r"재구매|재재|또 구매"),
    ]
    rep_reviews = [r for r in rep_reviews if r]

    return {
        "total": total, "avg_star": avg_star, "dist": dist,
        "keywords": keywords, "rep_reviews": rep_reviews,
    }


# ──────────────────────────────────────────────
# Page 2 분석: 구매자 프로필
# ──────────────────────────────────────────────

def analyze_buyer_profile(df: pd.DataFrame) -> dict:
    total = len(df)
    if total == 0:
        return {"buyers": [], "timing": {}, "motives": []}

    # 구매자 유형
    buyers = []
    for label, pattern in BUYER_PATTERNS.items():
        count = int(df["content"].str.contains(pattern, na=False).sum())
        pct   = round(count / total * 100, 1)
        buyers.append({"label": label, "count": count, "pct": pct})
    buyers.sort(key=lambda x: x["count"], reverse=True)

    # 구매 시점 (시험기간 vs 일상)
    exam_count = int(df["content"].str.contains(r"수험|시험|고3|중간고사|기말|입시", na=False).sum())
    timing = {
        "시험기간": {"count": exam_count, "pct": round(exam_count / total * 100, 1)},
        "일상":     {"count": total - exam_count, "pct": round((total - exam_count) / total * 100, 1)},
    }

    # 구매 동기
    motives = []
    for label, pattern in MOTIVE_PATTERNS:
        count = int(df["content"].str.contains(pattern, na=False).sum())
        pct   = round(count / total * 100, 1)
        motives.append({"label": label, "count": count, "pct": pct})
    motives.sort(key=lambda x: x["count"], reverse=True)

    return {"buyers": buyers, "timing": timing, "motives": motives[:3]}


# ──────────────────────────────────────────────
# Page 3 분석: 기회와 리스크
# ──────────────────────────────────────────────

def analyze_sentiment(df: pd.DataFrame) -> dict:
    df = df.copy()
    df["star"] = df["rating"].apply(extract_star)
    total = len(df)

    positive = df[df["star"] >= 4]
    negative = df[df["star"] <= 3]

    # 맛 선호도
    flavors = {}
    for label, pattern in FLAVOR_PATTERNS.items():
        count = int(df["content"].str.contains(pattern, na=False).sum())
        flavors[label] = count

    # 부정 리뷰 카테고리
    neg_cats = []
    for label, pattern in NEGATIVE_CATEGORIES:
        matched = negative[negative["content"].str.contains(pattern, na=False)]
        if not matched.empty:
            sample = str(matched.iloc[0]["content"])[:80].replace("\n", " ")
            neg_cats.append({"label": label, "count": len(matched), "sample": sample})

    # 분류되지 않은 부정 리뷰도 "기타"로 추가
    classified_idx = set()
    for _, pattern in NEGATIVE_CATEGORIES:
        matched_idx = negative[negative["content"].str.contains(pattern, na=False)].index
        classified_idx.update(matched_idx)
    unclassified = negative[~negative.index.isin(classified_idx)]
    if not unclassified.empty:
        sample = str(unclassified.iloc[0]["content"])[:80].replace("\n", " ")
        neg_cats.append({"label": "기타", "count": len(unclassified), "sample": sample})

    neg_cats.sort(key=lambda x: x["count"], reverse=True)

    return {
        "positive_count": len(positive),
        "negative_count": len(negative),
        "positive_pct":   round(len(positive) / total * 100, 1) if total > 0 else 0,
        "negative_pct":   round(len(negative) / total * 100, 1) if total > 0 else 0,
        "flavors":        flavors,
        "neg_categories":  neg_cats,
    }


# ──────────────────────────────────────────────
# matplotlib 차트 빌더
# ──────────────────────────────────────────────

def _fig_to_b64(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=100, bbox_inches="tight", facecolor="#ffffff")
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")


def build_chart_buyer_profile(profile: dict, channel_color: str) -> str:
    """구매자 유형 + 구매 시점 + 동기 TOP3 가로 바 차트."""
    fig, axes = plt.subplots(1, 3, figsize=(10.8, 5.5), facecolor="#ffffff",
                             gridspec_kw={"width_ratios": [1, 0.7, 1]})

    for ax in axes:
        ax.set_facecolor("#ffffff")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["bottom"].set_visible(False)
        ax.spines["left"].set_visible(False)
        ax.tick_params(left=False, bottom=False)

    # --- 구매자 유형 ---
    ax1 = axes[0]
    buyers = profile["buyers"]
    labels = [b["label"] for b in buyers]
    values = [b["pct"] for b in buyers]
    bars = ax1.barh(labels[::-1], values[::-1], color=channel_color, height=0.5, alpha=0.85)
    ax1.set_xlim(0, max(values) * 1.4 if values else 100)
    ax1.set_xticklabels([])
    ax1.set_yticks(range(len(labels)))
    ax1.set_yticklabels(labels[::-1], fontsize=18, fontweight="bold")
    for bar, val in zip(bars, values[::-1]):
        ax1.text(bar.get_width() + 1, bar.get_y() + bar.get_height() / 2,
                 f"{val}%", va="center", fontsize=16, fontweight="bold", color="#333")
    ax1.set_title("구매자 프로필", fontsize=22, fontweight="bold", pad=16)

    # --- 구매 시점 ---
    ax2 = axes[1]
    timing = profile["timing"]
    t_labels = list(timing.keys())
    t_values = [timing[k]["pct"] for k in t_labels]
    bars2 = ax2.barh(t_labels[::-1], t_values[::-1], color=[channel_color, "#CCCCCC"], height=0.5, alpha=0.85)
    ax2.set_xlim(0, max(t_values) * 1.4 if t_values else 100)
    ax2.set_xticklabels([])
    ax2.set_yticks(range(len(t_labels)))
    ax2.set_yticklabels(t_labels[::-1], fontsize=18, fontweight="bold")
    for bar, val in zip(bars2, t_values[::-1]):
        ax2.text(bar.get_width() + 1, bar.get_y() + bar.get_height() / 2,
                 f"{val}%", va="center", fontsize=16, fontweight="bold", color="#333")
    ax2.set_title("구매 시점", fontsize=22, fontweight="bold", pad=16)

    # --- 구매 동기 TOP3 ---
    ax3 = axes[2]
    motives = profile["motives"]
    m_labels = [m["label"] for m in motives]
    m_values = [m["pct"] for m in motives]
    colors3 = [channel_color, channel_color + "BB", channel_color + "77"]
    bars3 = ax3.barh(m_labels[::-1], m_values[::-1], color=colors3[::-1], height=0.5, alpha=0.85)
    ax3.set_xlim(0, max(m_values) * 1.4 if m_values else 100)
    ax3.set_xticklabels([])
    ax3.set_yticks(range(len(m_labels)))
    ax3.set_yticklabels(m_labels[::-1], fontsize=18, fontweight="bold")
    for bar, val in zip(bars3, m_values[::-1]):
        ax3.text(bar.get_width() + 1, bar.get_y() + bar.get_height() / 2,
                 f"{val}%", va="center", fontsize=16, fontweight="bold", color="#333")
    ax3.set_title("구매 동기 TOP 3", fontsize=22, fontweight="bold", pad=16)

    fig.subplots_adjust(wspace=0.45)
    return _fig_to_b64(fig)


def build_chart_flavor(flavors: dict) -> str:
    """맛 선호도 가로 바 차트."""
    total = sum(flavors.values())
    if total == 0:
        return ""

    fig, ax = plt.subplots(figsize=(10.8, 2.2), facecolor="#ffffff")
    ax.set_facecolor("#ffffff")
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(left=False, bottom=False)

    labels = list(flavors.keys())
    values = [flavors[k] for k in labels]
    pcts   = [round(v / total * 100) for v in values]
    colors = ["#FF8C00", "#7CCD7C"]

    bars = ax.barh(labels[::-1], pcts[::-1], color=colors[::-1], height=0.5, alpha=0.9)
    ax.set_xlim(0, max(pcts) * 1.4)
    ax.set_xticklabels([])
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels[::-1], fontsize=20, fontweight="bold")

    for bar, pct, cnt in zip(bars, pcts[::-1], values[::-1]):
        ax.text(bar.get_width() + 1, bar.get_y() + bar.get_height() / 2,
                f"{pct}% ({cnt}건)", va="center", fontsize=17, fontweight="bold", color="#333")

    return _fig_to_b64(fig)


# ──────────────────────────────────────────────
# HTML 공통 파츠
# ──────────────────────────────────────────────

def _header_html(cfg: dict, month_str: str, from_dir: str, instagram_account: str, year_month: str) -> str:
    css_rel   = resolve_asset(PATHS["css"], from_dir)
    insta_rel = resolve_asset(PATHS["instagram_icon"], from_dir)
    logo_rel  = resolve_asset(cfg["logo_path"], from_dir)

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{cfg['label']} 리뷰 써머리</title>
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
        <div class="top-right">출처: {cfg['label']} ({year_month.replace('_', '.')} ver.)</div>
      </div>

      <div class="hero-section">
        <div class="hero-left">
          <img src="{logo_rel}" alt="{cfg['label']}" class="hero-logo" />
        </div>
        <div class="hero-right trend-hero-right">
          <div class="trend-title-lines">
            <p class="trend-title-type">{month_str}월</p>
            <p class="trend-title-brand">REVIEW</p>
          </div>
        </div>
      </div>
"""


def _footer_html() -> str:
    return """
    </section>
  </div>
</body>
</html>
"""


def _section_title_html(title: str, channel_color: str) -> str:
    return f"""
      <div style="display:flex;align-items:center;gap:12px;margin-bottom:18px;">
        <div style="width:6px;height:36px;background:{channel_color};border-radius:3px;"></div>
        <span style="font-size:36px;font-weight:800;color:#111;font-family:'GmarketSans';letter-spacing:-0.05em;">{title}</span>
      </div>"""


def _divider_html(bold: bool = False) -> str:
    weight = "2px solid #000" if bold else "1.5px solid #E0E0E0"
    return f'<div style="border-top:{weight};margin-bottom:22px;"></div>'


def _insight_box_html(text: str, channel_color: str) -> str:
    return f"""
      <div style="
        background:{channel_color}11;
        border-left:5px solid {channel_color};
        border-radius:0 12px 12px 0;
        padding:22px 28px;
        margin-top:12px;
      ">
        <div style="font-size:28px;font-weight:600;color:#222;font-family:'Pretendard';line-height:1.6;letter-spacing:-0.03em;">
          {text}
        </div>
      </div>"""


# ──────────────────────────────────────────────
# Page 1: Overview
# ──────────────────────────────────────────────

def _rating_bars_html(dist: dict, total: int) -> str:
    rows = ""
    for star in [5, 4, 3, 2, 1]:
        cnt = dist.get(star, 0)
        pct = round(cnt / total * 100) if total > 0 else 0
        color = "#FFD700" if star >= 4 else ("#AAAAAA" if star == 3 else "#CCCCCC")
        rows += f"""
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">
          <span style="font-size:28px;font-weight:700;color:#444;width:30px;text-align:right;font-family:'GmarketSans';">{star}</span>
          <span style="font-size:24px;color:{color};">★</span>
          <div style="flex:1;background:#EFEFEF;border-radius:6px;height:22px;overflow:hidden;">
            <div style="width:{pct}%;height:100%;background:{color};border-radius:6px;"></div>
          </div>
          <span style="font-size:26px;color:#666;width:70px;text-align:right;font-family:'Pretendard';">{cnt}건</span>
        </div>"""
    return rows


def _keyword_tags_html(keywords: list, channel_color: str) -> str:
    tags = ""
    for kw in keywords:
        tags += f"""
        <div style="
          background:{channel_color}22;
          border:2px solid {channel_color};
          border-radius:50px;
          padding:14px 28px;
          text-align:center;
          flex:1;
        ">
          <div style="font-size:26px;font-weight:700;color:{channel_color};font-family:'GmarketSans';letter-spacing:-0.05em;">{kw['label']}</div>
          <div style="font-size:32px;font-weight:900;color:#111;font-family:'GmarketSans';letter-spacing:-0.05em;margin-top:4px;">{kw['count']}건 <span style="font-size:24px;font-weight:500;color:#888;">({kw['pct']}%)</span></div>
        </div>"""
    return tags


def _review_card_html(review: dict, channel_color: str) -> str:
    stars = "★" * review["star"] + "☆" * (5 - review["star"])
    return f"""
    <div style="
      background:#F9F9F9;
      border-left:5px solid {channel_color};
      border-radius:0 12px 12px 0;
      padding:24px 28px;
    ">
      <div style="display:flex;align-items:center;gap:12px;margin-bottom:10px;">
        <span style="font-size:26px;color:#FFD700;letter-spacing:2px;">{stars}</span>
        <span style="font-size:24px;color:#888;font-family:'Pretendard';">{review['reviewer']} / {review['date']}</span>
      </div>
      <div style="font-size:30px;font-weight:500;color:#222;font-family:'Pretendard';line-height:1.5;letter-spacing:-0.03em;">
        &ldquo;{review['content']}&rdquo;
      </div>
    </div>"""


def build_page1_html(channel: str, year_month: str, from_dir: str,
                     data: dict, instagram_account: str) -> str:
    cfg     = CHANNEL_CONFIG[channel]
    summary = data["summary"].iloc[0]
    month_str = year_month.split("_")[1].lstrip("0")

    brand   = str(summary["brand"])
    product = str(summary["product"])
    product_display = product[:28] + "..." if len(product) > 28 else product

    analysis = analyze_reviews(data["reviews"])

    review_growth_pct = float(summary.get("review_growth_pct", 0))
    review_growth     = int(summary.get("review_growth", 0))

    prod_img = get_product_image_path(channel, data["weekly"], from_dir)

    header = _header_html(cfg, month_str, from_dir, instagram_account, year_month)

    return header + f"""
      <!-- 제품 정보 -->
      <div style="display:flex;align-items:center;gap:24px;margin-bottom:22px;padding:0 4px;">
        <img src="{prod_img}" alt="product"
             style="width:110px;height:110px;border-radius:50%;object-fit:cover;border:3px solid {cfg['color']};flex-shrink:0;" />
        <div style="min-width:0;">
          <div style="font-size:28px;font-weight:700;color:{cfg['color']};font-family:'Pretendard';letter-spacing:-0.03em;">{brand}</div>
          <div style="font-size:30px;font-weight:600;color:#111;font-family:'Pretendard';letter-spacing:-0.04em;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{product_display}</div>
        </div>
      </div>

      {_divider_html(bold=True)}

      <!-- 별점 + 분포 -->
      <div style="display:flex;align-items:flex-start;gap:40px;margin-bottom:22px;">
        <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;min-width:200px;">
          <div style="font-size:96px;font-weight:900;font-family:'GmarketSans';color:#111;line-height:1;letter-spacing:-0.05em;">{analysis['avg_star']}</div>
          <div style="font-size:40px;color:#FFD700;letter-spacing:4px;margin:4px 0;">{'★' * round(analysis['avg_star'])}{'☆' * (5 - round(analysis['avg_star']))}</div>
          <div style="font-size:26px;color:#888;font-family:'Pretendard';">리뷰 {analysis['total']:,}건</div>
          <div style="font-size:24px;color:{cfg['color']};font-weight:700;font-family:'Pretendard';margin-top:6px;">+{review_growth:,}건 ({review_growth_pct:.1f}%)</div>
        </div>
        <div style="flex:1;padding-top:10px;">
          {_rating_bars_html(analysis['dist'], analysis['total'])}
        </div>
      </div>

      {_divider_html()}

      <!-- 키워드 -->
      <div style="display:flex;gap:16px;margin-bottom:22px;">
        {_keyword_tags_html(analysis['keywords'], cfg['color'])}
      </div>

      {_divider_html()}

      <!-- 대표 리뷰 -->
      <div style="display:flex;flex-direction:column;gap:18px;">
        {"".join(_review_card_html(r, cfg['color']) for r in analysis['rep_reviews'])}
      </div>
""" + _footer_html()


# ──────────────────────────────────────────────
# Page 2: 구매자 프로필
# ──────────────────────────────────────────────

def build_page2_html(channel: str, year_month: str, from_dir: str,
                     data: dict, instagram_account: str) -> str:
    cfg       = CHANNEL_CONFIG[channel]
    month_str = year_month.split("_")[1].lstrip("0")

    profile   = analyze_buyer_profile(data["reviews"])
    chart_b64 = build_chart_buyer_profile(profile, cfg["color"])

    header = _header_html(cfg, month_str, from_dir, instagram_account, year_month)

    # 인사이트 텍스트 생성
    top_buyer = profile["buyers"][0]["label"] if profile["buyers"] else "알 수 없음"
    top_pct   = profile["buyers"][0]["pct"] if profile["buyers"] else 0
    exam_pct  = profile["timing"].get("시험기간", {}).get("pct", 0)

    insight_text = (
        f"실구매자의 <b>{top_pct}%</b>가 <b>{top_buyer}</b>입니다.<br>"
        f"시험기간에 전체 리뷰의 <b>{exam_pct}%</b>가 집중되어 "
        f"광고 타깃은 <b>35~50대 학부모</b>층, "
        f"시험 2주 전부터 집행하는 것이 효과적입니다."
    )

    return header + f"""
      {_section_title_html("누가, 언제, 왜 사는가", cfg['color'])}

      <!-- 차트 -->
      <div style="margin-bottom:20px;">
        <img src="data:image/png;base64,{chart_b64}"
             style="width:100%;border-radius:8px;" alt="구매자 프로필 차트" />
      </div>

      {_divider_html()}

      {_section_title_html("실무 인사이트", cfg['color'])}

      {_insight_box_html(insight_text, cfg['color'])}
""" + _footer_html()


# ──────────────────────────────────────────────
# Page 3: 기회와 리스크
# ──────────────────────────────────────────────

def build_page3_html(channel: str, year_month: str, from_dir: str,
                     data: dict, instagram_account: str) -> str:
    cfg       = CHANNEL_CONFIG[channel]
    month_str = year_month.split("_")[1].lstrip("0")

    sentiment = analyze_sentiment(data["reviews"])

    header = _header_html(cfg, month_str, from_dir, instagram_account, year_month)

    # 강화 포인트
    positive_html = f"""
      <div style="
        background:#F0FFF0;
        border-radius:12px;
        padding:24px 28px;
        margin-bottom:20px;
      ">
        <div style="font-size:30px;font-weight:800;color:#2E8B57;font-family:'Pretendard';margin-bottom:12px;">
          긍정 {sentiment['positive_count']}건 ({sentiment['positive_pct']}%)
        </div>
        <div style="font-size:28px;color:#333;font-family:'Pretendard';line-height:1.6;">
          &ldquo;효과 짱&rdquo; &ldquo;먹기 편해&rdquo; &ldquo;재구매&rdquo;<br>
          <span style="color:#666;">제약사 신뢰 + 젤리 편의성이 핵심 구매 드라이버</span>
        </div>
      </div>"""

    # 맛 선호도
    flavor_html = ""
    if sentiment["flavors"] and sum(sentiment["flavors"].values()) > 0:
        flavor_b64 = build_chart_flavor(sentiment["flavors"])
        if flavor_b64:
            flavor_html = f"""
      {_section_title_html("맛 선호도", cfg['color'])}
      <div style="margin-bottom:20px;">
        <img src="data:image/png;base64,{flavor_b64}"
             style="width:100%;border-radius:8px;" alt="맛 선호도" />
      </div>"""

    # 부정 리뷰
    neg_items = ""
    for i, cat in enumerate(sentiment["neg_categories"], 1):
        neg_items += f"""
        <div style="margin-bottom:16px;">
          <div style="font-size:28px;font-weight:700;color:#C0392B;font-family:'Pretendard';">
            {i}. {cat['label']} ({cat['count']}건)
          </div>
          <div style="font-size:26px;color:#666;font-family:'Pretendard';margin-top:4px;font-style:italic;">
            &ldquo;{cat['sample']}&rdquo;
          </div>
        </div>"""

    negative_html = f"""
      <div style="
        background:#FFF5F5;
        border-radius:12px;
        padding:24px 28px;
        margin-bottom:20px;
      ">
        <div style="font-size:30px;font-weight:800;color:#C0392B;font-family:'Pretendard';margin-bottom:12px;">
          개선 시그널 {sentiment['negative_count']}건 ({sentiment['negative_pct']}%)
        </div>
        {neg_items}
      </div>"""

    # 액션 아이템
    action_text = (
        "1. 맛 라인업 확대 시 <b>텁텁함 개선</b> 우선<br>"
        "2. <b>효과 체감 후기</b> UGC 마케팅 강화<br>"
        "3. 시험 시즌 <b>2주 전</b> 타깃 광고 집행"
    )

    return header + f"""
      {_section_title_html("강화 포인트", cfg['color'])}
      {positive_html}

      {flavor_html}

      {_divider_html()}

      {_section_title_html("개선 시그널", cfg['color'])}
      {negative_html}

      {_divider_html()}

      {_section_title_html("액션 아이템", cfg['color'])}
      {_insight_box_html(action_text, cfg['color'])}
""" + _footer_html()


# ──────────────────────────────────────────────
# 저장 / 실행
# ──────────────────────────────────────────────

def save_review_summary(
    channel: str,
    year_month: str,
    output_dir: str,
    instagram_account: str = "RANKING_NAM",
) -> list[str]:
    folder   = os.path.join(output_dir, f"{year_month}_monthly")
    from_dir = os.path.abspath(folder)
    os.makedirs(folder, exist_ok=True)

    data = _load_hero_data(channel, year_month)

    builders = [
        (f"review_summary_{channel}_1.html", build_page1_html),
        (f"review_summary_{channel}_2.html", build_page2_html),
        (f"review_summary_{channel}_3.html", build_page3_html),
    ]

    saved = []
    for filename, builder_fn in builders:
        filepath = os.path.join(folder, filename)
        html = builder_fn(channel, year_month, from_dir, data, instagram_account)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html)
        logger.info(f"[{channel}] {filename} 저장 완료")
        saved.append(filepath)

    return saved


def run(year: int, month: int, output_dir: str, instagram_account: str) -> dict:
    year_month = f"{year}_{month:02d}"
    results = {"success": 0, "fail": 0}

    for channel in REVIEW_CHANNELS:
        excel_path = os.path.abspath(
            os.path.join(BASE_DIR, PATHS["hero_excel"].format(year_month=year_month, channel=channel))
        )
        if not os.path.exists(excel_path):
            logger.info(f"[{channel}] 파일 없음, 건너뜀")
            continue

        try:
            df_test = pd.read_excel(excel_path, sheet_name="reviews", nrows=1)
            if df_test.empty:
                logger.info(f"[{channel}] reviews 시트 비어있음, 건너뜀")
                continue
        except Exception:
            logger.info(f"[{channel}] reviews 시트 없음, 건너뜀")
            continue

        try:
            save_review_summary(channel, year_month, output_dir, instagram_account)
            results["success"] += 1
        except Exception as e:
            logger.error(f"[{channel}] 생성 실패: {e}", exc_info=True)
            results["fail"] += 1

    return results


# ──────────────────────────────────────────────
# 단독 실행
# ──────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    parser = argparse.ArgumentParser(description="히어로 리뷰 써머리 카드뉴스 HTML 생성 (3장)")
    parser.add_argument("--month",   default=None,             help="YYYY-MM (기본값: 전월)")
    parser.add_argument("--output",  default="../data/output", help="출력 루트 디렉토리")
    parser.add_argument("--account", default="RANKING_NAM",   help="인스타그램 계정명")
    args = parser.parse_args()

    if args.month:
        y, m = map(int, args.month.split("-"))
    else:
        now = datetime.now()
        m   = now.month - 1 or 12
        y   = now.year if now.month > 1 else now.year - 1

    result = run(y, m, args.output, args.account)
    print(f"\ncomplete: {result['success']} ok / {result['fail']} fail")
