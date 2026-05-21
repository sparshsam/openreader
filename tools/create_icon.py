from pathlib import Path
import argparse
import struct
import sys

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QImage, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QApplication


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
ICON_PATH = ASSETS / "pdfreader_by_sparsh.ico"


def make_png(size: int) -> bytes:
    image = QImage(size, size, QImage.Format_ARGB32)
    image.fill(Qt.transparent)

    painter = QPainter(image)
    painter.setRenderHint(QPainter.Antialiasing)

    scale = size / 256

    shadow = QPainterPath()
    shadow.addRoundedRect(QRectF(42 * scale, 24 * scale, 158 * scale, 210 * scale), 22 * scale, 22 * scale)
    painter.fillPath(shadow.translated(7 * scale, 8 * scale), QColor(0, 0, 0, 44))

    page = QPainterPath()
    page.addRoundedRect(QRectF(38 * scale, 20 * scale, 162 * scale, 214 * scale), 22 * scale, 22 * scale)
    painter.fillPath(page, QColor("#f8fafc"))
    painter.setPen(QPen(QColor("#cbd5e1"), max(1, int(3 * scale))))
    painter.drawPath(page)

    fold = QPainterPath()
    fold.moveTo(158 * scale, 20 * scale)
    fold.lineTo(200 * scale, 62 * scale)
    fold.lineTo(166 * scale, 72 * scale)
    fold.quadTo(158 * scale, 72 * scale, 158 * scale, 64 * scale)
    fold.closeSubpath()
    painter.fillPath(fold, QColor("#e2e8f0"))

    accent = QLinearGradient(QPointF(54 * scale, 142 * scale), QPointF(184 * scale, 214 * scale))
    accent.setColorAt(0, QColor("#ef4444"))
    accent.setColorAt(1, QColor("#b91c1c"))
    painter.setBrush(accent)
    painter.setPen(Qt.NoPen)
    painter.drawRoundedRect(QRectF(54 * scale, 142 * scale, 132 * scale, 58 * scale), 16 * scale, 16 * scale)

    painter.setPen(QPen(QColor("#94a3b8"), max(1, int(7 * scale)), Qt.SolidLine, Qt.RoundCap))
    for y in (82, 104, 126):
        painter.drawLine(QPointF(62 * scale, y * scale), QPointF(156 * scale, y * scale))

    font = QFont("Segoe UI", max(10, int(44 * scale)), QFont.Bold)
    painter.setFont(font)
    painter.setPen(QColor("white"))
    painter.drawText(QRectF(54 * scale, 137 * scale, 132 * scale, 66 * scale), Qt.AlignCenter, "S")

    small_font = QFont("Segoe UI", max(7, int(22 * scale)), QFont.Bold)
    painter.setFont(small_font)
    painter.setPen(QColor("#991b1b"))
    painter.drawText(QRectF(58 * scale, 204 * scale, 118 * scale, 24 * scale), Qt.AlignCenter, "PDF")

    painter.end()

    data = QByteArray()
    buffer = QBuffer(data)
    buffer.open(QIODevice.WriteOnly)
    image.save(buffer, "PNG")
    return bytes(data)


def write_ico(path: Path, sizes=(16, 24, 32, 48, 64, 128, 256)):
    pngs = [(size, make_png(size)) for size in sizes]
    header = struct.pack("<HHH", 0, 1, len(pngs))
    directory = bytearray()
    offset = 6 + 16 * len(pngs)

    for size, png in pngs:
        width = 0 if size == 256 else size
        height = 0 if size == 256 else size
        directory.extend(struct.pack("<BBBBHHII", width, height, 0, 0, 1, 32, len(png), offset))
        offset += len(png)

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as file:
        file.write(header)
        file.write(directory)
        for _, png in pngs:
            file.write(png)


def write_png_iconset(path: Path):
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
    path.mkdir(parents=True, exist_ok=True)
    for file_name, size in icon_sizes.items():
        image = QImage()
        image.loadFromData(make_png(size), "PNG")
        image.save(str(path / file_name), "PNG")


if __name__ == "__main__":
    app = QApplication.instance() or QApplication(sys.argv)
    parser = argparse.ArgumentParser(description="Create app icon assets.")
    parser.add_argument("--ico", default=str(ICON_PATH), help="Path for the Windows .ico output.")
    parser.add_argument("--png-iconset", help="Optional macOS .iconset directory to create.")
    args = parser.parse_args()

    write_ico(Path(args.ico))
    print(args.ico)
    if args.png_iconset:
        write_png_iconset(Path(args.png_iconset))
        print(args.png_iconset)
