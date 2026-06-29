# Testing

> Test suite, coverage areas, and quality gates for OpenReader.

---

## Running Tests

```bash
# Full test suite
python -m pytest tests/ -v

# Specific test file
python -m pytest tests/test_mcp_server.py -v

# Quick syntax check
python -m py_compile main.py tools/create_icon.py scripts/inject_version.py
```

---

## Test Coverage

| Area | File | Tests |
|------|------|-------|
| Reliability & safety | `tests/test_reliability.py` | 20 tests — version format, asset naming, safety limits, shortcut consistency |
| Security | `tests/test_security.py` | 12 tests — file validation, path handling, temp file security, subprocess safety |
| MCP Server | `tests/test_mcp_server.py` | 43 tests — tool registration, validation, output shape, error handling |
| Updater | `tests/test_updater.py` | 31 tests (headless-skipped) — version parsing, asset selection, metadata |
| Asset flow | `tools/test_updater_asset_flow.py` | 16 checks — release asset consistency |

---

## Quality Gates

Every push and PR must pass:

| Gate | Check |
|------|-------|
| **Compile** | `python -m py_compile` on all entry points |
| **Tests** | Full pytest suite |
| **Security** | Bandit (production code, 0 issues) |
| **Dependencies** | pip-audit (0 known vulnerabilities) |
| **Build** | Windows MSIX build validation (CI) |

These are enforced in CI via `.github/workflows/ci.yml` and `.github/workflows/security.yml`.

---

## Security Audit

The security workflow runs Bandit and pip-audit on every push:

- Bandit configured in `.bandit` (excludes test directories)
- pip-audit checks all pinned dependencies
- Both must pass before merging
