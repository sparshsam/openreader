#!/usr/bin/env python3
"""Generate all app icon assets from a source PNG.

Usage:
  python tools/create_icon.py --source <path-to-source-png> [--ico assets/icon.ico]

Generates:
  - Windows .ico (16, 24, 32, 48, 64, 128, 256 px)
  - MSIX-branded PNGs (44x44, 71x71, 150x150, 310x150, 620x300)
  - macOS .iconset directory (for iconutil -> .icns)
"""

import argparse
import io
import struct
import sys
from pathlib import Path

from PIL import Image


def load_source(source: Path) -> Image.Image:
    """Load source PNG, ensure RGBA mode."""
    img = Image.open(source)
    return img.convert("RGBA")


def make_png_square(img: Image.Image, size: int) -> Image.Image:
    """Resize to a square, cropping centered if needed."""
    w, h = img.size
    if w != h:
        # Crop to center square first
        min_dim = min(w, h)
        left = (w - min_dim) // 2
        top = (h - min_dim) // 2
        img = img.crop((left, top, left + min_dim, top + min_dim))
    return img.resize((size, size), Image.LANCZOS)


def make_png_rect(img: Image.Image, width: int, height: int) -> Image.Image:
    """Resize to a rectangle, cropping centered if needed to match aspect ratio."""
    src_w, src_h = img.size
    target_ratio = width / height
    src_ratio = src_w / src_h

    if abs(src_ratio - target_ratio) > 0.01:
        # Crop source to target ratio
        if src_ratio > target_ratio:
            # Source is wider, crop sides
            new_w = int(src_h * target_ratio)
            left = (src_w - new_w) // 2
            img = img.crop((left, 0, left + new_w, src_h))
        else:
            # Source is taller, crop top/bottom
            new_h = int(src_w / target_ratio)
            top = (src_h - new_h) // 2
            img = img.crop((0, top, src_w, top + new_h))

    return img.resize((width, height), Image.LANCZOS)


def write_ico(img: Image.Image, path: Path, sizes=(16, 24, 32, 48, 64, 128, 256)):
    """Write a multi-resolution .ico file from source image."""
    path.parent.mkdir(parents=True, exist_ok=True)

    pngs = []
    for size in sizes:
        resized = make_png_square(img, size)
        buf = io.BytesIO()
        resized.save(buf, "PNG")
        pngs.append(buf.getvalue())

    header = struct.pack("<HHH", 0, 1, len(pngs))
    directory = bytearray()
    offset = 6 + 16 * len(pngs)

    for size, png_data in zip(sizes, pngs):
        width = 0 if size >= 256 else size
        height = 0 if size >= 256 else size
        directory.extend(
            struct.pack(
                "<BBBBHHII", width, height, 0, 0, 1, 32, len(png_data), offset
            )
        )
        offset += len(png_data)

    with path.open("wb") as f:
        f.write(header)
        f.write(directory)
        for png_data in pngs:
            f.write(png_data)

    print(f"    .ico -> {path} ({len(sizes)} sizes)")


def write_msix_assets(img: Image.Image, output_dir: Path):
    """Write MSIX brand images at the sizes the manifest declares."""
    manifest_sizes = [
        ("icon-44x44.png", 44, 44),
        ("icon-71x71.png", 71, 71),
        ("icon-150x150.png", 150, 150),
        ("icon-310x150.png", 310, 150),
        ("icon-620x300.png", 620, 300),
    ]

    output_dir.mkdir(parents=True, exist_ok=True)
    for name, w, h in manifest_sizes:
        path = output_dir / name
        if w == h:
            resized = make_png_square(img, w)
        else:
            resized = make_png_rect(img, w, h)
        resized.save(path, "PNG")
        print(f"    MSIX asset -> {path} ({w}x{h})")


def write_macos_iconset(img: Image.Image, output_dir: Path):
    """Write macOS .iconset directory (for iconutil -> .icns on macOS)."""
    icon_sizes = {
        "icon_16x16.png": 16,
        "icon_16x16@2x.png": 32,
        "icon_32x32.png": 32,
        "icon_32x32@2x.png": 64,
        "icon_128x128.png": 128,
        "icon_128x128@2x.png": 256,
        "icon_256x256.png": 256,
        "icon_256x256@2x.png": 512,
        "icon_512x512.png": 512,
        "icon_512x512@2x.png": 1024,
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    for name, size in icon_sizes.items():
        resized = make_png_square(img, size)
        path = output_dir / name
        resized.save(path, "PNG")
    print(f"    macOS iconset -> {output_dir}/ ({len(icon_sizes)} files)")


def main():
    parser = argparse.ArgumentParser(description="Create app icon assets from source PNG.")
    parser.add_argument("--source", required=True, help="Path to source PNG (1024x1024 recommended)")
    parser.add_argument("--ico", default="assets/branding/pdfreader_by_sparsh.ico", help="Output .ico path")
    parser.add_argument("--msix-dir", default="assets/branding", help="Output directory for MSIX PNGs")
    parser.add_argument("--macos-iconset", default="assets/branding/AppIcon.iconset", help="Output macOS .iconset dir")
    args = parser.parse_args()

    source_path = Path(args.source)
    if not source_path.exists():
        print(f"ERROR: Source not found: {source_path}")
        sys.exit(1)

    print(f"Loading source: {source_path}")
    img = load_source(source_path)
    print(f"  Source size: {img.size}")

    root = Path(__file__).resolve().parents[1]

    # 1. Windows .ico
    ico_path = root / args.ico
    print(f"\nGenerating Windows .ico...")
    write_ico(img, ico_path)

    # 2. MSIX brand PNGs
    msix_dir = root / args.msix_dir
    print(f"\nGenerating MSIX brand assets...")
    write_msix_assets(img, msix_dir)

    # 3. macOS iconset
    iconset_dir = root / args.macos_iconset
    print(f"\nGenerating macOS iconset...")
    write_macos_iconset(img, iconset_dir)

    print(f"\n✅ All icon assets generated from {source_path.name}")


if __name__ == "__main__":
    main()
