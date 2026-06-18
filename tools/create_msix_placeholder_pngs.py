"""Generate minimal placeholder PNGs for MSIX packaging.

Creates 1x1 pixel PNG files at specified sizes. These are real valid PNGs
that MakeAppx accepts. Replace with proper icon assets before production.
"""
import struct
import zlib
import sys
from pathlib import Path


def create_png(filepath: Path, width: int, height: int):
    """Create a minimal valid 1x1 pixel PNG."""
    # PNG signature
    signature = b'\x89PNG\r\n\x1a\n'

    # IHDR chunk: width, height, bit_depth=8, color_type=2(RGB)
    ihdr_data = struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0)
    ihdr_crc = zlib.crc32(b'IHDR' + ihdr_data) & 0xffffffff
    ihdr = struct.pack('>I', 13) + b'IHDR' + ihdr_data + struct.pack('>I', ihdr_crc)

    # IDAT chunk: minimal compressed pixel data (1 pixel red)
    raw_data = b'\x00' + b'\xff\x00\x00'  # filter byte + RGB red
    compressed = zlib.compress(raw_data)
    idat_crc = zlib.crc32(b'IDAT' + compressed) & 0xffffffff
    idat = struct.pack('>I', len(compressed)) + b'IDAT' + compressed + struct.pack('>I', idat_crc)

    # IEND chunk
    iend_crc = zlib.crc32(b'IEND') & 0xffffffff
    iend = struct.pack('>I', 0) + b'IEND' + struct.pack('>I', iend_crc)

    filepath.parent.mkdir(parents=True, exist_ok=True)
    filepath.write_bytes(signature + ihdr + idat + iend)


def main():
    sizes = [
        ("icon-44x44.png", 44, 44),
        ("icon-150x150.png", 150, 150),
        ("icon-71x71.png", 71, 71),
        ("icon-310x150.png", 310, 150),
        ("icon-620x300.png", 620, 300),
    ]

    output_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("assets")

    for name, w, h in sizes:
        path = output_dir / name
        if path.exists():
            print(f"SKIP  {path} (exists)")
        else:
            create_png(path, w, h)
            print(f"CREATED {path} ({w}x{h})")


if __name__ == "__main__":
    main()
