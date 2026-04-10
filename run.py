"""
run.py
-------
전체 파이프라인 단일 실행 진입점

  1단계: 크롤링       (CRAWLING/main.py)
  2단계: 엑셀 리포트  (CRAWLING/report.py)
  3단계: 카드 생성    (GENERATE/main.py)

사용법:
    python run.py                        # 전체 실행
    python run.py --date 20250403        # 특정 날짜
    python run.py --skip-crawl           # 크롤링 건너뜀 (리포트+카드만)
    python run.py --skip-report          # 리포트 건너뜀
    python run.py --skip-generate        # 카드 생성 건너뜀
    python run.py --account my_account   # 인스타그램 계정명 지정
"""

import argparse
import logging
import subprocess
import sys
from datetime import datetime
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

ROOT         = Path(__file__).parent
CRAWLING_DIR = ROOT / "CRAWLING"
GENERATE_DIR = ROOT / "GENERATE"


def run_step(label: str, cmd: list[str], cwd: Path) -> bool:
    logger.info(f"▶ {label}")
    result = subprocess.run(cmd, cwd=cwd)
    if result.returncode != 0:
        logger.error(f"❌ {label} 실패 (exit code {result.returncode})")
        return False
    logger.info(f"✅ {label} 완료")
    return True


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="랭킹 카드 전체 파이프라인")
    parser.add_argument("--date",          default=None,           help="날짜 YYYYMMDD (기본값: 오늘)")
    parser.add_argument("--account",       default="RANKING_NAM",  help="인스타그램 계정명")
    parser.add_argument("--skip-crawl",    action="store_true",    help="크롤링 건너뜀")
    parser.add_argument("--skip-report",   action="store_true",    help="엑셀 리포트 건너뜀")
    parser.add_argument("--skip-generate", action="store_true",    help="카드 생성 건너뜀")
    return parser.parse_args()


def main() -> None:
    args  = parse_args()
    today = args.date or datetime.today().strftime("%Y%m%d")
    today1 = datetime.strptime(today, "%Y%m%d").strftime("%Y년 %m월 %d일")

    logger.info("=" * 55)
    logger.info(f"  RANKING_NAM 파이프라인 시작 — {today1}")
    logger.info("=" * 55)

    # ── 1단계: 크롤링
    if not args.skip_crawl:
        ok = run_step(
            "[1/3] 크롤링",
            [sys.executable, "main.py"],
            cwd=CRAWLING_DIR,
        )
        if not ok:
            sys.exit(1)
    else:
        logger.info("▷ [1/3] 크롤링 건너뜀 (--skip-crawl)")

    # ── 2단계: 엑셀 리포트
    if not args.skip_report:
        ok = run_step(
            "[2/3] 엑셀 리포트 생성",
            [sys.executable, "report.py"],
            cwd=CRAWLING_DIR,
        )
        if not ok:
            sys.exit(1)
    else:
        logger.info("▷ [2/3] 엑셀 리포트 건너뜀 (--skip-report)")

    # ── 3단계: 카드 생성
    if not args.skip_generate:
        cmd = [
            sys.executable, "main.py",
            "--date",    today,
            "--account", args.account,
        ]
        ok = run_step("[3/3] 카드 생성 (HTML → PNG)", cmd, cwd=GENERATE_DIR)
        if not ok:
            sys.exit(1)
    else:
        logger.info("▷ [3/3] 카드 생성 건너뜀 (--skip-generate)")

    logger.info("=" * 55)
    logger.info(f"  파이프라인 완료 ✅  결과물: data/output/{today}/")
    logger.info("=" * 55)


if __name__ == "__main__":
    main()
