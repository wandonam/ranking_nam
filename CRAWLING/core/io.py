from datetime import datetime
from pathlib import Path
import pandas as pd

def get_today():
    return datetime.now().strftime("%Y%m%d")

def ensure_dir(path: Path):
    path.mkdir(parents=True, exist_ok=True)
    return path

def save_csv(data: list, csv_path: Path):
    df = pd.DataFrame(data)
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    return df