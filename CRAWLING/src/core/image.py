# image.py
import os
import sys
import requests
from urllib.parse import urljoin
from pathlib import Path

def save_images(sources, save_dir: Path, current_url=None, limit=120):
    save_dir.mkdir(parents=True, exist_ok=True)
    targets = sources if limit is None else sources[:limit]
    total = len(targets)

    if total == 0:
        print("저장할 이미지가 없습니다.")
        return

    success, fail = 0, 0

    for idx, source in enumerate(targets, start=1):
        if isinstance(source, str):
            img_url = source
        else:
            img_url = source.get("src") or source.get("data-src")
            if not img_url:
                fail += 1
                continue
            if current_url:
                img_url = urljoin(current_url, img_url)

        if not img_url or not img_url.strip():
            fail += 1
            continue

        ext = os.path.splitext(img_url.split("?")[0])[1].lower()
        if ext not in [".jpg", ".jpeg", ".png", ".webp"]:
            ext = ".jpg"

        file_path = save_dir / f"{idx:02d}{ext}"

        try:
            response = requests.get(img_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
            response.raise_for_status()
            with open(file_path, "wb") as f:
                f.write(response.content)
            success += 1
        except Exception:
            fail += 1

        bar_len = 30
        filled = int(bar_len * idx / total)
        bar = "█" * filled + "░" * (bar_len - filled)
        pct = idx / total * 100
        sys.stdout.write(f"\r[이미지 저장]] [{bar}] {pct:5.1f}% ({idx}/{total})")
        sys.stdout.flush()