
import json
import os

import requests
import streamlit as st


def _get_secret(name: str) -> str:
    """Read a secret from Streamlit Secrets or environment variables."""
    try:
        value = st.secrets.get(name, "")
    except Exception:
        value = ""

    return str(value or os.getenv(name, "")).strip()


def _error(message: str) -> str:
    return json.dumps(
        {
            "status": "ERROR",
            "search_response": "",
            "executed_tools": [],
            "error": message,
        },
        ensure_ascii=False,
        indent=2,
    )


def search_web(query: str) -> str:
    """Search using Groq Browser Search and return evidence as JSON."""

    api_key = _get_secret("GROQ_API_KEY")

    if not api_key:
        return _error("GROQ_API_KEY is missing.")

    model = _get_secret("GROQ_MODEL") or "openai/gpt-oss-20b"
    url = "https://api.groq.com/openai/v1/chat/completions"

    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Research the user's task using browser search. "
                    "Prefer official and primary sources. Return source "
                    "titles, URLs, relevant evidence, and the claims each "
                    "source supports. Never invent sources or claim "
                    "verification without supporting evidence. Clearly "
                    "label unverified claims."
                ),
            },
            {"role": "user", "content": query},
        ],
        "tools": [{"type": "browser_search"}],
        "max_tokens": 2048,
    }

    try:
        response = requests.post(
            url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=45,
        )

        if response.status_code == 429:
            return _error(
                "Groq API quota/rate limit reached. Web search is "
                "temporarily unavailable. Try after the limit resets."
            )

        if not response.ok:
            return _error(
                f"Groq Browser Search returned HTTP {response.status_code}: "
                f"{response.text[:300]}"
            )

        data = response.json()
        choices = data.get("choices", [])

        if not choices:
            return _error("Groq returned no choices.")

        message = choices[0].get("message", {})
        content = message.get("content") or ""

        return json.dumps(
            {
                "status": "SUCCESS" if content else "ERROR",
                "model": model,
                "search_response": content,
                "executed_tools": message.get("executed_tools", []),
                "error": "" if content else "No textual search evidence returned.",
            },
            ensure_ascii=False,
            indent=2,
        )

    except requests.Timeout:
        return _error("Groq Browser Search timed out.")
    except requests.RequestException as exc:
        return _error(f"Network request failed: {type(exc).__name__}")
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        return _error(f"Unexpected Groq response: {type(exc).__name__}")
