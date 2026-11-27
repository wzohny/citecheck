"""argparse CLI for citecheck (exit codes 0 / 1 / 2)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from citecheck.types import CheckResult
from citecheck.verifier import __version__, verify


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="citecheck",
        description="Deterministic RAG citation verifier.",
    )
    parser.add_argument(
        "input",
        nargs="?",
        help="Path to JSON input file (answer + sources).",
    )
    parser.add_argument(
        "--stdin",
        action="store_true",
        help="Read JSON input from standard input.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Promote warn findings to error.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="Emit machine-readable JSON result to stdout.",
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="Print version and exit 0.",
    )
    return parser.parse_args(argv)


def _load_payload(args: argparse.Namespace) -> dict[str, Any]:
    if args.stdin and args.input:
        raise ValueError("provide either an input file or --stdin, not both")
    if args.stdin:
        raw = sys.stdin.read()
    elif args.input:
        path = Path(args.input)
        if not path.is_file():
            raise FileNotFoundError(f"input file not found: {args.input}")
        raw = path.read_text(encoding="utf-8")
    else:
        raise ValueError("provide an input JSON file path or --stdin")

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"malformed JSON: {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError("input JSON must be an object with 'answer' and 'sources'")
    if "answer" not in data:
        raise ValueError("input JSON missing required field 'answer'")
    if "sources" not in data:
        raise ValueError("input JSON missing required field 'sources'")
    if not isinstance(data["sources"], list):
        raise ValueError("'sources' must be a JSON array")
    return data


def _format_human(result: CheckResult) -> str:
    lines = [
        f"citecheck {result.version}",
        (
            f"{'PASS' if result.ok else 'FAIL'} — "
            f"{result.errors} error(s), {result.warnings} warning(s), "
            f"{result.citations_checked} citation(s) checked, "
            f"{result.sources_provided} source(s)"
        ),
    ]
    for f in result.findings:
        loc = f"sentence {f.sentence}" if f.sentence is not None else "-"
        cite = f.citation or "-"
        lines.append(f"  [{f.severity}] {f.rule} ({loc}, {cite}): {f.message}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    try:
        args = _parse_args(argv)
    except SystemExit as exc:
        code = exc.code
        if code in (None, 0):
            return 0
        return 2 if isinstance(code, int) else 2

    if args.version:
        print(__version__)
        return 0

    try:
        payload = _load_payload(args)
        result = verify(
            answer=payload["answer"],
            sources=payload["sources"],
            strict=args.strict,
        )
    except (OSError, ValueError, TypeError) as exc:
        print(f"citecheck: error: {exc}", file=sys.stderr)
        return 2

    if args.as_json:
        print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
    else:
        print(_format_human(result))

    return 0 if result.ok else 1


if __name__ == "__main__":
    sys.exit(main())
