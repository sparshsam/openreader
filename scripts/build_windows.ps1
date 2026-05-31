$ErrorActionPreference = "Stop"

Set-Location -Path (Split-Path -Parent $PSScriptRoot)

# Inject version from latest git tag
$version = "0.0.0-dev"
$tag = git describe --tags --abbrev=0 2>$null
if ($tag) {
    $version = $tag -replace '^v', ''
}
"__version__ = ""${version}""" | Out-File -FilePath version.py -Encoding utf8

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
