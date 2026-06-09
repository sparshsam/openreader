#!/usr/bin/env bash
# Create a polished macOS DMG from a built .app bundle
# =====================================================
#
# Prerequisites:
#   brew install create-dmg
#
# Usage:
#   ./scripts/create_dmg.sh [version]
#
# If version is omitted, it's auto-detected from the latest git tag.
#
# Output:
#   dist/PDFReader-by-Sparsh-{version}-Apple-Silicon.dmg   (on arm64 Mac)
#   dist/PDFReader-by-Sparsh-{version}-Intel.dmg           (on Intel Mac)

set -euo pipefail

cd "$(dirname "$0")/.."

# ── Version ───────────────────────────────────────────────────────────

if [ $# -ge 1 ]; then
  VERSION="$1"
else
  VERSION="$(git describe --tags --abbrev=0 2>/dev/null || echo "0.0.0-dev")"
  VERSION="${VERSION#v}"
fi

# ── Detect architecture ───────────────────────────────────────────────

ARCH="$(uname -m)"
if [ "$ARCH" = "arm64" ]; then
  ARCH_LABEL="Apple-Silicon"
  DMG_NAME="PDFReader-by-Sparsh-${VERSION}-Apple-Silicon.dmg"
else
  ARCH_LABEL="Intel"
  DMG_NAME="PDFReader-by-Sparsh-${VERSION}-Intel.dmg"
fi

APP_BUNDLE="dist/PDFReader by Sparsh.app"
DMG_PATH="dist/$DMG_NAME"
STAGING_DIR="dist/dmg-staging"

# ── Validate app bundle ───────────────────────────────────────────────

if [ ! -d "$APP_BUNDLE" ]; then
  echo "ERROR: App bundle not found at $APP_BUNDLE"
  echo "Run scripts/build_macos.sh first."
  exit 1
fi

# ── Clean previous DMG ────────────────────────────────────────────────

rm -f "$DMG_PATH"
rm -rf "$STAGING_DIR"

# ── Check for create-dmg ──────────────────────────────────────────────

if ! command -v create-dmg >/dev/null 2>&1; then
  echo "WARNING: create-dmg not found. Installing via Homebrew..."
  if command -v brew >/dev/null 2>&1; then
    brew install create-dmg
  else
    echo "ERROR: Homebrew not available. Install create-dmg manually:"
    echo "  brew install create-dmg"
    echo ""
    echo "Falling back to basic DMG via hdiutil..."
    # Fallback: create a simple DMG with just the .app inside
    mkdir -p "$STAGING_DIR"
    cp -R "$APP_BUNDLE" "$STAGING_DIR/"
    hdiutil create -volname "PDFReader by Sparsh" \
      -srcfolder "$STAGING_DIR" \
      -ov -format UDZO \
      "$DMG_PATH"
    rm -rf "$STAGING_DIR"
    echo "=== Basic DMG created: $DMG_PATH ==="
    exit 0
  fi
fi

# ── Build polished DMG with create-dmg ────────────────────────────────
#
# create-dmg produces a window that shows:
#   - The app icon
#   - A symlink to /Applications
#   - Background (if provided)
#
# The user drags the app onto the Applications symlink to install.

# Optional background image
BACKGROUND=""
if [ -f "assets/dmg-background.png" ]; then
  BACKGROUND="--background assets/dmg-background.png"
fi

create-dmg \
  --volname "PDFReader by Sparsh ${VERSION}" \
  --volicon "assets/pdfreader_by_sparsh.icns" \
  $BACKGROUND \
  --window-pos 200 200 \
  --window-size 640 480 \
  --icon-size 128 \
  --icon "PDFReader by Sparsh.app" 160 200 \
  --hide-extension "PDFReader by Sparsh.app" \
  --app-drop-link 480 200 \
  "$DMG_PATH" \
  "$APP_BUNDLE"

echo "=== Polished DMG created: $DMG_PATH ($ARCH_LABEL) ==="
