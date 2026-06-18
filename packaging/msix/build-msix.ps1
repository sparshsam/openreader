<#
.SYNOPSIS
    Build an MSIX package for OpenReader.

.DESCRIPTION
    This script packages a PyInstaller build output into an MSIX container
    suitable for Microsoft Store, sideloading, or App Installer distribution.

    Prerequisites (Windows):
    - Visual Studio 2022 Build Tools (or SDK): install "Desktop development with C++"
    - Or install the Windows SDK standalone:
      https://developer.microsoft.com/en-us/windows/downloads/windows-sdk/
    - A code-signing certificate (.pfx) for package signing (or use Store signing)

    Usage:
      .\build-msix.ps1 -ExeDir "..\dist\OpenReader" -Version "1.2.0.0"

    Optional:
      -PfxPath ".\certificate.pfx" -PfxPassword "password"

    The script generates:
      - OpenReader.msix (sideload-ready or Store-ready)

    FROZEN IDENTITY (do not change):
      Identity Name:  SparshSam.OpenReader
      Publisher:      CN=E6186421-BF8A-47E0-A89C-0F513DFF91C0
      Executable:     OpenReader.exe

.NOTES
    File: build-msix.ps1
    Author: Sparsh Sam
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
# Normalize to path string (Get-Command returns CommandInfo, Get-ChildItem returns FileInfo)
$makeAppxPath = if ($makeAppx -is [System.IO.FileInfo]) { $makeAppx.FullName } else { $makeAppxPath }

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

# Normalize to path string (Get-Command returns CommandInfo, Get-ChildItem returns FileInfo)
$makeAppxPath = if ($makeAppx -is [System.IO.FileInfo]) { $makeAppx.FullName } else { $makeAppxPath }

if (-not $makeAppx) {
    Write-Error "MakeAppx.exe not found. Install the Windows SDK (https://developer.microsoft.com/en-us/windows/downloads/windows-sdk/)"
    exit 1
}

Write-Host "Using MakeAppx: $($makeAppxPath)" -ForegroundColor Cyan

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
$content = [System.IO.File]::ReadAllText("$ManifestDest")
$content = $content -creplace 'Version="[^"]+"', 'Version="' + "$Version" + '"'
[System.IO.File]::WriteAllText("$ManifestDest", $content, [System.Text.UTF8Encoding]$false)

# Generate MSIX asset placeholders using Python
Write-Host "Generating MSIX asset placeholders..." -ForegroundColor Cyan
$AssetDir = Join-Path $StageDir "assets"
New-Item -ItemType Directory -Path $AssetDir -Force | Out-Null
$PngScript = Join-Path (Split-Path $PSScriptRoot -Parent) "tools" "create_msix_placeholder_pngs.py"
if (Test-Path $PngScript) {
    & python $PngScript $AssetDir
    if ($LASTEXITCODE -ne 0) { Write-Error "Asset generation failed"; exit 1 }
} else {
    Write-Warning "Asset generation script not found at $PngScript"
    Write-Warning "Creating minimal PNGs with PowerShell fallback..."
    Add-Type -AssemblyName System.Drawing
    $sizes = @(@(44,44), @(150,150), @(71,71), @(310,150), @(620,300))
    foreach ($pair in $sizes) {
        $p = Join-Path $AssetDir "icon-$($pair[0])x$($pair[1]).png"
        if (-not (Test-Path $p)) {
            $bmp = New-Object System.Drawing.Bitmap($pair[0], $pair[1])
            $bmp.Save($p, [System.Drawing.Imaging.ImageFormat]::Png)
            $bmp.Dispose()
        }
    }
}

# --- Build MSIX ---
$MsixPath = Join-Path $OutputDir "OpenReader.msix"
Write-Host "Building MSIX: $MsixPath" -ForegroundColor Cyan

if ($PfxPath -and (Test-Path $PfxPath)) {
    # Build and sign in one step (Windows 10 SDK 10.0.17763+)
    & $makeAppxPath pack /p $MsixPath /d $StageDir /l
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
    & $makeAppxPath pack /p $MsixPath /d $StageDir /l
    if ($LASTEXITCODE -ne 0) { Write-Error "MakeAppx failed (exit $LASTEXITCODE)"; exit 1 }
    Write-Warning "No signing certificate provided. MSIX is unsigned — must be sideloaded in Developer Mode."
}

# --- Clean up staging ---
Remove-Item -Recurse -Force $StageDir

Write-Host "MSIX build complete: $MsixPath" -ForegroundColor Green
