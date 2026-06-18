<#
.SYNOPSIS
    Create a self-signed test certificate for local MSIX beta testing.

.DESCRIPTION
    Creates a self-signed code-signing certificate whose Subject matches
    the frozen MSIX Publisher identity exactly:
      CN=E6186421-BF8A-47E0-A89C-0F513DFF91C0

    This certificate is for LOCAL TESTING ONLY. It is not trusted by
    Windows by default — testers must install it into Trusted Root or
    Trusted People (see install-test-cert.ps1).

    Production signing should use the Microsoft Store. This script exists
    solely to enable MSIX update validation on test machines without
    enabling Developer Mode.

    The .pfx file is password-protected and can be safely shared with
    testers, but must NOT be used for production distribution.

.NOTES
    Run this script on a Windows machine with the Windows SDK installed
    (provides MakeCert.exe / PowerShell New-SelfSignedCertificate).

    File: create-test-cert.ps1
    Author: Sparsh Sam
#>

$ErrorActionPreference = "Stop"

$PublisherCN = "CN=E6186421-BF8A-47E0-A89C-0F513DFF91C0"
$CertName = "OpenReader-Test-Cert"
$PfxFile = Join-Path $PSScriptRoot "OpenReader-Test-Cert.pfx"
$CerFile = Join-Path $PSScriptRoot "OpenReader-Test-Cert.cer"
$PfxPassword = "OpenReaderTest2024"  # Used only for local testing; not a security secret

Write-Host "=== OpenReader Test Certificate Generator ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Publisher: $PublisherCN" -ForegroundColor Yellow
Write-Host "Output: $PfxFile" -ForegroundColor Yellow
Write-Host "Public key: $CerFile" -ForegroundColor Yellow
Write-Host ""
Write-Host "WARNING: This certificate is for LOCAL TESTING ONLY." -ForegroundColor Red
Write-Host "Do NOT use for production distribution." -ForegroundColor Red
Write-Host ""

# Check if certificate already exists
if (Test-Path $PfxFile) {
    Write-Host "Certificate already exists at $PfxFile" -ForegroundColor Yellow
    Write-Host "Delete it first if you want to regenerate." -ForegroundColor Yellow
    exit 0
}

# Create self-signed code-signing certificate
# Using New-SelfSignedCertificate (available on Windows 10+ / Windows Server 2016+)
Write-Host "Creating self-signed code-signing certificate..." -ForegroundColor Cyan

try {
    # Try New-SelfSignedCertificate (modern PowerShell)
    $cert = New-SelfSignedCertificate `
        -Subject $PublisherCN `
        -FriendlyName $CertName `
        -Type CodeSigning `
        -CertStoreLocation "Cert:\CurrentUser\My" `
        -NotAfter (Get-Date).AddYears(3) `
        -KeyUsage DigitalSignature `
        -TextExtension @("2.5.29.37={text}1.3.6.1.5.5.7.3.3")  # Code Signing EKU

    Write-Host "Certificate created: $($cert.Thumbprint)" -ForegroundColor Green

    # Export to .pfx (private key + cert, password-protected)
    $securePass = ConvertTo-SecureString -String $PfxPassword -Force -AsPlainText
    Export-PfxCertificate -Cert $cert -FilePath $PfxFile -Password $securePass
    Write-Host "Exported private key: $PfxFile" -ForegroundColor Green

    # Export public key as .cer (for distribution to testers)
    Export-Certificate -Cert $cert -FilePath $CerFile -Type CERT
    Write-Host "Exported public key: $CerFile" -ForegroundColor Green

    Write-Host ""
    Write-Host "Certificate generation complete." -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "  1. Sign the MSIX:   .\sign-msix-test.ps1" -ForegroundColor Cyan
    Write-Host "  2. Distribute .cer to testers who need to install the cert" -ForegroundColor Cyan

} catch {
    Write-Error "Failed to create certificate: $_"
    Write-Host ""
    Write-Host "Alternative: Use a Windows machine with the Windows SDK installed." -ForegroundColor Yellow
    exit 1
}
