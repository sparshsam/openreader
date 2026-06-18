# Microsoft Store Submission Checklist — OpenReader

**Target version:** v1.2.2 stable (MSIX version `1.2.2.0`)
**Store ID:** `9MXDVW2645LL`
**PFN:** `SparshSam.OpenReader_yh0byntbzd2qw`
**Status:** 🔜 Ready for submission (privacy policy published)
**Privacy policy URL:** https://sparshsam.github.io/pdfreader-by-sparsh/privacy/
**Upload artifact:** `OpenReader.msix` from v1.2.2 GitHub Release (built by release.yml workflow)

---

## 1. Pre-Submission Validation

Run these checks on a **clean Windows 11 VM** before uploading to Partner Center.

### 1.1 Identity Verification

```powershell
# Confirm the MSIX carries the correct frozen identity
Get-AppxPackage SparshSam.OpenReader | Select Name, Version, PackageFamilyName
```

**Expected:**
```text
Name                    Version  PackageFamilyName
----                    -------  -----------------
SparshSam.OpenReader    1.2.2.0  SparshSam.OpenReader_yh0byntbzd2qw
```

### 1.2 Manifest Audit

Extract the MSIX and inspect `AppxManifest.xml`:

```powershell
# Extract MSIX to temp directory
Expand-Archive -Path .\OpenReader.msix -DestinationPath .\msix-check -Force

# Verify identity values
Select-Xml -Path .\msix-check\AppxManifest.xml -XPath "//*[local-name()='Identity']" |
  Select-Object -ExpandProperty Node
```

**Checklist:**

- [ ] `<Identity Name="SparshSam.OpenReader">`
- [ ] `<Publisher="CN=E6186421-BF8A-47E0-A89C-0F513DFF91C0">`
- [ ] Version is `1.2.2.0`
- [ ] `<DisplayName>OpenReader</DisplayName>`
- [ ] `<PublisherDisplayName>Sparsh Sam</PublisherDisplayName>`
- [ ] Executable is `OpenReader.exe`
- [ ] `TargetDeviceFamily MinVersion="10.0.17763.0"` (must be > 10.0.17134.0 for Store)
- [ ] No placeholder or draft values remain

### 1.3 Capability Review

Manifest declares these capabilities:

| Capability | Required For | Store Approval Risk |
|---|---|---|
| `runFullTrust` | Desktop app (Win32) execution | ✅ Expected for Win32 desktop bridge apps |
| `internetClient` | GitHub update check | ✅ Low — documented as non-essential |

> ⚠️ **No restricted capabilities** are declared. `runFullTrust` is standard for
> desktop bridge (Centennial) apps and is accepted by the Store for Win32 packages.

### 1.4 Sideload Test

```powershell
# Install the unsigned MSIX (requires Developer Mode)
Add-AppxPackage .\OpenReader.msix

# Launch and verify basic UI
Start-Process "OpenReader"
```

- [ ] Install succeeds on Windows 11 23H2+
- [ ] Install succeeds on Windows 10 22H2
- [ ] App launches from Start Menu
- [ ] Help → About shows correct version
- [ ] Open a PDF, search, annotate — basic flows work
- [ ] Uninstall via Settings → Apps → Installed apps

---

## 2. Partner Center Upload Checklist

### 2.1 Required Assets

| Asset | Source | Notes |
|---|---|---|
| `.msix` package | `.\packaging\msix\` output from release workflow | **Upload unsigned** — Store signs automatically |
| App Store icons | `assets\icon-*.png` (44, 71, 150, 310x150, 620x300) | Must match manifest declarations |
| Screenshots (at least 1) | Capture from running app | 1366×768 or 1920×1080 PNG recommended |
| Description text | See README overview section | 1–3 paragraphs, no HTML |
| Privacy policy URL | `https://sparshsam.github.io/pdfreader-by-sparsh/privacy/` | Published via GitHub Pages from repo `docs/` directory |
| Age rating questionnaire | Complete in Partner Center | Desktop app category |

### 2.2 Store Listing Details

| Field | Value |
|---|---|
| App name | OpenReader |
| Publisher name | Sparsh Sam |
| Category | Books & Reference (or Productivity) |
| Subcategory | (none required) |
| Supported languages | English (United States) |
| Age rating | 3+ (no restricted content) |
| Price | Free |

### 2.3 Package Upload Process

1. Navigate to **Partner Center** → OpenReader → **Packages**
2. Upload the **unsigned** `OpenReader.msix` from the GitHub Release
3. The Store will automatically sign the package with its Store identity
4. Set `1.2.2.0` as the version in Partner Center (must match manifest)
5. Submit for certification

> **ℹ️** Upload the MSIX produced by the GitHub Actions release workflow directly.
> Do not test-sign it before upload — the Store rejects packages with third-party
> signatures and replaces them with its own.

---

## 3. Unsigned GitHub MSIX vs Store-Signed MSIX

| Aspect | GitHub Release MSIX | Store-Signed MSIX |
|---|---|---|
| Signature | **Unsigned** | Signed by Microsoft Store |
| Developer Mode required? | ✅ Yes (for sideloading) | ❌ No |
| SmartScreen warning? | ✅ Yes | ❌ No |
| Update mechanism | Manual download | Store-managed (automatic) |
| Install scope | Per-user (sideload) | Per-user (Store) |
| Upgrade compatible? | → Store MSIX can upgrade sideload | ← Sideload MSIX can upgrade Store |
| Identity | `SparshSam.OpenReader` (same) | `SparshSam.OpenReader` (same) |
| PFN | `...yh0byntbzd2qw` (same) | `...yh0byntbzd2qw` (same) |

> **Upgrade continuity:** Because the identity and PFN are frozen and identical,
> a Store install will upgrade an existing sideloaded installation and vice versa.
> Users who installed sideloaded betas will receive Store updates without
> re-installing.

---

## 4. Certification Blockers & Risks

### 4.1 Potential Blockers

| Risk | Impact | Mitigation |
|---|---|---|
| **Privacy policy URL missing** | Store requires one for `internetClient` | Publish a privacy policy (GitHub Pages or similar). See `PRIVACY.md` template in this repo. |
| **`runFullTrust` capability** | Store may ask why a desktop app needs full trust | Expected for Win32 desktop bridge apps. Document in submission notes: *"Desktop PDF reader using PySide6 — requires full trust for file system access and window management."* |
| **App description claims** | Store may reject if claims are unrealistic | Keep description factual and shipping-feature-only. Remove roadmap items from Store description. |
| **Unsplash/mock screenshots** | Store requires real app screenshots | Use actual app screenshots from `assets/` |
| **Version mismatch** | Upload rejected if manifest version ≠ Partner Center version | Verify `1.2.2.0` matches everywhere |
| **Store ID reuse** | Cannot reuse Store ID for a different app | Reserved ID `9MXDVW2645LL` is tied to OpenReader — do not reassign |

### 4.2 Certification Notes for Submission

Include these notes in the Partner Center submission's **Notes for certification** field:

```
This is a Win32 desktop application packaged as MSIX using the Desktop Bridge.
The internetClient capability is used only for an optional version check
against GitHub's releases API. No telemetry, no analytics, no user data
collection. The app never uploads or transmits PDF content.
All PDF processing is local.

The app uses PySide6 (Qt 6) for its UI. All PDF rendering uses local
PyMuPDF/MuPDF libraries. No web frameworks or remote services are bundled.
```

### 4.3 After Submission

- [ ] Certification typically takes **1–3 business days**
- [ ] Monitor Partner Center for test result reports
- [ ] If rejected, address the stated issue and resubmit
- [ ] After approval, set availability date or publish immediately
- [ ] Verify the Store listing appears in search
- [ ] Test install from Store on a clean VM

---

## 5. Final Pre-Submit Validation Commands

Run these from PowerShell on a **clean Windows 11 VM** with the MSIX you intend to upload.

### 5.1 Package Integrity

```powershell
# Verify the MSIX is a valid package
Add-AppxPackage .\OpenReader.msix
```

**Expected:** Success. No error code.

### 5.2 Installed State

```powershell
# Check the installed package identity
Get-AppxPackage SparshSam.OpenReader | Select Name, Version, PackageFamilyName
```

**Expected:**
```text
Name                    Version  PackageFamilyName
----                    -------  -----------------
SparshSam.OpenReader    1.2.2.0  SparshSam.OpenReader_yh0byntbzd2qw
```

### 5.3 Functional Smoke Test

```powershell
# Launch from command line
Start-Process "OpenReader"

# Verify process starts
Get-Process OpenReader
```

- [ ] App window appears with "OpenReader" title
- [ ] `Ctrl+O` opens a file dialog
- [ ] Select a PDF → it renders
- [ ] `Ctrl+F` shows search bar
- [ ] `Ctrl+Q` quits gracefully

### 5.4 Manifest Checksum

```powershell
# Verify the manifest embedded in the MSIX matches expectations
$msixPath = ".\OpenReader.msix"
$manifest = [System.IO.Compression.ZipFile]::OpenRead($msixPath)
  .Entries | Where-Object { $_.Name -eq "AppxManifest.xml" }
$reader = New-Object System.IO.StreamReader($manifest.Open())
$xml = $reader.ReadToEnd()
$reader.Close()
$manifest.Dispose()

# Output identity elements
$xml -match 'Name="SparshSam\.OpenReader"' > $null
Write-Host "Identity check: $($matches.Count -gt 0 ? 'PASS' : 'FAIL')"
$xml -match 'CN=E6186421-BF8A-47E0-A89C-0F513DFF91C0' > $null
Write-Host "Publisher check: $($matches.Count -gt 0 ? 'PASS' : 'FAIL')"
```

---

## 6. Post-Submission Tasks

- [x] Publish privacy policy URL (published at `https://sparshsam.github.io/pdfreader-by-sparsh/privacy/`)
- [ ] Prepare Winget manifest for `SparshSam.OpenReader` (optional, medium priority)
- [ ] Monitor Partner Center certification report
- [ ] After acceptance: test Store install on clean Windows VM
- [ ] After acceptance: test Store upgrade over existing sideloaded installation
- [ ] Update `README.md` to reflect Store availability
- [ ] Update `docs/windows-distribution.md` with Store channel details

---

## References

- [Windows Distribution Strategy](windows-distribution.md)
- [MSIX Update Validation](msix-update-validation.md)
- [MSIX Packaging README](../packaging/msix/README.md)
- [Microsoft Store certification docs](https://learn.microsoft.com/en-us/windows/uwp/publish/store-policies)
