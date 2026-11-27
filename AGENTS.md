# AGENTS.md

## Project Overview
`citecheck` is a zero-dependency Python 3.11+ CLI and library that deterministically verifies RAG citation markers against retrieved source chunks. Read `SPEC.md` before making changes. Do not expand beyond the v0.1.0 rules or add runtime dependencies.

## Architecture Boundaries
Planned modules under `src/citecheck/` (implement only after Step 1 approval):

```text
__init__.py   # Exports verify, CheckResult, Finding, __version__
types.py      # Frozen dataclasses: Source, Finding, CheckResult
normalize.py  # Text & citation-ID normalization helpers
verifier.py   # Core deterministic rules engine (5 rules)
cli.py        # argparse CLI, exit codes 0/1/2, human & --json output
```

- Keep rule logic in the verifier module; CLI handles I/O and formatting only.
- Total lines across `src/citecheck/*.py` must stay strictly under 600.
- Python 3.11+ standard library only. Zero external runtime dependencies.

## Code Style & Rules
- Prefer small, flat, readable functions. No premature abstractions or unrequested features.
- Frozen dataclasses for public result types. Deterministic output ordering.
- Implement exactly these rules: `cite/empty-answer`, `cite/unknown-source`, `cite/ungrounded-quote`, `cite/ungrounded-claim`, `cite/unused-source`.
- Exit codes: `0` pass, `1` findings (errors), `2` runtime/config error. `--strict` promotes warns to errors.

## Forbidden Patterns
- No LLM calls, embeddings, network I/O, or third-party packages.
- No PDF/HTML ingestion; callers pass plain text or JSON.
- Do not add rules, flags, or config files beyond `SPEC.md` v0.1.0.

## Local Verification Gate
Run this single command before finishing any task or opening a PR:

```bash
make check
```

This runs: `py_compile` (plus `ruff` if installed) → `unittest discover` → examples smoke → LOC audit (`< 600`). All steps must exit `0`.

## Commit Hygiene
Keep commits focused and logical (e.g., core verifier → CLI → tests & examples → README & docs).
