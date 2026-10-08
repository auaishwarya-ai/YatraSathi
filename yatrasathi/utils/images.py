"""Resolve the best image for a destination: downloaded local file > admin URL > (browser fetches Wikipedia photo)."""
from pathlib import Path

PLACES_DIR = Path(__file__).resolve().parent.parent / "static" / "images" / "places"


def place_image_url(slug, image_url=""):
    for ext in ("jpg", "jpeg", "png", "webp"):
        if (PLACES_DIR / f"{slug}.{ext}").exists():
            return f"/static/images/places/{slug}.{ext}"
    return image_url or ""


def with_images(cards):
    for c in cards or []:
        c["image_url"] = place_image_url(c["slug"], c.get("image_url", ""))
    return cards
