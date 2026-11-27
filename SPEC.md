# `citecheck` — Specification (v0.1.0)

Deterministic RAG citation verifier for catching decorative, broken, or ungrounded `[Source]` claims before expensive LLM-as-a-judge evaluation.

---

## 1. Goals & Non-Goals

### Goals
- **Deterministic & Fast:** Verify inline citations in generated answers against retrieved source chunks in `<10ms` using Python 3.11+ standard library only (zero external runtime dependencies).
- **Dual Interface:** Usable both as a zero-bloat Python library (`from citecheck import verify`) and a machine-readable CLI (`citecheck`).
- **Pre-Judge Gate:** Catch structural and lexical citation failures (non-existent source IDs, missing quotes, ungrounded high-specificity claims, unused sources) before spending tokens on LLM-based evaluation.

### Non-Goals (v0.1.0)
- No LLM calls, embeddings, or semantic entailment scoring.
- No network fetching, web scraping, or PDF/HTML ingestion (callers pass plain text or JSON payloads).
- No third-party runtime dependencies.

---

## 2. Input Contract

`citecheck` accepts a JSON payload (via file path, `--stdin`, or Python `dict`) containing an `answer` string and a list of `sources`:

```json
{
  "answer": "Revenue grew 18% in Q3 [S1], driven by enterprise renewals [S2].",
  "sources": [
    {
      "id": "S1",
      "text": "Q3 total revenue grew 18% year-over-year to $42.5M.",
      "title": "Q3 Earnings Release"
    },
    {
      "id": "S2",
      "text": "Net dollar retention reached 114% across enterprise accounts."
    }
  ]
}

```

### Supported Citation Formats in `answer`

* Bracketed source IDs: `[S1]`, `[1]`, `[doc_2]`, `[Source 1]` (normalized to match `source.id`).
* Multi-citations: `[S1, S2]` or `[1][2]`.
* Inline attributed quotes: `"exact or lightly normalized quote" [S1]`.

---

## 3. Verification Rules (v0.1.0)

| Rule ID | Default Severity | Description |
| --- | --- | --- |
| `cite/empty-answer` | `error` | `answer` must not be empty or whitespace-only. |
| `cite/unknown-source` | `error` | Every inline citation marker (`[S3]`, `[99]`) must map to a valid `id` in `sources`. |
| `cite/ungrounded-quote` | `error` | When a double-quoted span (`"..."`, `>= 12` chars) is immediately followed by a citation (`"..." [S1]`), its normalized text (lowercased, collapsed whitespace, stripped outer punctuation) must appear as a substring of the cited source's `text`. |
| `cite/ungrounded-claim` | `warn` | Sentences containing high-specificity factual anchors (numbers, percentages, currency amounts, or 4-digit years) must include at least one citation marker. |
| `cite/unused-source` | `warn` | Provided `sources` entries that are never cited anywhere in `answer` (helps detect context bloat or decorative retrieval). |

*(Note: `--strict` promotes all `warn` findings to `error`.)*

---

## 4. CLI Specification

```bash
citecheck <input.json> [--strict] [--json]
cat payload.json | citecheck --stdin [--strict] [--json]

```

### Options

* `<input.json>`: Path to JSON input file.
* `--stdin`: Read JSON input from standard input.
* `--strict`: Treat warnings (`cite/ungrounded-claim`, `cite/unused-source`) as errors.
* `--json`: Emit machine-readable JSON result to `stdout`.
* `--version`: Print version (`0.1.0`) and exit `0`.

### Deterministic Exit Codes

* `0` — Pass (zero errors; warnings allowed unless `--strict`).
* `1` — Findings / Validation Violations (one or more `error` findings).
* `2` — Runtime / Configuration Error (bad CLI flags, missing file, malformed JSON, invalid schema).

### `--json` Output Schema

```json
{
  "ok": false,
  "version": "0.1.0",
  "summary": {
    "errors": 1,
    "warnings": 1,
    "citations_checked": 2,
    "sources_provided": 2
  },
  "findings": [
    {
      "rule": "cite/unknown-source",
      "severity": "error",
      "sentence": 2,
      "citation": "[S3]",
      "message": "Cited source 'S3' does not exist in sources."
    }
  ]
}

```

---

## 5. Python Library API

```python
from citecheck import verify, CheckResult, Finding

result: CheckResult = verify(
    answer="Revenue grew 18% in Q3 [S1].",
    sources=[{"id": "S1", "text": "Q3 total revenue grew 18% YoY."}],
    strict=False,
)

assert result.ok is True
assert result.errors == 0

```

---

## 6. Architecture & Repository Layout

Core logic across `src/citecheck/` must remain under **600 lines** total with **zero external runtime dependencies**.

```text
citecheck/
├── pyproject.toml              # PEP 621 metadata, console_scripts entrypoint, zero deps
├── Makefile                    # Single gate: `make check` (lint -> typecheck -> test -> examples)
├── SPEC.md                     # This specification
├── README.md                   # 60-second quickstart, CLI + Python usage, Yosr AI footer
├── llms.txt                    # llmstxt.org v2 guide for consuming AI agents
├── AGENTS.md                   # Rules & verification gate for contributing AI agents
├── LICENSE                     # MIT
├── src/
│   └── citecheck/
│       ├── __init__.py         # Exports `verify`, `CheckResult`, `Finding`, `__version__`
│       ├── types.py            # Frozen dataclasses: Source, Finding, CheckResult
│       ├── normalize.py        # Text & citation-ID normalization helpers
│       ├── verifier.py         # Core deterministic rules engine
│       └── cli.py              # argparse CLI, exit codes (0/1/2), human & --json formatters
├── tests/
│   ├── test_verifier.py        # Unit tests for all 5 rules, edge cases, normalization
│   └── test_cli.py             # Subprocess CLI tests for exit codes 0, 1, 2 and --json
└── examples/
    ├── verify_rag_output.py    # Minimal Python library integration example
    └── sample_payload.json     # Sample RAG payload for CLI quickstart

```

---

## 7. Local Verification Gate (`make check`)

Before any commit is tagged `v0.1.0`, `make check` must pass with exit code `0`:

1. **Format / Lint:** `python3 -m py_compile src/citecheck/*.py tests/*.py examples/*.py` (plus `ruff` if installed locally).
2. **Tests:** `python3 -m unittest discover -s tests -v`
3. **Examples Smoke Check:** `python3 examples/verify_rag_output.py` and `PYTHONPATH=src python3 -m citecheck examples/sample_payload.json --json`
4. **Line Ceiling Audit:** Total lines across `src/citecheck/*.py` `< 600`.
