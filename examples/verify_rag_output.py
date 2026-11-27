#!/usr/bin/env python3
"""Minimal library integration example for citecheck."""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Allow running without an editable install.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from citecheck import verify  # noqa: E402


def main() -> int:
    payload_path = Path(__file__).with_name("sample_payload.json")
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    result = verify(answer=payload["answer"], sources=payload["sources"])
    print(
        f"ok={result.ok} errors={result.errors} warnings={result.warnings} "
        f"citations={result.citations_checked}"
    )
    if not result.ok:
        for finding in result.findings:
            print(f"  [{finding.severity}] {finding.rule}: {finding.message}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
