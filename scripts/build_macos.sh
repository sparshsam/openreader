#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

# Inject version from latest git tag directly into main.py
VERSION=$(git describe --tags --abbrev=0 2>/dev/null || echo "0.0.0-dev")
VERSION="${VERSION#v}"
python3 scripts/inject_version.py "$VERSION"

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
  --noupx \
  --name "OpenReader" \
  --argv-emulation \
  "${ICON_ARGS[@]}" \
  main.py

echo "Built dist/OpenReader.app (version ${VERSION})"
