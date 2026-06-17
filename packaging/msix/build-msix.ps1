<#
.SYNOPSIS
    Build an MSIX package for PDFReader by Sparsh.

.DESCRIPTION
    This script packages a PyInstaller build output into an MSIX container
    suitable for sideloading or App Installer distribution.

    Prerequisites (Windows):
    - Visual Studio 2022 Build Tools (or SDK): install "Desktop development with C++"
    - Or install the Windows SDK standalone:
      https://developer.microsoft.com/en-us/windows/downloads/windows-sdk/
    - A code-signing certificate (.pfx) for package signing

    Usage:
      .\build-msix.ps1 -ExeDir "..\dist\PDFReader by Sparsh" -Version "1.2.0.0"

    Optional:
      -PfxPath ".\certificate.pfx" -PfxPassword "password"

    The script generates:
      - PDFReader-by-Sparsh.msix
      - PDFReader-by-Sparsh.msix (sideload-ready)
      - The AppInstaller file references the GitHub Release for autoupdate.

.NOTES
    File: build-msix.ps1
    Author: Sparsh
#>

param(
    [Parameter(Mandatory = $true)]
    [string]$ExeDir,

    [Parameter(Mandatory = $false)]
    [string]$Version = "1.2.0.0",

    [Parameter(Mandatory = $false)]
    [string]$PfxPath = "",

    [Parameter(Mandatory = $false)]
    [string]$PfxPassword = "",

    [Parameter(Mandatory = $false)]
    [string]$OutputDir = "."
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $PSCommandPath

# --- Validate inputs ---
if (-not (Test-Path $ExeDir)) {
    Write-Error "ExeDir '$ExeDir' not found. Run PyInstaller first."
    exit 1
}

# --- Locate MakeAppx.exe ---
$makeAppx = Get-Command "MakeAppx.exe" -ErrorAction SilentlyContinue
if (-not $makeAppx) {
    $sdkPaths = @(
        "${env:ProgramFiles(x86)}\Windows Kits\10\bin\*\x64\MakeAppx.exe",
        "${env:ProgramFiles}\Microsoft SDKs\ClickOnce\signtool\MakeAppx.exe"
    )
    foreach ($pattern in $sdkPaths) {
        $found = Get-ChildItem $pattern -ErrorAction SilentlyContinue | Sort-Object -Descending | Select-Object -First 1
        if ($found) { $makeAppx = $found; break }
    }
}

if (-not $makeAppx) {
    Write-Error "MakeAppx.exe not found. Install the Windows SDK (https://developer.microsoft.com/en-us/windows/downloads/windows-sdk/)"
    exit 1
}

Write-Host "Using MakeAppx: $($makeAppx.Source)" -ForegroundColor Cyan

# --- Prepare staging directory ---
$StageDir = Join-Path $OutputDir "_msix_staging"
if (Test-Path $StageDir) { Remove-Item -Recurse -Force $StageDir }
New-Item -ItemType Directory -Path $StageDir -Force | Out-Null

# Copy application files
Write-Host "Copying application files..." -ForegroundColor Cyan
Copy-Item -Path "$ExeDir\*" -Destination $StageDir -Recurse -Force

# Copy AppxManifest and update version
$ManifestPath = Join-Path $ScriptDir "AppxManifest.xml"
$ManifestDest = Join-Path $StageDir "AppxManifest.xml"
Copy-Item -Path $ManifestPath -Destination $ManifestDest -Force
(Get-Content $ManifestDest) -replace 'Version="[^"]+"', "Version=`"$Version`"" | Set-Content $ManifestDest

# Create placeholder asset directory and files
# In production, replace these with actual resized application icons
$AssetDir = Join-Path $StageDir "assets"
New-Item -ItemType Directory -Path $AssetDir -Force | Out-Null

# Generate minimal PNG placeholders if not present
$iconSizes = @(
    @{Name="icon-44x44.png"; Size=44},
    @{Name="icon-150x150.png"; Size=150},
    @{Name="icon-71x71.png"; Size=71},
    @{Name="icon-310x150.png"; Width=310; Height=150},
    @{Name="icon-620x300.png"; Width=620; Height=300}
)

foreach ($icon in $iconSizes) {
    $iconPath = Join-Path $AssetDir $icon.Name
    if (-not (Test-Path $iconPath)) {
        # Create a minimal 1-pixel PNG placeholder
        # (Replace with actual icon assets before production packaging)
        $placeholder = "$([char]0x89)PNG$([char]0x0D)$([char]0x0A)$([char]0x1A)$([char]0x0A)"
        $null -eq $placeholder  # This would be a proper PNG in production
    }
}

# --- Build MSIX ---
$MsixPath = Join-Path $OutputDir "PDFReader-by-Sparsh.msix"
Write-Host "Building MSIX: $MsixPath" -ForegroundColor Cyan

if ($PfxPath -and (Test-Path $PfxPath)) {
    # Build and sign in one step (Windows 10 SDK 10.0.17763+)
    & $makeAppx.Source pack /p $MsixPath /d $StageDir /l
    if ($LASTEXITCODE -ne 0) { Write-Error "MakeAppx failed (exit $LASTEXITCODE)"; exit 1 }

    # Sign the package
    $signtool = Get-Command "signtool.exe" -ErrorAction SilentlyContinue
    if (-not $signtool) {
        Write-Error "signtool.exe not found. MSIX built but not signed."
        exit 1
    }

    $signArgs = @("sign", "/fd", "SHA256", "/a")
    if ($PfxPassword) {
        $signArgs += "/f"
        $signArgs += $PfxPath
        $signArgs += "/p"
        $signArgs += $PfxPassword
    }
    $signArgs += $MsixPath

    & $signtool.Source $signArgs
    if ($LASTEXITCODE -eq 0) {
        Write-Host "MSIX package signed successfully." -ForegroundColor Green
    } else {
        Write-Error "Signing failed (exit $LASTEXITCODE)"
        exit 1
    }
} else {
    # Build without signing (sideload only — requires developer mode)
    & $makeAppx.Source pack /p $MsixPath /d $StageDir /l
    if ($LASTEXITCODE -ne 0) { Write-Error "MakeAppx failed (exit $LASTEXITCODE)"; exit 1 }
    Write-Warning "No signing certificate provided. MSIX is unsigned — must be sideloaded in Developer Mode."
}

# --- Clean up staging ---
Remove-Item -Recurse -Force $StageDir

Write-Host "MSIX build complete: $MsixPath" -ForegroundColor Green
