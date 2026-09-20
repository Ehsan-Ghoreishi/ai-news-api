"""Streamlit frontend for the AI News API.

Talks to the FastAPI service over plain HTTP - it's a separate process from
the API and never touches the database or OpenAI directly. Run the API
first (see README.md), then run this.
"""

import os
from typing import Any

import requests
import streamlit as st

API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000").rstrip("/")
REQUEST_TIMEOUT_SECONDS = 30

st.set_page_config(page_title="AI News API", page_icon="📰")
st.title("📰 AI News API")
st.caption(f"Talking to API at {API_BASE_URL}")

with st.expander("How this works"):
    st.markdown(
        """
        This app doesn't let the AI answer from memory. When you ask a
        question, it:

        1. **Searches** a database of indexed news articles for the chunks
           of text most relevant to your question (semantic search, not
           keyword matching).
        2. **Hands those chunks to the AI** and instructs it to answer using
           *only* that text - never its own outside knowledge.
        3. **Checks whether the answer is actually backed by the retrieved
           text.** If it isn't, you get an honest "not enough information"
           instead of a guess, and no sources are cited.

        That's why every answer below comes with a **Supported** flag and,
        when supported, the exact articles it was built from.
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


def _post_ask(question: str, limit: int) -> dict[str, Any] | None:
    result: dict[str, Any] | None = _request(
        "POST", "/ask/", json={"question": question, "limit": limit}
    )
    return result


def _get_search(query: str, limit: int) -> list[dict[str, Any]] | None:
    results: list[dict[str, Any]] | None = _request(
        "GET", "/search/", params={"q": query, "limit": limit}
    )
    return results


with ask_tab:
    st.write(
        "Ask a natural-language question. The answer is grounded strictly in indexed articles."
    )
    question = st.text_input(
        "Your question",
        placeholder="How much RAM did Cloudflare reclaim?",
        key="ask_question",
    )
    ask_limit = st.slider(
        "Max chunks to retrieve for grounding",
        min_value=1,
        max_value=20,
        value=5,
        key="ask_limit",
    )

    if st.button("Ask", type="primary") and question.strip():
        with st.spinner("Retrieving evidence and asking the model..."):
            result = _post_ask(question, ask_limit)

        if result is not None:
            if result["supported"]:
                st.success(f"**Answer:** {result['answer']}")
            else:
                st.warning(f"**Answer:** {result['answer']}")
            st.metric(
                "Supported by retrieved evidence",
                "Yes" if result["supported"] else "No",
            )

            if result["citations"]:
                st.subheader("Sources")
                for citation in result["citations"]:
                    st.markdown(f"- [{citation['title']}]({citation['url']})")
            else:
                st.caption(
                    "No sources cited - the answer wasn't grounded in the retrieved articles."
                )

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
