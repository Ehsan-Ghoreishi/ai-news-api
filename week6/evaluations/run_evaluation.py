"""CLI to evaluate the /ask endpoint against a set of known questions."""

import argparse
import json
import sys
from pathlib import Path

import requests

from week6.evaluations.scoring import score_answer

QUESTIONS_PATH = Path(__file__).parent / "questions.json"


def evaluate(base_url: str) -> list[dict]:
    """Run every question against the API and return per-question results.

    Most questions expect a grounded answer backed by a specific source article.
    A few questions (`expect_supported: false`) deliberately ask about things the
    corpus doesn't cover, to check that the API correctly declines to answer
    instead of hallucinating - for those, retrieval_ok doesn't apply.
    """
    questions = json.loads(QUESTIONS_PATH.read_text())

    results = []
    for question in questions:
        response = requests.post(
            f"{base_url}/ask/",
            json={"question": question["question"], "limit": 5},
        )
        response.raise_for_status()
        payload = response.json()

        if not question.get("expect_supported", True):
            retrieval_ok = None
            answer_ok = not payload["supported"]
            end_to_end_ok = answer_ok
        else:
            retrieval_ok = any(
                citation["source_id"] == question["source_id"] for citation in payload["citations"]
            )
            answer_ok = payload["supported"] and score_answer(
                question["answer_type"],
                question["expected_answer"],
                payload["answer"],
                question.get("accepted_answers"),
            )
            end_to_end_ok = retrieval_ok and answer_ok

        results.append(
            {
                "id": question["id"],
                "retrieval_ok": retrieval_ok,
                "answer_ok": answer_ok,
                "end_to_end_ok": end_to_end_ok,
            }
        )

    return results


def report(results: list[dict]) -> float:
    """Print per-question and summary results; return the end-to-end accuracy."""
    for result in results:
        status = "PASS" if result["end_to_end_ok"] else "FAIL"
        retrieval_display = "n/a" if result["retrieval_ok"] is None else result["retrieval_ok"]
        print(f"{status} {result['id']} (retrieval: {retrieval_display}, answer: {result['answer_ok']})")

    total = len(results)
    # Retrieval accuracy only makes sense for questions that expect a specific source.
    retrieval_results = [r["retrieval_ok"] for r in results if r["retrieval_ok"] is not None]
    retrieval_count = sum(retrieval_results)
    retrieval_total = len(retrieval_results)
    answer_count = sum(r["answer_ok"] for r in results)
    end_to_end_count = sum(r["end_to_end_ok"] for r in results)

    if retrieval_total:
        print(f"Retrieval accuracy: {retrieval_count}/{retrieval_total} ({retrieval_count / retrieval_total:.1%})")
    print(f"Answer accuracy: {answer_count}/{total} ({answer_count / total:.1%})")
    print(f"End-to-end accuracy: {end_to_end_count}/{total} ({end_to_end_count / total:.1%})")

    return end_to_end_count / total


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate the /ask endpoint against known questions.")
    parser.add_argument("--base-url", default="http://localhost:8001")
    parser.add_argument("--minimum-accuracy", type=float, default=None)
    args = parser.parse_args()

    results = evaluate(args.base_url)
    end_to_end_accuracy = report(results)

    if args.minimum_accuracy is not None and end_to_end_accuracy < args.minimum_accuracy:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
