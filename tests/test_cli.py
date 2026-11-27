"""Subprocess CLI tests for citecheck exit codes and flags."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
ENV = {**os.environ, "PYTHONPATH": str(SRC)}


def run_cli(*args: str, stdin: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "citecheck", *args],
        input=stdin,
        capture_output=True,
        text=True,
        env=ENV,
        cwd=str(ROOT),
    )


PASS_PAYLOAD = {
    "answer": "Revenue grew 18% in Q3 [S1].",
    "sources": [{"id": "S1", "text": "Q3 total revenue grew 18% year-over-year."}],
}

FAIL_PAYLOAD = {
    "answer": "Revenue grew 18% in Q3 [S9].",
    "sources": [{"id": "S1", "text": "Q3 total revenue grew 18% year-over-year."}],
}


class TestCliExitCodes(unittest.TestCase):
    def test_exit_0_pass(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
            json.dump(PASS_PAYLOAD, fh)
            path = fh.name
        try:
            proc = run_cli(path)
            self.assertEqual(proc.returncode, 0, proc.stderr)
        finally:
            os.unlink(path)

    def test_exit_1_findings(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
            json.dump(FAIL_PAYLOAD, fh)
            path = fh.name
        try:
            proc = run_cli(path)
            self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        finally:
            os.unlink(path)

    def test_exit_2_missing_file(self) -> None:
        proc = run_cli("/no/such/citecheck-input.json")
        self.assertEqual(proc.returncode, 2)
        self.assertIn("error", proc.stderr.lower())

    def test_exit_2_malformed_json(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
            fh.write("{not-json")
            path = fh.name
        try:
            proc = run_cli(path)
            self.assertEqual(proc.returncode, 2)
        finally:
            os.unlink(path)

    def test_exit_2_bad_schema(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
            json.dump({"answer": "hi"}, fh)
            path = fh.name
        try:
            proc = run_cli(path)
            self.assertEqual(proc.returncode, 2)
        finally:
            os.unlink(path)


class TestCliFlags(unittest.TestCase):
    def test_stdin(self) -> None:
        proc = run_cli("--stdin", "--json", stdin=json.dumps(PASS_PAYLOAD))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        data = json.loads(proc.stdout)
        self.assertTrue(data["ok"])

    def test_json_schema(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
            json.dump(FAIL_PAYLOAD, fh)
            path = fh.name
        try:
            proc = run_cli(path, "--json")
            self.assertEqual(proc.returncode, 1)
            data = json.loads(proc.stdout)
            self.assertIn("ok", data)
            self.assertEqual(data["version"], "0.1.0")
            self.assertIn("summary", data)
            for key in (
                "errors",
                "warnings",
                "citations_checked",
                "sources_provided",
            ):
                self.assertIn(key, data["summary"])
            self.assertIsInstance(data["findings"], list)
            self.assertGreaterEqual(len(data["findings"]), 1)
            finding = data["findings"][0]
            self.assertIn("rule", finding)
            self.assertIn("severity", finding)
            self.assertIn("message", finding)
        finally:
            os.unlink(path)

    def test_version(self) -> None:
        proc = run_cli("--version")
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(proc.stdout.strip(), "0.1.0")

    def test_strict_exit_1(self) -> None:
        payload = {
            "answer": "Revenue grew 18% in Q3.",
            "sources": [{"id": "S1", "text": "Q3 total revenue grew 18%."}],
        }
        proc = run_cli("--stdin", "--strict", stdin=json.dumps(payload))
        self.assertEqual(proc.returncode, 1)


if __name__ == "__main__":
    unittest.main()
