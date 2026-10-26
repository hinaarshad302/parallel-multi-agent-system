import os
import streamlit as st
from crewai import LLM


def get_secret(name: str) -> str:
    """Get a secret from Streamlit Cloud first, then environment variables."""
    try:
        value = st.secrets.get(name, "")
    except Exception:
        value = ""
    return value or os.getenv(name, "")


def get_llm() -> LLM:
    api_key = get_secret("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY missing hai. Streamlit Cloud → App settings → Secrets mein add karein."
        )

    model_id = get_secret("GROQ_MODEL") or "openai/gpt-oss-120b"
    return LLM(
        model=f"groq/{model_id}",
        api_key=api_key,
        temperature=0.2,
    )
