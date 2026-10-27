
import os
import requests
import streamlit as st


def get_secret(name):
    try:
        value = st.secrets.get(name, "")
    except Exception:
        value = ""
    return value or os.getenv(name, "")


def test_groq_browser_search():
    api_key = get_secret("GROQ_API_KEY")

    if not api_key:
        print("ERROR: GROQ_API_KEY missing.")
        return

    url = "https://api.groq.com/openai/v1/chat/completions"

    payload = {
        "model": "openai/gpt-oss-120b",
        "messages": [
            {
                "role": "user",
                "content": (
                    "Search the web for the official OpenAI GPT-4 "
                    "Technical Report. Return its title and source URL. "
                    "If you cannot find it, say so clearly."
                ),
            }
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

        print("HTTP status:", response.status_code)

        if response.ok:
            print(response.json())
        else:
            print("Search test failed:", response.text[:1000])

    except requests.RequestException as error:
        print("Connection error:", str(error))


if __name__ == "__main__":
    test_groq_browser_search()
