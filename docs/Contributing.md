# Contributing

> Guide for contributors to OpenReader.

---

## Before You Start

Please read these documents before opening issues or pull requests:

- [Code of Conduct](../CODE_OF_CONDUCT.md)
- [Security Policy](../SECURITY.md)

## Areas We Welcome Contributions

- Bug fixes and reliability improvements
- UI polish and accessibility
- PDF parsing edge cases and format support
- MCP server tool improvements
- Documentation and translation
- Platform compatibility (especially macOS)

## Areas We Don't Accept Contributions

- Cloud features, accounts, sync, or telemetry
- Plugin systems or extension APIs
- AI features that upload documents to third parties
- Breaking the local-first or privacy-by-design model

## Pull Request Process

1. Branch from `main`. Use prefixes: `fix/`, `feat/`, `docs/`, `refactor/`.
2. One logical change per PR.
3. Run lint and tests before creating the PR.
4. All CI checks must pass before merge.
5. No direct pushes to `main` — PRs only.

## Development Setup

See [Development](Development.md) for build and run instructions.

## Architecture

See [Architecture](Architecture.md) for the system design overview.

## Design Playbooks

Design and architectural decisions should reference:

- [Product Architecture Playbook](playbooks/PRODUCT_ARCHITECTURE_PLAYBOOK.md)
- [Design Playbook](playbooks/DESIGN_PLAYBOOK.md)
- [Kovina Repository Standard](playbooks/KOVINA_REPOSITORY_STANDARD.md)
