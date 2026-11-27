"""Core deterministic citation verification rules."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from citecheck.normalize import (
    collapse_ws,
    extract_citation_ids,
    has_factual_anchor,
    iter_citations,
    normalize_id,
    normalize_quote,
    QUOTE_CITE_RE,
    sentence_index_at,
    split_sentences,
)
from citecheck.types import CheckResult, Finding, Source

__version__ = "0.1.0"


def _coerce_sources(sources: Sequence[Mapping[str, Any] | Source]) -> list[Source]:
    out: list[Source] = []
    for item in sources:
        if isinstance(item, Source):
            out.append(item)
        elif isinstance(item, Mapping):
            out.append(Source.from_mapping(dict(item)))
        else:
            raise ValueError("each source must be a mapping or Source")
    return out


def _severity(default: str, strict: bool) -> str:
    if strict and default == "warn":
        return "error"
    return default


def _quote_in_source(quote: str, source_text: str) -> bool:
    """True if normalized quote appears as a substring of normalized source text."""
    needle = normalize_quote(quote)
    if not needle:
        return True
    hay = collapse_ws(source_text).lower()
    if needle in hay:
        return True
    return needle in normalize_quote(source_text)


def verify(
    answer: str,
    sources: Sequence[Mapping[str, Any] | Source],
    *,
    strict: bool = False,
) -> CheckResult:
    """Verify citation markers in ``answer`` against ``sources``."""
    if not isinstance(answer, str):
        raise ValueError("'answer' must be a string")

    parsed = _coerce_sources(sources)
    by_norm = {normalize_id(src.id): src for src in parsed}
    findings: list[Finding] = []

    if not answer.strip():
        findings.append(
            Finding(
                rule="cite/empty-answer",
                severity="error",
                message="answer must not be empty or whitespace-only.",
            )
        )
        return _finish(findings, 0, len(parsed))

    citations = iter_citations(answer)
    cited_norms: set[str] = set()
    citations_checked = 0

    for raw_marker, ids, start, _end in citations:
        for cid in ids:
            citations_checked += 1
            cited_norms.add(cid)
            if cid not in by_norm:
                findings.append(
                    Finding(
                        rule="cite/unknown-source",
                        severity="error",
                        sentence=sentence_index_at(answer, start),
                        citation=raw_marker if len(ids) == 1 else f"[{cid}]",
                        message=f"Cited source '{cid}' does not exist in sources.",
                    )
                )

    for m in QUOTE_CITE_RE.finditer(answer):
        quote_raw, marker = m.group(1), m.group(2)
        ids = extract_citation_ids(marker[1:-1])
        for cid in ids:
            src = by_norm.get(cid)
            if src is None:
                continue
            if not _quote_in_source(quote_raw, src.text):
                findings.append(
                    Finding(
                        rule="cite/ungrounded-quote",
                        severity="error",
                        sentence=sentence_index_at(answer, m.start()),
                        citation=marker,
                        message=f"Quoted text is not grounded in source '{cid}'.",
                    )
                )

    for num, sent in split_sentences(answer):
        if has_factual_anchor(sent) and not iter_citations(sent):
            findings.append(
                Finding(
                    rule="cite/ungrounded-claim",
                    severity=_severity("warn", strict),
                    sentence=num,
                    message=(
                        "Sentence with high-specificity factual anchors "
                        "has no citation marker."
                    ),
                )
            )

    for src in parsed:
        if normalize_id(src.id) not in cited_norms:
            findings.append(
                Finding(
                    rule="cite/unused-source",
                    severity=_severity("warn", strict),
                    message=f"Source '{src.id}' is never cited in answer.",
                )
            )

    return _finish(findings, citations_checked, len(parsed))


def _finish(
    findings: list[Finding],
    citations_checked: int,
    sources_provided: int,
) -> CheckResult:
    errors = sum(1 for f in findings if f.severity == "error")
    warnings = sum(1 for f in findings if f.severity == "warn")
    return CheckResult(
        ok=errors == 0,
        version=__version__,
        findings=tuple(findings),
        citations_checked=citations_checked,
        sources_provided=sources_provided,
        errors=errors,
        warnings=warnings,
    )
