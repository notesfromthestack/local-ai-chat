import logging
import re
from pathlib import Path
from typing import List

from api.app.config import settings

logger = logging.getLogger(__name__)

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)


def extract_text_from_markdown(file_path: str) -> str:
    """Read a markdown file and return its raw text."""
    logger.info(f"Reading markdown file: {file_path}")
    text = Path(file_path).read_text(encoding="utf-8")
    logger.info(f"Read {len(text)} characters from {file_path}")
    return text


def _split_by_headings(text: str) -> List[tuple]:
    """Split markdown into (heading_path, section_text) tuples.

    heading_path is the stack of ancestor headings joined by ' > ', e.g. 'Intro > Setup'.
    Content before any heading is grouped under an empty path.
    """
    matches = list(_HEADING_RE.finditer(text))
    if not matches:
        return [("", text)]

    sections: List[tuple] = []
    heading_stack: List[tuple] = []  # (level, title)

    preamble = text[: matches[0].start()].strip()
    if preamble:
        sections.append(("", preamble))

    for i, m in enumerate(matches):
        level = len(m.group(1))
        title = m.group(2).strip()

        while heading_stack and heading_stack[-1][0] >= level:
            heading_stack.pop()
        heading_stack.append((level, title))

        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        section = text[start:end].strip()
        if section:
            path = " > ".join(t for _, t in heading_stack)
            sections.append((path, section))

    return sections


def chunk_text(text: str, chunk_size: int = None, overlap: int = None) -> List[str]:
    """Chunk markdown heading-aware, then size-limit within each section.

    The first chunk of each section is prefixed with its heading path (e.g.
    'Intro > Setup') to preserve context for retrieval. Continuation chunks
    within the same section don't repeat the prefix — they use the overlap
    from the previous chunk instead so the model sees a smooth handoff.
    """
    chunk_size = chunk_size or settings.rag_chunk_size
    overlap = overlap or settings.rag_chunk_overlap

    chunks: List[str] = []

    for path, section in _split_by_headings(text):
        prefix = f"[{path}]\n\n" if path else ""
        first_budget = max(1, chunk_size - len(prefix))

        if len(section) <= first_budget:
            chunks.append(prefix + section)
            continue

        chunks.append(prefix + section[:first_budget])
        start = first_budget - overlap
        while start < len(section):
            chunks.append(section[start : start + chunk_size])
            start += chunk_size - overlap

    logger.info(
        f"Split markdown into {len(chunks)} chunks (size={chunk_size}, overlap={overlap})"
    )
    return chunks
