# citecheck

Deterministic RAG citation verifier for Python 3.11+. Catch decorative, broken, or ungrounded `[Source]` claims in under 10ms—before spending tokens on LLM-as-a-judge.

**Zero external runtime dependencies.** Library + CLI.

## 60-second quickstart

```bash
# From this repo (no install required)
PYTHONPATH=src python3 -m citecheck examples/sample_payload.json

# Or install
pip install -e .
citecheck examples/sample_payload.json --json
```

Expected human output for the sample payload:

```text
citecheck 0.1.0
PASS — 0 error(s), 0 warning(s), 2 citation(s) checked, 2 source(s)
```

### Python

```python
from citecheck import verify

result = verify(
    answer="Revenue grew 18% in Q3 [S1].",
    sources=[{"id": "S1", "text": "Q3 total revenue grew 18% YoY."}],
)
assert result.ok
```

### CLI

```bash
citecheck payload.json [--strict] [--json]
cat payload.json | citecheck --stdin [--strict] [--json]
citecheck --version
```

## Rules (v0.1.0)

| Rule | Default | What it catches |
| --- | --- | --- |
| `cite/empty-answer` | error | Empty / whitespace-only answer |
| `cite/unknown-source` | error | Citation ID not in `sources` |
| `cite/ungrounded-quote` | error | `"quote…" [S1]` (≥12 chars) not found in cited source text |
| `cite/ungrounded-claim` | warn | Sentence with numbers / % / currency / years and no citation |
| `cite/unused-source` | warn | Retrieved source never cited |

`--strict` promotes all warnings to errors.

## Exit codes

| Code | Meaning |
| --- | --- |
| `0` | Pass (zero errors; warnings allowed unless `--strict`) |
| `1` | One or more `error` findings |
| `2` | Runtime / config error (bad flags, missing file, malformed JSON, invalid schema) |

## Verify locally

```bash
make check
```

---

*Built by Wael Zohny — crafting simple, deterministic AI tools at [Yosr AI](https://yosr.ai).*
