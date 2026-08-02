#!/usr/bin/env python3
"""Inject version string into OpenReader's version sources at build time.

Writes the version into every canonical source so the app, the MCP package,
and the MSIX packaging stay in lockstep:

  - main.py                                            __version__ = "<version>"
  - packages/mcp-server/pyproject.toml                 version = "<version>"
  - packages/mcp-server/src/openreader_mcp.egg-info/PKG-INFO
                                                       Version: <version>
  - packaging/msix/AppxManifest.xml                    Identity Version="<version>.0"
  - packaging/msix/AppInstaller.xml                    MainPackage Version="<version>.0"

MSIX manifests require a 4-part version (x.y.z.0), so they are rewritten
only when <version> is strict semver (digits only). Dev/test builds such
as 0.0.0-dev or branch-test still bump main.py and the MCP package but
leave the MSIX manifests alone — CI patches those from the git tag.

Usage: python scripts/inject_version.py <version>
Example: python scripts/inject_version.py 1.2.5
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Canonical sources updated on every build, whatever the version string.
TARGETS = [
    (
        "main.py",
        r'__version__ = "[^"]+"',
        lambda v: f'__version__ = "{v}"',
    ),
    (
        "packages/mcp-server/pyproject.toml",
        r'^version = "[^"]+"',
        lambda v: f'version = "{v}"',
    ),
    (
        "packages/mcp-server/src/openreader_mcp.egg-info/PKG-INFO",
        r"^Version: [^\n]+",
        lambda v: f"Version: {v}",
    ),
]

# MSIX manifests: strict semver only, mapped to a 4-part version (x.y.z.0).
# Patterns are scoped to their element so MinVersion/MaxVersionTested in
# TargetDeviceFamily (and the AppInstaller schema Version) are never touched.
SEMVER = re.compile(r"^\d+\.\d+\.\d+$")
MSIX_TARGETS = [
    (
        "packaging/msix/AppxManifest.xml",
        r'(<Identity\b[^>]*?Version=")[^"]+(")',
        lambda v: rf"\g<1>{v}.0\g<2>",
    ),
    (
        "packaging/msix/AppInstaller.xml",
        r'(<MainPackage\b[^>]*?Version=")[^"]+(")',
        lambda v: rf"\g<1>{v}.0\g<2>",
    ),
]


def _rewrite(path: str, pattern: str, replacement: str) -> bool:
    full = ROOT / path
    if not full.exists():
        print(f"  skip  (missing)  {path}")
        return False
    text = full.read_text(encoding="utf-8")
    new_text, count = re.subn(
        pattern, replacement, text, count=1, flags=re.MULTILINE
    )
    if count == 0:
        print(f"  skip  (no match) {path}")
        return False
    full.write_text(new_text, encoding="utf-8")
    print(f"  ok    {path}")
    return True


def main():
    version = sys.argv[1] if len(sys.argv) > 1 else "0.0.0-dev"
    strict = bool(SEMVER.match(version))

    print(f"Injecting version: {version}")
    for path, pattern, make_repl in TARGETS:
        _rewrite(path, pattern, make_repl(version))

    if strict:
        for path, pattern, make_repl in MSIX_TARGETS:
            _rewrite(path, pattern, make_repl(version))
    else:
        print("  skip  MSIX manifests (version is not strict semver)")


if __name__ == "__main__":
    main()
