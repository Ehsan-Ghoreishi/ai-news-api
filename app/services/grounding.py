"""Checks that an answer the model calls supported is really backed by the retrieved chunks."""

import re

MIN_EVIDENCE_CHARS = 8

_QUOTES = str.maketrans({"\u2019": "'", "\u2018": "'", "\u201c": '"', "\u201d": '"', "\u00a0": " "})


def normalize(text: str) -> str:
    """Lowercase, unify curly quotes and collapse whitespace."""
    return re.sub(r"\s+", " ", text.translate(_QUOTES)).strip().lower()


def squash(text: str) -> str:
    """Words and numbers only, lowercase, single-spaced.

    Punctuation, markdown and table pipes are dropped, so a table row quoted as prose
    ('| Severity | 8.1 High |' vs 'Severity: 8.1 High') still matches, while the words and
    numbers must be identical and in the same order.
    """
    return " ".join(re.findall(r"[a-z0-9]+", text.translate(_QUOTES).lower()))


def verified_citation_indices(evidence: str, declared: list[int], chunks: list[str]) -> list[int] | None:
    """Return the 0-based indices of the chunks to cite, or None if the evidence is not in any chunk.

    The evidence must appear verbatim (words and numbers, in order) in at least one chunk.
    Chunks the model declared as used (1-based numbers, out-of-range ones ignored) are added.
    This proves the quoted text exists in the retrieved chunks, not that it states the answer.
    """
    needle = squash(evidence)
    if len(needle) < MIN_EVIDENCE_CHARS:
        return None
    padded = f" {needle} "
    found = {i for i, chunk in enumerate(chunks) if padded in f" {squash(chunk)} "}
    if not found:
        return None
    declared_valid = {n - 1 for n in declared if 1 <= n <= len(chunks)}
    return sorted(found | declared_valid)
