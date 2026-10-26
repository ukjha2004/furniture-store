
"""Give every product its own photo without renaming 200 files by hand.

Usage (from the project root):
  1. python -m pip install pillow      (one time)
  2. python tools/assign_photos.py     (first run creates the photo-inbox folders)
  3. Download photos into photo-inbox/<category>/, e.g. 20 sofa photos into photo-inbox/sofas/
  4. python tools/assign_photos.py     (again: shrinks, renames and saves them)
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.seed import CATEGORIES, generate_products  # noqa: E402

INBOX = ROOT / "photo-inbox"
OUTPUT = ROOT / "frontend" / "public" / "images" / "products"
MAX_WIDTH = 800
IMAGE_TYPES = {".jpg", ".jpeg", ".png", ".webp"}


def slug(category):
    return category.lower().replace(" ", "-")  # "Dining Tables" -> "dining-tables"


def product_ids_by_category():
    """Product ids are 1, 2, 3... in the order seed.py generates them (same as the database)."""
    ids = {category: [] for category in CATEGORIES}
    for product_id, product in enumerate(generate_products(), start=1):
        ids[product["category"]].append(product_id)
    return ids


def save_as_jpg(source, destination):
    from PIL import Image

    with Image.open(source) as image:
        image = image.convert("RGB")  # PNG/WebP may have transparency; JPG doesn't
        if image.width > MAX_WIDTH:
            image = image.resize((MAX_WIDTH, round(image.height * MAX_WIDTH / image.width)))
        image.save(destination, "JPEG", quality=82, optimize=True)


def main():
    try:
        import PIL  # noqa: F401
    except ImportError:
        sys.exit("Pillow is not installed. Run:  python -m pip install pillow")

    OUTPUT.mkdir(parents=True, exist_ok=True)
    for category in CATEGORIES:
        (INBOX / slug(category)).mkdir(parents=True, exist_ok=True)

    missing = []
    for category, ids in product_ids_by_category().items():
        folder = INBOX / slug(category)
        photos = sorted(p for p in folder.iterdir() if p.suffix.lower() in IMAGE_TYPES)
        if len(photos) > len(ids):
            print(f"  note: {folder.name} has {len(photos)} photos; only the first {len(ids)} are used")

        done = 0
        for product_id, photo in zip(ids, photos):
            try:
                save_as_jpg(photo, OUTPUT / f"{product_id}.jpg")
                done += 1
            except Exception as err:  # a broken file shouldn't stop the rest
                print(f"  skipped {photo.name}: {err}")
        print(f"{category:<14} {done:>2}/{len(ids)} photos")
        missing += [i for i in ids if not (OUTPUT / f"{i}.jpg").exists()]

    total = sum(len(v) for v in product_ids_by_category().values())
    print(f"\n{total - len(missing)}/{total} products have their own photo.")
    if missing:
        print(f"Still missing: {len(missing)}. Add more photos to {INBOX.name}/ and run again.")
    print(f"Photos saved in {OUTPUT.relative_to(ROOT)}. Commit and push them to publish.")


if __name__ == "__main__":
    main()