#!/usr/bin/env bash
# Build macOS App Bundle for PDFReader by Sparsh
# ===============================================
#
# Usage:
#   chmod +x scripts/build_macos.sh
#   ./scripts/build_macos.sh
#
# What it does:
#   1. Detects the latest git tag and injects it as the app version.
#   2. Creates or reuses a Python virtual environment.
#   3. Installs dependencies from requirements.txt.
#   4. Generates the .icns app icon (if missing).
#   5. Builds a PyInstaller --onedir --windowed .app bundle.
#
# Output:
#   dist/PDFReader by Sparsh.app/
#
# To build the DMG installer after this script:
#   ./scripts/create_dmg.sh
#
# See release.yml for the CI-based full build.
# ===============================================

set -euo pipefail

cd "$(dirname "$0")/.."

# ── 1. Detect and inject version ─────────────────────────────────────

VERSION="$(git describe --tags --abbrev=0 2>/dev/null || echo "0.0.0-dev")"
VERSION="${VERSION#v}"
python3 scripts/inject_version.py "$VERSION"
echo "=== Injected version: $VERSION ==="

# ── 2. Check Python ──────────────────────────────────────────────────

if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: python3 is required. Install Python 3.11+ from:"
  echo "  https://www.python.org/downloads/macos/"
  exit 1
fi

# ── 3. Virtual environment ───────────────────────────────────────────

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
  echo "Created .venv"
fi

.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt

# ── 4. Generate app icon ─────────────────────────────────────────────

if [ ! -f "assets/pdfreader_by_sparsh.icns" ] && command -v iconutil >/dev/null 2>&1; then
  QT_QPA_PLATFORM=offscreen .venv/bin/python tools/create_icon.py --png-iconset assets/AppIcon.iconset
  iconutil -c icns assets/AppIcon.iconset -o assets/pdfreader_by_sparsh.icns
  echo "Generated assets/pdfreader_by_sparsh.icns"
fi

ICON_ARGS=()
if [ -f "assets/pdfreader_by_sparsh.icns" ]; then
  ICON_ARGS=(--icon "assets/pdfreader_by_sparsh.icns")
fi

# ── 5. Clean previous build artifacts ────────────────────────────────

rm -rf "dist/PDFReader by Sparsh.app" "build/pyinstaller"

# ── 6. Build PyInstaller bundle ──────────────────────────────────────

.venv/bin/pyinstaller \
  --windowed \
  --onedir \
  --clean \
  --noupx \
  --name "PDFReader by Sparsh" \
  --argv-emulation \
  --workpath "build/pyinstaller" \
  "${ICON_ARGS[@]}" \
  main.py

echo "=== Build complete ==="
echo "App bundle: $(pwd)/dist/PDFReader by Sparsh.app"
echo "Version injected: $VERSION"

# ── 7. Optional: Build DMG ───────────────────────────────────────────
#
# If you have create-dmg installed, run:
#   ./scripts/create_dmg.sh "$VERSION"
#
# This is also done automatically in CI (release.yml).
