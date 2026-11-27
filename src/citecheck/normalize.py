"""Text and citation-ID normalization helpers."""

from __future__ import annotations

import re

# Bracketed citation markers: [S1], [Source 1], [S1, S2], [doc_2]
CITATION_RE = re.compile(r"\[([^\[\]]+)\]")
# Double-quoted span immediately followed by optional space + citation
QUOTE_CITE_RE = re.compile(r'"([^"]{12,})"\s*(\[[^\[\]]+\])')
# High-specificity factual anchors
ANCHOR_RE = re.compile(
    r"""
    (?:
        \$\s?\d[\d,]*(?:\.\d+)?(?:\s?[MBKmbk])?   # currency
      | \d+(?:\.\d+)?\s?%                        # percentages
      | \b(?:19|20)\d{2}\b                       # 4-digit years 1900-2099
      | \b\d[\d,]*(?:\.\d+)?\b                   # other numbers
    )
    """,
    re.VERBOSE,
)
_SOURCE_PREFIX_RE = re.compile(r"(?i)^source\s+")
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
_WHITESPACE_RE = re.compile(r"\s+")
_OUTER_PUNCT_RE = re.compile(r"^[\W_]+|[\W_]+$", re.UNICODE)
# Markdown constructs whose bracketed spans are not citation markers.
_FENCE_RE = re.compile(r"(?ms)^[ \t]*(?:```|~~~)[^\n]*\n.*?^[ \t]*(?:```|~~~)[ \t]*$")
_INLINE_CODE_RE = re.compile(r"`[^`\n]*`")
_MD_LINK_RE = re.compile(r"\[[^\]\n]*\]\([^\n)]*\)")


def mask_non_prose(text: str) -> str:
    """Blank fenced/inline code and Markdown links, preserving offsets.

    Bracketed spans inside those constructs are formatting, not citation
    markers. Blanking (rather than removing) keeps character positions stable
    so callers can still report the correct sentence index.
    """
    masked = list(text)
    for pattern in (_FENCE_RE, _INLINE_CODE_RE, _MD_LINK_RE):
        for match in pattern.finditer(text):
            for pos in range(match.start(), match.end()):
                if masked[pos] != "\n":
                    masked[pos] = " "
    return "".join(masked)


def collapse_ws(text: str) -> str:
    return _WHITESPACE_RE.sub(" ", text).strip()


def normalize_id(raw: str) -> str:
    """Normalize a citation or source id for lookup.

    ``Source 1`` / ``source 1`` → ``S1``; otherwise strip and collapse whitespace.
    """
    s = collapse_ws(raw)
    if _SOURCE_PREFIX_RE.match(s):
        rest = _SOURCE_PREFIX_RE.sub("", s).strip()
        if rest.isdigit():
            return f"S{rest}"
        return rest
    return s


def normalize_quote(text: str) -> str:
    """Lowercase, collapse whitespace, strip outer punctuation."""
    return _OUTER_PUNCT_RE.sub("", collapse_ws(text).lower())


def extract_citation_ids(marker_inner: str) -> list[str]:
    """Split a citation body into normalized ids (``S1, S2`` → ``['S1', 'S2']``)."""
    parts = re.split(r"\s*,\s*", marker_inner.strip())
    return [normalize_id(p) for p in parts if p.strip()]


def iter_citations(answer: str) -> list[tuple[str, list[str], int, int]]:
    """Return (raw_marker, normalized_ids, start, end) for each ``[...]`` in answer."""
    out: list[tuple[str, list[str], int, int]] = []
    for m in CITATION_RE.finditer(mask_non_prose(answer)):
        inner = m.group(1)
        ids = extract_citation_ids(inner)
        if ids:
            out.append((f"[{inner}]", ids, m.start(), m.end()))
    return out


def split_sentences(answer: str) -> list[tuple[int, str]]:
    """Split answer into 1-indexed (sentence_number, text) pairs."""
    parts = [p.strip() for p in _SENTENCE_SPLIT_RE.split(answer.strip()) if p.strip()]
    return [(i + 1, p) for i, p in enumerate(parts)]


def has_factual_anchor(sentence: str) -> bool:
    # Strip citations so markers like [S1] don't count as anchors via digits.
    cleaned = CITATION_RE.sub(" ", mask_non_prose(sentence))
    return ANCHOR_RE.search(cleaned) is not None


def sentence_index_at(answer: str, pos: int) -> int:
    """1-indexed sentence number containing character offset ``pos``."""
    sentences = split_sentences(answer)
    if not sentences:
        return 1
    cursor = 0
    text = answer.strip()
    for num, sent in sentences:
        idx = text.find(sent, cursor)
        if idx < 0:
            continue
        end = idx + len(sent)
        if idx <= pos < end + 1:  # allow trailing space before next sentence
            return num
        cursor = end
    return sentences[-1][0]
