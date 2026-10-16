import os

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("DATABASE_URL", "postgresql://user:pass@localhost/db")

import unittest

from app.services.grounding import normalize, verified_citation_indices

CHUNKS = [
    "Cloudflare operates at a scale so big. That allowed us to reclaim more than 100TB of RAM globally.",
    "Unrelated text about Wine on Linux.",
    "The company\u2019s \u201cquick tunnels\u201d are free.",
]


class NormalizeTests(unittest.TestCase):
    def test_collapses_whitespace_and_case(self):
        self.assertEqual(normalize("  Hello\n  WORLD "), "hello world")

    def test_unifies_curly_quotes(self):
        self.assertEqual(normalize("it\u2019s \u201cok\u201d"), 'it\'s "ok"')


class VerifiedCitationIndicesTests(unittest.TestCase):
    def test_returns_chunk_containing_the_evidence(self):
        self.assertEqual(
            verified_citation_indices("reclaim more than 100TB of RAM globally", [], CHUNKS), [0]
        )

    def test_matches_despite_quote_style_and_spacing(self):
        evidence = 'The company\'s "quick   tunnels" are free'
        self.assertEqual(verified_citation_indices(evidence, [], CHUNKS), [2])

    def test_rejects_evidence_that_is_in_no_chunk(self):
        evidence = "Typesafe AI raised $870M at a $7.5B valuation"
        self.assertIsNone(verified_citation_indices(evidence, [1], CHUNKS))

    def test_rejects_empty_or_too_short_evidence(self):
        for evidence in ("", "   ", "100TB"):
            self.assertIsNone(verified_citation_indices(evidence, [1], CHUNKS))

    def test_adds_declared_chunks_deduplicated_in_retrieval_order(self):
        got = verified_citation_indices(
            "reclaim more than 100TB of RAM globally", [3, 3, 1, 9, 0, -2], CHUNKS
        )
        self.assertEqual(got, [0, 2])

    def test_table_row_quoted_as_prose_still_matches(self):
        chunks = ["| Severity | 8.1 High, CVSS:3.1/AV:N/AC:L |"]
        evidence = "Severity: 8.1 High, CVSS:3.1/AV:N/AC:L"
        self.assertEqual(verified_citation_indices(evidence, [], chunks), [0])

    def test_numbers_must_match_whole_tokens(self):
        chunks = ["The patch fixes 28 1 percent of cases on average today."]
        self.assertIsNone(verified_citation_indices("8 1 percent of cases", [], chunks))
