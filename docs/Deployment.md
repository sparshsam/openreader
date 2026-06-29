# Deployment

> CI/CD, release workflow, and distribution channels for OpenReader.

---

## Distribution Channels

| Channel | Status | Updates |
|---------|--------|---------|
| **Microsoft Store** | Live (`9MXDVW2645LL`) | Automatic through Store |
| **GitHub Releases** (MSIX) | Active | Manual (Help → Check for Updates) |
| **GitHub Releases** (Setup.exe) | Legacy | Manual recovery only |
| **GitHub Releases** (Portable ZIP) | Active | Manual download |
| **Winget** | Future | `SparshSam.OpenReader` |

---

## Release Workflow

Tagging triggers the [release workflow](.github/workflows/release.yml):

```bash
git tag vMAJOR.MINOR.PATCH
git push origin vMAJOR.MINOR.PATCH
```

The CI pipeline:

1. Runs full test suite and security audit
2. Builds Python package with PyInstaller (`--onedir` mode)
3. Creates MSIX package with Windows App Installer support
4. Builds Inno Setup installer
5. Packages macOS builds (experimental)
6. Uploads all assets to a GitHub Release
7. Injects version from tag via `scripts/inject_version.py`

### Release Assets

| Asset | Format | Platform |
|-------|--------|----------|
| `OpenReader.msix` | MSIX | Windows 10/11 |
| `OpenReader-Setup.exe` | Inno Setup | Windows (legacy) |
| `OpenReader-Windows.zip` | Portable ZIP | Windows |
| `OpenReader-macOS-Apple-Silicon.zip` | DMG/ZIP | macOS |
| `OpenReader-macOS-Intel.zip` | DMG/ZIP | macOS |

### MSIX Version Mapping

| Tag Format | MSIX Version |
|-----------|--------------|
| `v1.2.3` | `1.2.3.0` |
| `v1.2.3-beta.1` | `1.2.3.0` |
| `v1.0.0-rc.1` | `1.0.0.0` |

---

## CI Pipelines

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| `ci.yml` | PR + push to `main` | Tests, linting, security scan |
| `build-windows.yml` | PR + push to `main` | Windows build validation |
| `build-macos.yml` | PR + push to `main` | macOS build validation (experimental) |
| `release.yml` | Tag push | Full release with all assets |
| `security.yml` | Scheduled + push | Bandit, pip-audit, Dependabot |
| `deploy-site.yml` | Push touching `site/` | Deploys landing page to Cloudflare Pages |

### Required Checks

Before merging to `main`:

- All CI workflows must pass
- `Build Windows Release Asset` status check is enforced
- PR approval required (branch protection)

---

## Build Locally

See [Development](Development.md) for local build instructions.

## Platform Support

| Platform | Support Level | Notes |
|----------|--------------|-------|
| Windows 10/11 | Full | Primary target, MSIX + installer |
| macOS Apple Silicon | Experimental | Source build, no signed package |
| macOS Intel | Experimental | Source build, no signed package |
| Linux | Unsupported | Not planned |
