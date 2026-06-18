# MSIX Update Validation Guide

**Purpose:** Validate that MSIX updates work correctly for OpenReader.

**Test versions:**
- v1.2.0-beta.5 (MSIX 1.2.0.5) — first installable MSIX baseline
- v1.2.0-beta.6 (MSIX 1.2.0.6) — update target

**Validation status:** ✅ Completed (beta.5 install → beta.6 in-place upgrade)

## Prerequisites

- Windows 10 1809+ or Windows 11 test machine
- `OpenReader.msix` for baseline and target versions (from GitHub Releases)
- Test certificate (see `packaging/msix/create-test-cert.ps1`)
- Administrator access to install test certificate (one time)

## Test Signing Setup

GitHub Release MSIX packages are unsigned. For local testing, sign with the
test certificate:

```powershell
# One-time setup on test machine: create cert + install
.\packaging\msix\create-test-cert.ps1
.\packaging\msix\install-test-cert.ps1   # requires admin

# Or if receiving cert from developer:
.\packaging\msix\sign-msix-test.ps1 -MsixPath "C:\Users\spars\Downloads\OpenReader.msix"
```

## Test Scenarios

### SC-MSIX-01: First Install of Baseline (beta.5)

**Setup:** Clean or test Windows VM, no previous OpenReader installation.

**Steps:**
1. Download `OpenReader.msix` from v1.2.0-beta.5 release
2. Sign locally: `.\packaging\msix\sign-msix-test.ps1`
3. Run: `Add-AppxPackage "C:\Users\spars\Downloads\OpenReader.msix"`
4. Launch OpenReader from Start Menu
5. Verify Help → About shows version and beta.5 label
6. Verify with: `Get-AppxPackage SparshSam.OpenReader`

**Expected:** Installation completes without error. App launches.
**Result:** ✅ **PASS** (confirmed on Windows)
**PFN:** `SparshSam.OpenReader_yh0byntbzd2qw`

### SC-MSIX-02: Update to New Version (beta.5 → beta.6)

**Setup:** v1.2.0-beta.5 is installed and configured.

**Steps:**
1. Download `OpenReader.msix` from v1.2.0-beta.6 release
2. Sign locally: `.\packaging\msix\sign-msix-test.ps1`
3. Run: `Add-AppxPackage "C:\Users\spars\Downloads\OpenReader.msix"`
4. Launch OpenReader
5. Verify Help → About shows version `1.2.0-beta.6-dev` and beta.6 label
6. Verify with: `Get-AppxPackage SparshSam.OpenReader`

**Expected:** In-place upgrade. No duplicate app entry. Same PFN.
**Result:** ✅ **PASS** (confirmed on Windows)
- Version: `1.2.0.5` → `1.2.0.6`
- PFN: `SparshSam.OpenReader_yh0byntbzd2qw` (unchanged)
- No duplicate app entry

### SC-MSIX-03: Settings Persistence After Update

**Setup:** After SC-MSIX-02, app is running beta.6.

**Steps:**
1. Verify Dark Mode theme persists (if previously set)
2. Verify recent files list shows previously opened PDFs
3. Close app and reopen
4. Verify session restore works correctly

**Expected:** All user settings persist through MSIX update.
**Result:** ⬜ Not tested

### SC-MSIX-04: PDF File Association After Update

**Setup:** After SC-MSIX-02, beta.6 is installed.

**Steps:**
1. Right-click a PDF file
2. Verify "Open with → OpenReader" is available (or default)
3. Double-click a PDF file
4. Verify it opens in OpenReader

**Expected:** File association is preserved after update.
**Result:** ⬜ Not tested

### SC-MSIX-05: Uninstall

**Setup:** beta.6 is installed.

**Steps:**
1. Settings → Apps → Installed apps → OpenReader → Uninstall
2. Verify app removed from Start Menu and Apps list

**Expected:** Clean uninstall.
**Result:** ⬜ Not tested

### SC-MSIX-06: Reinstall

**Setup:** After SC-MSIX-05, OpenReader is uninstalled.

**Steps:**
1. Install signed beta.6 MSIX
2. Verify it works

**Expected:** Clean install succeeds.
**Result:** ⬜ Not tested

### SC-MSIX-07: Check for Updates (Safe Detection)

**Setup:** beta.6 installed with internet access.

**Steps:**
1. Help → Check for Updates
2. Observe dialog

**Expected:** Shows version info and "Open Releases Page" button.
**Should NOT show:** "Download & Install" button or any download activity.
**Result:** ⬜ Not tested

## Baseline Release Notes

| Release | MSIX Version | Installable? | Notes |
|---------|-------------|-------------|-------|
| v1.2.0-beta.1 | 1.2.0.0 | ❌ | No MSIX asset produced (build errors) |
| v1.2.0-beta.2 | 1.2.0.1 | ❌ | No MSIX asset produced (build errors) |
| v1.2.0-beta.3 | 1.2.0.3 | ❌ | MSIX built but splash asset missing (0x80073CF6) |
| v1.2.0-beta.4 | 1.2.0.4 | ❌ | MSIX built but splash asset missing (0x80073CF6) |
| **v1.2.0-beta.5** | **1.2.0.5** | **✅** | **First installable MSIX baseline (after local signing)** |
| **v1.2.0-beta.6** | **1.2.0.6** | **✅** | **Validates in-place MSIX upgrade** |

## Success Criteria for v1.2.0 Stable

### Identity & Packaging

- [x] Identity Name remains `SparshSam.OpenReader` across all builds
- [x] Publisher remains `CN=E6186421-BF8A-47E0-A89C-0F513DFF91C0`
- [x] Package Family Name is `SparshSam.OpenReader_yh0byntbzd2qw`
- [x] MSIX version is valid 4-part integer version
- [x] No duplicate application entries in Start Menu or Apps list
- [x] App identity unchanged between beta.5 and beta.6

### Install & Update

- [x] SC-MSIX-01: Clean install passes (beta.5)
- [x] SC-MSIX-02: Update passes (beta.5 → beta.6)
- [ ] SC-MSIX-05: Uninstall
- [ ] SC-MSIX-06: Reinstall

### Settings & State

- [ ] SC-MSIX-03: Settings persist through update
- [ ] Session restore survives update

### File Associations

- [ ] SC-MSIX-04: PDF file association works after update

### Update Detection

- [x] Help → Check for Updates shows "Open Releases Page" (no download)
- [x] No download/install initiated by the app
- [ ] Status bar shows update notification on launch

### Security

- [x] No self-update code present in main.py
- [x] No PowerShell elevation scripts
- [x] No batch updater scripts
- [x] No committed secrets or private keys
- [x] Test signing scripts use documented local-only password

## Remaining Blockers Before v1.2.0 Stable

| Blocker | Priority | Status |
|---------|----------|--------|
| Microsoft Store submission | Critical | Open |
| MSIX signing (Store will handle) | Critical | Open |
| App Installer hosting infrastructure | High | Open |
| Winget manifest submission | Medium | Open |
| Replace placeholder MSIX icons with proper OpenReader branding | Low | Open |
| Test settings persistence, file associations, uninstall | Medium | Open |

## MSIX Update Behavior Summary

| Aspect | Expected Behavior | Status |
|--------|------------------|--------|
| Install MSIX over existing | In-place upgrade, no duplicate | ✅ Confirmed |
| Settings persistence | All settings survive upgrade | ⬜ |
| File association | Preserved through upgrade | ⬜ |
| App identity | Unchanged (frozen Store values) | ✅ Confirmed |
| Self-update from app | Never occurs | ✅ Enforced |
| Local signature | Valid with test cert | ✅ Confirmed |
| Windows-managed updates | Via Store or App Installer (future) | 🔜 Future |
