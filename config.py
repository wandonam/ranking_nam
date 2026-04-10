"""
config.py
----------
프로젝트 공통 경로 상수
"""
from pathlib import Path

ROOT = Path(__file__).parent

DATA_DIR    = ROOT / "data"
RAW_DIR     = DATA_DIR / "raw"
REPORT_DIR  = DATA_DIR / "report"
OUTPUT_DIR  = DATA_DIR / "output"

CRAWLING_DIR = ROOT / "CRAWLING"
GENERATE_DIR = ROOT / "GENERATE"
DRIVER_DIR   = ROOT / "driver"
