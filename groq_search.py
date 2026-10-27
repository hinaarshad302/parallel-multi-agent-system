
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

    return value or os.getenv(name, "")


def search_web(query: str) -> str:
    """Search with Groq Browser Search and return evidence as JSON text."""

    api_key = _get_secret("GROQ_API_KEY")

    if not api_key:
        return json.dumps({
            "status": "ERROR",
            "search_response": "",
            "executed_tools": [],
            "error": "GROQ_API_KEY is missing.",
        }, ensure_ascii=False, indent=2)

    model = _get_secret("GROQ_MODEL") or "openai/gpt-oss-120b"
    url = "https://api.groq.com/openai/v1/chat/completions"

    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Research the user's task using browser search. Prefer "
                    "official and primary sources. Return source titles, URLs, "
                    "relevant evidence, and the claims each source supports. "
                    "Never invent sources or say you verified something unless "
                    "the returned evidence supports that statement. Clearly "
                    "label claims that could not be verified."
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
            return json.dumps({
                "status": "ERROR",
                "search_response": "",
                "executed_tools": [],
                "error": (
                    f"Groq returned HTTP {response.status_code}: "
                    f"{response.text[:400]}"
                ),
            }, ensure_ascii=False, indent=2)

        data = response.json()
        choices = data.get("choices", [])

        if not choices:
            return json.dumps({
                "status": "ERROR",
                "search_response": "",
                "executed_tools": [],
                "error": "Groq returned no choices in its response.",
            }, ensure_ascii=False, indent=2)

        message = choices[0].get("message", {})

        content = message.get("content", "")
        if not content:
            content = "No textual search evidence was returned."

        result = {
            "status": "SUCCESS",
            "model": model,
            "search_response": content,
            "executed_tools": message.get("executed_tools", []),
        }

        return json.dumps(result, ensure_ascii=False, indent=2)

    except requests.Timeout:
        error = "Groq Browser Search timed out."
    except requests.RequestException as exc:
        error = f"Network request failed: {type(exc).__name__}"
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        error = f"Unexpected Groq response: {type(exc).__name__}"

    return json.dumps({
        "status": "ERROR",
        "search_response": "",
        "executed_tools": [],
        "error": error,
    }, ensure_ascii=False, indent=2)
