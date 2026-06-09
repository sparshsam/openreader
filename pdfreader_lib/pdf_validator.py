"""PDF validation and safety utilities.

Isolates all PDF security checks, path validation, and document integrity
verification so they can be tested independently of the UI layer.
"""

from pathlib import Path

import fitz


class PdfSafetyError(Exception):
    """Raised when a PDF fails a safety or validation check."""
    pass


def validate_pdf_path(file_name: str, max_size_bytes: int = 500 * 1024 * 1024) -> Path:
    """Validate that *file_name* points to a real, non-empty PDF under the size limit.

    Returns the resolved ``Path`` on success.
    Raises ``PdfSafetyError`` with a user-facing message on any failure.
    """
    path = Path(file_name).expanduser()
    if not path.exists() or not path.is_file():
        raise PdfSafetyError("The selected file does not exist.")
    if path.suffix.lower() != ".pdf":
        raise PdfSafetyError("Only .pdf files are supported.")
    size = path.stat().st_size
    if size <= 0:
        raise PdfSafetyError("The selected file is empty.")
    if size > max_size_bytes:
        max_mb = max_size_bytes // (1024 * 1024)
        raise PdfSafetyError(f"The selected PDF is larger than the {max_mb} MB safety limit.")
    with path.open("rb") as f:
        header = f.read(1024)
    if b"%PDF-" not in header:
        raise PdfSafetyError("The selected file does not look like a valid PDF.")
    return path


def validate_document_pages(document: fitz.Document, max_page_dimension: int = 14400) -> None:
    """Verify every page in *document* has sensible dimensions.

    Raises ``PdfSafetyError`` if any page has zero or impossibly-large bounds.
    """
    for page_index in range(document.page_count):
        page = document.load_page(page_index)
        if (
            page.rect.width <= 0
            or page.rect.height <= 0
            or page.rect.width > max_page_dimension
            or page.rect.height > max_page_dimension
        ):
            raise PdfSafetyError(
                f"Page {page_index + 1} is outside the supported page size limits."
            )


def safe_open_pdf(file_name: str, max_size_bytes: int = 500 * 1024 * 1024,
                  max_page_dimension: int = 14400) -> fitz.Document:
    """Open and validate a PDF in one call.

    Validates the path, opens the document, checks for empty pages, and
    validates page dimensions.  Returns the opened ``fitz.Document``.
    Raised ``PdfSafetyError`` on any failure (caller must not close on error).
    """
    path = validate_pdf_path(file_name, max_size_bytes=max_size_bytes)
    document = None
    try:
        document = fitz.open(str(path))
        if document.page_count == 0:
            raise PdfSafetyError("The PDF does not contain any pages.")
        validate_document_pages(document, max_page_dimension=max_page_dimension)
        return document
    except Exception:
        if document is not None:
            document.close()
        raise
