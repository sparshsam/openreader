# Release Readiness: v1.2.0-beta.1 — OpenReader MSIX Migration

## Identity Freeze Verification

- [ ] AppxManifest.xml uses `Identity Name="SparshSam.OpenReader"`
- [ ] AppxManifest.xml uses `Publisher="CN=E6186421-BF8A-47E0-A89C-0F513DFF91C0"`
- [ ] AppxManifest.xml uses `PublisherDisplayName="Sparsh Sam"`
- [ ] AppInstaller.xml uses `Name="SparshSam.OpenReader"`
- [ ] AppInstaller.xml uses `Publisher="CN=E6186421-BF8A-47E0-A89C-0F513DFF91C0"`
- [ ] Executable name is `OpenReader.exe` everywhere
- [ ] No placeholder Publisher values remain
- [ ] No `com.sparshsam.*` identities exist anywhere
- [ ] `PDFReaderBySparsh` no longer appears in any identity field

## Versioning

- [ ] MSIX version is 4-part (`1.2.0.0`)
- [ ] Git tag `v1.2.0-beta.1` maps to MSIX version `1.2.0.0`
- [ ] CI workflow correctly injects version from tag

## Validation Scenarios

### SC-01: Clean Windows 11 Install (MSIX)
**Setup:** Clean Windows 11 VM, MSIX downloaded from GitHub Releases
**Steps:**
1. Enable Developer Mode (Settings → Privacy & security → For developers)
2. Double-click `OpenReader.msix`
3. Observe installation completes
4. Launch OpenReader from Start Menu
**Pass:** App launches, shows "OpenReader" in title bar and About dialog
**Fail:** Installation blocked, app crashes on launch, wrong app name
**[ ] Status:**

### SC-02: Clean Windows 11 Install (Store)
**Setup:** Clean Windows 11 VM with Store access
**Steps:**
1. Open Microsoft Store
2. Search for "OpenReader" or use Store link
3. Install
4. Launch
**Pass:** App installs without Developer Mode, launches correctly
**Fail:** Store listing not found, installation fails
**[ ] Status:**

### SC-03: Upgrade from v1.1.10 (Legacy Setup.exe)
**Setup:** Windows 11 with OpenReader v1.1.10 installed via Setup.exe
**Steps:**
1. Verify v1.1.10 is installed (Help → About)
2. Download `OpenReader-Setup.exe` (legacy installer)
3. Run as Administrator
4. Install over existing
**Pass:** OpenReader launches successfully, user settings migrated
**Fail:** Installer fails, settings lost, app doesn't launch
**[ ] Status:**

### SC-04: Upgrade from v1.1.11 (Legacy Setup.exe)
**Setup:** Windows 11 with OpenReader v1.1.11 installed
**Steps:** Same as SC-03
**Pass/Fail:** Same criteria
**[ ] Status:**

### SC-05: MSIX Upgrade (v1.2.0-beta.1 → v1.2.0)
**Setup:** Windows 11 with v1.2.0-beta.1 MSIX installed
**Steps:**
1. Verify current version
2. Download new `OpenReader.msix`
3. Install (should auto-upgrade)
**Pass:** Upgrade succeeds, settings preserved, app launches
**Fail:** Upgrade blocked by identity mismatch, settings lost
**[ ] Status:**

### SC-06: Uninstall (MSIX)
**Setup:** Windows 11 with OpenReader MSIX installed
**Steps:**
1. Settings → Apps → Installed apps → OpenReader → Uninstall
2. Verify removal
**Pass:** App removed, no leftover files in install directory, Start Menu entry gone
**Fail:** Uninstall fails, files remain
**[ ] Status:**

### SC-07: Reinstall (MSIX)
**Setup:** Windows 11, OpenReader was previously installed and uninstalled
**Steps:**
1. Install `OpenReader.msix` fresh
2. Launch
**Pass:** Clean install succeeds, app launches correctly
**Fail:** Installation fails due to stale registry/data
**[ ] Status:**

### SC-08: Settings Persistence
**Setup:** Windows 11 with OpenReader installed
**Steps:**
1. Open a PDF
2. Change theme to Dark Mode
3. Change zoom level
4. Close app
5. Reopen
**Pass:** Theme, zoom, and window position restored
**Fail:** Settings reset to defaults
**[ ] Status:**

### SC-09: Recent Files Persistence
**Setup:** Windows 11 with OpenReader installed
**Steps:**
1. Open several PDFs
2. Close app
3. Reopen
4. Check File → Open Recent
**Pass:** Recently opened files listed
**Fail:** Recent files list empty
**[ ] Status:**

### SC-10: Theme Persistence
**Setup:** Windows 11 with OpenReader installed
**Steps:**
1. Set theme to Dark, Light, and Auto modes
2. Close and reopen app each time
**Pass:** Theme setting persists across restarts
**Fail:** Theme resets to default each launch
**[ ] Status:**

### SC-11: Session Restore Persistence
**Setup:** Windows 11 with OpenReader installed
**Steps:**
1. Open 3 PDFs, navigate to different pages
2. Close app
3. Reopen
4. Respond to session restore prompt
**Pass:** All 3 PDFs reopen at their respective pages
**Fail:** PDFs don't restore, wrong pages
**[ ] Status:**

### SC-12: PDF File Association (MSIX)
**Setup:** Windows 11 with OpenReader installed
**Steps:**
1. Right-click a PDF file
2. Open with → OpenReader
3. Double-click a PDF file (if default)
**Pass:** PDF opens in OpenReader
**Fail:** PDF doesn't open, wrong app opens
**[ ] Status:**

### SC-13: PDF File Association (Legacy Setup.exe)
**Setup:** Windows 11 with OpenReader installed via Setup.exe
**Steps:** Same as SC-12
**Pass/Fail:** Same criteria
**[ ] Status:**

### SC-14: Check for Updates (Safe Mode)
**Setup:** Windows 11 with OpenReader installed, internet connection
**Steps:**
1. Help → Check for Updates
2. Observe dialog
**Pass:** Dialog shows version info and "Open Releases Page" button
**Fail:** Dialog shows "Download & Install" (v1.1.x behavior), app attempts download, error dialog
**[ ] Status:**

### SC-15: Auto-Update Check (Background)
**Setup:** Windows 11 with OpenReader installed, "Automatically Check for Updates" enabled
**Steps:**
1. Launch app
2. Observe status bar
**Pass:** If update available, status bar briefly shows message. No dialog or download.
**Fail:** App attempts to download anything, shows unexpected dialogs
**[ ] Status:**

### SC-16: Rollback (MSIX)
**Setup:** Windows 11 with OpenReader v1.2.0 installed
**Steps:**
1. Settings → Apps → Installed apps → OpenReader → Advanced options → Reset or uninstall
2. Verify rollback behavior
**Pass:** Windows allows reset or clean uninstall
**Fail:** App cannot be recovered to working state
**[ ] Status:**

## Cross-Platform Validation

### macOS (Source Build)
- [ ] `python main.py` launches without import errors
- [ ] Window title shows "OpenReader"
- [ ] About dialog shows "OpenReader" and correct version
- [ ] Help → Check for Updates shows "Open Releases Page"

## Code Quality

- [ ] `python -m py_compile main.py` passes
- [ ] No runtime import errors on launch
- [ ] All state references to old app name removed (QSettings, IPC, etc.)

## Release Artifacts

- [ ] `OpenReader.msix` produced by CI
- [ ] `OpenReader-Setup.exe` produced by CI (legacy)
- [ ] `OpenReader-Windows.zip` produced by CI
- [ ] `OpenReader-macOS-Apple-Silicon.zip` produced by CI
- [ ] `OpenReader-macOS-Intel.zip` produced by CI
- [ ] Release notes generated correctly

## Blockers

- [ ] **MSIX signing** — unsigned MSIX requires Developer Mode. Either Store submission or code-signing certificate needed for production.
- [ ] **Store submission** — not yet submitted to Microsoft Store.
- [ ] **App Installer hosting** — `downloads.openreader.app` domain + HTTPS hosting not yet configured.
- [ ] **Winget submission** — not yet submitted to winget-pkgs.
- [ ] **Icon assets** — placeholder MSIX icons should be replaced with proper OpenReader branding.

## Pass/Fail Summary

| Scenario | Result | Notes |
|----------|--------|-------|
| SC-01: Clean MSIX install | ⬜ | |
| SC-02: Store install | ⬜ | Blocked by Store submission |
| SC-03: Upgrade from v1.1.10 | ⬜ | |
| SC-04: Upgrade from v1.1.11 | ⬜ | |
| SC-05: MSIX upgrade | ⬜ | |
| SC-06: Uninstall | ⬜ | |
| SC-07: Reinstall | ⬜ | |
| SC-08: Settings persistence | ⬜ | |
| SC-09: Recent files | ⬜ | |
| SC-10: Theme persistence | ⬜ | |
| SC-11: Session restore | ⬜ | |
| SC-12: PDF association (MSIX) | ⬜ | |
| SC-13: PDF association (Setup) | ⬜ | |
| SC-14: Check for Updates (safe) | ⬜ | |
| SC-15: Auto-update check | ⬜ | |
| SC-16: Rollback | ⬜ | |

**Overall: ⬜ NOT READY** — must pass SC-01, SC-06, SC-08, SC-09, SC-10, SC-11, SC-14, SC-15 at minimum for beta. SC-02 blocked by Store submission.

## Next Steps

1. Build MSIX on Windows CI → test SC-01
2. Run upgrade tests (SC-03, SC-04) on Windows VM
3. Procure code-signing or prioritize Store submission
4. Create proper OpenReader icon assets for MSIX
5. Fix any failures
6. Re-test before tagging `v1.2.0-beta.1`
