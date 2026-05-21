#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required. Install Python 3.11 or newer from https://www.python.org/downloads/macos/."
  exit 1
fi

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi

.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt

ICON_ARGS=()
if [ ! -f "assets/pdfreader_by_sparsh.icns" ] && command -v iconutil >/dev/null 2>&1; then
  QT_QPA_PLATFORM=offscreen .venv/bin/python tools/create_icon.py --png-iconset assets/AppIcon.iconset
  iconutil -c icns assets/AppIcon.iconset -o assets/pdfreader_by_sparsh.icns
fi

if [ -f "assets/pdfreader_by_sparsh.icns" ]; then
  ICON_ARGS=(--icon "assets/pdfreader_by_sparsh.icns")
fi

.venv/bin/pyinstaller \
  --windowed \
  --onedir \
  --name "PDFReader by Sparsh" \
  --argv-emulation \
  "${ICON_ARGS[@]}" \
  main.py

echo "Built dist/PDFReader by Sparsh.app"
