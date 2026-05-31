#!/usr/bin/env python3
"""Inject version string into main.py at build time.

Usage: python scripts/inject_version.py <version>
Example: python scripts/inject_version.py 0.1.5
"""
import re
import sys

def main():
    if len(sys.argv) < 2:
        version = "0.0.0-dev"
    else:
        version = sys.argv[1]

    with open("main.py", encoding="utf-8") as f:
        src = f.read()

    src = re.sub(
        r'__version__ = "[^"]+"',
        f'__version__ = "{version}"',
        src,
    )

    with open("main.py", "w", encoding="utf-8") as f:
        f.write(src)

    print(f"Injected version: {version}")

if __name__ == "__main__":
    main()
