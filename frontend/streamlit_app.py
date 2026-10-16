"""Streamlit frontend for the AI News API.

Talks to the FastAPI service over plain HTTP - it's a separate process from
the API and never touches the database or OpenAI directly. Run the API
first (see README.md), then run this.
"""

import os
from typing import Any

import requests
import streamlit as st

API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8001").rstrip("/")
REQUEST_TIMEOUT_SECONDS = 30

st.set_page_config(page_title="AI News API", page_icon="📰")
st.title("📰 AI News API")
st.caption(f"Talking to API at {API_BASE_URL}")

with st.expander("How this works"):
    st.markdown(
        """
        When you ask a question, the app:

        1. **Searches** a database of indexed news articles for the passages most
           relevant to your question (semantic search, not keyword matching).
        2. **Hands those passages to the AI**, which writes an answer using *only*
           that text - and shows you the **sources** it used.
        3. **Is upfront when the articles don't cover your question.** You can still
           get an answer from the AI's general knowledge, but it's clearly labelled
           as *not* coming from the indexed articles and is not verified.
        """
    )

ask_tab, search_tab = st.tabs(["Ask a question", "Search articles"])


def _handle_response(response: requests.Response) -> Any | None:
    """Return parsed JSON, or None after showing a friendly error for bad statuses."""
    if response.status_code == 429:
        st.warning(
            "You're asking faster than the API allows (10 requests per minute per "
            "IP). Please wait a moment and try again."
        )
        return None
    if not response.ok:
        st.error(
            f"The API returned an error (status {response.status_code}). Please try again."
        )
        return None
    return response.json()


def _request(method: str, path: str, **kwargs: Any) -> Any | None:
    try:
        response = requests.request(
            method, f"{API_BASE_URL}{path}", timeout=REQUEST_TIMEOUT_SECONDS, **kwargs
        )
    except requests.exceptions.ConnectionError:
        st.error(
            f"Couldn't reach the API at {API_BASE_URL}. Is it running? "
            "(`uv run uvicorn app.main:app --port 8001`, and set API_BASE_URL "
            "if it's not on the default port.)"
        )
        return None
    except requests.exceptions.Timeout:
        st.error("The API took too long to respond. Please try again.")
        return None
    return _handle_response(response)


def _post_ask(
    question: str, limit: int, detailed: bool, allow_general_knowledge: bool
) -> dict[str, Any] | None:
    result: dict[str, Any] | None = _request(
        "POST",
        "/ask/",
        json={
            "question": question,
            "limit": limit,
            "style": "detailed" if detailed else "concise",
            "allow_general_knowledge": allow_general_knowledge,
        },
    )
    return result


def _get_search(query: str, limit: int) -> list[dict[str, Any]] | None:
    results: list[dict[str, Any]] | None = _request(
        "GET", "/search/", params={"q": query, "limit": limit}
    )
    return results


EXAMPLE_QUESTIONS = [
    "What is the coding-agent harness study about, and what did it find?",
    "Summarize the main AI news in the indexed articles.",
    "How did the Conway's conjecture proof get built, and what did it cost?",
]


def _render_answer(result: dict[str, Any]) -> None:
    """Show the answer as normal text, with a clear label for where it came from."""
    source = result.get("answer_source", "articles" if result["supported"] else "none")

    if source == "articles":
        st.caption("Answered from the indexed news articles")
        st.markdown(result["answer"])
    elif source == "general_knowledge":
        st.info(
            "The indexed articles don't cover this question, so the answer below comes from "
            "the AI's general knowledge. It is not backed by any article and isn't verified."
        )
        st.markdown(result["answer"])
    else:
        st.warning(
            "The indexed articles don't contain enough information to answer this question."
        )

    if result["citations"]:
        st.subheader("Sources")
        shown: set[str] = set()
        for citation in result["citations"]:
            if citation["url"] in shown:
                continue
            shown.add(citation["url"])
            with st.expander(citation["title"]):
                st.markdown(f"[Open article]({citation['url']})")
                st.caption("Passage used:")
                st.write(citation["chunk_content"])
    elif result.get("related_articles"):
        st.subheader("Closest articles in the index")
        st.caption("What the index does cover, in case it helps:")
        for article in result["related_articles"]:
            st.markdown(f"- [{article['title']}]({article['url']})")


with ask_tab:
    st.write(
        "Ask a question in plain English. Answers come with the sources they were built from."
    )

    st.caption("Try an example:")
    example_columns = st.columns(len(EXAMPLE_QUESTIONS))
    for column, example in zip(example_columns, EXAMPLE_QUESTIONS, strict=True):
        if column.button(example, key=f"example_{example}", use_container_width=True):
            st.session_state["ask_question"] = example

    question = st.text_input(
        "Your question",
        placeholder="How much RAM did Cloudflare reclaim, and how?",
        key="ask_question",
    )

    with st.expander("Options"):
        detailed = st.checkbox(
            "Detailed answers (uncheck for a short, bare answer)",
            value=True,
            key="ask_detailed",
        )
        allow_general_knowledge = st.checkbox(
            "If the articles don't cover it, answer from the AI's general knowledge "
            "(clearly labelled, unverified)",
            value=True,
            key="ask_general_knowledge",
        )
        ask_limit = st.slider(
            "How many passages to retrieve",
            min_value=1,
            max_value=20,
            value=10,
            key="ask_limit",
        )

    if st.button("Ask", type="primary") and question.strip():
        with st.spinner("Retrieving evidence and writing an answer..."):
            result = _post_ask(question, ask_limit, detailed, allow_general_knowledge)

        if result is not None:
            _render_answer(result)

with search_tab:
    st.write(
        "Raw semantic search over indexed article chunks - no AI-generated answer, just the matches."
    )
    query = st.text_input(
        "Search query",
        placeholder="consistent hashing memory savings",
        key="search_query",
    )
    search_limit = st.slider(
        "Max results", min_value=1, max_value=50, value=5, key="search_limit"
    )

    if st.button("Search", type="primary") and query.strip():
        with st.spinner("Searching..."):
            results = _get_search(query, search_limit)

        if results is not None:
            if not results:
                st.info("No matching articles found.")
            for item in results:
                with st.container(border=True):
                    st.markdown(f"**[{item['title']}]({item['url']})**")
                    st.caption(f"Similarity: {item['similarity']:.3f}")
                    st.write(item["chunk_content"])
