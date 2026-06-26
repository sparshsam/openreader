"""
MCP server for OpenReader — standalone package.

Lets AI agents read, search, compare, merge, split, compress,
and index PDFs on your local machine. No cloud, no uploads.

Usage:
    pip install openreader-mcp
    python -m openreader_mcp

Configure your AI assistant with:
    "mcpServers": {
      "openreader": {
        "command": "python",
        "args": ["-m", "openreader_mcp"]
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

import fitz

from ._search_index import (
    SearchResult,
    extract_text as _lib_extract_text,
    get_indexed_docs,
    index_folder,
    search_keyword,
    get_tfidf,
    IndexProgress,
)
from ._comparison import compare_pdfs as _lib_compare_pdfs, generate_diff_summary

# ---------------------------------------------------------------------------
# Safety limits
# ---------------------------------------------------------------------------
MAX_PDF_SIZE_BYTES = 500 * 1024 * 1024  # 500 MB
MAX_SPLIT_PAGES = 500


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
    p = _validate_pdf(path_str)
    doc = fitz.open(str(p))
    try:
        if page_num < 1 or page_num > doc.page_count:
            raise ValueError(f"Page {page_num} out of range (1-{doc.page_count})")
        page = doc.load_page(page_num - 1)
        return page.get_text("text")
    finally:
        doc.close()


def _extract_text(path_str: str) -> list[dict]:
    p = _validate_pdf(path_str)
    return _lib_extract_text(str(p))


def _merge_pdfs(input_paths: list[str], output_path: str) -> str:
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
        merged.save(str(out), garbage=4, deflate=True, deflate_images=True,
                     deflate_fonts=True, use_objstms=1, compression_effort=9)
    finally:
        for src in opened:
            src.close()
        merged.close()
    return str(out)


def _split_every_page(path_str: str, output_dir: str) -> list[str]:
    p = _validate_pdf(path_str)
    out_dir = Path(output_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(str(p))
    try:
        page_count = doc.page_count
        if page_count > MAX_SPLIT_PAGES:
            raise ValueError(f"Cannot split more than {MAX_SPLIT_PAGES} pages at once.")
        saved = []
        base_name = p.stem
        for i in range(page_count):
            target = out_dir / f"{base_name}_page_{i + 1}.pdf"
            new_doc = fitz.open()
            try:
                new_doc.insert_pdf(doc, from_page=i, to_page=i)
                new_doc.save(str(target), garbage=4, deflate=True, use_objstms=1)
            finally:
                new_doc.close()
            saved.append(str(target))
        return saved
    finally:
        doc.close()


def _parse_page_ranges(text: str, page_count: int) -> list[int]:
    pages: list[int] = []
    for chunk in text.replace(" ", "").split(","):
        if not chunk:
            continue
        if "-" in chunk:
            start_str, end_str = chunk.split("-", 1)
            start, end = int(start_str), int(end_str)
            if start > end:
                start, end = end, start
            pages.extend(range(start - 1, end))
        else:
            pages.append(int(chunk) - 1)

    unique: list[int] = []
    seen: set[int] = set()
    for page in pages:
        if page < 0 or page >= page_count:
            raise ValueError(f"Page {page + 1} is outside valid range 1-{page_count}.")
        if page not in seen:
            seen.add(page)
            unique.append(page)
    if not unique:
        raise ValueError("No valid pages found in the range string.")
    return unique


def _extract_pages(path_str: str, page_ranges: str, output_path: str | None = None) -> str:
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
            new_doc.save(str(out), garbage=4, deflate=True, use_objstms=1)
        finally:
            new_doc.close()
        return str(out)
    finally:
        doc.close()


def _compress_pdf(path_str: str, output_path: str | None = None) -> str:
    p = _validate_pdf(path_str)
    if output_path:
        out = Path(output_path).expanduser().resolve()
    else:
        out = p.with_stem(f"{p.stem}_compressed")
    if out.suffix.lower() != ".pdf":
        out = out.with_suffix(".pdf")

    doc = fitz.open(str(p))
    try:
        doc.save(str(out), garbage=4, clean=True, deflate=True,
                 deflate_images=True, deflate_fonts=True,
                 use_objstms=1, compression_effort=9)
    finally:
        doc.close()

    source_size = p.stat().st_size
    output_size = out.stat().st_size
    ratio = round((source_size - output_size) / source_size * 100, 1) if source_size > 0 else 0

    return json.dumps({
        "output_path": str(out),
        "original_bytes": source_size,
        "compressed_bytes": output_size,
        "savings_percent": ratio,
    })


def _compare_pdfs(path_a: str, path_b: str) -> dict:
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
                "segments_a": [{"text": s.text, "tag": s.tag} for s in dp.segments_a],
                "segments_b": [{"text": s.text, "tag": s.tag} for s in dp.segments_b],
            }
            for dp in result.pages
        ],
    }


def _search_single_pdf(path_str: str, query: str) -> list[dict]:
    p = _validate_pdf(path_str)
    doc = fitz.open(str(p))
    try:
        results = []
        for i in range(doc.page_count):
            page = doc.load_page(i)
            text = page.get_text("text")
            if not text:
                continue
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
                results.append({
                    "page": i + 1,
                    "match_count": len(matches),
                    "snippets": snippets[:5],
                })
        return results
    finally:
        doc.close()


# ---------------------------------------------------------------------------
# MCP Server
# ---------------------------------------------------------------------------
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent


TOOLS: list[Tool] = [
    Tool(
        name="extract_text",
        description="Read all text from every page of a PDF. Returns a list of objects with page number and character count — not the full text. Use this first to see which pages have content before calling get_page_text.",
        inputSchema={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to the PDF file on your computer"}
            },
            "required": ["path"],
        },
    ),
    Tool(
        name="get_page_text",
        description="Read the full text of one specific page from a PDF (page numbers start at 1). Use this after extract_text told you which pages have content.",
        inputSchema={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to the PDF file"},
                "page": {"type": "integer", "description": "Page number to read (1 = first page)"},
            },
            "required": ["path", "page"],
        },
    ),
    Tool(
        name="get_metadata",
        description="Get PDF info: title, author, page count, file size, subject, keywords. Returns a structured JSON object.",
        inputSchema={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to the PDF file"}
            },
            "required": ["path"],
        },
    ),
    Tool(
        name="get_page_count",
        description="Quickly check how many pages a PDF has. Just returns a number — faster than get_metadata if all you need is the page count.",
        inputSchema={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to the PDF file"}
            },
            "required": ["path"],
        },
    ),
    Tool(
        name="search_pdf",
        description="Search for a word or phrase inside a single PDF. Returns matches per page with context snippets. Case-insensitive, finds partial matches too.",
        inputSchema={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to the PDF file"},
                "query": {"type": "string", "description": "Word or phrase to search for"},
            },
            "required": ["path", "query"],
        },
    ),
    Tool(
        name="compare_pdfs",
        description="Compare two PDFs page by page and show what changed. Returns a structured diff with added, removed, and unchanged text segments plus an overall summary. path_a = older version, path_b = newer version.",
        inputSchema={
            "type": "object",
            "properties": {
                "path_a": {"type": "string", "description": "Path to the first PDF (older version)"},
                "path_b": {"type": "string", "description": "Path to the second PDF (newer version)"},
            },
            "required": ["path_a", "path_b"],
        },
    ),
    Tool(
        name="merge_pdfs",
        description="Combine multiple PDFs into one file. Provide a list of file paths and an output path. PDFs are combined in the order you list them.",
        inputSchema={
            "type": "object",
            "properties": {
                "paths": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of PDF file paths to merge (at least 2)",
                },
                "output_path": {"type": "string", "description": "Where to save the merged PDF"},
            },
            "required": ["paths", "output_path"],
        },
    ),
    Tool(
        name="split_pdf",
        description="Split a multi-page PDF into individual single-page files. Each page becomes its own PDF, saved in the output directory. Max 500 pages.",
        inputSchema={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to the PDF to split"},
                "output_dir": {"type": "string", "description": "Directory to save the individual pages"},
            },
            "required": ["path", "output_dir"],
        },
    ),
    Tool(
        name="extract_pages",
        description="Pull out specific pages from a PDF into a new file. Use range notation like '1-3,5,7-9'. Pages are 1-indexed.",
        inputSchema={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to the PDF file"},
                "page_ranges": {"type": "string", "description": "Pages to extract, e.g. '1-3,5,7-9' or '1,3,5'"},
                "output_path": {"type": "string", "description": "Optional output path (defaults to input_stem_extracted.pdf)"},
            },
            "required": ["path", "page_ranges"],
        },
    ),
    Tool(
        name="compress_pdf",
        description="Make a PDF file smaller. Uses aggressive compression on images and fonts. Returns stats: original size, compressed size, and savings percentage.",
        inputSchema={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to the PDF to compress"},
                "output_path": {"type": "string", "description": "Optional output path (defaults to input_stem_compressed.pdf)"},
            },
            "required": ["path"],
        },
    ),
    Tool(
        name="index_folder",
        description="Build a searchable index of all PDFs in a folder. Scans all PDFs recursively, extracts text, and indexes them for fast searching. Run this before using search_library or search_semantic. Re-run it to refresh the index when new PDFs are added.",
        inputSchema={
            "type": "object",
            "properties": {
                "folder_path": {"type": "string", "description": "Path to a folder of PDFs to index (scanned recursively)"},
            },
            "required": ["folder_path"],
        },
    ),
    Tool(
        name="search_library",
        description="Search across all previously indexed PDFs using fast keyword matching. Returns ranked results with file name, page number, context snippet, and relevance score. Requires index_folder to have been run first.",
        inputSchema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search term to find across indexed PDFs"},
                "max_results": {"type": "integer", "description": "Max results (default 20, max 100)"},
                "folder": {"type": "string", "description": "Optional folder to limit the search to"},
            },
            "required": ["query"],
        },
    ),
    Tool(
        name="search_semantic",
        description="Meaning-based search across indexed PDFs. Finds related content even when the exact words don't match. Uses TF-IDF (fully local, no AI dependencies). Requires index_folder first.",
        inputSchema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query — finds conceptually related content"},
                "max_results": {"type": "integer", "description": "Max results (default 20, max 100)"},
                "folder": {"type": "string", "description": "Optional folder to limit the search to"},
            },
            "required": ["query"],
        },
    ),
    Tool(
        name="list_indexed_docs",
        description="List all PDFs currently in the search index with file name, path, page count, and character count. Returns empty list if index_folder hasn't been run yet.",
        inputSchema={
            "type": "object",
            "properties": {},
        },
    ),
]


async def handle_call(name: str, args: dict) -> list[TextContent]:
    try:
        return await _handle_call(name, args)
    except FileNotFoundError as e:
        return [TextContent(type="text", text=f"File not found: {e}. Verify the path is correct.")]
    except ValueError as e:
        return [TextContent(type="text", text=f"Invalid input: {e}")]
    except KeyError as e:
        return [TextContent(type="text", text=f"Missing required parameter: {e}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error: {type(e).__name__}: {e}")]


async def _handle_call(name: str, args: dict) -> list[TextContent]:
    match name:
        case "extract_text":
            pages = _extract_text(args["path"])
            return [TextContent(
                type="text",
                text=json.dumps([{"page": p["page"], "text_length": len(p["text"])} for p in pages], indent=2),
            )]

        case "get_page_text":
            text = _extract_page_text(args["path"], args["page"])
            return [TextContent(type="text", text=text)]

        case "get_metadata":
            return [TextContent(type="text", text=json.dumps(_get_metadata(args["path"]), indent=2))]

        case "get_page_count":
            return [TextContent(type="text", text=str(_get_page_count(args["path"])))]

        case "search_pdf":
            return [TextContent(type="text", text=json.dumps(_search_single_pdf(args["path"], args["query"]), indent=2))]

        case "compare_pdfs":
            return [TextContent(type="text", text=json.dumps(_compare_pdfs(args["path_a"], args["path_b"]), indent=2, default=str))]

        case "merge_pdfs":
            result = _merge_pdfs(args["paths"], args["output_path"])
            return [TextContent(type="text", text=f"Merged PDF saved to: {result}")]

        case "split_pdf":
            result = _split_every_page(args["path"], args["output_dir"])
            return [TextContent(type="text", text=f"Split into {len(result)} files:\n" + "\n".join(result))]

        case "extract_pages":
            result = _extract_pages(args["path"], args["page_ranges"], args.get("output_path"))
            return [TextContent(type="text", text=f"Extracted pages saved to: {result}")]

        case "compress_pdf":
            return [TextContent(type="text", text=_compress_pdf(args["path"], args.get("output_path")))]

        case "index_folder":
            progress = IndexProgress()
            files, chars = index_folder(args["folder_path"], progress)
            return [TextContent(
                type="text",
                text=f"Indexed {files} files ({chars:,} characters) from: {args['folder_path']}",
            )]

        case "search_library":
            results: list[SearchResult] = search_keyword(
                args["query"],
                max_results=args.get("max_results", 20),
                folder=args.get("folder"),
            )
            return [TextContent(
                type="text",
                text=json.dumps([
                    {"file": r.filename, "path": r.path, "page": r.page,
                     "snippet": r.snippet, "score": round(r.score, 3)}
                    for r in results
                ], indent=2),
            )]

        case "search_semantic":
            tfidf = get_tfidf(args.get("folder"))
            results = tfidf.search(args["query"], max_results=args.get("max_results", 20))
            return [TextContent(
                type="text",
                text=json.dumps([
                    {"file": r.filename, "path": r.path, "page": r.page,
                     "snippet": r.snippet, "score": round(r.score, 3)}
                    for r in results
                ], indent=2),
            )]

        case "list_indexed_docs":
            docs = get_indexed_docs()
            return [TextContent(
                type="text",
                text=json.dumps([
                    {"file": d["filename"], "path": d["path"], "pages": d["pages"], "chars": d["chars"]}
                    for d in docs
                ], indent=2),
            )]

        case _:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="OpenReader MCP Server — AI tools for PDFs")
    parser.add_argument("--transport", choices=["stdio", "sse"], default="stdio",
                        help="Transport protocol (default: stdio)")
    parser.add_argument("--port", type=int, default=8312, help="Port for SSE transport")
    parser.add_argument("--host", default="0.0.0.0", help="Host for SSE transport")
    args = parser.parse_args()

    import asyncio

    if args.transport == "sse":
        asyncio.run(_serve_sse(host=args.host, port=args.port))
    else:
        asyncio.run(_serve_stdio())


async def _serve_stdio() -> None:
    """Run MCP server over stdio transport."""
    server = Server("openreader")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return TOOLS

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        return await handle_call(name, arguments)

    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())


async def _serve_sse(host: str = "0.0.0.0", port: int = 8312) -> None:
    """Run MCP server over SSE transport."""
    from mcp.server.sse import SseServerTransport

    try:
        from starlette.applications import Starlette
        from starlette.routing import Mount, Route
    except ImportError:
        print(
            "SSE transport requires starlette and uvicorn. Install with: pip install 'mcp[sse]'",
            file=sys.stderr,
        )
        sys.exit(1)

    import uvicorn

    server = Server("openreader")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return TOOLS

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        return await handle_call(name, arguments)

    sse = SseServerTransport("/messages/")

    async def handle_sse(request):
        async with sse.connect_sse(request.scope, request.receive, request._send) as (read, write):
            await server.run(read, write, server.create_initialization_options())

    async def handle_messages(request):
        await sse.handle_post_message(request.scope, request.receive, request._send)

    app = Starlette(debug=False, routes=[
        Route("/sse", endpoint=handle_sse),
        Mount("/messages/", app=handle_messages),
    ])

    print(f"MCP SSE server listening on http://{host}:{port}/sse", file=sys.stderr)
    await uvicorn.run(app, host=host, port=port, log_level="warning")


if __name__ == "__main__":
    main()
