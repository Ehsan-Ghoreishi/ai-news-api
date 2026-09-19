import re


def score_answer(
    answer_type: str,
    expected_answer: str,
    model_answer: str,
    accepted_answers: list[str] | None = None,
) -> bool:
    if answer_type == "number":
        """Extract the first int/float found in each string (ignoring units like
        "%" or "articles") and compare them as floats."""
        number_pattern = r"-?\d+(?:\.\d+)?"
        expected_match = re.search(number_pattern, expected_answer)
        model_match = re.search(number_pattern, model_answer)
        if not expected_match or not model_match:
            return False
        return float(expected_match.group()) == float(model_match.group())

    if answer_type == "boolean":
        """Extract the leading true/false or yes/no token from model_answer,
        normalize yes->true and no->false, and compare against expected_answer
        (also normalized) case-insensitively."""
        token_pattern = r"^\s*(true|false|yes|no)\b"
        model_match = re.match(token_pattern, model_answer, re.IGNORECASE)
        if not model_match:
            return False

        def normalize(token: str) -> str:
            token = token.lower()
            if token == "yes":
                return "true"
            if token == "no":
                return "false"
            return token

        model_value = normalize(model_match.group(1))
        expected_value = normalize(expected_answer.strip())
        return model_value == expected_value

    if answer_type == "text":
        """Normalize both strings (lowercase, strip, collapse whitespace) and
        return True if model_answer contains expected_answer, or any of
        accepted_answers, as a substring."""

        def normalize(text: str) -> str:
            return re.sub(r"\s+", " ", text.strip().lower())

        normalized_model = normalize(model_answer)
        candidates = [expected_answer] + (accepted_answers or [])
        return any(normalize(candidate) in normalized_model for candidate in candidates)

    raise ValueError(f"Unknown answer_type: {answer_type!r}")
