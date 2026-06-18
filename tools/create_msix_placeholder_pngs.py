"""Generate MSIX brand image assets from the project's source icon.

Creates MSIX-required PNGs at the sizes declared in AppxManifest.xml.
Uses the project's source icon for real brand images instead of placeholders.
"""

import sys
from pathlib import Path

from PIL import Image


def make_png_square(img: Image.Image, size: int) -> Image.Image:
    w, h = img.size
    if w != h:
        min_dim = min(w, h)
        left = (w - min_dim) // 2
        top = (h - min_dim) // 2
        img = img.crop((left, top, left + min_dim, top + min_dim))
    return img.resize((size, size), Image.LANCZOS)


def make_png_rect(img: Image.Image, width: int, height: int) -> Image.Image:
    src_w, src_h = img.size
    target_ratio = width / height
    src_ratio = src_w / src_h
    if abs(src_ratio - target_ratio) > 0.01:
        if src_ratio > target_ratio:
            new_w = int(src_h * target_ratio)
            left = (src_w - new_w) // 2
            img = img.crop((left, 0, left + new_w, src_h))
        else:
            new_h = int(src_w / target_ratio)
            top = (src_h - new_h) // 2
            img = img.crop((0, top, src_w, top + new_h))
    return img.resize((width, height), Image.LANCZOS)


def main():
    root = Path(__file__).resolve().parents[1]
    source_path = root / "assets" / "pdfreader_by_sparsh.ico"
    output_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else root / "assets"

    # Load from .ico or find source PNG
    if source_path.exists():
        img = Image.open(source_path)
        # .ico loads first frame; get full size
        img = img.convert("RGBA")
    else:
        # Fallback: try a source PNG
        png_path = root / "assets" / "icon-150x150.png"
        if png_path.exists():
            img = Image.open(png_path).convert("RGBA")
        else:
            print("ERROR: No source icon found. Run tools/create_icon.py first.")
            sys.exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)

    sizes = [
        ("icon-44x44.png", 44, 44),
        ("icon-150x150.png", 150, 150),
        ("icon-71x71.png", 71, 71),
        ("icon-310x150.png", 310, 150),
        ("icon-620x300.png", 620, 300),
    ]

    for name, w, h in sizes:
        path = output_dir / name
        if w == h:
            resized = make_png_square(img, w)
        else:
            resized = make_png_rect(img, w, h)
        resized.save(path, "PNG")
        print(f"GENERATED {path} ({w}x{h})")


if __name__ == "__main__":
    main()
