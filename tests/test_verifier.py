"""Unit tests for citecheck verification rules."""

from __future__ import annotations

import unittest

from citecheck import verify
from citecheck.normalize import normalize_id, normalize_quote, split_sentences


class TestNormalize(unittest.TestCase):
    def test_sentence_split_preserves_common_abbreviations(self) -> None:
        first = "Dr. Patel recorded a change, e.g. 18% vs. last year, i.e. a gain."
        self.assertEqual(
            split_sentences(f"{first} Results followed! Questions remained?"),
            [(1, first), (2, "Results followed!"), (3, "Questions remained?")],
        )

    def test_sentence_split_does_not_match_abbreviation_suffixes(self) -> None:
        self.assertEqual(
            split_sentences("Meet at the backdr. Results followed."),
            [(1, "Meet at the backdr."), (2, "Results followed.")],
        )

    def test_source_one_to_s1(self) -> None:
        self.assertEqual(normalize_id("Source 1"), "S1")
        self.assertEqual(normalize_id("source 1"), "S1")
        self.assertEqual(normalize_id("S1"), "S1")
        self.assertEqual(normalize_id("doc_2"), "doc_2")

    def test_quote_normalization(self) -> None:
        self.assertEqual(
            normalize_quote('  Hello,   World!  '),
            "hello, world",
        )


class TestEmptyAnswer(unittest.TestCase):
    def test_empty(self) -> None:
        r = verify(answer="   ", sources=[{"id": "S1", "text": "x"}])
        self.assertFalse(r.ok)
        self.assertEqual(r.errors, 1)
        self.assertEqual(r.findings[0].rule, "cite/empty-answer")


class TestUnknownSource(unittest.TestCase):
    def test_unknown(self) -> None:
        r = verify(
            answer="Claim [S3].",
            sources=[{"id": "S1", "text": "Claim text here."}],
        )
        self.assertFalse(r.ok)
        rules = [f.rule for f in r.findings]
        self.assertIn("cite/unknown-source", rules)

    def test_source_one_normalization(self) -> None:
        r = verify(
            answer='Revenue grew. "Q3 total revenue grew 18 percent year over year" [Source 1].',
            sources=[
                {
                    "id": "S1",
                    "text": "Q3 total revenue grew 18 percent year over year to $42.5M.",
                }
            ],
        )
        unknown = [f for f in r.findings if f.rule == "cite/unknown-source"]
        self.assertEqual(unknown, [])


class TestMultiCitations(unittest.TestCase):
    def test_comma_multi(self) -> None:
        r = verify(
            answer="Both agree [S1, S2].",
            sources=[
                {"id": "S1", "text": "Alpha says yes."},
                {"id": "S2", "text": "Beta says yes."},
            ],
        )
        self.assertEqual(r.citations_checked, 2)
        self.assertEqual(r.errors, 0)
        unused = [f for f in r.findings if f.rule == "cite/unused-source"]
        self.assertEqual(unused, [])

    def test_adjacent_brackets(self) -> None:
        r = verify(
            answer="Both agree [1][2].",
            sources=[
                {"id": "1", "text": "Alpha."},
                {"id": "2", "text": "Beta."},
            ],
        )
        self.assertEqual(r.citations_checked, 2)
        self.assertTrue(r.ok or r.errors == 0)


class TestUngroundedQuote(unittest.TestCase):
    def test_grounded_quote(self) -> None:
        quote = "Q3 total revenue grew 18% year-over-year"
        r = verify(
            answer=f'Report said "{quote}" [S1].',
            sources=[
                {
                    "id": "S1",
                    "text": "Q3 total revenue grew 18% year-over-year to $42.5M.",
                }
            ],
        )
        bad = [f for f in r.findings if f.rule == "cite/ungrounded-quote"]
        self.assertEqual(bad, [])

    def test_ungrounded_quote(self) -> None:
        r = verify(
            answer='Report said "completely fabricated twelve-plus chars" [S1].',
            sources=[{"id": "S1", "text": "Q3 total revenue grew 18% year-over-year."}],
        )
        bad = [f for f in r.findings if f.rule == "cite/ungrounded-quote"]
        self.assertEqual(len(bad), 1)
        self.assertEqual(bad[0].severity, "error")

    def test_short_quote_ignored(self) -> None:
        # Quotes under 12 chars are not checked by cite/ungrounded-quote.
        r = verify(
            answer='Said "short one" [S1] and nothing else.',
            sources=[{"id": "S1", "text": "Unrelated body text without the quote."}],
        )
        bad = [f for f in r.findings if f.rule == "cite/ungrounded-quote"]
        self.assertEqual(bad, [])


class TestUngroundedClaim(unittest.TestCase):
    def test_citation_after_abbreviation_covers_the_whole_sentence(self) -> None:
        r = verify(
            answer="Revenue grew 18% vs. last year [S1]. Costs later rose 5%.",
            sources=[{"id": "S1", "text": "Revenue grew 18% vs. last year."}],
        )
        claims = [f.sentence for f in r.findings if f.rule == "cite/ungrounded-claim"]
        self.assertEqual(claims, [2])

    def test_warn_without_citation(self) -> None:
        r = verify(
            answer="Revenue grew 18% in Q3.",
            sources=[{"id": "S1", "text": "Q3 total revenue grew 18%."}],
            strict=False,
        )
        claims = [f for f in r.findings if f.rule == "cite/ungrounded-claim"]
        self.assertEqual(len(claims), 1)
        self.assertEqual(claims[0].severity, "warn")
        self.assertTrue(r.ok)  # warnings do not fail unless --strict

    def test_ok_with_citation(self) -> None:
        r = verify(
            answer="Revenue grew 18% in Q3 [S1].",
            sources=[{"id": "S1", "text": "Q3 total revenue grew 18%."}],
        )
        claims = [f for f in r.findings if f.rule == "cite/ungrounded-claim"]
        self.assertEqual(claims, [])


class TestUnusedSource(unittest.TestCase):
    def test_unused_warn(self) -> None:
        r = verify(
            answer="Hello world without numbers [S1].",
            sources=[
                {"id": "S1", "text": "Hello world without numbers."},
                {"id": "S2", "text": "Unused chunk."},
            ],
        )
        unused = [f for f in r.findings if f.rule == "cite/unused-source"]
        self.assertEqual(len(unused), 1)
        self.assertEqual(unused[0].severity, "warn")
        self.assertIn("S2", unused[0].message)


class TestStrict(unittest.TestCase):
    def test_strict_promotes_warns(self) -> None:
        r = verify(
            answer="Revenue grew 18% in Q3.",
            sources=[
                {"id": "S1", "text": "Q3 total revenue grew 18%."},
                {"id": "S2", "text": "Unused."},
            ],
            strict=True,
        )
        self.assertFalse(r.ok)
        self.assertGreater(r.errors, 0)
        self.assertEqual(r.warnings, 0)
        rules = {f.rule for f in r.findings}
        self.assertIn("cite/ungrounded-claim", rules)
        self.assertIn("cite/unused-source", rules)
        for f in r.findings:
            if f.rule in ("cite/ungrounded-claim", "cite/unused-source"):
                self.assertEqual(f.severity, "error")


class TestHappyPath(unittest.TestCase):
    def test_spec_example(self) -> None:
        r = verify(
            answer=(
                "Revenue grew 18% in Q3 [S1], driven by enterprise renewals [S2]."
            ),
            sources=[
                {
                    "id": "S1",
                    "text": "Q3 total revenue grew 18% year-over-year to $42.5M.",
                    "title": "Q3 Earnings Release",
                },
                {
                    "id": "S2",
                    "text": "Net dollar retention reached 114% across enterprise accounts.",
                },
            ],
        )
        self.assertTrue(r.ok)
        self.assertEqual(r.errors, 0)
        self.assertEqual(r.citations_checked, 2)
        self.assertEqual(r.sources_provided, 2)


if __name__ == "__main__":
    unittest.main()
