from pathlib import Path

BASE_DIR = Path("../data/raw")

CHANNEL_PATHS = {
    "naver":      BASE_DIR / "naver",
    "coupang":    BASE_DIR / "coupang",
    "oliveyoung": BASE_DIR / "oliveyoung",
    "kakao":      BASE_DIR / "kakao",
    "daiso":      BASE_DIR / "daiso",
}

RANKING_COMPARE_COLUMNS = {
    "naver":      ["price", "review", "rank", "star"],
    "coupang":    ["price", "review", "rank", "star"],
    "oliveyoung": ["price", "rank"],
    "kakao":      ["price", "rank", "like"],
    "daiso":      ["price", "review", "rank", "star"],
}
