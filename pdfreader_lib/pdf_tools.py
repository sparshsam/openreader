"""PDF manipulation tools — merge, split, compress.

All functions are pure (no Qt dependency) and accept a fitz.Document plus
the validation helpers they need.  The caller (main window) is responsible
for any UI — file dialogs, status bar messages, progress indication.
"""

from pathlib import Path

import fitz

from pdfreader_lib.pdf_validator import PdfSafetyError, safe_open_pdf


def merge_pdfs(file_names: list[str], output_path: str) -> None:
    """Merge multiple PDFs into a single file at *output_path*.

    Each file is validated before merging.  Raises on failure.
    """
    merged = fitz.open()
    opened_docs: list[fitz.Document] = []
    try:
        for file_name in file_names:
            source = safe_open_pdf(file_name)
            opened_docs.append(source)
            merged.insert_pdf(source)
        merged.save(
            output_path,
            garbage=4,
            deflate=True,
            deflate_images=True,
            deflate_fonts=True,
            use_objstms=1,
            compression_effort=9,
        )
    finally:
        for source in opened_docs:
            source.close()
        merged.close()


def split_every_page(document: fitz.Document, current_path: str,
                     output_dir: Path, max_split_pages: int = 1000) -> list[Path]:
    """Split *document* into one PDF per page into *output_dir*.

    Returns the list of saved paths.
    """
    if document.page_count > max_split_pages:
        raise PdfSafetyError(
            f"Splitting every page is limited to {max_split_pages} pages at a time."
        )
    base_name = Path(current_path).stem
    saved: list[Path] = []
    for page_index in range(document.page_count):
        target = output_dir / f"{base_name}_page_{page_index + 1}.pdf"
        new_doc = fitz.open()
        try:
            new_doc.insert_pdf(document, from_page=page_index, to_page=page_index)
            new_doc.save(target, garbage=4, deflate=True, use_objstms=1)
        finally:
            new_doc.close()
        saved.append(target)
    return saved


def extract_pages(document: fitz.Document, current_path: str,
                  output_dir: Path, pages: list[int]) -> Path:
    """Extract specific *pages* (0-indexed list) from *document* into a new PDF.

    Returns the saved path.
    """
    base_name = Path(current_path).stem
    suffix = "_".join(str(page + 1) for page in pages[:6])
    if len(pages) > 6:
        suffix += "_etc"
    target = output_dir / f"{base_name}_pages_{suffix}.pdf"
    new_doc = fitz.open()
    try:
        for page_index in pages:
            new_doc.insert_pdf(document, from_page=page_index, to_page=page_index)
        new_doc.save(target, garbage=4, deflate=True, use_objstms=1)
    finally:
        new_doc.close()
    return target


def parse_page_ranges(text: str, page_count: int) -> list[int]:
    """Parse a user-supplied page-range string (e.g. ``\"1-3,5\"``) into a
    sorted, deduplicated list of 0-indexed page numbers.

    Raises ``ValueError`` for invalid or out-of-range pages.
    """
    pages: list[int] = []
    for chunk in text.replace(" ", "").split(","):
        if not chunk:
            continue
        if "-" in chunk:
            start_text, end_text = chunk.split("-", 1)
            start = int(start_text)
            end = int(end_text)
            if start > end:
                start, end = end, start
            pages.extend(range(start - 1, end))
        else:
            pages.append(int(chunk) - 1)

    unique_pages: list[int] = []
    seen: set[int] = set()
    for page in pages:
        if page < 0 or page >= page_count:
            raise ValueError(f"Page {page + 1} is outside the valid range 1-{page_count}.")
        if page not in seen:
            seen.add(page)
            unique_pages.append(page)
    if not unique_pages:
        raise ValueError("No valid pages were selected.")
    return unique_pages


def compress_pdf(source_path: str, output_path: str) -> tuple[int, int]:
    """Re-save *source_path* with maximum compression to *output_path*.

    Returns ``(original_bytes, compressed_bytes)``.
    """
    source = safe_open_pdf(source_path)
    try:
        source.save(
            output_path,
            garbage=4,
            clean=True,
            deflate=True,
            deflate_images=True,
            deflate_fonts=True,
            use_objstms=1,
            compression_effort=9,
        )
    finally:
        source.close()

    original_size = Path(source_path).stat().st_size
    compressed_size = Path(output_path).stat().st_size
    return original_size, compressed_size
