"""
MCP server for OpenReader.

Provides AI agents with programmatic access to PDF operations —
extract text, search, compare, merge, split, compress, index folders,
and manage the library search index — all local, all through the MCP protocol.

Usage (stdio transport, standard for agents):
    python -m pdfreader_lib.mcp_server

Usage (SSE transport for HTTP-based gateways):
    python -m pdfreader_lib.mcp_server --transport sse --port 8312

Agent configuration (Claude Code, Hermes, etc.):
    {
      "mcpServers": {
        "openreader": {
          "command": "python",
          "args": ["-m", "pdfreader_lib.mcp_server"]
        }
      }
    }
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

import fitz  # PyMuPDF

from .search_index import (
    SearchResult,
    extract_text as _lib_extract_text,
    get_indexed_docs,
    index_folder,
    invalidate_tfidf,
    search_keyword,
    get_tfidf,
    IndexProgress,
)
from .comparison import compare_pdfs as _lib_compare_pdfs, generate_diff_summary


# ---------------------------------------------------------------------------
# Self-contained PDF operations (mirrors logic from main.py for MCP use)
# ---------------------------------------------------------------------------

# Safety limits from main.py
MAX_PDF_SIZE_BYTES = 500 * 1024 * 1024  # 500 MB
MAX_SPLIT_PAGES = 500
MAX_PAGE_DIMENSION_POINTS = 14400  # 200 inches at 72 dpi


def _validate_pdf(path_str: str) -> Path:
    p = Path(path_str).expanduser().resolve()
    if not p.exists() or not p.is_file():
        raise FileNotFoundError(f"File not found: {p}")
    if p.suffix.lower() != ".pdf":
        raise ValueError(f"Not a PDF file: {p}")
    size = p.stat().st_size
    if size <= 0:
        raise ValueError(f"File is empty: {p}")
    if size > MAX_PDF_SIZE_BYTES:
        raise ValueError(
            f"File exceeds {MAX_PDF_SIZE_BYTES // (1024 * 1024)} MB safety limit: {p}"
        )
    with open(p, "rb") as fh:
        header = fh.read(1024)
    if b"%PDF-" not in header:
        raise ValueError(f"File does not appear to be a valid PDF: {p}")
    return p


def _get_page_count(path_str: str) -> int:
    p = _validate_pdf(path_str)
    doc = fitz.open(str(p))
    try:
        return doc.page_count
    finally:
        doc.close()


def _get_metadata(path_str: str) -> dict[str, Any]:
    p = _validate_pdf(path_str)
    doc = fitz.open(str(p))
    try:
        meta = doc.metadata or {}
        return {
            "title": meta.get("title") or "",
            "author": meta.get("author") or "",
            "subject": meta.get("subject") or "",
            "keywords": meta.get("keywords") or "",
            "producer": meta.get("producer") or "",
            "creator": meta.get("creator") or "",
            "pages": doc.page_count,
            "file_size": p.stat().st_size,
            "file_name": p.name,
        }
    finally:
        doc.close()


def _extract_page_text(path_str: str, page_num: int) -> str:
    """Extract text from a single page (1-indexed)."""
    p = _validate_pdf(path_str)
    doc = fitz.open(str(p))
    try:
        if page_num < 1 or page_num > doc.page_count:
            raise ValueError(
                f"Page {page_num} out of range (1-{doc.page_count})"
            )
        page = doc.load_page(page_num - 1)
        return page.get_text("text")
    finally:
        doc.close()


def _extract_text(path_str: str) -> list[dict]:
    """Extract text from all pages. Returns list of {page, text}."""
    p = _validate_pdf(path_str)
    return _lib_extract_text(str(p))


def _merge_pdfs(input_paths: list[str], output_path: str) -> str:
    """Merge multiple PDFs into one."""
    out = Path(output_path).expanduser().resolve()
    if out.suffix.lower() != ".pdf":
        out = out.with_suffix(".pdf")

    merged = fitz.open()
    opened: list[fitz.Document] = []
    try:
        for inp in input_paths:
            p = _validate_pdf(inp)
            src = fitz.open(str(p))
            opened.append(src)
            merged.insert_pdf(src)
        merged.save(
            str(out),
            garbage=4,
            deflate=True,
            deflate_images=True,
            deflate_fonts=True,
            use_objstms=1,
            compression_effort=9,
        )
    finally:
        for src in opened:
            src.close()
        merged.close()
    return str(out)


def _split_every_page(path_str: str, output_dir: str) -> list[str]:
    """Split PDF into one file per page."""
    p = _validate_pdf(path_str)
    out_dir = Path(output_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(str(p))
    try:
        page_count = doc.page_count
        if page_count > MAX_SPLIT_PAGES:
            raise ValueError(
                f"Cannot split more than {MAX_SPLIT_PAGES} pages at once."
            )
        saved = []
        base_name = p.stem
        for i in range(page_count):
            target = out_dir / f"{base_name}_page_{i + 1}.pdf"
            new_doc = fitz.open()
            try:
                new_doc.insert_pdf(doc, from_page=i, to_page=i)
                new_doc.save(
                    str(target), garbage=4, deflate=True, use_objstms=1
                )
            finally:
                new_doc.close()
            saved.append(str(target))
        return saved
    finally:
        doc.close()


def _parse_page_ranges(text: str, page_count: int) -> list[int]:
    """Parse page range string like '1-3,5,7-9' into 0-indexed list."""
    pages: list[int] = []
    for chunk in text.replace(" ", "").split(","):
        if not chunk:
            continue
        if "-" in chunk:
            start_str, end_str = chunk.split("-", 1)
            start = int(start_str)
            end = int(end_str)
            if start > end:
                start, end = end, start
            pages.extend(range(start - 1, end))
        else:
            pages.append(int(chunk) - 1)

    unique: list[int] = []
    seen: set[int] = set()
    for page in pages:
        if page < 0 or page >= page_count:
            raise ValueError(
                f"Page {page + 1} is outside valid range 1-{page_count}."
            )
        if page not in seen:
            seen.add(page)
            unique.append(page)
    if not unique:
        raise ValueError("No valid pages found in the range string.")
    return unique


def _extract_pages(
    path_str: str, page_ranges: str, output_path: str | None = None
) -> str:
    """Extract specific pages from a PDF into a new PDF."""
    p = _validate_pdf(path_str)
    doc = fitz.open(str(p))
    try:
        page_indices = _parse_page_ranges(page_ranges, doc.page_count)
        if output_path:
            out = Path(output_path).expanduser().resolve()
        else:
            out = p.with_stem(f"{p.stem}_extracted")
        if out.suffix.lower() != ".pdf":
            out = out.with_suffix(".pdf")

        new_doc = fitz.open()
        try:
            for pi in page_indices:
                new_doc.insert_pdf(doc, from_page=pi, to_page=pi)
            new_doc.save(
                str(out), garbage=4, deflate=True, use_objstms=1
            )
        finally:
            new_doc.close()
        return str(out)
    finally:
        doc.close()


def _compress_pdf(path_str: str, output_path: str | None = None) -> str:
    """Create a compressed copy of a PDF."""
    p = _validate_pdf(path_str)
    if output_path:
        out = Path(output_path).expanduser().resolve()
    else:
        out = p.with_stem(f"{p.stem}_compressed")
    if out.suffix.lower() != ".pdf":
        out = out.with_suffix(".pdf")

    doc = fitz.open(str(p))
    try:
        doc.save(
            str(out),
            garbage=4,
            clean=True,
            deflate=True,
            deflate_images=True,
            deflate_fonts=True,
            use_objstms=1,
            compression_effort=9,
        )
    finally:
        doc.close()

    source_size = p.stat().st_size
    output_size = out.stat().st_size
    ratio = (
        round((source_size - output_size) / source_size * 100, 1)
        if source_size > 0
        else 0
    )

    return json.dumps(
        {
            "output_path": str(out),
            "original_bytes": source_size,
            "compressed_bytes": output_size,
            "savings_percent": ratio,
        }
    )


def _compare_pdfs(path_a: str, path_b: str) -> dict:
    """Compare two PDFs page by page and return structured diff."""
    _validate_pdf(path_a)
    _validate_pdf(path_b)
    result = _lib_compare_pdfs(path_a, path_b)
    return {
        "file_a": result.file_a,
        "file_b": result.file_b,
        "total_pages_compared": len(result.pages),
        "total_changes": result.total_changes,
        "summary": generate_diff_summary(result),
        "pages": [
            {
                "page_a": dp.page_a,
                "page_b": dp.page_b,
                "has_changes": dp.has_changes,
                "segments_a": [
                    {"text": s.text, "tag": s.tag} for s in dp.segments_a
                ],
                "segments_b": [
                    {"text": s.text, "tag": s.tag} for s in dp.segments_b
                ],
            }
            for dp in result.pages
        ],
    }


def _search_single_pdf(
    path_str: str, query: str
) -> list[dict]:
    """Search for text within a single PDF. Returns per-page results."""
    p = _validate_pdf(path_str)
    doc = fitz.open(str(p))
    try:
        results = []
        for i in range(doc.page_count):
            page = doc.load_page(i)
            text = page.get_text("text")
            if not text:
                continue
            # Simple substring/word search
            text_lower = text.lower()
            q_lower = query.lower()
            matches = []
            idx = 0
            while True:
                pos = text_lower.find(q_lower, idx)
                if pos < 0:
                    break
                matches.append(pos)
                idx = pos + 1

            if matches:
                # Extract context snippets around each match
                snippets = []
                for m_pos in matches:
                    start = max(0, m_pos - 60)
                    end = min(len(text), m_pos + len(query) + 60)
                    snippet = text[start:end].replace("\n", " ").strip()
                    if start > 0:
                        snippet = "..." + snippet
                    if end < len(text):
                        snippet = snippet + "..."
                    snippets.append(snippet)

                results.append(
                    {
                        "page": i + 1,
                        "match_count": len(matches),
                        "snippets": snippets[:5],  # limit per page
                    }
                )
        return results
    finally:
        doc.close()


# ---------------------------------------------------------------------------
# MCP Server
# ---------------------------------------------------------------------------

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent, ImageContent

    HAVE_MCP = True
except ImportError:
    HAVE_MCP = False


def _make_tool(
    name: str,
    description: str,
    properties: dict[str, dict],
    required: list[str] | None = None,
) -> Tool:
    return Tool(
        name=name,
        description=description,
        inputSchema={
            "type": "object",
            "properties": properties,
            "required": required or [],
        },
    )


def _ok(content: str) -> list[TextContent]:
    return [TextContent(type="text", text=content)]


def _err(msg: str) -> list[TextContent]:
    return [TextContent(type="text", text=f"Error: {msg}")]


def _err_not_found(name: str, path: str) -> list[TextContent]:
    return [TextContent(type="text", text=f"File not found: '{path}'. Verify the file path is correct and the file exists on the local filesystem. Use an absolute path if the relative path does not resolve.")]


def _err_validation(detail: str) -> list[TextContent]:
    return [TextContent(type="text", text=f"Invalid input: {detail} Check the tool's parameter requirements and try again.")]


TOOLS: list[Tool] = [
    _make_tool(
        "extract_text",
        "Extract all text from every page of a PDF file. Returns a list of objects each with page number and text character count — not the full text itself. Use this to get an overview of a document's content structure or to determine which pages have content before calling get_page_text for the full text of specific pages. For a single page use get_page_text instead.",
        {"path": {"type": "string", "description": "Absolute or relative path to the PDF file on the local filesystem"}},
        required=["path"],
    ),
    _make_tool(
        "get_page_text",
        "Extract the full text content from a single page of a PDF (1-indexed). Returns the complete raw text of the requested page. Use this when you need to read the actual text of a specific page — for example after extract_text told you which pages have content. For multiple pages use extract_text instead.",
        {
            "path": {"type": "string", "description": "Absolute or relative path to the PDF file on the local filesystem"},
            "page": {
                "type": "integer",
                "description": "Page number to read (1-indexed, e.g. 1 for the first page)",
            },
        },
        required=["path", "page"],
    ),
    _make_tool(
        "get_metadata",
        "Get PDF metadata and basic file info including title, author, subject, keywords, page count, file size, and file name. Returns a structured JSON object. Use this to inspect a PDF's properties before deciding which operations to perform on it.",
        {"path": {"type": "string", "description": "Absolute or relative path to the PDF file on the local filesystem"}},
        required=["path"],
    ),
    _make_tool(
        "get_page_count",
        "Get the number of pages in a PDF as a single integer. This is a light operation — use this when you only need the page count without the rest of the metadata that get_metadata returns.",
        {"path": {"type": "string", "description": "Absolute or relative path to the PDF file on the local filesystem"}},
        required=["path"],
    ),
    _make_tool(
        "search_pdf",
        "Search for text within a single PDF file using substring matching (case-insensitive). Returns matches grouped by page with surrounding context snippets (up to 5 snippets per page). Use this to find specific terms, names, or phrases in a document. For cross-document search across a library of indexed PDFs use search_library instead.",
        {
            "path": {"type": "string", "description": "Absolute or relative path to the PDF file on the local filesystem"},
            "query": {
                "type": "string",
                "description": "The text to search for (case-insensitive substring match)",
            },
        },
        required=["path", "query"],
    ),
    _make_tool(
        "compare_pdfs",
        "Compare two PDFs page by page and return a structured diff showing what changed. Returns page-level comparison with added, removed, and unchanged text segments plus a summary of total changes. Use this to review document revisions, contract changes, or draft updates. The first path (path_a) is treated as the older version, path_b as the newer version.",
        {
            "path_a": {
                "type": "string",
                "description": "Path to the first/older PDF file",
            },
            "path_b": {
                "type": "string",
                "description": "Path to the second/newer PDF file",
            },
        },
        required=["path_a", "path_b"],
    ),
    _make_tool(
        "merge_pdfs",
        "Merge two or more PDF files into a single combined PDF. Accepts a list of file paths (minimum 2) and an output path. The PDFs are concatenated in the order provided. Returns the path to the merged output file. Use this to combine separate documents, chapters, or scanned files into one PDF.",
        {
            "paths": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of PDF file paths to merge in order (at least 2 required)",
            },
            "output_path": {
                "type": "string",
                "description": "Desired output path for the merged PDF (must end in .pdf)",
            },
        },
        required=["paths", "output_path"],
    ),
    _make_tool(
        "split_pdf",
        "Split a multi-page PDF into individual single-page PDF files. Each page of the source document becomes its own PDF saved in the specified output directory. Files are named as {original_name}_page_{N}.pdf. Use this when you need to separate a document into individual pages for redistribution or further processing. Maximum 500 pages per split.",
        {
            "path": {"type": "string", "description": "Path to the PDF file to split"},
            "output_dir": {
                "type": "string",
                "description": "Directory where the individual page PDFs will be saved (created if it doesn't exist)",
            },
        },
        required=["path", "output_dir"],
    ),
    _make_tool(
        "extract_pages",
        "Extract specific pages from a PDF into a new PDF file. Uses page range notation like '1-3,5,7-9' to specify which pages to include. Pages are 1-indexed. Returns the path to the extracted output file. Use this to create a subset document containing only the pages you need — for example pulling out specific chapters or sections. For splitting every page individually use split_pdf instead.",
        {
            "path": {
                "type": "string",
                "description": "Path to the PDF file to extract pages from",
            },
            "page_ranges": {
                "type": "string",
                "description": "Page ranges to extract, e.g. '1-3,5,7-9' (1-indexed, comma-separated ranges)",
            },
            "output_path": {
                "type": "string",
                "description": "Optional output path (defaults to input_stem_extracted.pdf in the same directory)",
            },
        },
        required=["path", "page_ranges"],
    ),
    _make_tool(
        "compress_pdf",
        "Create a compressed copy of a PDF with reduced file size. Uses aggressive compression on images, fonts, and content streams. Returns compression stats including original size, compressed size, and savings percentage. Use this to reduce PDF file sizes for storage or sharing. Typical savings range from 20-80% depending on image content.",
        {
            "path": {"type": "string", "description": "Path to the PDF file to compress"},
            "output_path": {
                "type": "string",
                "description": "Optional output path for the compressed copy (defaults to input_stem_compressed.pdf)",
            },
        },
        required=["path"],
    ),
    _make_tool(
        "index_folder",
        "Build or update the SQLite FTS5 full-text search index for all PDFs in a folder. Scans all PDF files recursively, extracts their text, and builds a searchable index. Returns the number of files indexed and total characters processed. Run this before using search_library or search_semantic. Re-run it to update the index when new PDFs are added to the folder.",
        {
            "folder_path": {
                "type": "string",
                "description": "Path to a folder containing PDFs to index (scanned recursively)",
            }
        },
        required=["folder_path"],
    ),
    _make_tool(
        "search_library",
        "Search across all previously indexed PDFs using SQLite FTS5 full-text search. Returns ranked results with file name, path, page number, context snippet, and relevance score. Use this to find documents by their content across your entire PDF library. Requires index_folder to have been run first on the target folder. For searching within a single PDF use search_pdf instead.",
        {
            "query": {"type": "string", "description": "Search query text to find across indexed PDFs"},
            "max_results": {
                "type": "integer",
                "description": "Maximum number of results to return (default: 20, max: 100)",
            },
            "folder": {
                "type": "string",
                "description": "Optional folder path to scope the search to a specific indexed directory",
            },
        },
        required=["query"],
    ),
    _make_tool(
        "search_semantic",
        "Search across indexed PDFs using TF-IDF cosine similarity for meaning-based search (no ML dependencies, fully local). Returns ranked results with relevance scores. Unlike search_library which uses exact keyword matching, this finds conceptually related content even when the exact words don't match. Requires index_folder to have been run first.",
        {
            "query": {"type": "string", "description": "Search query — finds conceptually related content even without exact keyword matches"},
            "max_results": {
                "type": "integer",
                "description": "Maximum number of results to return (default: 20, max: 100)",
            },
            "folder": {
                "type": "string",
                "description": "Optional folder path to scope the search to a specific indexed directory",
            },
        },
        required=["query"],
    ),
    _make_tool(
        "list_indexed_docs",
        "List all PDF documents currently in the library search index with metadata including file name, path, page count, and character count. Run this to see what documents are available for searching before using search_library or search_semantic. Returns an empty list if index_folder has not been run yet.",
        {},
    ),
]


async def serve_stdio() -> None:
    """Run the MCP server over stdio transport (standard for AI agents)."""
    server = Server("openreader")

    @server.list_tools()
    async def _list_tools() -> list[Tool]:
        return TOOLS

    @server.call_tool()
    async def _call_tool(
        name: str, arguments: dict
    ) -> list[TextContent]:
        try:
            return await _handle_call(name, arguments)
        except FileNotFoundError as exc:
            return _err_not_found(name, str(exc))
        except ValueError as exc:
            return _err_validation(str(exc))
        except KeyError as exc:
            return _err_validation(f"Missing required parameter: {exc}")
        except Exception as exc:
            return _err(f"{type(exc).__name__}: {exc}")

    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())


# ---------------------------------------------------------------------------
# Tool dispatch (shared between stdio and SSE)
# ---------------------------------------------------------------------------


async def _handle_call(
    name: str, args: dict
) -> list[TextContent]:
    match name:
        case "extract_text":
            pages = _extract_text(args["path"])
            return _ok(
                json.dumps(
                    [
                        {"page": p["page"], "text_length": len(p["text"])}
                        for p in pages
                    ],
                    indent=2,
                )
            )

        case "get_page_text":
            text = _extract_page_text(args["path"], args["page"])
            return _ok(text)

        case "get_metadata":
            meta = _get_metadata(args["path"])
            return _ok(json.dumps(meta, indent=2))

        case "get_page_count":
            count = _get_page_count(args["path"])
            return _ok(str(count))

        case "search_pdf":
            results = _search_single_pdf(args["path"], args["query"])
            return _ok(json.dumps(results, indent=2))

        case "compare_pdfs":
            result = _compare_pdfs(args["path_a"], args["path_b"])
            return _ok(json.dumps(result, indent=2, default=str))

        case "merge_pdfs":
            result = _merge_pdfs(args["paths"], args["output_path"])
            return _ok(f"Merged PDF saved to: {result}")

        case "split_pdf":
            result = _split_every_page(args["path"], args["output_dir"])
            return _ok(
                f"Split into {len(result)} files:\n"
                + "\n".join(result)
            )

        case "extract_pages":
            result = _extract_pages(
                args["path"],
                args["page_ranges"],
                args.get("output_path"),
            )
            return _ok(f"Extracted pages saved to: {result}")

        case "compress_pdf":
            result = _compress_pdf(
                args["path"], args.get("output_path")
            )
            return _ok(result)

        case "index_folder":
            progress = IndexProgress()
            files, chars = index_folder(args["folder_path"], progress)
            return _ok(
                f"Indexed {files} files ({chars:,} characters) from: {args['folder_path']}"
            )

        case "search_library":
            results: list[SearchResult] = search_keyword(
                args["query"],
                max_results=args.get("max_results", 20),
                folder=args.get("folder"),
            )
            return _ok(
                json.dumps(
                    [
                        {
                            "file": r.filename,
                            "path": r.path,
                            "page": r.page,
                            "snippet": r.snippet,
                            "score": round(r.score, 3),
                        }
                        for r in results
                    ],
                    indent=2,
                )
            )

        case "search_semantic":
            tfidf = get_tfidf(args.get("folder"))
            results = tfidf.search(
                args["query"],
                max_results=args.get("max_results", 20),
            )
            return _ok(
                json.dumps(
                    [
                        {
                            "file": r.filename,
                            "path": r.path,
                            "page": r.page,
                            "snippet": r.snippet,
                            "score": round(r.score, 3),
                        }
                        for r in results
                    ],
                    indent=2,
                )
            )

        case "list_indexed_docs":
            docs = get_indexed_docs()
            return _ok(
                json.dumps(
                    [
                        {
                            "file": d["filename"],
                            "path": d["path"],
                            "pages": d["pages"],
                            "chars": d["chars"],
                        }
                        for d in docs
                    ],
                    indent=2,
                )
            )

        case _:
            return _err(f"Unknown tool: {name}")


# ---------------------------------------------------------------------------
# SSE transport (optional, for HTTP-based gateways)
# ---------------------------------------------------------------------------


async def serve_sse(host: str = "0.0.0.0", port: int = 8312) -> None:
    """Run the MCP server over SSE transport for HTTP gateways."""
    from mcp.server.sse import SseServerTransport

    try:
        from starlette.applications import Starlette
        from starlette.routing import Mount, Route
    except ImportError:
        print(
            "SSE transport requires starlette. Install with: pip install 'mcp[sse]'",
            file=sys.stderr,
        )
        sys.exit(1)

    import uvicorn

    server = Server("openreader")

    @server.list_tools()
    async def _list_tools() -> list[Tool]:
        return TOOLS

    @server.call_tool()
    async def _call_tool(
        name: str, arguments: dict
    ) -> list[TextContent]:
        try:
            return await _handle_call(name, arguments)
        except FileNotFoundError as exc:
            return _err_not_found(name, str(exc))
        except ValueError as exc:
            return _err_validation(str(exc))
        except KeyError as exc:
            return _err_validation(f"Missing required parameter: {exc}")
        except Exception as exc:
            return _err(f"{type(exc).__name__}: {exc}")

    sse = SseServerTransport("/messages/")

    async def handle_sse(request):
        async with sse.connect_sse(
            request.scope, request.receive, request._send
        ) as (read, write):
            await server.run(
                read, write, server.create_initialization_options()
            )

    async def handle_messages(request):
        await sse.handle_post_message(
            request.scope, request.receive, request._send
        )

    app = Starlette(
        debug=False,
        routes=[
            Route("/sse", endpoint=handle_sse),
            Mount("/messages/", app=handle_messages),
        ],
    )

    print(
        f"MCP SSE server listening on http://{host}:{port}/sse",
        file=sys.stderr,
    )
    await uvicorn.run(app, host=host, port=port, log_level="warning")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="OpenReader — MCP Server",
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse"],
        default="stdio",
        help="Transport protocol (default: stdio)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8312,
        help="Port for SSE transport (default: 8312)",
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host for SSE transport (default: 0.0.0.0)",
    )

    args = parser.parse_args()

    if not HAVE_MCP:
        print(
            "ERROR: MCP SDK not installed. Run:\n"
            "  pip install mcp\n"
            "Or for SSE support:\n"
            "  pip install 'mcp[sse]'",
            file=sys.stderr,
        )
        sys.exit(1)

    import asyncio

    if args.transport == "sse":
        asyncio.run(serve_sse(host=args.host, port=args.port))
    else:
        asyncio.run(serve_stdio())


if __name__ == "__main__":
    main()
