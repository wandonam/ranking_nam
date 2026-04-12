"""
main.py
--------
랭킹 카드 생성 파이프라인 진입점
  1단계: generate_html  → Excel 읽어 HTML 카드 생성
  2단계: html2png       → HTML → PNG 변환 (1080×1350)

사용법:
    python main.py                        # 오늘 날짜, 전체 실행
    python main.py --date 20250403        # 특정 날짜
    python main.py --skip-png            # HTML 생성만
    python main.py --skip-html           # PNG 변환만 (HTML 이미 존재할 때)
    python main.py --account my_account  # 인스타그램 계정명 지정
"""

import argparse
import logging
import sys
from datetime import datetime

import generate_html
import generate_html_trend
import html2png

# ──────────────────────────────────────────────
# 로깅 설정 (main에서만 basicConfig 호출)
# ──────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

RESULT_DIR = "../data/output"


# ──────────────────────────────────────────────
# 인자 파싱
# ──────────────────────────────────────────────
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="랭킹 카드 생성 파이프라인")
    parser.add_argument(
        "--date",
        default=None,
        help="처리할 날짜 (YYYYMMDD). 기본값: 오늘",
    )
    parser.add_argument(
        "--output",
        default=RESULT_DIR,
        help=f"결과 저장 루트 디렉토리. 기본값: {RESULT_DIR}",
    )
    parser.add_argument(
        "--account",
        default="RANKING_NAM",
        help="카드에 표시할 인스타그램 계정명. 기본값: RANKING_NAM",
    )
    parser.add_argument(
        "--skip-html",
        action="store_true",
        help="HTML 생성 건너뜀 (이미 생성된 HTML이 있을 때)",
    )
    parser.add_argument(
        "--skip-png",
        action="store_true",
        help="PNG 변환 건너뜀",
    )
    return parser.parse_args()


# ──────────────────────────────────────────────
# 메인
# ──────────────────────────────────────────────
def main() -> None:
    args  = parse_args()
    today = args.date or datetime.today().strftime("%Y%m%d")
    today1 = datetime.strptime(today, "%Y%m%d").strftime("%Y년 %m월 %d일")

    logger.info("=" * 50)
    logger.info(f"  랭킹 카드 파이프라인 시작 — {today1}")
    logger.info("=" * 50)

    total_success, total_fail = 0, 0

    # ── 1단계: HTML 생성 (TOP10 + 트렌드)
    if not args.skip_html:
        logger.info("▶ [1/3] TOP10 HTML 카드 생성 시작")
        try:
            result = generate_html.run(
                today=today,
                output_dir=args.output,
                instagram_account=args.account,
            )
            total_success += result["success"]
            total_fail    += result["fail"]
        except FileNotFoundError as e:
            logger.error(f"TOP10 HTML 생성 중단: {e}")
            sys.exit(1)

        logger.info("▶ [2/3] 트렌드 HTML 카드 생성 시작 (급상승/급하락)")
        try:
            result = generate_html_trend.run(
                today=today,
                output_dir=args.output,
                instagram_account=args.account,
            )
            total_success += result["success"]
            total_fail    += result["fail"]
        except FileNotFoundError as e:
            logger.error(f"트렌드 HTML 생성 중단: {e}")
            sys.exit(1)
    else:
        logger.info("▶ [1/3] HTML 생성 건너뜀 (--skip-html)")
        logger.info("▶ [2/3] HTML 생성 건너뜀 (--skip-html)")

    # ── 3단계: PNG 변환
    if not args.skip_png:
        logger.info("▶ [3/3] PNG 변환 시작")
        result = html2png.run(
            today=today,
            input_dir=args.output,
        )
        total_success += result["success"]
        total_fail    += result["fail"]
    else:
        logger.info("▶ [3/3] PNG 변환 건너뜀 (--skip-png)")

    # ── 최종 결과
    logger.info("=" * 50)
    logger.info(f"  파이프라인 완료 ✅  성공 {total_success}개 / 실패 {total_fail}개")
    logger.info("=" * 50)

    if total_fail > 0:
        sys.exit(1)  # 실패 항목 있으면 exit code 1


if __name__ == "__main__":
    main()
