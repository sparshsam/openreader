# openreader-mcp

AI assistant tools for PDFs — read, search, compare, merge, split, compress, and index PDFs locally through MCP (Model Context Protocol).

Works with Claude, ChatGPT, Cursor, and any MCP-compatible AI assistant. No cloud, no uploads, no accounts.

## Install

```bash
pip install openreader-mcp
```

## Usage

```bash
python -m openreader_mcp
```

## Configure your AI assistant

### Claude Code

Add to your `.claude/settings.local.json`:

```json
{
  "mcpServers": {
    "openreader": {
      "command": "python",
      "args": ["-m", "openreader_mcp"]
    }
  }
}
```

### Claude Desktop

Settings → MCP Servers → Add:

```json
{
  "mcpServers": {
    "openreader": {
      "command": "python",
      "args": ["-m", "openreader_mcp"]
    }
  }
}
```

### Cursor

Settings → MCP Servers → Add New Server:
- Name: `openreader`
- Type: `command`
- Command: `python -m openreader_mcp`

## Tools (14 total)

| Tool | Description |
|------|-------------|
| `extract_text` | Read all text from every page of a PDF |
| `get_page_text` | Read one specific page (1-indexed) |
| `get_metadata` | Get PDF info (pages, author, title, size) |
| `get_page_count` | Quick page count |
| `search_pdf` | Find text inside a single PDF with context snippets |
| `compare_pdfs` | Show differences between two PDFs |
| `merge_pdfs` | Combine multiple PDFs into one |
| `split_pdf` | Split a PDF into separate pages |
| `extract_pages` | Extract specific pages by range |
| `compress_pdf` | Make a PDF smaller |
| `index_folder` | Build a searchable index of all PDFs in a folder |
| `search_library` | Search across all indexed PDFs |
| `search_semantic` | Meaning-based search (TF-IDF, no ML dependencies) |
| `list_indexed_docs` | List PDFs in the search index |

## Requirements

- Python 3.10+
- Works on Windows, macOS, Linux

## License

AGPL-3.0-or-later
