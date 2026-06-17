# Security

OpenReader is designed to process PDFs locally. It does not upload files or call network services.

If you discover a security issue, please open a GitHub issue with a clear description and reproduction steps. Avoid sharing private or sensitive PDF files in public issues.

## Supported Versions

Only the latest release is supported for security fixes.

## Handling Untrusted PDFs

OpenReader performs lightweight validation and resource checks before opening PDFs, but it is not a hardened sandbox. PDFs from unknown sources may still exercise vulnerabilities in PDF parsing libraries or stress local system resources.

For sensitive environments, open untrusted PDFs in an OS-level sandbox, virtual machine, or disposable user profile.
