"""citecheck — deterministic RAG citation verifier."""

from citecheck.types import CheckResult, Finding, Source
from citecheck.verifier import __version__, verify

__all__ = [
    "__version__",
    "CheckResult",
    "Finding",
    "Source",
    "verify",
]
