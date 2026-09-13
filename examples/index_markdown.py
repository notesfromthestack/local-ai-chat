#!/usr/bin/env python
"""
Example: Index a markdown file or a directory of markdown files via the RAG API.

Usage:
    python examples/index_markdown.py path/to/doc.md
    python examples/index_markdown.py path/to/docs_dir
"""

import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).parent.parent))

from api.app.document_processor import chunk_text, extract_text_from_markdown


def index_file(md_path: Path, api_url: str) -> int:
    print(f"Processing: {md_path}")
    text = extract_text_from_markdown(str(md_path))
    chunks = chunk_text(text)
    print(f"  {len(text)} chars -> {len(chunks)} chunks")

    metadata = [
        {"source": str(md_path), "chunk_index": i} for i in range(len(chunks))
    ]

    response = httpx.post(
        f"{api_url}/rag/index",
        json={"texts": chunks, "metadata": metadata},
        timeout=60.0,
    )
    response.raise_for_status()
    result = response.json()
    print(f"  Indexed {result['indexed_count']} chunks")
    return result["indexed_count"]


def main(target: str, api_url: str = "http://localhost:8000") -> None:
    path = Path(target)
    if not path.exists():
        print(f"Error: not found: {target}")
        sys.exit(1)

    if path.is_file():
        files = [path]
    else:
        files = sorted(path.rglob("*.md"))
        if not files:
            print(f"Error: no .md files found under {target}")
            sys.exit(1)

    total = 0
    for f in files:
        total += index_file(f, api_url)

    print(f"\nDone. Indexed {total} chunks from {len(files)} file(s).")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python examples/index_markdown.py <file.md | dir>")
        sys.exit(1)
    main(sys.argv[1])
