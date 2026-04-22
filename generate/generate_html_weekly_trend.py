"""
generate_html_weekly_trend.py
------------------------------
채널별 히어로 제품 주간 순위 추이 카드 HTML 생성 모듈

단독 실행:
    cd generate
    python generate_html_weekly_trend.py
    python generate_html_weekly_trend.py --month 2026-04
    python generate_html_weekly_trend.py --month 2026-04 --output ../data/output --account RANKING_NAM

출력 경로:
    data/output/{YYYY_MM}_monthly/weekly_trend_{channel}.html

데이터 소스:
    data/hero/{YYYY_MM}/{channel}.xlsx
        weekly  시트: week, date, rank, price, review/like, star
        summary 시트: brand, last_date, last_rank, ...
"""

import base64
import io
import logging
import os
from datetime import datetime

import matplotlib
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import pandas as pd

matplotlib.use("Agg")

# 한글 폰트 설정 (Windows: Malgun Gothic)
import matplotlib.font_manager as fm
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

CHANNEL_COLORS = {
    "naver":      "#03C75A",
    "coupang":    "#FF4C00",
    "oliveyoung": "#00A651",
    "kakao":      "#F7D300",
    "daiso":      "#E60012",
}

CHANNEL_CONFIG = {
    "naver":      {"label": "네이버",   "upper": "NAVER",      "logo_path": "./images/naver.png"},
    "coupang":    {"label": "쿠팡",     "upper": "COUPANG",    "logo_path": "./images/coupang.png"},
    "oliveyoung": {"label": "올리브영", "upper": "OLIVEYOUNG", "logo_path": "./images/oliveyoung.png"},
    "kakao":      {"label": "카카오",   "upper": "KAKAO",      "logo_path": "./images/kakao.png"},
    "daiso":      {"label": "다이소",   "upper": "DAISO",      "logo_path": "./images/daiso.png"},
}


# ──────────────────────────────────────────────
# 경로 유틸
# ──────────────────────────────────────────────
def abs_to_rel(abs_path: str, from_dir: str) -> str:
    return os.path.relpath(abs_path, start=from_dir).replace("\\", "/")


def resolve_asset(relative_to_base: str, from_dir: str) -> str:
    abs_path = os.path.abspath(os.path.join(BASE_DIR, relative_to_base))
    return abs_to_rel(abs_path, from_dir)


def get_image_path(channel: str, date: str, rank: int, from_dir: str) -> str:
    base_path = PATHS["product_image"].format(channel=channel, date=date, rank=rank)
    for ext in ("jpg", "png", "jpeg", "webp"):
        abs_path = os.path.abspath(os.path.join(BASE_DIR, f"{base_path}.{ext}"))
        if os.path.exists(abs_path):
            return abs_to_rel(abs_path, from_dir)
    return resolve_asset(PATHS["no_image"], from_dir)


# ──────────────────────────────────────────────
# 차트 생성
# ──────────────────────────────────────────────
def build_chart_b64(df_weekly: pd.DataFrame, channel: str) -> str:
    """weekly 시트 DataFrame으로 순위 + 리뷰 정규화 꺾은선을 단일 차트에 생성하고 base64 PNG 반환."""
    import matplotlib.patheffects as pe
    import numpy as np
    try:
        from scipy.interpolate import make_interp_spline
        HAS_SCIPY = True
    except ImportError:
        HAS_SCIPY = False

    RANK_COLOR   = "#EF402F"
    REVIEW_COLOR = "#4590CA"

    shadow = [
        pe.SimpleLineShadow(shadow_color="#000000", alpha=0.25, offset=(2, -2)),
        pe.Normal(),
    ]
    # 텍스트 외곽선: 각 그래프 색상과 동일한 stroke → 더 굵고 선명하게
    rank_label_fx   = [pe.withStroke(linewidth=2, foreground=RANK_COLOR),   pe.Normal()]
    review_label_fx = [pe.withStroke(linewidth=2, foreground=REVIEW_COLOR), pe.Normal()]

    def smooth_line(x_pts, y_pts):
        """scipy 있으면 스플라인, 데이터 수에 따라 k 자동 조정."""
        if HAS_SCIPY and len(x_pts) >= 2:
            k = min(3, len(x_pts) - 1)
            x_s = np.linspace(x_pts[0], x_pts[-1], 300)
            spl = make_interp_spline(x_pts, y_pts, k=k)
            return x_s, spl(x_s)
        return np.array(x_pts), np.array(y_pts)

    # date 컬럼 → "MM/DD" 문자열
    dates    = [str(int(d)) for d in df_weekly["date"]]
    x_labels = [f"{d[4:6]}/{d[6:8]}" for d in dates]
    ranks    = list(df_weekly["rank"].astype(int))
    n        = len(ranks)
    x        = list(range(n))

    # 랭킹 정규화: 1위=1.0 → 밴드 [0.1, 0.9]
    min_rank, max_rank = min(ranks), max(ranks)
    r_range    = max_rank - min_rank if max_rank != min_rank else 1
    norm_ranks = [0.1 + ((max_rank - r) / r_range) * 0.8 for r in ranks]

    # 리뷰/좋아요 컬럼 감지
    review_col = next(
        (c for c in ("review", "like") if c in df_weekly.columns and df_weekly[c].notna().any()),
        None,
    )
    has_review = review_col is not None

    fig, ax = plt.subplots(
        figsize=(10.8, 10.5), dpi=100, facecolor="#ffffff",
        constrained_layout=True,
    )
    ax.set_facecolor("#ffffff")
    ax.set_ylim(-0.18, 1.12)
    ax.set_xlim(-0.5, n - 0.5)

    # ── 리뷰 선 (먼저 그려서 순위 선이 위에 오도록) ──
    if has_review:
        reviews   = df_weekly[review_col].fillna(0).astype(float).tolist()
        rv_min, rv_max = min(reviews), max(reviews)
        rv_range  = rv_max - rv_min if rv_max != rv_min else 1
        # 밴드 [0, 0.8]
        norm_revs = [((r - rv_min) / rv_range) * 0.8 for r in reviews]

        xs, ys = smooth_line(x, norm_revs)
        ax.plot(xs, ys, color=REVIEW_COLOR, linewidth=8, zorder=2, path_effects=shadow)
        ax.plot(x, norm_revs, "o", color=REVIEW_COLOR, markersize=16,
                markerfacecolor="#ffffff", markeredgecolor=REVIEW_COLOR, markeredgewidth=3, zorder=3)

        # 리뷰 레이블: 항상 선 아래 배치 + 흰색 배경 박스
        for xi, rv, nv in zip(x, reviews, norm_revs):
            ax.annotate(
                f"{int(rv):,}개", xy=(xi, nv), xytext=(0, -32),
                textcoords="offset points", ha="center", va="top",
                fontsize=24, fontweight="bold", color=REVIEW_COLOR,
                path_effects=review_label_fx, zorder=10, clip_on=False,
                bbox=dict(facecolor="white", alpha=0.85, edgecolor="none",
                          boxstyle="round,pad=0.2"),
            )

    # ── 순위 선 ──
    xs, ys = smooth_line(x, norm_ranks)
    ax.plot(xs, ys, color=RANK_COLOR, linewidth=8, zorder=4, path_effects=shadow)
    ax.plot(x, norm_ranks, "o", color=RANK_COLOR, markersize=16,
            markerfacecolor="#ffffff", markeredgecolor=RANK_COLOR, markeredgewidth=3, zorder=5)

    # 순위 레이블: 항상 선 위 배치 + 흰색 배경 박스
    for xi, rank, nv in zip(x, ranks, norm_ranks):
        ax.annotate(
            f"{rank}위", xy=(xi, nv), xytext=(0, 32),
            textcoords="offset points", ha="center", va="bottom",
            fontsize=24, fontweight="bold", color=RANK_COLOR,
            path_effects=rank_label_fx, zorder=10, clip_on=False,
            bbox=dict(facecolor="white", alpha=0.85, edgecolor="none",
                      boxstyle="round,pad=0.2"),
        )

    # ── 축 설정 ──
    ax.set_xticks(x)
    ax.set_xticklabels(x_labels, fontsize=18, fontweight="bold")
    # Y축 tick/label 숨기되 grid는 유지
    ax.tick_params(axis="y", which="both", left=False, labelleft=False)
    ax.yaxis.grid(True, linestyle="--", alpha=0.3, color="#9A9A9A")
    ax.xaxis.grid(False)

    # ── 범례: X축 우측 상단 ──
    from matplotlib.lines import Line2D
    review_label_name = "좋아요" if has_review and review_col == "like" else "리뷰수"
    legend_handles = [
        Line2D([0], [0], color=RANK_COLOR,   linewidth=4, marker="o",
               markerfacecolor="#ffffff", markeredgecolor=RANK_COLOR, markeredgewidth=2,
               markersize=10, label="순위"),
    ]
    if has_review:
        legend_handles.append(
            Line2D([0], [0], color=REVIEW_COLOR, linewidth=4, marker="o",
                   markerfacecolor="#ffffff", markeredgecolor=REVIEW_COLOR, markeredgewidth=2,
                   markersize=10, label=review_label_name)
        )
    legend = ax.legend(
        handles=legend_handles,
        loc="lower right",
        fontsize=18,
        frameon=False,
        labelcolor="black",
    )
    ax.set_axisbelow(True)

    # X축 하단 선 검은색
    for side, spine in ax.spines.items():
        if side == "bottom":
            spine.set_visible(True)
            spine.set_color("#000000")
            spine.set_linewidth(1.5)
        else:
            spine.set_visible(False)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=100, bbox_inches="tight", facecolor="#ffffff")
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")


# ──────────────────────────────────────────────
# HTML 빌더
# ──────────────────────────────────────────────
def build_weekly_trend_html(
    df_weekly: pd.DataFrame,
    df_summary: pd.DataFrame,
    channel: str,
    year_month: str,
    from_dir: str,
    instagram_account: str = "RANKING_NAM",
) -> str:
    cfg = CHANNEL_CONFIG[channel]
    color = CHANNEL_COLORS[channel]

    # 날짜 파싱: weekly 시트의 마지막 date
    last_date_int = int(df_weekly["date"].iloc[-1])
    last_date_str = str(last_date_int)
    date_display = (
        f"{last_date_str[:4]}년 {last_date_str[4:6]}월 {last_date_str[6:8]}일"
    )

    # 월 표시
    ym = year_month  # "YYYY-MM"
    month_num = ym.split("-")[1].lstrip("0")  # "04" → "4"

    # 제품 이미지 경로: weekly 시트에서 rank <= 100인 가장 최근 주차 사용
    # (이미지는 1~120위까지만 저장되므로 100위 이내 주차 우선)
    within_100 = df_weekly[df_weekly["rank"].astype(int) <= 100]
    if not within_100.empty:
        img_row = within_100.iloc[-1]   # 가장 최근 행
        img_date = str(int(img_row["date"]))
        img_rank = int(img_row["rank"])
    else:
        img_date = last_date_str
        img_rank = int(df_summary["last_rank"].iloc[0])
    product_img_path = get_image_path(channel, img_date, img_rank, from_dir)

    # 브랜드명
    brand = str(df_summary["brand"].iloc[0]).strip()

    # 차트 base64
    chart_b64 = build_chart_b64(df_weekly, channel)

    # 에셋 경로
    css_rel   = resolve_asset(PATHS["css"], from_dir)
    insta_rel = resolve_asset(PATHS["instagram_icon"], from_dir)
    logo_rel  = resolve_asset(cfg["logo_path"], from_dir)

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{cfg['label']} 히어로 주간 순위 추이</title>
  <link rel="stylesheet" href="{css_rel}" />
  <style>
    .weekly-trend-body {{
      position: relative;
      flex: 1;
      min-height: 0;
    }}
    .trend-chart-wrap {{
      position: absolute;
      bottom: 0;
      left: 0;
      width: 100%;
    }}
    .trend-chart-wrap img {{
      width: 100%;
      display: block;
    }}
    .weekly-product-circle {{
      position: absolute;
      top: 0;
      left: 36px;
      width: 280px;
      height: 280px;
      border-radius: 50%;
      overflow: hidden;
      border: 4px solid #000000;
      box-shadow: 4px 4px 10px rgba(0,0,0,0.3);
      background: #ffffff;
      z-index: 10;
    }}
    .weekly-product-circle img {{
      width: 100%;
      height: 100%;
      object-fit: cover;
    }}
    .weekly-brand-label {{
      position: absolute;
      top: 290px;
      left: 36px;
      width: 280px;
      text-align: center;
      font-family: 'Pretendard';
      font-size: 36px;
      font-weight: 700;
      color: #000000;
      letter-spacing: -0.05em;
      z-index: 10;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }}
  </style>
</head>
<body>
  <div class="canvas">
    <section class="card" style="display:flex; flex-direction:column;">

      <div class="top-bar">
        <div class="top-left">
          <img src="{insta_rel}" alt="instagram" class="insta-logo" />
          <span class="ranking-name">{instagram_account}</span>
        </div>
        <div class="top-right">
          출처: {cfg['label']} ({date_display} ver.)
        </div>
      </div>

      <div class="hero-section" style="flex-shrink:0;">
        <div class="hero-left">
          <img src="{logo_rel}" alt="{cfg['label']}" class="hero-logo" />
        </div>
        <div class="hero-right trend-hero-right">
          <div class="trend-title-lines">
            <p class="trend-title-type">{month_num}월</p>
            <p class="trend-title-brand">HERO</p>
          </div>
        </div>
      </div>

      <div class="weekly-trend-body">
        <div class="weekly-product-circle">
          <img src="{product_img_path}" alt="{brand} 제품 이미지" />
        </div>
        <div class="weekly-brand-label">{brand}</div>
        <div class="trend-chart-wrap">
          <img src="data:image/png;base64,{chart_b64}" alt="주간 순위 추이 차트" />
        </div>
      </div>

    </section>
  </div>
</body>
</html>
"""


# ──────────────────────────────────────────────
# 데이터 로딩
# ──────────────────────────────────────────────
def load_hero_data(
    channel: str, year_month: str
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    히어로 엑셀에서 weekly, summary 시트를 읽어 반환.
    year_month: "YYYY-MM" 형식
    """
    ym_path = year_month.replace("-", "_")  # "2026-04" → "2026_04"
    rel_path = PATHS["hero_excel"].format(
        year_month=ym_path, channel=channel
    )
    excel_path = os.path.abspath(os.path.join(BASE_DIR, rel_path))

    if not os.path.exists(excel_path):
        raise FileNotFoundError(
            f"히어로 엑셀 파일을 찾을 수 없습니다: {excel_path}"
        )

    logger.info(f"[{channel}] Excel 로드: {excel_path}")
    df_weekly  = pd.read_excel(excel_path, sheet_name="weekly")
    df_summary = pd.read_excel(excel_path, sheet_name="summary")
    return df_weekly, df_summary


# ──────────────────────────────────────────────
# 저장
# ──────────────────────────────────────────────
def save_weekly_trend_card(
    channel: str,
    year_month: str,
    output_dir: str,
    instagram_account: str = "RANKING_NAM",
) -> str:
    """
    단일 채널의 주간 추이 카드를 생성하고 저장.
    반환값: 저장된 파일 경로
    """
    df_weekly, df_summary = load_hero_data(channel, year_month)

    # 출력 디렉토리: data/output/{YYYY_MM}_monthly/
    ym_dir = year_month.replace("-", "_")  # "2026_04"
    out_dir = os.path.join(output_dir, f"{ym_dir}_monthly")
    os.makedirs(out_dir, exist_ok=True)

    filepath = os.path.join(out_dir, f"weekly_trend_{channel}.html")
    from_dir = os.path.abspath(out_dir)

    html = build_weekly_trend_html(
        df_weekly=df_weekly,
        df_summary=df_summary,
        channel=channel,
        year_month=year_month,
        from_dir=from_dir,
        instagram_account=instagram_account,
    )

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)

    logger.info(f"저장 완료: {filepath}")
    return filepath


# ──────────────────────────────────────────────
# 단독 실행 진입점
# ──────────────────────────────────────────────
def run(
    year_month: str,
    output_dir: str,
    instagram_account: str = "RANKING_NAM",
) -> dict[str, int]:
    """
    전체 채널 주간 추이 카드 일괄 생성.

    Args:
        year_month:        "YYYY-MM" 형식 (예: "2026-04")
        output_dir:        결과 저장 루트 (기본값: "../data/output")
        instagram_account: 인스타그램 계정명

    반환값:
        {"success": N, "fail": N}
    """
    logger.info(f"[WEEKLY TREND HTML] 대상 월: {year_month}")
    success, fail = 0, 0

    for channel in CHANNEL_CONFIG:
        try:
            path = save_weekly_trend_card(
                channel=channel,
                year_month=year_month,
                output_dir=output_dir,
                instagram_account=instagram_account,
            )
            logger.info(f"[{channel}] 완료 → {path}")
            success += 1
        except FileNotFoundError as e:
            logger.warning(f"[{channel}] 파일 없음 — 건너뜀: {e}")
            fail += 1
        except Exception as e:
            logger.error(f"[{channel}] 생성 실패: {e}")
            fail += 1

    logger.info(
        f"[WEEKLY TREND HTML] 완료 — 성공 {success}개 / 실패 {fail}개"
    )
    return {"success": success, "fail": fail}


if __name__ == "__main__":
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    parser = argparse.ArgumentParser(
        description="히어로 제품 주간 순위 추이 HTML 카드 생성"
    )
    parser.add_argument(
        "--month",
        default=None,
        help="대상 월 YYYY-MM (기본값: 이번 달)",
    )
    parser.add_argument(
        "--output",
        default="../data/output",
        help="결과 저장 루트 디렉토리 (기본값: ../data/output)",
    )
    parser.add_argument(
        "--account",
        default="RANKING_NAM",
        help="인스타그램 계정명 (기본값: RANKING_NAM)",
    )
    args = parser.parse_args()

    year_month = args.month or datetime.today().strftime("%Y-%m")

    result = run(
        year_month=year_month,
        output_dir=args.output,
        instagram_account=args.account,
    )
    print(f"완료: 성공 {result['success']}개 / 실패 {result['fail']}개")
