<#
.SYNOPSIS
    Sign an OpenReader.msix with the local test certificate.

.DESCRIPTION
    Uses SignTool.exe (from Windows SDK) to sign an OpenReader.msix
    package with the local test certificate created by create-test-cert.ps1.

    This signature is for LOCAL TESTING ONLY. Windows will not trust this
    certificate by default. Testers must install the .cer file into Trusted
    Root (see install-test-cert.ps1).

    Production signing must use the Microsoft Store.

.NOTES
    Prerequisites:
      - Windows SDK (provides SignTool.exe)
      - OpenReader-Test-Cert.pfx (created by create-test-cert.ps1)
      - OpenReader.msix (built by release CI or build-msix.ps1)

    File: sign-msix-test.ps1
    Author: Sparsh Sam
#>

param(
    [Parameter(Mandatory = $false)]
    [string]$MsixPath = "",

    [Parameter(Mandatory = $false)]
    [string]$PfxPath = "",

    [Parameter(Mandatory = $false)]
    [string]$PfxPassword = "OpenReaderTest2024",

    [Parameter(Mandatory = $false)]
    [string]$TimestampServer = "http://timestamp.digicert.com"
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $PSCommandPath

# --- Resolve paths ---
if (-not $MsixPath) {
    $MsixPath = Join-Path $ScriptDir "..\..\OpenReader.msix"
    if (-not (Test-Path $MsixPath)) {
        $MsixPath = Join-Path $ScriptDir "..\..\OpenReader-test.msix"
    }
}

if (-not $PfxPath) {
    $PfxPath = Join-Path $ScriptDir "OpenReader-Test-Cert.pfx"
}

# --- Validate inputs ---
if (-not (Test-Path $MsixPath)) {
    Write-Error "MSIX not found at $MsixPath. Build it first (CI or build-msix.ps1)."
    exit 1
}

if (-not (Test-Path $PfxPath)) {
    Write-Error "Test certificate not found at $PfxPath. Run create-test-cert.ps1 first."
    exit 1
}

# --- Locate SignTool.exe ---
$signtool = Get-Command "signtool.exe" -ErrorAction SilentlyContinue
if (-not $signtool) {
    $sdkPaths = @(
        "${env:ProgramFiles(x86)}\Windows Kits\10\bin\*\x64\signtool.exe",
        "${env:ProgramFiles}\Windows Kits\10\bin\*\x64\signtool.exe",
        "${env:ProgramFiles(x86)}\Microsoft SDKs\Windows\v*\Bin\signtool.exe"
    )
    foreach ($pattern in $sdkPaths) {
        $found = Get-ChildItem $pattern -ErrorAction SilentlyContinue | Sort-Object -Descending | Select-Object -First 1
        if ($found) { $signtool = $found; break }
    }
}

if (-not $signtool) {
    Write-Error "SignTool.exe not found. Install the Windows SDK."
    exit 1
}

Write-Host "=== OpenReader MSIX Test Signing ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "SignTool: $($signtool.Source)" -ForegroundColor Cyan
Write-Host "MSIX:     $MsixPath" -ForegroundColor Cyan
Write-Host "Cert:     $PfxPath" -ForegroundColor Cyan
Write-Host ""

# --- Sign ---
Write-Host "Signing MSIX package..." -ForegroundColor Cyan

$signArgs = @(
    "sign",
    "/fd", "SHA256",
    "/a",
    "/f", (Resolve-Path $PfxPath).Path,
    "/p", $PfxPassword,
    "/v"
)

if ($TimestampServer) {
    $signArgs += "/tr"
    $signArgs += $TimestampServer
    $signArgs += "/td"
    $signArgs += "SHA256"
}

$signArgs += (Resolve-Path $MsixPath).Path

& $signtool.Source $signArgs
if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "=== SIGNING SUCCESSFUL ===" -ForegroundColor Green
    Write-Host "MSIX signed for local testing: $MsixPath" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "  1. Distribute the .cer file to testers" -ForegroundColor Cyan
    Write-Host "  2. Testers run: .\install-test-cert.ps1" -ForegroundColor Cyan
    Write-Host "  3. Testers can now install the signed MSIX" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "WARNING: This signature is for TESTING ONLY." -ForegroundColor Red
    Write-Host "Production signing must use Microsoft Store." -ForegroundColor Red
} else {
    Write-Error "Signing failed with exit code $LASTEXITCODE"
    exit 1
}
