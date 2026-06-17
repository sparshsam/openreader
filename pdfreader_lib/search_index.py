"""
OpenReader — Library Search Index

SQLite FTS5 for full-text search across a folder of PDFs.
TF-IDF cosine similarity for offline semantic-like search.

Data stored in ~/.pdfreader/library/
"""

import json
import math
import os
import re
import sqlite3
import threading
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable


LIBRARY_DIR = Path.home() / ".pdfreader" / "library"
DB_PATH = LIBRARY_DIR / "index.db"
STOP_WORDS = frozenset({
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will", "would",
    "could", "should", "may", "might", "shall", "can", "need", "dare",
    "i", "you", "he", "she", "it", "we", "they", "me", "him", "her",
    "us", "them", "my", "your", "his", "its", "our", "their", "this",
    "that", "these", "those", "what", "which", "who", "whom", "whose",
    "why", "how", "not", "no", "nor", "so", "very", "just", "about",
    "above", "after", "again", "all", "also", "any", "because", "before",
    "between", "both", "each", "few", "more", "most", "other", "some",
    "such", "only", "own", "same", "than", "too", "into", "over", "up",
})


@dataclass
class SearchResult:
    path: str
    filename: str
    page: int
    snippet: str
    score: float
    match_type: str = "keyword"  # "keyword" or "semantic"


@dataclass
class IndexProgress:
    total_files: int = 0
    completed: int = 0
    current_file: str = ""
    cancelled: bool = False


# ---------------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------------

def _ensure_db():
    LIBRARY_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=OFF")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY,
            path TEXT UNIQUE NOT NULL,
            filename TEXT NOT NULL,
            last_indexed REAL NOT NULL,
            page_count INTEGER DEFAULT 0,
            total_chars INTEGER DEFAULT 0
        )
    """)
    conn.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS pages_fts USING fts5(
            path, page, content,
            tokenize='porter unicode61'
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS folders (
            id INTEGER PRIMARY KEY,
            path TEXT UNIQUE NOT NULL
        )
    """)
    conn.commit()
    return conn


# ---------------------------------------------------------------------------
# Text extraction
# ---------------------------------------------------------------------------

_TOKENIZE_RE = re.compile(r"[a-zA-Z]\w{1,50}")

def tokenize(text: str) -> list[str]:
    """Normalize and tokenize text into lowercase words."""
    return [t.lower() for t in _TOKENIZE_RE.findall(text) if t.lower() not in STOP_WORDS and len(t) > 1]


def extract_text(path: str, progress: IndexProgress | None = None, cancel_check: Callable | None = None) -> list[dict]:
    """Extract text from every page of a PDF. Returns list of {page, text}."""
    import fitz
    doc = fitz.open(path)
    pages = []
    total = doc.page_count
    for i in range(total):
        if cancel_check and cancel_check():
            break
        page = doc.load_page(i)
        text = page.get_text("text")
        pages.append({"page": i + 1, "text": text})
        if progress:
            progress.current_file = f"{Path(path).name} — page {i + 1}/{total}"
    doc.close()
    return pages


# ---------------------------------------------------------------------------
# Index building
# ---------------------------------------------------------------------------

def _index_pdf(conn: sqlite3.Connection, path: str, pages: list[dict]) -> int:
    """Index a single PDF's pages. Returns total chars indexed."""
    total_chars = 0
    cursor = conn.cursor()

    # Delete old entries for this path
    cursor.execute("DELETE FROM pages_fts WHERE path = ?", (path,))

    # Insert new entries
    for p in pages:
        text = p["text"].strip()
        if not text:
            continue
        total_chars += len(text)
        try:
            cursor.execute(
                "INSERT INTO pages_fts(path, page, content) VALUES (?, ?, ?)",
                (path, p["page"], text),
            )
        except sqlite3.OperationalError as e:
            if "too many terms" in str(e):
                # Page has too many unique terms for FTS5 limit — truncate
                cursor.execute(
                    "INSERT INTO pages_fts(path, page, content) VALUES (?, ?, ?)",
                    (path, p["page"], text[:50000]),
                )
            else:
                raise
    return total_chars


def index_folder(folder_path: str, progress: IndexProgress | None = None) -> tuple[int, int]:
    """Index all PDFs in a folder. Returns (files_indexed, total_chars)."""
    import fitz

    folder = Path(folder_path).expanduser().resolve()
    pdfs = list(folder.rglob("*.pdf"))
    if not pdfs:
        return 0, 0

    if progress:
        progress.total_files = len(pdfs)

    conn = _ensure_db()
    cursor = conn.cursor()
    files_indexed = 0
    total_chars = 0

    # Add folder to tracked list
    cursor.execute(
        "INSERT OR IGNORE INTO folders(path) VALUES (?)",
        (str(folder),),
    )
    conn.commit()

    for pdf_path in pdfs:
        if progress and progress.cancelled:
            break

        str_path = str(pdf_path)
        if progress:
            progress.current_file = pdf_path.name

        try:
            doc = fitz.open(str_path)
            page_count = doc.page_count
            pages = []
            for i in range(page_count):
                if progress and progress.cancelled:
                    break
                page = doc.load_page(i)
                text = page.get_text("text")
                pages.append({"page": i + 1, "text": text})
            doc.close()

            chars = _index_pdf(conn, str_path, pages)
            total_chars += chars

            cursor.execute("""
                INSERT INTO documents(path, filename, last_indexed, page_count, total_chars)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(path) DO UPDATE SET
                    last_indexed = excluded.last_indexed,
                    page_count = excluded.page_count,
                    total_chars = excluded.total_chars
            """, (str_path, pdf_path.name, time.time(), page_count, chars))
            conn.commit()
            files_indexed += 1
        except Exception:
            continue

        if progress:
            progress.completed = files_indexed

    return files_indexed, total_chars


# ---------------------------------------------------------------------------
# Full-text search (FTS5)
# ---------------------------------------------------------------------------

def search_keyword(query: str, max_results: int = 50, folder: str | None = None) -> list[SearchResult]:
    """FTS5 full-text search. Returns ranked results across all indexed docs."""
    conn = _ensure_db()
    cursor = conn.cursor()

    # Clean up query for FTS5
    q = query.strip().replace('"', '""')
    # Support phrase search if user provides quotes
    if " " in q and not q.startswith('"'):
        fts_query = f'"{q}" OR ' + " OR ".join(
            t for t in q.split() if len(t) > 1
        )
    else:
        fts_query = q

    try:
        # FTS5 search with BM25 ranking
        cursor.execute("""
            SELECT p.path, d.filename, p.page, p.content, rank
            FROM pages_fts p
            JOIN documents d ON d.path = p.path
            WHERE pages_fts MATCH ?
            ORDER BY rank
            LIMIT ?
        """, (fts_query, max_results))
    except sqlite3.OperationalError:
        # FTS5 syntax error — fall back to LIKE
        cursor.execute("""
            SELECT p.path, d.filename, p.page, p.content
            FROM pages_fts p
            JOIN documents d ON d.path = p.path
            WHERE p.content LIKE ?
            LIMIT ?
        """, (f"%{q}%", max_results))

    rows = cursor.fetchall()
    conn.close()

    results = []
    for row in rows:
        path, filename, page, content, *rank_info = row
        score = -rank_info[0] if rank_info else 1.0  # FTS5 rank is negative for better matches
        snippet = _make_snippet(content, q, 120)
        results.append(SearchResult(
            path=path,
            filename=filename,
            page=page,
            snippet=snippet,
            score=score,
            match_type="keyword",
        ))

    return results


# ---------------------------------------------------------------------------
# Semantic search (TF-IDF cosine similarity, no external deps)
# ---------------------------------------------------------------------------

class TfidfIndex:
    """Simple in-memory TF-IDF index built from the database."""

    def __init__(self):
        self.doc_vectors: dict[int, Counter] = {}  # doc_id -> term -> count
        self.idf: dict[str, float] = {}
        self.terms: set[str] = set()
        self.doc_info: list[dict] = []  # doc_id -> {path, filename, page}
        self._built = False

    def build(self, folder: str | None = None):
        """Build TF-IDF index from the SQLite database for selected folder."""
        conn = _ensure_db()
        cursor = conn.cursor()

        if folder:
            cursor.execute("""
                SELECT d.path, d.filename, p.page, p.content
                FROM pages_fts p
                JOIN documents d ON d.path = p.path
                WHERE d.path LIKE ?
            """, (f"{folder}%",))
        else:
            cursor.execute("""
                SELECT d.path, d.filename, p.page, p.content
                FROM pages_fts p
                JOIN documents d ON d.path = p.path
            """)

        rows = cursor.fetchall()
        conn.close()

        # Build term frequencies per document
        doc_terms: list[Counter] = []
        doc_info: list[dict] = []
        doc_freq: Counter = Counter()

        for path, filename, page, content in rows:
            tokens = tokenize(content)
            if not tokens:
                continue
            counter = Counter(tokens)
            doc_terms.append(counter)
            doc_info.append({"path": path, "filename": filename, "page": page})
            # Document frequency: how many docs contain each term
            for term in counter:
                doc_freq[term] += 1

        if not doc_terms:
            return

        num_docs = len(doc_terms)
        self.terms = set(doc_freq.keys())
        self.idf = {term: math.log(num_docs / (1 + freq)) for term, freq in doc_freq.items()}
        self.doc_vectors = {}
        for i, counter in enumerate(doc_terms):
            # TF: log-normalized term frequency
            max_tf = max(counter.values()) if counter else 1
            vec = {}
            for term, count in counter.items():
                tf = 1 + math.log(count) if count > 0 else 0
                tf_normalized = tf / (1 + math.log(max_tf))
                vec[term] = tf_normalized * self.idf.get(term, 1.0)
            self.doc_vectors[i] = vec
            self.doc_info.append(doc_info[i])

        self._built = True

    def search(self, query: str, max_results: int = 20) -> list[SearchResult]:
        if not self._built or not self.doc_vectors:
            return []

        query_tokens = tokenize(query)
        if not query_tokens:
            return []

        # Build query vector
        q_counter = Counter(query_tokens)
        q_max = max(q_counter.values())
        q_vec = {}
        for term, count in q_counter.items():
            if term in self.idf:
                tf = 1 + math.log(count)
                tf_norm = tf / (1 + math.log(q_max))
                q_vec[term] = tf_norm * self.idf[term]

        if not q_vec:
            return []

        # Cosine similarity with each document vector
        scored = []
        for i, vec in self.doc_vectors.items():
            if i >= len(self.doc_info):
                continue
            dot = sum(q_vec.get(t, 0) * vec.get(t, 0) for t in q_vec)
            q_norm = math.sqrt(sum(v * v for v in q_vec.values()))
            d_norm = math.sqrt(sum(v * v for v in vec.values()))
            if q_norm == 0 or d_norm == 0:
                continue
            similarity = dot / (q_norm * d_norm)
            if similarity > 0.01:
                scored.append((similarity, i))

        scored.sort(reverse=True)

        results = []
        for score, i in scored[:max_results]:
            info = self.doc_info[i] if i < len(self.doc_info) else {}
            results.append(SearchResult(
                path=info.get("path", ""),
                filename=info.get("filename", ""),
                page=info.get("page", 1),
                snippet=self._get_snippet(i, query),
                score=round(score, 4),
                match_type="semantic",
            ))

        return results

    def _get_snippet(self, doc_idx: int, query: str) -> str:
        conn = _ensure_db()
        try:
            info = self.doc_info[doc_idx]
            cursor = conn.cursor()
            cursor.execute(
                "SELECT content FROM pages_fts WHERE path = ? AND page = ?",
                (info["path"], info["page"]),
            )
            row = cursor.fetchone()
            content = row[0] if row else ""
        except Exception:
            content = ""
        finally:
            conn.close()
        return _make_snippet(content, query, 150)


# Global TF-IDF index (lazy-built)
_tfidf_cache: TfidfIndex | None = None
_tfidf_lock = threading.Lock()

def get_tfidf(folder: str | None = None) -> TfidfIndex:
    """Get (or build) the cached TF-IDF index."""
    global _tfidf_cache
    with _tfidf_lock:
        if _tfidf_cache is None:
            _tfidf_cache = TfidfIndex()
            _tfidf_cache.build(folder)
        return _tfidf_cache


def invalidate_tfidf():
    """Force TF-IDF index rebuild on next query."""
    global _tfidf_cache
    with _tfidf_lock:
        _tfidf_cache = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_snippet(text: str, query: str, target_len: int = 120) -> str:
    """Create a context snippet around the first match of query in text."""
    if not text:
        return ""

    # Clean up text
    text = re.sub(r'\s+', ' ', text).strip()
    if not text:
        return ""

    query_lower = query.lower().strip()
    if not query_lower:
        return text[:target_len] + ("..." if len(text) > target_len else "")

    # Find query tokens in text
    tokens = query_lower.split()
    text_lower = text.lower()
    first_pos = len(text)

    for t in tokens:
        pos = text_lower.find(t)
        if pos >= 0 and pos < first_pos:
            first_pos = pos

    if first_pos >= len(text):
        return text[:target_len] + ("..." if len(text) > target_len else "")

    # Center snippet around match
    start = max(0, first_pos - target_len // 2)
    end = min(len(text), start + target_len)

    prefix = "..." if start > 0 else ""
    suffix = "..." if end < len(text) else ""
    return prefix + text[start:end].strip() + suffix


def get_indexed_docs() -> list[dict]:
    """List all indexed documents with metadata."""
    conn = _ensure_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT path, filename, page_count, total_chars, last_indexed
        FROM documents
        ORDER BY filename
    """)
    rows = cursor.fetchall()
    conn.close()
    return [
        {"path": r[0], "filename": r[1], "pages": r[2], "chars": r[3], "indexed": r[4]}
        for r in rows
    ]


def get_indexed_folders() -> list[str]:
    """List tracked folders."""
    conn = _ensure_db()
    cursor = conn.cursor()
    cursor.execute("SELECT path FROM folders ORDER BY path")
    rows = cursor.fetchall()
    conn.close()
    return [r[0] for r in rows]


def remove_folder(folder_path: str) -> int:
    """Remove a folder and all documents indexed from it. Returns count removed."""
    conn = _ensure_db()
    cursor = conn.cursor()
    folder = str(Path(folder_path).expanduser().resolve())
    cursor.execute("DELETE FROM folders WHERE path = ?", (folder,))
    cursor.execute("SELECT path FROM documents WHERE path LIKE ?", (f"{folder}%",))
    doc_paths = [r[0] for r in cursor.fetchall()]
    for dp in doc_paths:
        cursor.execute("DELETE FROM pages_fts WHERE path = ?", (dp,))
    cursor.execute("DELETE FROM documents WHERE path LIKE ?", (f"{folder}%",))
    conn.commit()
    removed = cursor.rowcount
    conn.close()
    invalidate_tfidf()
    return removed


def clear_index():
    """Delete the entire index."""
    conn = _ensure_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM pages_fts")
    cursor.execute("DELETE FROM documents")
    cursor.execute("DELETE FROM folders")
    conn.commit()
    conn.close()
    invalidate_tfidf()
