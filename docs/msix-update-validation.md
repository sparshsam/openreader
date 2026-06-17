# MSIX Update Validation Guide

**Purpose:** Validate that MSIX updates work correctly.

**Test versions:**
- v1.2.0-beta.1 (MSIX 1.2.0.0) — base install
- v1.2.0-beta.2 (MSIX 1.2.0.1) — update target

## Prerequisites

- Windows 10 1809+ or Windows 11 VM (clean or with known state)
- `OpenReader.msix` for v1.2.0-beta.1
- `OpenReader.msix` for v1.2.0-beta.2
- Enable Developer Mode (Settings → Privacy & security → For developers)
- Administrator access for legacy Setup.exe tests

## Test Scenarios

### SC-MSIX-01: Clean Install of v1.2.0-beta.1

**Setup:** Clean Windows VM, no previous OpenReader/PDFReader installation.

**Steps:**
1. Download `OpenReader.msix` (v1.2.0-beta.1)
2. Double-click the MSIX file
3. Observe installation dialog
4. Launch OpenReader from Start Menu
5. Verify Help → About shows version `1.2.0-beta.1-dev`

**Expected:** Installation completes without errors. App launches. Version is correct.
**Pass/Fail:** [ ]

### SC-MSIX-02: Configure Application State

**Setup:** After SC-MSIX-01, app is running.

**Steps:**
1. Open a PDF file
2. Set theme to Dark Mode (View → Theme → Dark)
3. Set zoom to 150%
4. Navigate to page 5
5. Resize window
6. Open 2 more PDFs (3 total)
7. Open Help → About and note the version
8. Close app
9. Reopen app and respond to session restore prompt
10. Verify: all 3 PDFs restored, page positions, Dark Mode, zoom, window size

**Expected:** All settings preserved after restart.
**Pass/Fail:** [ ]

### SC-MSIX-03: Update from v1.2.0-beta.1 to v1.2.0-beta.2

**Setup:** After SC-MSIX-02, v1.2.0-beta.1 is installed and configured.

**Steps:**
1. Download `OpenReader.msix` (v1.2.0-beta.2)
2. Double-click the MSIX file (while app is running or closed — test both)
3. Observe installation completes without error
4. Launch OpenReader
5. Verify Help → About shows version `1.2.0-beta.2-dev`

**Expected:** Update installs over existing. Version is updated. No duplicate app entries appear in Start Menu or Apps list.
**Pass/Fail:** [ ]

### SC-MSIX-04: Settings Persistence After Update

**Setup:** After SC-MSIX-03, app is running v1.2.0-beta.2.

**Steps:**
1. Verify Dark Mode theme is still active (from SC-MSIX-02)
2. Verify recent files list shows previously opened PDFs
3. Close app and reopen
4. Verify session restore works correctly
5. Verify all 3 PDFs restore to their correct pages

**Expected:** All user settings, recent files, and session state persist through the MSIX update.
**Pass/Fail:** [ ]

### SC-MSIX-05: PDF File Association After Update

**Setup:** After SC-MSIX-03, v1.2.0-beta.2 is installed.

**Steps:**
1. Right-click a PDF file
2. Verify "Open with → OpenReader" is available
3. Set OpenReader as default PDF handler
4. Double-click a PDF file
5. Verify it opens in OpenReader

**Expected:** File association is preserved or restored after update.
**Pass/Fail:** [ ]

### SC-MSIX-06: Uninstall

**Setup:** After SC-MSIX-03, v1.2.0-beta.2 is installed.

**Steps:**
1. Settings → Apps → Installed apps → OpenReader → Uninstall
2. Confirm uninstall
3. Verify app no longer appears in Start Menu
4. Verify app no longer appears in Apps list

**Expected:** Clean uninstall. No leftover files in install directory.
**Pass/Fail:** [ ]

### SC-MSIX-07: Reinstall

**Setup:** After SC-MSIX-06, OpenReader is fully uninstalled.

**Steps:**
1. Double-click `OpenReader.msix` (v1.2.0-beta.2)
2. Verify installation completes
3. Launch app
4. Verify it works correctly

**Expected:** Clean install succeeds. App launches.
**Pass/Fail:** [ ]

### SC-MSIX-08: Rollback

**Setup:** v1.2.0-beta.2 is installed.

**Steps:**
1. Uninstall v1.2.0-beta.2 (Settings → Apps → OpenReader → Uninstall)
2. Install v1.2.0-beta.1 MSIX
3. Launch app
4. Verify Help → About shows version `1.2.0-beta.1-dev`

**Expected:** Rollback to older version works. App functions correctly.
**Pass/Fail:** [ ]

### SC-MSIX-09: Side-by-Side MSIX and Setup.exe

**Setup:** Clean Windows VM.

**Steps:**
1. Install `OpenReader-Setup.exe` (v1.2.0-beta.1) as Administrator
2. Launch Setup.exe version, note the install path
3. Install `OpenReader.msix` (v1.2.0-beta.1) — this should be separate
4. Verify both versions appear in Start Menu (should be one, or two distinct)
5. Launch the MSIX version

**Expected:** MSIX and Setup.exe installs are independent. No conflicts. If both exist, they are side-by-side.
**Pass/Fail:** [ ]

### SC-MSIX-10: Check for Updates (Safe Detection)

**Setup:** v1.2.0-beta.1 is installed with internet access.

**Steps:**
1. Help → Check for Updates
2. Observe the dialog

**Expected:** Dialog shows version info and "Open Releases Page" button.
**Should NOT show:** "Download & Install" button, any download progress, any installer launch.
**Pass/Fail:** [ ]

## Success Criteria for v1.2.0 Stable

The following criteria must all pass before marking v1.2.0 as production-ready:

### Identity & Packaging

- [ ] Identity Name remains `SparshSam.OpenReader` across all builds
- [ ] Publisher remains `CN=E6186421-BF8A-47E0-A89C-0F513DFF91C0`
- [ ] Package Family Name is `SparshSam.OpenReader_yh0byntbzd2qw`
- [ ] MSIX version is valid 4-part integer version
- [ ] No duplicate application entries in Start Menu or Apps list
- [ ] App identity unchanged between beta.1 and beta.2

### Install & Update

- [ ] SC-MSIX-01: Clean install passes
- [ ] SC-MSIX-03: Update from beta.1 to beta.2 passes
- [ ] SC-MSIX-06: Uninstall passes
- [ ] SC-MSIX-07: Reinstall passes
- [ ] SC-MSIX-08: Rollback passes

### Settings & State

- [ ] SC-MSIX-02: Application state configuration works
- [ ] SC-MSIX-04: Settings persist through update
- [ ] Dark mode, zoom, window position, recent files all survive update
- [ ] Session restore survives update

### File Associations

- [ ] SC-MSIX-05: PDF file association works after update
- [ ] PDF opens correctly from file explorer

### Update Detection

- [ ] SC-MSIX-10: Check for Updates shows "Open Releases Page"
- [ ] No download/install initiated by the app
- [ ] Status bar shows update notification on launch (if newer version exists)

### No Regressions

- [ ] Open, read, and navigate PDFs
- [ ] Search (keyword + library)
- [ ] Merge, split, compress, extract
- [ ] Annotations (highlight, underline, sticky notes)
- [ ] Dark/Light theme toggle
- [ ] Session restore
- [ ] Help → About shows correct version

## Remaining Blockers Before v1.2.0 Stable

| Blocker | Priority | Status |
|---------|----------|--------|
| MSIX signing (Store or third-party cert) | Critical | Open |
| Microsoft Store submission | Critical | Open |
| App Installer hosting infrastructure | High | Open |
| Winget manifest submission | Medium | Open |
| Replace placeholder MSIX icons with OpenReader branding | Low | Open |
| End-to-end MSIX update validation on Windows 10/11 | Critical | **Active** |

## MSIX Update Behavior Summary

| Aspect | Expected Behavior | Status |
|--------|------------------|--------|
| Install MSIX over existing | Upgrade in-place, no duplicate | To test |
| Settings persistence | All settings survive upgrade | To test |
| File association | Preserved through upgrade | To test |
| App identity | Unchanged (frozen Store values) | ✅ Verified |
| Self-update from app | Never occurs | ✅ Enforced |
| Windows-managed updates | Via Store or App Installer (future) | 🔜 Future |
