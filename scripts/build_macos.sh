#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

# Version precedence:
#   1. Explicit override (BUILD_VERSION env)
#   2. Exact tag on HEAD (git describe --exact-match)
#   3. Authoritative source version already in main.py
# Never fall back to an older Git tag or 0.0.0-dev, which would silently
# regress the embedded application version.
VERSION="${BUILD_VERSION:-}"
if [ -z "$VERSION" ]; then
  TAG=$(git describe --tags --exact-match HEAD 2>/dev/null || true)
  if [ -n "$TAG" ]; then
    VERSION="${TAG#v}"
  fi
fi
if [ -n "$VERSION" ]; then
  python3 scripts/inject_version.py "$VERSION"
else
  VERSION=$(python3 scripts/inject_version.py --source-version)
  echo "Using source version: $VERSION (no build override or exact tag)"
fi

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
