from pathlib import Path

BASE_DIR = Path("../00_Database")

CHANNEL_PATHS = {
    "naver": BASE_DIR / "01_naver" / "01_healthyfood",
    "coupang": BASE_DIR / "02_coupang" / "01_healthyfood",
    "oliveyoung": BASE_DIR / "03_oliveyoung" / "01_healthyfood",
    "kakao": BASE_DIR / "04_kakao" / "01_healthyfood",
    "daiso": BASE_DIR / "05_daiso" / "01_healthyfood",
}

RANKING_COMPARE_COLUMNS = {
    "naver": ["price", "review", "rank", "star"],
    "coupang": ["price", "review", "rank", "star"],
    "oliveyoung": ["price", "rank"],
    "kakao": ["price", "rank", "like"],
    "daiso": ["price", "review", "rank", "star"],
}