"""
monthly/aggregate.py
---------------------
월간 데이터 집계 모듈

주간 단위로 수집된 CSV 파일들을 해당 월 기준으로 집계해
data/report/YYYY_MM_monthly.xlsx 를 생성합니다.

시트 구성:
  {channel}_daily  : 주간 스냅샷 전체 원본
  {channel}_stats  : 제품별 월간 통계 (avg_rank, best_rank, 리뷰 증가 등)

단독 실행:
    python aggregate.py
    python aggregate.py --month 2026-04
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).parent.parent
RAW_DIR     = ROOT / "data" / "raw"
MONTHLY_DIR = ROOT / "data" / "monthly"

# 채널별 보유 필드 정의
CHANNEL_META = {
    "naver":      {"has_review": True,  "has_star": True,  "has_like": False},
    "coupang":    {"has_review": True,  "has_star": True,  "has_like": False},
    "oliveyoung": {"has_review": False, "has_star": False, "has_like": False},
    "kakao":      {"has_review": False, "has_star": False, "has_like": True},
    "daiso":      {"has_review": True,  "has_star": True,  "has_like": False},
}


# ──────────────────────────────────────────────
# 로딩
# ──────────────────────────────────────────────

def load_month_csvs(channel: str, year: int, month: int) -> pd.DataFrame:
    """해당 월에 속하는 모든 CSV를 로드해 합친다.

    신규 파일: period_ym 컬럼(YYYYMM)으로 필터링.
    구파일(period_ym 없음): 파일명 prefix(YYYYMMDD) 방식으로 fallback.
    """
    channel_dir = RAW_DIR / channel
    target_ym = f"{year}{month:02d}"

    all_csv = sorted(channel_dir.glob("*.csv"))
    if not all_csv:
        raise FileNotFoundError(f"[{channel}] CSV 파일 없음: {channel_dir}")

    new_frames, old_frames = [], []
    for f in all_csv:
        try:
            df_tmp = pd.read_csv(f)
        except Exception:
            continue

        if "period_ym" in df_tmp.columns:
            filtered = df_tmp[df_tmp["period_ym"].astype(str) == target_ym]
            if not filtered.empty:
                new_frames.append(filtered)
        elif f.stem.startswith(target_ym):
            old_frames.append(df_tmp)

    frames = new_frames if new_frames else old_frames
    if not frames:
        raise FileNotFoundError(
            f"[{channel}] {target_ym} 해당 데이터 없음: {channel_dir}"
        )

    df = pd.concat(frames, ignore_index=True)
    df["date"] = df["date"].astype(str)
    return df


# ──────────────────────────────────────────────
# 통계 계산
# ──────────────────────────────────────────────

def compute_stats(daily_df: pd.DataFrame, channel: str) -> pd.DataFrame:
    """주간 스냅샷으로부터 제품별 월간 통계를 계산한다."""
    cfg = CHANNEL_META[channel]
    dates = sorted(daily_df["date"].unique())
    total_weeks = len(dates)

    rows = []
    for code, grp in daily_df.groupby("code"):
        g = grp.sort_values("date").reset_index(drop=True)

        row: dict = {
            "code":        code,
            "brand":       g["brand"].iloc[-1],
            "product":     g["product"].iloc[-1],
            "price":       g["price"].iloc[-1],
            "appearances": len(g),
            "total_weeks": total_weeks,
            "avg_rank":    round(g["rank"].mean(), 2),
            "best_rank":   int(g["rank"].min()),
            "first_rank":  int(g["rank"].iloc[0]),
            "last_rank":   int(g["rank"].iloc[-1]),
            "first_date":  g["date"].iloc[0],
            "last_date":   g["date"].iloc[-1],
        }
        # 순위 변화: 양수 = 순위 올라감 (숫자 작아짐)
        row["rank_change"] = row["first_rank"] - row["last_rank"]

        if cfg["has_review"] and "review" in g.columns:
            first_rev = _safe_int(g["review"].iloc[0])
            last_rev  = _safe_int(g["review"].iloc[-1])
            row["first_review"]       = first_rev
            row["last_review"]        = last_rev
            row["review_growth"]      = last_rev - first_rev
            row["review_growth_pct"]  = (
                round((last_rev - first_rev) / first_rev * 100, 2)
                if first_rev and first_rev > 0 else 0.0
            )

        if cfg["has_star"] and "star" in g.columns:
            row["avg_star"] = round(g["star"].mean(), 2)

        if cfg["has_like"] and "like" in g.columns:
            first_like = _safe_int(g["like"].iloc[0])
            last_like  = _safe_int(g["like"].iloc[-1])
            row["first_like"]       = first_like
            row["last_like"]        = last_like
            row["like_growth"]      = last_like - first_like
            row["like_growth_pct"]  = (
                round((last_like - first_like) / first_like * 100, 2)
                if first_like and first_like > 0 else 0.0
            )

        rows.append(row)

    stats_df = pd.DataFrame(rows).sort_values("avg_rank").reset_index(drop=True)
    return stats_df


def _safe_int(val) -> int:
    try:
        return int(str(val).replace(",", "").strip())
    except (ValueError, TypeError):
        return 0


# ──────────────────────────────────────────────
# 메인
# ──────────────────────────────────────────────

def run(year: int, month: int) -> Path:
    """월간 집계 실행 → Excel 저장 경로 반환."""
    MONTHLY_DIR.mkdir(parents=True, exist_ok=True)
    output_path = MONTHLY_DIR / f"{year}_{month:02d}_monthly.xlsx"

    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        for channel in CHANNEL_META:
            try:
                daily_df = load_month_csvs(channel, year, month)
                stats_df = compute_stats(daily_df, channel)

                daily_df.to_excel(writer, sheet_name=f"{channel}_daily", index=False)
                stats_df.to_excel(writer, sheet_name=f"{channel}_stats", index=False)

                print(f"  [{channel}] 완료 - {len(stats_df)}개 제품, {daily_df['date'].nunique()}주")
            except FileNotFoundError as e:
                print(f"  [{channel}] 건너뜀: {e}")

    print(f"\n저장 완료: {output_path}")
    return output_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="월간 랭킹 집계")
    parser.add_argument("--month", default=None, help="YYYY-MM (기본값: 이번 달)")
    args = parser.parse_args()

    if args.month:
        y, m = map(int, args.month.split("-"))
    else:
        now = datetime.now()
        m = now.month - 1 or 12
        y = now.year if now.month > 1 else now.year - 1

    run(y, m)
