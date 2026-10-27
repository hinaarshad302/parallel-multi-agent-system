"""
Parallel Multi-Agent AI System
Streamlit application with Supabase authentication.
Payments are not activated by this application.
"""

from __future__ import annotations

import logging
import os
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import streamlit as st
from supabase import Client, create_client
from crew_runner import run_user_task as run_task


# --------------------------------------------------
# 1. APP CONFIGURATION
# --------------------------------------------------

st.set_page_config(
    page_title="Parallel Multi-Agent AI System",
    page_icon="🤖",
    layout="wide",
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("parallel_agents")

MAX_TASK_LENGTH = 5000
FREE_DAILY_LIMIT = 5
TASKS_TABLE = "task_history"
SUBSCRIPTIONS_TABLE = "subscriptions"


# --------------------------------------------------
# 2. SECRETS AND SUPABASE CLIENT
# --------------------------------------------------

def get_setting(name: str, default: str = "") -> str:
    try:
        value = st.secrets.get(name)
        if value is not None:
            return str(value).strip()
    except Exception:
        pass

    return os.environ.get(name, default).strip()


def normalize_supabase_url(raw_url: str) -> str:
    """Accept the project URL, not a REST/Auth endpoint URL."""
    parsed = urlsplit(raw_url.strip())

    if parsed.scheme != "https" or not parsed.netloc:
        raise RuntimeError("Supabase URL valid HTTPS URL honi chahiye.")

    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise RuntimeError("Supabase URL configuration check karein.")

    path = parsed.path.rstrip("/")

    for suffix in ("/rest/v1", "/auth/v1"):
        if path.endswith(suffix):
            path = path[:-len(suffix)].rstrip("/")

    if path:
        raise RuntimeError(
            "SUPABASE_URL mein sirf project URL hona chahiye; "
            "extra path remove karein."
        )

    return urlunsplit((parsed.scheme, parsed.netloc, "", "", ""))


def get_supabase_config() -> tuple[str, str]:
    raw_url = get_setting("SUPABASE_URL")
    key = get_setting("SUPABASE_ANON_KEY")

    if not raw_url or not key:
        raise RuntimeError("Supabase configuration missing hai.")

    return normalize_supabase_url(raw_url), key


def get_supabase_client() -> Client:
    url, key = get_supabase_config()
    client = create_client(url, key)

    token = st.session_state.get("access_token")
    if token:
        client.postgrest.auth(token)
