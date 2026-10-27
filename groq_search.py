
import os
import json
import requests
import streamlit as st


def _get_secret(name: str) -> str:
    """Read a secret from Streamlit or environment variables."""
    try:
        value = st.secrets.get(name, "")
    except Exception:
        value = ""

    return value or os.getenv(name, "")


def search_web(query: str) -> str:
    """Search the web through Groq Browser Search and return evidence."""

    api_key = _get_secret("GROQ_API_KEY")

    if not api_key:
        return "SEARCH ERROR: GROQ_API_KEY is missing."

    url = "https://api.groq.com/openai/v1/chat/completions"

    payload = {
        "model": _get_secret("GROQ_MODEL")
        or "openai/gpt-oss-120b",
        "messages": [
            {
                "role": "system",
                "content": (
                    "Research the user's request using web search. "
                    "Prefer official and primary sources. Return source "
                    "titles, URLs, relevant evidence, and which claims "
                    "the evidence supports. Never invent a source. "
                    "Clearly label anything you could not verify."
                ),
            },
            {"role": "user", "content": query},
        ],
        "tools": [{"type": "browser_search"}],
    }

    try:
        response = requests.post(
            url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=60,
        )

        if not response.ok:
            return (
                "SEARCH ERROR: Groq returned HTTP "
                f"{response.status_code}. Details: "
                f"{response.text[:500]}"
            )

        data = response.json()
        message = data["choices"][0]["message"]

        result = {
            "search_response": message.get("content", ""),
            "executed_tools": message.get("executed_tools", []),
        }

        return json.dumps(result, ensure_ascii=False, indent=2)

    except (requests.RequestException, ValueError, KeyError, IndexError) as error:
        return f"SEARCH ERROR: {type(error).__name__}: {error}"
