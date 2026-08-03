$ErrorActionPreference = "Stop"

Set-Location -Path (Split-Path -Parent $PSScriptRoot)

# Version precedence:
#   1. Explicit override (BUILD_VERSION env)
#   2. Exact tag on HEAD (git describe --exact-match)
#   3. Authoritative source version already in main.py
# Never fall back to an older Git tag or 0.0.0-dev, which would silently
# regress the embedded application version.
$version = $env:BUILD_VERSION
if (-not $version) {
    $tag = git describe --tags --exact-match HEAD 2>$null
    if ($tag) {
        $version = $tag -replace '^v', ''
    }
}

if ($version) {
    python scripts/inject_version.py $version
    Write-Host "Injected version: $version"
} else {
    $match = [regex]::Match(
        (Get-Content -LiteralPath "main.py" -Raw), '__version__ = "([^"]+)"'
    )
    if ($match.Success) {
        $version = $match.Groups[1].Value
    } else {
        $version = "0.0.0-dev"
    }
    Write-Host "Using source version: $version (no build override or exact tag)"
}

if (!(Test-Path -LiteralPath ".\.venv")) {
    python -m venv .venv
}

.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

.\.venv\Scripts\pyinstaller.exe `
    --noconsole `
    --onedir `
    --noupx `
    --name "OpenReader" `
    --icon ".\assets\branding\pdfreader_by_sparsh.ico" `
    main.py

Write-Host "Built dist\OpenReader.exe (version ${version})"
