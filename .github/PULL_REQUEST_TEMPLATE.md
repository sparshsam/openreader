# Pull Request

## Description

<!-- A clear and concise description of the change. -->

Fixes #<!-- issue number, if applicable -->

## Type of Change

- [ ] Bug fix
- [ ] New feature
- [ ] Documentation / governance
- [ ] CI / build / packaging
- [ ] Refactor (no functional change)

## Checklist

- [ ] I have read [CONTRIBUTING.md](CONTRIBUTING.md).
- [ ] Existing tests pass: `python -m pytest tests/ -v`
- [ ] `python -m compileall . -q` passes
- [ ] No new Bandit warnings: `bandit -q -r main.py tools/`
- [ ] CHANGELOG.md updated if user-facing
