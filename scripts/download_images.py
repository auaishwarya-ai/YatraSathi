"""
Optional: download one photo per destination from Wikipedia into
yatrasathi/static/images/places/<slug>.jpg so the site shows real photos
even without internet later.

    python scripts/download_images.py

(Without this step the browser loads the photos from Wikipedia on the fly.)
Images are from Wikimedia Commons; check each file's licence before any
commercial use.
"""
import json
import sys
import time
from pathlib import Path
from urllib.parse import quote

import requests

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "yatrasathi" / "static" / "images" / "places"
HEADERS = {"User-Agent": "YatraSathi-student-project/1.0 (educational use)"}


def find_image(title, name):
    r = requests.get("https://en.wikipedia.org/api/rest_v1/page/summary/" + quote(title.replace(" ", "_")), headers=HEADERS, timeout=20)
    if r.ok:
        j = r.json()
        if j.get("originalimage") and j["originalimage"].get("width", 9999) <= 1600:
            return j["originalimage"]["source"]
        if j.get("thumbnail"):
            import re
            return re.sub(r"/\d+px-", "/960px-", j["thumbnail"]["source"])
    r = requests.get("https://en.wikipedia.org/w/api.php", headers=HEADERS, timeout=20, params={
        "action": "query", "format": "json", "generator": "search", "gsrsearch": name + " Karnataka", "gsrlimit": 1,
        "prop": "pageimages", "piprop": "thumbnail", "pithumbsize": 960})
    pages = (r.json().get("query") or {}).get("pages") or {}
    for p in pages.values():
        if p.get("thumbnail"):
            return p["thumbnail"]["source"]
    return None


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    places = []
    for f in sorted((ROOT / "data" / "destinations").glob("*.json")):
        places += json.loads(f.read_text(encoding="utf-8"))
    ok = 0
    for d in places:
        target = OUT / f"{d['slug']}.jpg"
        if target.exists():
            ok += 1
            continue
        try:
            url = find_image(d.get("wiki") or d["name"], d["name"])
            if not url:
                print("  no image:", d["name"])
                continue
            img = requests.get(url, headers=HEADERS, timeout=30)
            img.raise_for_status()
            target.write_bytes(img.content)
            ok += 1
            print("  saved:", target.name)
            time.sleep(0.3)
        except Exception as exc:
            print("  failed:", d["name"], exc)
    print(f"Done - {ok}/{len(places)} images available in {OUT}")


if __name__ == "__main__":
    sys.exit(main())
