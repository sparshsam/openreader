# Pull Request

## Description

<!-- A clear and concise description of the change. -->

Fixes #<!-- issue number, if applicable -->

## Type of Change

- [ ] Bug fix (non-breaking fix)
- [ ] New feature (non-breaking addition)
- [ ] Breaking change (fix or feature that breaks existing behaviour)
- [ ] Documentation / governance
- [ ] CI / build / packaging
- [ ] Refactor (no functional change)

## Checklist

- [ ] I have read [CONTRIBUTING.md](CONTRIBUTING.md).
- [ ] The app launches and opens a PDF without errors.
- [ ] Existing tests pass: `python -m pytest tests/ -v` (if tests/ exists).
- [ ] `python -m compileall . -q` passes (Python compile-check).
- [ ] No new warnings from Bandit (run `bandit -q -r main.py tools/`).
- [ ] I have not introduced network-dependent features (PDFs stay local).
- [ ] CHANGELOG.md is updated if this change is user-facing.

## Screenshots (if UI change)

<!-- Drag-and-drop images here. -->

## Additional Notes

<!-- Anything the reviewer should know. -->
