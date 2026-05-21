$ErrorActionPreference = "Stop"

Set-Location -Path (Split-Path -Parent $PSScriptRoot)

if (!(Test-Path -LiteralPath ".\.venv")) {
    python -m venv .venv
}

.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

.\.venv\Scripts\pyinstaller.exe `
    --noconsole `
    --onefile `
    --name "PDFReader by Sparsh" `
    --icon ".\assets\pdfreader_by_sparsh.ico" `
    main.py

Write-Host "Built dist\PDFReader by Sparsh.exe"
