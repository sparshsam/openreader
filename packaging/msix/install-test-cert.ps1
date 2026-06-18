<#
.SYNOPSIS
    Install the OpenReader test certificate into the Trusted Root store.

.DESCRIPTION
    Installs the OpenReader test certificate (OpenReader-Test-Cert.cer)
    into the Local Machine Trusted Root Certification Authorities store.

    This makes the test-signed MSIX package trusted on this machine,
    allowing installation without enabling Developer Mode.

    WARNING: Installing a test certificate into Trusted Root grants it
    full trust on this machine. Only do this on TEST/VIRTUAL machines.
    Uninstall the certificate after testing (see instructions below).

.NOTES
    Requires Administrator privileges (installs into Local Machine store).

    To remove the certificate after testing:
      certlm.msc → Trusted Root Certification Authorities → Certificates
      → Find "OpenReader-Test-Cert" → Right-click → Delete

    Or via PowerShell (admin):
      Get-ChildItem Cert:\LocalMachine\Root | Where-Object {
        $_.Subject -eq "CN=E6186421-BF8A-47E0-A89C-0F513DFF91C0"
      } | Remove-Item

    File: install-test-cert.ps1
    Author: Sparsh Sam
#>

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $PSCommandPath
$CerFile = Join-Path $ScriptDir "OpenReader-Test-Cert.cer"

# --- Check admin ---
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator
)
if (-not $isAdmin) {
    Write-Error "Administrator privileges required. Run PowerShell as Administrator."
    exit 1
}

# --- Validate .cer exists ---
if (-not (Test-Path $CerFile)) {
    Write-Error "Certificate not found at $CerFile. Run create-test-cert.ps1 first."
    Write-Host ""
    Write-Host "If you received the .cer file from a developer, copy it to:" -ForegroundColor Yellow
    Write-Host "  $CerFile" -ForegroundColor Yellow
    exit 1
}

Write-Host "=== OpenReader Test Certificate Installer ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "WARNING: This installs a test certificate into" -ForegroundColor Red
Write-Host "         Local Machine Trusted Root." -ForegroundColor Red
Write-Host "         Only do this on TEST/VIRTUAL MACHINES." -ForegroundColor Red
Write-Host ""

# Confirm
$confirm = Read-Host "Install test certificate? This trusts all code signed by it. (y/N)"
if ($confirm -ne "y" -and $confirm -ne "Y") {
    Write-Host "Cancelled." -ForegroundColor Yellow
    exit 0
}

# --- Install into Trusted Root ---
try {
    $cert = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2($CerFile)
    $store = New-Object System.Security.Cryptography.X509Certificates.X509Store("Root", "LocalMachine")
    $store.Open("ReadWrite")

    # Check if already installed
    $existing = $store.Certificates | Where-Object {
        $_.Thumbprint -eq $cert.Thumbprint
    }
    if ($existing) {
        Write-Host "Certificate already installed in Trusted Root." -ForegroundColor Yellow
    } else {
        $store.Add($cert)
        Write-Host "Certificate installed in Trusted Root successfully." -ForegroundColor Green
    }
    $store.Close()

    # Also install into Trusted People (recommended for MSIX)
    $store2 = New-Object System.Security.Cryptography.X509Certificates.X509Store("TrustedPeople", "LocalMachine")
    $store2.Open("ReadWrite")
    $existing2 = $store2.Certificates | Where-Object {
        $_.Thumbprint -eq $cert.Thumbprint
    }
    if (-not $existing2) {
        $store2.Add($cert)
        Write-Host "Certificate also installed in Trusted People." -ForegroundColor Green
    }
    $store2.Close()

} catch {
    Write-Error "Failed to install certificate: $_"
    exit 1
}

Write-Host ""
Write-Host "=== INSTALLATION COMPLETE ===" -ForegroundColor Green
Write-Host ""
Write-Host "You can now install the signed OpenReader.msix by double-clicking it." -ForegroundColor Cyan
Write-Host ""
Write-Host "To uninstall the certificate after testing:" -ForegroundColor Yellow
Write-Host "  certlm.msc → Trusted Root Certification Authorities → Certificates" -ForegroundColor Yellow
Write-Host "  → Find 'OpenReader-Test-Cert' → Right-click → Delete" -ForegroundColor Yellow
Write-Host ""
Write-Host "Or via PowerShell (admin):" -ForegroundColor Yellow
Write-Host '  Get-ChildItem Cert:\LocalMachine\Root | Where-Object {' -ForegroundColor Yellow
Write-Host '    $_.Subject -eq "CN=E6186421-BF8A-47E0-A89C-0F513DFF91C0"' -ForegroundColor Yellow
Write-Host '  } | Remove-Item' -ForegroundColor Yellow
