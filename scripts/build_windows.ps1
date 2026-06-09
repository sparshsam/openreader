# Build Windows Executable for PDFReader by Sparsh
# ==================================================
#
# Usage:
#   .\scripts\build_windows.ps1
#
# What it does:
#   1. Detects the latest git tag and injects it as the app version.
#   2. Creates or reuses a Python virtual environment.
#   3. Installs dependencies from requirements.txt.
#   4. Builds a PyInstaller --onedir bundle.
#
# Output:
#   dist\PDFReader by Sparsh\
#   ├── PDFReader by Sparsh.exe
#   └── _internal\  (Python runtime + dependencies)
#
# To build the Inno Setup installer after this script:
#   iscc installer/setup.iss
#
# See release.yml for the CI-based full build (PyInstaller + ISCC).
# ==================================================

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location -Path $RepoRoot

# ── 1. Detect and inject version ─────────────────────────────────────

$version = "0.0.0-dev"
$tag = git describe --tags --abbrev=0 2>$null
if ($tag) {
    $version = $tag -replace '^v', ''
    if ($version -notmatch '^\d+\.\d+\.\d+') {
        Write-Warning "Tag '$tag' does not look like a semver tag. Falling back to dev version."
        $version = "0.0.0-dev"
    }
}
python scripts/inject_version.py $version
Write-Host "=== Injected version: $version ==="

# ── 2. Virtual environment ───────────────────────────────────────────

if (!(Test-Path -LiteralPath ".\.venv")) {
    python -m venv .venv
    Write-Host "Created .venv"
}

.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

# ── 3. Clean previous build artifacts ─────────────────────────────────

if (Test-Path "dist\PDFReader by Sparsh") {
    Remove-Item -Recurse -Force "dist\PDFReader by Sparsh"
    Write-Host "Cleaned old dist\PDFReader by Sparsh"
}
if (Test-Path "build") {
    Remove-Item -Recurse -Force "build"
    Write-Host "Cleaned old build\"
}

# ── 4. Build PyInstaller bundle ──────────────────────────────────────

.\.venv\Scripts\pyinstaller.exe `
    --noconsole `
    --onedir `
    --clean `
    --noupx `
    --name "PDFReader by Sparsh" `
    --icon ".\assets\pdfreader_by_sparsh.ico" `
    --workpath "build\pyinstaller" `
    main.py

if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller build failed with exit code $LASTEXITCODE"
}

Write-Host "=== Build complete ==="
Write-Host "Executable: $RepoRoot\dist\PDFReader by Sparsh\PDFReader by Sparsh.exe"
Write-Host "Version injected: $version"

# ── 5. Optional: Build Inno Setup installer ──────────────────────────
#
# If ISCC.exe is available, build the setup.exe.
# Install Inno Setup from: https://jrsoftware.org/isdl.php

$iscc = (Get-Command "iscc.exe" -ErrorAction SilentlyContinue).Source
if (-not $iscc) {
    $paths = @(
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "${env:ProgramFiles}\Inno Setup 6\ISCC.exe",
        "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe"
    )
    foreach ($p in $paths) { if (Test-Path $p) { $iscc = $p; break } }
}

if ($iscc) {
    Write-Host "=== Building Inno Setup installer ==="
    $srcDir = (Get-Item "dist\PDFReader by Sparsh").FullName
    & $iscc /Q "/DAppVersion=$version" "/DAppSourceDir=$srcDir" installer/setup.iss
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "ISCC exited with code $LASTEXITCODE — installer not built"
    } else {
        $expected = "dist\installer\PDFReader-by-Sparsh-$version-Setup.exe"
        if (Test-Path $expected) {
            Write-Host "=== Installer built: $expected ==="
        } else {
            Write-Warning "Installer not found at expected path: $expected"
        }
    }
} else {
    Write-Host "=== ISCC.exe not found — installer skipped ==="
    Write-Host "Install Inno Setup and re-run, or build manually:"
    Write-Host "  iscc installer/setup.iss"
}

Write-Host "=== Done ==="
