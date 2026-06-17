# Versioning

## Scheme

OpenReader follows [Semantic Versioning 2.0](https://semver.org/):

- **MAJOR** — breaking changes to the application (e.g., removed features, incompatible save format changes, dropped platform support).
- **MINOR** — backward-compatible additions (new features, new tools, new platform support).
- **PATCH** — bug fixes, security updates, documentation improvements, release engineering changes.

## Current Version

The current version is tracked in the `__version__` variable in `main.py`.

- **Source builds** — use a `-dev` suffix (e.g., `1.2.0-beta.2-dev`).
- **Packaged releases** — the version is injected from the Git tag during the release workflow (see `scripts/inject_version.py`).

## Tag Format

Release tags must follow the format:

```
vMAJOR.MINOR.PATCH[-prerelease.N]
```

Examples: `v1.2.0-beta.1`, `v1.2.0`, `v1.2.1`.

The leading `v` is stripped at build time, so tag `v1.2.0` produces an application that reports version `1.2.0`.

## MSIX Versioning

MSIX packages use a 4-part version: `major.minor.patch.build`.

| Git Tag | MSIX Version |
|---------|--------------|
| `v1.2.0-beta.1` | `1.2.0.0` |
| `v1.2.0-beta.2` | `1.2.0.1` |
| `v1.2.0-rc.1` | `1.2.0.2` |
| `v1.2.0` | `1.2.0.0` |
| `v1.2.1` | `1.2.1.0` |

The build number is the prerelease index minus 1 (beta.1 → 0, beta.2 → 1, etc.).
Stable releases use build 0. The CI workflow automatically extracts the correct
MSIX version from the Git tag.

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history.

## Release Process

See [RELEASE.md](RELEASE.md) for the complete release workflow, including:

1. Tag creation and push
2. GitHub Actions build pipeline
3. Canonical release asset naming
4. Validation checklist

## Pre-Release Versions

Pre-release versions use the suffix format `-beta.N` or `-rc.N`:

- `1.2.0-beta.1` — beta testing build
- `1.2.0-rc.1` — release candidate

Pre-release tags use conventional naming: `v1.2.0-beta.1`.

## When to Release

- **Backward-compatible features** (new PDF tool, new search capability): MINOR.
- **Bug fixes, security patches, release engineering changes**: PATCH.
- **Breaking changes** (removed feature, platform dropped): MAJOR, with migration documentation.

The project does not release on a fixed schedule. Releases happen when meaningful change has accumulated or a security fix is needed.
