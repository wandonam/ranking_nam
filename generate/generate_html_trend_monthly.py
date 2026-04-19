"""
generate_html_trend_monthly.py
--------------------------------
월간 히어로 제품 순위 추이 카드 HTML 생성 모듈 (Card 2)

matplotlib으로 주간 순위 라인 차트를 생성하고 base64로 HTML에 삽입합니다.
출력: data/output/{YYYY_MM_monthly}/trend_{channel}.html/.png

단독 실행:
    python generate_html_trend_monthly.py --month 2026-04
    python generate_html_trend_monthly.py --month 2026-04 --output ../data/output
"""

import base64
import io
import logging
import os
from datetime import datetime

import matplotlib
matplotlib.use("Agg")  # 헤드리스 환경
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import pandas as pd

# 한글 폰트 (Windows: Malgun Gothic, 없으면 기본 폰트)
import matplotlib.font_manager as fm
_KR_FONTS = ["Malgun Gothic", "AppleGothic", "NanumGothic", "DejaVu Sans"]
plt.rcParams["font.family"] = next(
    (f for f in _KR_FONTS if any(f in ff.name for ff in fm.fontManager.ttflist)),
    "DejaVu Sans",
)
plt.rcParams["axes.unicode_minus"] = False

# matplotlib의 categorical units 반복 INFO 억제
logging.getLogger("matplotlib").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

PATHS = {
    "monthly_excel":  "../data/report/{year_month}_monthly.xlsx",
    "css":            "./css/style.css",
    "instagram_icon": "./images/instagram.png",
}

# 채널별 차트 색상
CHANNEL_COLORS = {
    "naver":      "#03C75A",
    "coupang":    "#FF4C00",
    "oliveyoung": "#00A651",
    "kakao":      "#F7D300",
    "daiso":      "#E60012",
}

TREND_CHANNEL_CONFIG = {
    "naver":      {"channel_label": "네이버",   "logo_path": "./images/naver.png",      "filename": "trend_naver"},
    "coupang":    {"channel_label": "쿠팡",     "logo_path": "./images/coupang.png",    "filename": "trend_coupang"},
    "oliveyoung": {"channel_label": "올리브영", "logo_path": "./images/oliveyoung.png", "filename": "trend_oliveyoung"},
    "kakao":      {"channel_label": "카카오",   "logo_path": "./images/kakao.png",      "filename": "trend_kakao"},
    "daiso":      {"channel_label": "다이소",   "logo_path": "./images/daiso.png",      "filename": "trend_daiso"},
}


# ──────────────────────────────────────────────
# 경로 유틸
# ──────────────────────────────────────────────

def abs_to_rel(abs_path: str, from_dir: str) -> str:
    return os.path.relpath(abs_path, start=from_dir).replace("\\", "/")


def resolve_asset(relative_to_base: str, from_dir: str) -> str:
    abs_path = os.path.abspath(os.path.join(BASE_DIR, relative_to_base))
    return abs_to_rel(abs_path, from_dir)


# ──────────────────────────────────────────────
# 차트 생성
# ──────────────────────────────────────────────

def make_rank_chart(
    dates: list[str],
    ranks: list[int],
    channel_key: str,
    brand: str,
) -> str:
    """주간 순위 추이 라인 차트를 base64 PNG 문자열로 반환."""
    color = CHANNEL_COLORS.get(channel_key, "#333333")

    # 날짜 레이블: YYYYMMDD -> MM/DD
    labels = [f"{d[4:6]}/{d[6:8]}" for d in dates]

    fig, ax = plt.subplots(figsize=(10.8, 6.5), facecolor="#ffffff")
    ax.set_facecolor("#fafafa")

    # 라인 + 마커
    ax.plot(
        labels, ranks,
        color=color,
        linewidth=4,
        marker="o",
        markersize=14,
        markerfacecolor=color,
        markeredgecolor="#ffffff",
        markeredgewidth=2,
        zorder=3,
    )

    # 각 포인트에 순위 레이블
    for i, (lbl, rank) in enumerate(zip(labels, ranks)):
        va = "bottom" if i % 2 == 0 else "top"
        offset = -0.6 if va == "top" else 0.6
        ax.annotate(
            f"{rank}위",
            xy=(lbl, rank),
            xytext=(0, 22 if va == "bottom" else -22),
            textcoords="offset points",
            ha="center",
            va=va,
            fontsize=18,
            fontweight="bold",
            color=color,
        )

    # Y축 반전 (1위가 위)
    max_rank = max(ranks) + 2
    ax.set_ylim(max_rank, 0)
    ax.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))
    ax.set_yticks(range(1, max_rank))
    ax.set_yticklabels([f"{i}위" for i in range(1, max_rank)], fontsize=14)

    # X축
    ax.set_xticks(labels)
    ax.set_xticklabels(labels, fontsize=16, fontweight="bold")

    # 그리드
    ax.grid(axis="y", linestyle="--", alpha=0.4, color="#cccccc", zorder=0)
    ax.set_axisbelow(True)

    # 테두리 정리
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(left=False, bottom=False)

    plt.tight_layout(pad=1.5)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=100, bbox_inches="tight", facecolor="#ffffff")
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")


# ──────────────────────────────────────────────
# HTML 빌더
# ──────────────────────────────────────────────

def build_trend_monthly_card_html(
    hero_row: pd.Series,
    daily_df: pd.DataFrame,
    channel_key: str,
    year_month_label: str,
    from_dir: str,
    instagram_account: str = "RANKING_NAM",
) -> str:
    cfg       = TREND_CHANNEL_CONFIG[channel_key]
    css_rel   = resolve_asset(PATHS["css"], from_dir)
    insta_rel = resolve_asset(PATHS["instagram_icon"], from_dir)
    logo_rel  = resolve_asset(cfg["logo_path"], from_dir)

    # 히어로 제품의 일별 순위 추출
    code = hero_row["code"]
    product_daily = (
        daily_df[daily_df["code"] == code]
        .sort_values("date")
        .reset_index(drop=True)
    )

    dates = product_daily["date"].astype(str).tolist()
    ranks = product_daily["rank"].astype(int).tolist()
    brand = str(hero_row.get("brand", "")).strip()

    chart_b64 = make_rank_chart(dates, ranks, channel_key, brand)

    # 통계 박스 데이터
    avg_rank    = hero_row.get("avg_rank", "-")
    best_rank   = hero_row.get("best_rank", "-")
    appearances = int(hero_row.get("appearances", 0))
    total_weeks = int(hero_row.get("total_weeks", 0))
    rank_change = hero_row.get("rank_change", 0)

    avg_rank_str  = f"{float(avg_rank):.1f}위" if avg_rank != "-" else "-"
    best_rank_str = f"{int(best_rank)}위"       if best_rank != "-" else "-"
    appear_str    = f"{appearances}/{total_weeks}주"

    # 순위 변화 표시
    if pd.isna(rank_change) or rank_change == 0:
        change_str = "-"
        change_cls = ""
    elif rank_change > 0:
        change_str = f"&#9650;{int(rank_change)}"
        change_cls = " highlight"
    else:
        change_str = f"&#9660;{abs(int(rank_change))}"
        change_cls = ""

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{cfg['channel_label']} 월간 순위 추이</title>
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
          <p class="title-main">순위</p>
          <p class="title-sub">추이</p>
        </div>
      </div>

      <div class="monthly-trend-body">

        <div class="trend-chart-wrap">
          <img src="data:image/png;base64,{chart_b64}" alt="순위 추이 차트" />
        </div>

        <div class="trend-stats-grid">
          <div class="trend-stat-box">
            <div class="trend-stat-label">평균 순위</div>
            <div class="trend-stat-value highlight">{avg_rank_str}</div>
          </div>
          <div class="trend-stat-box">
            <div class="trend-stat-label">최고 순위</div>
            <div class="trend-stat-value highlight">{best_rank_str}</div>
          </div>
          <div class="trend-stat-box">
            <div class="trend-stat-label">순위 변화</div>
            <div class="trend-stat-value{change_cls}">{change_str}</div>
          </div>
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

def save_trend_card(
    hero_row: pd.Series,
    daily_df: pd.DataFrame,
    channel_key: str,
    year_month_label: str,
    filepath: str,
    instagram_account: str = "RANKING_NAM",
) -> None:
    from_dir = os.path.dirname(os.path.abspath(filepath))
    os.makedirs(from_dir, exist_ok=True)

    html = build_trend_monthly_card_html(
        hero_row, daily_df, channel_key, year_month_label, from_dir, instagram_account
    )
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)
    logger.info(f"저장 완료: {filepath}")


def load_monthly_data(year_month: str) -> tuple[dict, dict]:
    """hero 행 dict, daily df dict 반환."""
    excel_path = os.path.abspath(
        os.path.join(BASE_DIR, PATHS["monthly_excel"].format(year_month=year_month))
    )
    if not os.path.exists(excel_path):
        raise FileNotFoundError(f"월간 파일 없음: {excel_path}")

    heroes = {}
    dailies = {}
    for channel in TREND_CHANNEL_CONFIG:
        try:
            heroes[channel]  = pd.read_excel(excel_path, sheet_name=f"{channel}_hero").iloc[0]
            dailies[channel] = pd.read_excel(excel_path, sheet_name=f"{channel}_daily")
        except Exception as e:
            logger.warning(f"[{channel}] 데이터 로드 실패: {e}")
    return heroes, dailies


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

    logger.info(f"[TREND MONTHLY] {year_month_label}")

    heroes, dailies = load_monthly_data(year_month)
    success, fail = 0, 0

    for channel_key, hero_row in heroes.items():
        if channel_key not in dailies:
            continue
        cfg      = TREND_CHANNEL_CONFIG[channel_key]
        filepath = os.path.join(output_dir, folder_name, f"{cfg['filename']}.html")
        try:
            save_trend_card(
                hero_row, dailies[channel_key],
                channel_key, year_month_label,
                filepath, instagram_account,
            )
            success += 1
        except Exception as e:
            logger.error(f"저장 실패 [{filepath}]: {e}")
            fail += 1

    logger.info(f"[TREND MONTHLY] 완료 - 성공 {success}개 / 실패 {fail}개")
    return {"success": success, "fail": fail}


if __name__ == "__main__":
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    parser = argparse.ArgumentParser(description="월간 순위 추이 카드 생성")
    parser.add_argument("--month",   default=None,           help="YYYY-MM (기본값: 이번 달)")
    parser.add_argument("--output",  default="../data/output", help="결과 저장 루트 디렉토리")
    parser.add_argument("--account", default="RANKING_NAM",  help="인스타그램 계정명")
    args = parser.parse_args()

    if args.month:
        y, m = map(int, args.month.split("-"))
    else:
        now = datetime.now()
        y, m = now.year, now.month

    output = os.path.abspath(os.path.join(BASE_DIR, args.output))
    run(year=y, month=m, output_dir=output, instagram_account=args.account)
