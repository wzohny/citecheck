"""Frozen result types for citecheck."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class Source:
    id: str
    text: str
    title: str | None = None

    @classmethod
    def from_mapping(cls, raw: dict[str, Any]) -> Source:
        sid = raw.get("id")
        text = raw.get("text")
        if not isinstance(sid, str) or not sid.strip():
            raise ValueError("each source requires a non-empty string 'id'")
        if not isinstance(text, str):
            raise ValueError(f"source '{sid}' requires a string 'text'")
        title = raw.get("title")
        if title is not None and not isinstance(title, str):
            raise ValueError(f"source '{sid}' title must be a string if present")
        return cls(id=sid, text=text, title=title)


@dataclass(frozen=True, slots=True)
class Finding:
    rule: str
    severity: str  # "error" | "warn"
    message: str
    sentence: int | None = None
    citation: str | None = None

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "rule": self.rule,
            "severity": self.severity,
            "message": self.message,
        }
        if self.sentence is not None:
            out["sentence"] = self.sentence
        if self.citation is not None:
            out["citation"] = self.citation
        return out


@dataclass(frozen=True, slots=True)
class CheckResult:
    ok: bool
    version: str
    findings: tuple[Finding, ...] = ()
    citations_checked: int = 0
    sources_provided: int = 0
    errors: int = 0
    warnings: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "version": self.version,
            "summary": {
                "errors": self.errors,
                "warnings": self.warnings,
                "citations_checked": self.citations_checked,
                "sources_provided": self.sources_provided,
            },
            "findings": [f.to_dict() for f in self.findings],
        }
