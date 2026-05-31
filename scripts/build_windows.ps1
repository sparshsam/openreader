$ErrorActionPreference = "Stop"

Set-Location -Path (Split-Path -Parent $PSScriptRoot)

# Inject version from latest git tag directly into main.py
$version = "0.0.0-dev"
$tag = git describe --tags --abbrev=0 2>$null
if ($tag) {
    $version = $tag -replace '^v', ''
}
python scripts/inject_version.py $version
Write-Host "Injected version: $version"

if (!(Test-Path -LiteralPath ".\.venv")) {
    python -m venv .venv
}

.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

.\.venv\Scripts\pyinstaller.exe `
    --noconsole `
    --onefile `
    --noupx `
    --name "PDFReader by Sparsh" `
    --icon ".\assets\pdfreader_by_sparsh.ico" `
    main.py

Write-Host "Built dist\PDFReader by Sparsh.exe (version ${version})"
