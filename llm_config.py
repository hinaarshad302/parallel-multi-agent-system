
import os
import streamlit as st
from crewai import LLM


def get_secret(name: str) -> str:
    """Get a secret from Streamlit Cloud or environment variables."""
    try:
        value = st.secrets.get(name, "")
    except Exception:
        value = ""

    return str(value or os.getenv(name, "")).strip()


def get_llm() -> LLM:
    api_key = get_secret("GROQ_API_KEY")

    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY missing hai. "
            "Streamlit Cloud ke App Settings > Secrets mein add karein."
        )

    # Lighter supported Groq model
    model_id = get_secret("GROQ_MODEL") or "openai/gpt-oss-20b"

    return LLM(
        model=f"groq/{model_id}",
        api_key=api_key,
        temperature=0.2,
        max_tokens=2048,
        timeout=120,
        max_retries=1,
    )
