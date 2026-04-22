"""
run_monthly.py
---------------
월간 히어로 제품 파이프라인 진입점

  1단계: 월간 집계          (monthly/aggregate.py)
  2단계: 히어로 선발        (monthly/hero.py)
  3단계: 히어로 상세 파일   (monthly/export.py)
  4단계: 리뷰 크롤링        (monthly/crawl_reviews.py)
  5단계: 카드 HTML          (generate/generate_html_hero.py, generate_html_trend_monthly.py)
  6단계: PNG 변환           (generate/html2png.py)

사용법:
    python run_monthly.py                       # 이번 달 전체 실행
    python run_monthly.py --month 2026-04       # 특정 월
    python run_monthly.py --skip-aggregate      # 집계 건너뜀 (Excel 이미 있을 때)
    python run_monthly.py --skip-hero           # 히어로 선발 건너뜀
    python run_monthly.py --skip-cards          # 카드 생성 건너뜀
    python run_monthly.py --skip-png            # PNG 변환 건너뜀
    python run_monthly.py --skip-reviews        # 리뷰 크롤링 건너뜀
    python run_monthly.py --account my_account  # 인스타그램 계정명 지정
"""

import argparse
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

ROOT         = Path(__file__).parent
MONTHLY_DIR  = ROOT / "monthly"
GENERATE_DIR = ROOT / "generate"
OUTPUT_DIR   = ROOT / "data" / "output"
LOG_FILE     = ROOT / "run_monthly.txt"

# ──────────────────────────────────────────────
# 로깅 설정
# ──────────────────────────────────────────────
_fmt     = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
_console = logging.StreamHandler()
_console.setFormatter(_fmt)
_file    = logging.FileHandler(LOG_FILE, encoding="utf-8")
_file.setFormatter(_fmt)
logging.basicConfig(level=logging.INFO, handlers=[_console, _file])
logger = logging.getLogger(__name__)

# ── 모듈 경로 등록
sys.path.insert(0, str(MONTHLY_DIR))
sys.path.insert(0, str(GENERATE_DIR))

import aggregate
import hero
import export
import crawl_reviews


# ──────────────────────────────────────────────
# 인자 파싱
# ──────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="월간 히어로 제품 파이프라인")
    parser.add_argument("--month",          default=None,          help="YYYY-MM (기본값: 이번 달)")
    parser.add_argument("--account",        default="RANKING_NAM", help="인스타그램 계정명")
    parser.add_argument("--skip-aggregate", action="store_true",   help="월간 집계 건너뜀")
    parser.add_argument("--skip-hero",      action="store_true",   help="히어로 선발 건너뜀")
    parser.add_argument("--skip-export",    action="store_true",   help="히어로 상세 파일 생성 건너뜀")
    parser.add_argument("--skip-cards",     action="store_true",   help="카드 HTML 생성 건너뜀")
    parser.add_argument("--skip-png",       action="store_true",   help="PNG 변환 건너뜀")
    parser.add_argument("--skip-reviews",   action="store_true",   help="리뷰 크롤링 건너뜀")
    return parser.parse_args()


# ──────────────────────────────────────────────
# 메인
# ──────────────────────────────────────────────

def main() -> None:
    args = parse_args()

    if args.month:
        year, month = map(int, args.month.split("-"))
    else:
        now   = datetime.now()
        year, month = now.year, now.month

    year_month       = f"{year}_{month:02d}"
    year_month_label = f"{year}년 {month:02d}월"
    output_dir       = str(OUTPUT_DIR)
    monthly_folder   = OUTPUT_DIR / f"{year_month}_monthly"

    logger.info("=" * 55)
    logger.info(f"  월간 히어로 파이프라인 시작 - {year_month_label}")
    logger.info("=" * 55)


    total_success, total_fail = 0, 0

    # ── 1단계: 월간 집계
    if not args.skip_aggregate:
        logger.info("[1/6] 월간 데이터 집계 시작")
        try:
            aggregate.run(year, month)
            logger.info("[1/6] 집계 완료")
        except Exception as e:
            logger.error(f"[1/6] 집계 실패: {e}")
            sys.exit(1)
    else:
        logger.info("[1/6] 집계 건너뜀 (--skip-aggregate)")

    # ── 2단계: 히어로 선발
    if not args.skip_hero:
        logger.info("[2/6] 히어로 제품 선발 시작")
        try:
            heroes = hero.run(year, month)
            logger.info(f"[2/6] 히어로 선발 완료 - {len(heroes)}개 채널")
        except Exception as e:
            logger.error(f"[2/6] 히어로 선발 실패: {e}")
            sys.exit(1)
    else:
        logger.info("[2/6] 히어로 선발 건너뜀 (--skip-hero)")

    # ── 3단계: 히어로 상세 파일 생성
    if not args.skip_export:
        logger.info("[3/6] 히어로 상세 파일 생성 시작")
        try:
            results = export.run(year, month)
            for ch, path in results.items():
                logger.info(f"  [{ch}] {path}")
            logger.info(f"[3/6] 상세 파일 생성 완료 - {len(results)}개 채널")
        except Exception as e:
            logger.error(f"[3/6] 상세 파일 생성 실패: {e}")
            sys.exit(1)
    else:
        logger.info("[3/6] 상세 파일 생성 건너뜀 (--skip-export)")

    # ── 4단계: 리뷰 크롤링
    if not args.skip_reviews:
        logger.info("[4/6] 히어로 제품 리뷰 크롤링 시작")
        try:
            crawl_reviews.run(year, month)
            logger.info("[4/6] 리뷰 크롤링 완료")
        except Exception as e:
            logger.error(f"[4/6] 리뷰 크롤링 실패: {e}")
    else:
        logger.info("[4/6] 리뷰 크롤링 건너뜀 (--skip-reviews)")

    # ── 5단계: 카드 HTML 생성
    if not args.skip_cards:
        import generate_html_hero
        import generate_html_trend_monthly
        logger.info("[5/6] 히어로 카드 HTML 생성 시작")
        try:
            r = generate_html_hero.run(
                year=year, month=month,
                output_dir=output_dir,
                instagram_account=args.account,
            )
            total_success += r["success"]
            total_fail    += r["fail"]
            logger.info(f"  히어로 카드: 성공 {r['success']}개 / 실패 {r['fail']}개")
        except Exception as e:
            logger.error(f"  히어로 카드 생성 실패: {e}")
            total_fail += 1

        logger.info("  순위 추이 카드 HTML 생성 시작")
        try:
            r = generate_html_trend_monthly.run(
                year=year, month=month,
                output_dir=output_dir,
                instagram_account=args.account,
            )
            total_success += r["success"]
            total_fail    += r["fail"]
            logger.info(f"  추이 카드: 성공 {r['success']}개 / 실패 {r['fail']}개")
        except Exception as e:
            logger.error(f"  추이 카드 생성 실패: {e}")
            total_fail += 1

        logger.info(f"[5/6] 카드 HTML 생성 완료")
    else:
        logger.info("[5/6] 카드 HTML 생성 건너뜀 (--skip-cards)")

    # ── 6단계: PNG 변환
    if not args.skip_png:
        import html2png
        logger.info("[6/6] PNG 변환 시작")
        try:
            r = html2png.run_folder(str(monthly_folder))
            total_success += r["success"]
            total_fail    += r["fail"]
            logger.info(f"[6/6] PNG 변환 완료")
        except Exception as e:
            logger.error(f"[6/6] PNG 변환 실패: {e}")
            total_fail += 1
    else:
        logger.info("[6/6] PNG 변환 건너뜀 (--skip-png)")

    # ── 최종 결과
    logger.info("=" * 55)
    logger.info(f"  파이프라인 완료 - 성공 {total_success}개 / 실패 {total_fail}개")
    logger.info(f"  결과물: data/output/{year_month}_monthly/")
    logger.info("=" * 55)

    if total_fail > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
