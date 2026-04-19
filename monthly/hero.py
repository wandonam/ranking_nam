"""
monthly/hero.py
----------------
히어로 제품 선발 모듈

4가지 기준으로 채널별 히어로 제품 1개를 선발합니다.

  순위 안정성  (30pt) : 수집 기간 중 TOP N 진입 비율
  최고 순위    (25pt) : 월 중 달성한 최고 순위
  순위 상승폭  (25pt) : 첫 주 대비 마지막 주 순위 변화
  참여도 성장  (20pt) : 리뷰/좋아요 증가율

채널 특성에 따라 가중치를 조정합니다.
  - OliveYoung : 리뷰/별점 없음 → 안정성+최고순위만 (50/50)
  - Kakao      : 리뷰 없고 좋아요만 있음 → 좋아요 증가율 사용

단독 실행:
    python hero.py
    python hero.py --month 2026-04
"""

import argparse
from datetime import datetime
from pathlib import Path

import pandas as pd

ROOT       = Path(__file__).parent.parent
REPORT_DIR = ROOT / "data" / "report"

# 채널별 가중치 (합계 = 100)
SCORE_WEIGHTS = {
    "naver":      {"stability": 30, "best_rank": 25, "rank_change": 25, "engagement": 20},
    "coupang":    {"stability": 30, "best_rank": 25, "rank_change": 25, "engagement": 20},
    "oliveyoung": {"stability": 50, "best_rank": 50, "rank_change": 0,  "engagement": 0},
    "kakao":      {"stability": 30, "best_rank": 25, "rank_change": 25, "engagement": 20},
    "daiso":      {"stability": 30, "best_rank": 25, "rank_change": 25, "engagement": 20},
}

# 최고 순위 → 원점수 매핑
BEST_RANK_RAW = {1: 25, 2: 22, 3: 18, 4: 14, 5: 11, 6: 9, 7: 7, 8: 5, 9: 3, 10: 2}

# 정규화 기준 상수
MAX_RANK_CHANGE   = 10   # 10칸 상승 = 100% 점수
MAX_ENGAGE_PCT    = 30.0 # 30% 증가 = 100% 점수


# ──────────────────────────────────────────────
# 개별 점수 계산
# ──────────────────────────────────────────────

def score_stability(appearances: int, total_weeks: int, weight: float) -> float:
    if total_weeks == 0:
        return 0.0
    return round((appearances / total_weeks) * weight, 3)


def score_best_rank(best_rank: int, weight: float) -> float:
    raw = BEST_RANK_RAW.get(int(best_rank), 1)
    return round((raw / 25) * weight, 3)


def score_rank_change(rank_change, weight: float) -> float:
    if pd.isna(rank_change) or rank_change <= 0:
        return 0.0
    return round(min(rank_change / MAX_RANK_CHANGE, 1.0) * weight, 3)


def score_engagement(growth_pct, weight: float) -> float:
    if pd.isna(growth_pct) or growth_pct <= 0:
        return 0.0
    return round(min(growth_pct / MAX_ENGAGE_PCT, 1.0) * weight, 3)


# ──────────────────────────────────────────────
# 채널 전체 제품 채점
# ──────────────────────────────────────────────

def compute_scores(stats_df: pd.DataFrame, channel: str) -> pd.DataFrame:
    """stats_df 각 행에 점수 컬럼을 추가해 반환."""
    w  = SCORE_WEIGHTS[channel]
    df = stats_df.copy()

    df["score_stability"]   = df.apply(
        lambda r: score_stability(r["appearances"], r["total_weeks"], w["stability"]), axis=1
    )
    df["score_best_rank"]   = df["best_rank"].apply(
        lambda x: score_best_rank(x, w["best_rank"])
    )
    df["score_rank_change"] = df["rank_change"].apply(
        lambda x: score_rank_change(x, w["rank_change"])
    )

    # 참여도 열 자동 선택 (리뷰 > 좋아요)
    if w["engagement"] > 0:
        if "review_growth_pct" in df.columns:
            engage_col = "review_growth_pct"
        elif "like_growth_pct" in df.columns:
            engage_col = "like_growth_pct"
        else:
            engage_col = None

        df["score_engagement"] = (
            df[engage_col].apply(lambda x: score_engagement(x, w["engagement"]))
            if engage_col else 0.0
        )
    else:
        df["score_engagement"] = 0.0

    df["total_score"] = (
        df["score_stability"]
        + df["score_best_rank"]
        + df["score_rank_change"]
        + df["score_engagement"]
    ).round(2)

    return df.sort_values("total_score", ascending=False).reset_index(drop=True)


# ──────────────────────────────────────────────
# 메인
# ──────────────────────────────────────────────

def run(year: int, month: int) -> dict:
    """채널별 히어로 선발 결과 반환. monthly.xlsx에 {channel}_hero 시트 추가."""
    monthly_path = REPORT_DIR / f"{year}_{month:02d}_monthly.xlsx"
    if not monthly_path.exists():
        raise FileNotFoundError(
            f"월간 집계 파일 없음: {monthly_path}\naggregate.py 를 먼저 실행하세요."
        )

    channels = list(SCORE_WEIGHTS.keys())
    heroes: dict = {}

    with pd.ExcelWriter(
        monthly_path, engine="openpyxl", mode="a", if_sheet_exists="replace"
    ) as writer:
        for channel in channels:
            try:
                stats_df = pd.read_excel(monthly_path, sheet_name=f"{channel}_stats")
            except Exception:
                print(f"  [{channel}] stats 시트 없음, 건너뜀")
                continue

            scored_df = compute_scores(stats_df, channel)
            hero      = scored_df.iloc[0]
            heroes[channel] = hero.to_dict()

            scored_df.to_excel(writer, sheet_name=f"{channel}_hero", index=False)

            print(
                f"  [{channel}] {hero['brand']} | "
                f"{str(hero['product'])[:25]}... | "
                f"점수: {hero['total_score']:.1f}"
            )

    return heroes


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="월간 히어로 제품 선발")
    parser.add_argument("--month", default=None, help="YYYY-MM (기본값: 이번 달)")
    args = parser.parse_args()

    if args.month:
        y, m = map(int, args.month.split("-"))
    else:
        now = datetime.now()
        y, m = now.year, now.month

    result = run(y, m)
    print(f"\n총 {len(result)}개 채널 히어로 선발 완료")
