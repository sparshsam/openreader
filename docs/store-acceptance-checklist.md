# Post-Release Store Acceptance Checklist

The MSIX package cannot be produced or signed locally: production signing uses
the Microsoft Store identity (no self-procured code-signing certificate), and
the Windows SDK `MakeAppx.exe`/Store signing pipeline runs in Partner Center.
This checklist covers the Store-specific validation that must happen **after**
the `v1.2.7` MSIX is submitted and signed by the Store.

Frozen identity (do not alter):
| Field | Value |
|-------|-------|
| Identity Name | `SparshSam.OpenReader` |
| Publisher | `CN=E6186421-BF8A-47E0-A89C-0F513DFF91C0` |
| Package Family Name | `SparshSam.OpenReader_yh0byntbzd2qw` |
| Store ID | `9MXDVW2645LL` |

## On a clean Windows machine, after Store install

- [ ] Install from the Microsoft Store; app launches and reports **v1.2.7** (Help → About).
- [ ] `Get-AppxPackage` shows the package with the frozen identity and PFN.
- [ ] The process runs with a package identity — install-source detection
      reports the Store channel (no GitHub request on launch; Help → Check for
      Updates shows the Store-managed dialog with **Open Microsoft Store**).

### File association (v1.2.5)
- [ ] Right-click a `.pdf` → **Open with** lists **OpenReader** with the correct icon.
- [ ] **Settings → Apps → Default apps** lists OpenReader once, named `OpenReader`,
      file-type description "PDF Document".
- [ ] Double-clicking a `.pdf` opens it in OpenReader.
- [ ] With OpenReader running, opening a second `.pdf` routes to the existing
      instance as a new tab.
- [ ] Paths with spaces / Unicode / parentheses / long names open correctly.

### Default reader (v1.2.6)
- [ ] **File → Settings → Files / Default Apps** reads the current handler from
      `UserChoice` and shows "OpenReader is the default PDF reader" — **no**
      recovery warning.
- [ ] Setting another app as default then reopening Settings shows that app's
      name, and the recovery message appears only if OpenReader's association
      is genuinely missing.
- [ ] First-launch prompt: **Set as default** opens Default Apps; **Do not ask
      again** persists across launches.

### Updates (v1.2.7)
- [ ] Store install never queries `api.github.com` (silent launch check and
      Help → Check for Updates both use the Store channel).
- [ ] **Open Microsoft Store** button opens the Store listing.

## Sideloaded MSIX (developer mode, for pre-submission testing)

- [ ] `Add-AppxPackage` the unsigned MSIX from a GitHub test build succeeds in
      Developer Mode.
- [ ] Because sideloaded and Store packages both run with an AppX identity,
      install-source detection reports the same Store channel — expected.

## Out of scope

- Do not weaken or replace the frozen identity.
- Do not publish a GitHub Release or submit to Partner Center without explicit
  instruction.
