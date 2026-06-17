"""
OpenReader — PDF Version Comparison

Extract text from two PDFs, align by page, diff with difflib,
and produce structured diff data for the UI.
"""

import difflib
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class DiffSegment:
    """One chunk of text in a diff display."""
    text: str
    tag: str  # "equal", "insert", "delete", "replace_old", "replace_new"


@dataclass
class DiffPage:
    page_a: int
    page_b: int
    segments_a: list[DiffSegment] = field(default_factory=list)
    segments_b: list[DiffSegment] = field(default_factory=list)
    has_changes: bool = False


@dataclass
class DiffResult:
    file_a: str
    file_b: str
    pages: list[DiffPage] = field(default_factory=list)
    total_changes: int = 0


# ---------------------------------------------------------------------------
# Page-level alignment
# ---------------------------------------------------------------------------

def _extract_pages(path: str) -> list[str]:
    """Extract text from every page of a PDF. Returns list of (page_number, text)."""
    import fitz
    doc = fitz.open(path)
    pages = []
    for i in range(doc.page_count):
        page = doc.load_page(i)
        text = page.get_text("text")
        pages.append(text)
    doc.close()
    return pages


def _split_into_lines(text: str) -> list[str]:
    """Split text into meaningful lines for diffing."""
    # Normalize whitespace first
    lines = text.splitlines()
    # Remove empty lines at edges
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return lines


# ---------------------------------------------------------------------------
# Diff engine
# ---------------------------------------------------------------------------

def compare_pdfs(path_a: str, path_b: str) -> DiffResult:
    """
    Compare two PDFs page by page. Aligns pages sequentially
    (page 1 ↔ page 1, page 2 ↔ page 2, etc.).
    """
    pages_a = _extract_pages(path_a)
    pages_b = _extract_pages(path_b)

    result = DiffResult(
        file_a=str(Path(path_a).resolve()),
        file_b=str(Path(path_b).resolve()),
    )
    max_pages = max(len(pages_a), len(pages_b))
    total_changes = 0

    for i in range(max_pages):
        page_a = pages_a[i] if i < len(pages_a) else ""
        page_b = pages_b[i] if i < len(pages_b) else ""

        lines_a = _split_into_lines(page_a)
        lines_b = _split_into_lines(page_b)

        matcher = difflib.SequenceMatcher(None, lines_a, lines_b)
        segments_a: list[DiffSegment] = []
        segments_b: list[DiffSegment] = []
        page_has_changes = False

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "equal":
                segment_text = "\n".join(lines_a[i1:i2])
                segments_a.append(DiffSegment(text=segment_text, tag="equal"))
                segments_b.append(DiffSegment(text=segment_text, tag="equal"))
            elif tag == "delete":
                segment_text = "\n".join(lines_a[i1:i2])
                segments_a.append(DiffSegment(text=segment_text, tag="delete"))
                segments_b.append(DiffSegment(text="", tag="equal"))
                page_has_changes = True
                total_changes += i2 - i1
            elif tag == "insert":
                segment_text = "\n".join(lines_b[j1:j2])
                segments_a.append(DiffSegment(text="", tag="equal"))
                segments_b.append(DiffSegment(text=segment_text, tag="insert"))
                page_has_changes = True
                total_changes += j2 - j1
            elif tag == "replace":
                old_text = "\n".join(lines_a[i1:i2])
                new_text = "\n".join(lines_b[j1:j2])
                segments_a.append(DiffSegment(text=old_text, tag="replace_old"))
                segments_b.append(DiffSegment(text=new_text, tag="replace_new"))
                page_has_changes = True
                total_changes += max(i2 - i1, j2 - j1)

        dp = DiffPage(
            page_a=i + 1,
            page_b=i + 1,
            segments_a=segments_a,
            segments_b=segments_b,
            has_changes=page_has_changes,
        )
        result.pages.append(dp)

    result.total_changes = total_changes
    return result


def compare_texts(text_a: str, text_b: str, context_lines: int = 3) -> list[DiffSegment]:
    """
    Compare two text strings line by line. Returns unified segments
    suitable for rendering in a diff view.
    """
    lines_a = text_a.splitlines()
    lines_b = text_b.splitlines()

    result: list[DiffSegment] = []
    matcher = difflib.SequenceMatcher(None, lines_a, lines_b)

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            # Show only context lines around changes
            seg_lines = lines_a[i1:i2]
            if len(seg_lines) > context_lines * 2:
                # Show first context_lines and last context_lines with ... in middle
                result.append(DiffSegment(
                    text="\n".join(seg_lines[:context_lines]),
                    tag="equal",
                ))
                result.append(DiffSegment(text="...", tag="equal"))
                result.append(DiffSegment(
                    text="\n".join(seg_lines[-context_lines:]),
                    tag="equal",
                ))
            else:
                result.append(DiffSegment(text="\n".join(seg_lines), tag="equal"))
        elif tag == "delete":
            result.append(DiffSegment(
                text="\n".join(f"- {l}" for l in lines_a[i1:i2]),
                tag="delete",
            ))
        elif tag == "insert":
            result.append(DiffSegment(
                text="\n".join(f"+ {l}" for l in lines_b[j1:j2]),
                tag="insert",
            ))
        elif tag == "replace":
            result.append(DiffSegment(
                text="\n".join(f"- {l}" for l in lines_a[i1:i2]),
                tag="replace_old",
            ))
            result.append(DiffSegment(
                text="\n".join(f"+ {l}" for l in lines_b[j1:j2]),
                tag="replace_new",
            ))

    return result


def generate_diff_summary(result: DiffResult) -> str:
    """Generate a human-readable summary of the diff."""
    lines = [
        f"Comparison: {Path(result.file_a).name} ↔ {Path(result.file_b).name}",
        f"Pages compared: {len(result.pages)}",
        f"Total changes: {result.total_changes} line(s)",
        "",
    ]

    for dp in result.pages:
        if dp.has_changes:
            line_counts = []
            for seg in dp.segments_a + dp.segments_b:
                if seg.tag in ("delete", "replace_old"):
                    line_counts.append(f"-{len(seg.text.splitlines()) if seg.text else 0}")
                elif seg.tag in ("insert", "replace_new"):
                    line_counts.append(f"+{len(seg.text.splitlines()) if seg.text else 0}")
            lines.append(f"  Page {dp.page_a}: {', '.join(line_counts)}")

    if result.total_changes == 0:
        lines.append("  No differences found — files appear identical.")

    return "\n".join(lines)
