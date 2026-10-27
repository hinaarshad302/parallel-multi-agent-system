
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

    return client


# --------------------------------------------------
# 3. SESSION
# --------------------------------------------------

DEFAULTS = {
    "access_token": None,
    "refresh_token": None,
    "user_id": None,
    "user_email": None,
}

for name, value in DEFAULTS.items():
    if name not in st.session_state:
        st.session_state[name] = value


def clear_session() -> None:
    for name, value in DEFAULTS.items():
        st.session_state[name] = value


def validate_email(email: str) -> bool:
    if len(email) > 254:
        return False

    return bool(
        re.fullmatch(
            r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@"
            r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
            r"(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)+",
            email,
        )
    )


def save_auth_session(response: Any) -> bool:
    session = getattr(response, "session", None)
    user = getattr(response, "user", None)

    if not session or not user or not getattr(user, "id", None):
        return False

    access_token = getattr(session, "access_token", None)
    refresh_token = getattr(session, "refresh_token", None)

    if not access_token or not refresh_token:
        return False

    st.session_state.access_token = access_token
    st.session_state.refresh_token = refresh_token
    st.session_state.user_id = str(user.id)
    st.session_state.user_email = getattr(user, "email", "") or ""

    return True


def get_authenticated_user() -> dict[str, str] | None:
    token = st.session_state.get("access_token")
    if not token:
        return None

    try:
        client = get_supabase_client()
        response = client.auth.get_user(token)
        user = getattr(response, "user", None)

        if not user or not getattr(user, "id", None):
            clear_session()
            return None

        st.session_state.user_id = str(user.id)
        st.session_state.user_email = getattr(user, "email", "") or ""

        return {
            "id": str(user.id),
            "email": getattr(user, "email", "") or "",
        }

    except Exception:
        logger.warning("Session verification failed.")
        clear_session()
        return None


# --------------------------------------------------
# 4. LOGIN, SIGNUP AND PASSWORD RESET
# --------------------------------------------------

def render_authentication() -> None:
    st.title("🤖 Parallel Multi-Agent AI System")
    st.write("Apne account mein login karein ya naya account banayein.")

    login_tab, signup_tab, reset_tab = st.tabs(
        ["Login", "Create Account", "Forgot Password"]
    )

    with login_tab:
        with st.form("login_form"):
            email = st.text_input("Email", max_chars=254).strip().lower()
            password = st.text_input(
                "Password", type="password", max_chars=256
            )
            submitted = st.form_submit_button(
                "Login", type="primary", use_container_width=True
            )

        if submitted:
            if not validate_email(email) or not password:
                st.error("Valid email aur password enter karein.")
            else:
                try:
                    response = get_supabase_client().auth.sign_in_with_password(
                        {"email": email, "password": password}
                    )

                    if save_auth_session(response):
                        st.success("Login successful.")
                        st.rerun()
                    else:
                        st.warning(
                            "Login session nahi mili. Agar email verification "
                            "enabled hai to pehle email verify karein."
                        )

                except Exception:
                    logger.warning("Login request failed.")
                    st.error(
                        "Login nahi ho saka. Email/password, email "
                        "verification aur Supabase configuration check karein."
                    )

    with signup_tab:
        with st.form("signup_form"):
            email = st.text_input(
                "Email address", max_chars=254
            ).strip().lower()
            password = st.text_input(
                "Password (minimum 12 characters)",
                type="password",
                max_chars=256,
            )
            confirm = st.text_input(
                "Confirm password", type="password", max_chars=256
            )
            accepted = st.checkbox(
                "I agree to the website Terms and Privacy Policy."
            )
            submitted = st.form_submit_button(
                "Create Account", use_container_width=True
            )

        if submitted:
            if not validate_email(email):
                st.error("Valid email address enter karein.")
            elif len(password) < 12:
                st.error("Password kam az kam 12 characters ka rakhein.")
            elif password != confirm:
                st.error("Dono passwords match nahi karte.")
            elif not accepted:
                st.error("Terms aur Privacy Policy accept karein.")
            else:
                try:
                    response = get_supabase_client().auth.sign_up(
                        {"email": email, "password": password}
                    )

                    if save_auth_session(response):
                        st.success("Account create ho gaya.")
                        st.rerun()
                    else:
                        st.success(
                            "Signup request process ho gayi. Apni email "
                            "check karein aur verification link par click karein."
                        )

                except Exception:
                    logger.warning("Signup request failed.")
                    st.error(
                        "Account create nahi ho saka. Supabase Auth settings, "
                        "project URL aur Streamlit logs check karein."
                    )

    with reset_tab:
        with st.form("reset_form"):
            email = st.text_input(
                "Account email", max_chars=254
            ).strip().lower()
            submitted = st.form_submit_button("Send Reset Email")

        if submitted:
            if not validate_email(email):
                st.error("Valid email address enter karein.")
            else:
                try:
                    get_supabase_client().auth.reset_password_email(email)
                    st.success(
                        "Agar account maujood hai, reset email bhej di jayegi. "
                        "Inbox aur spam folder check karein."
                    )
                except Exception:
                    logger.warning("Password reset request failed.")
                    st.error(
                        "Reset request process nahi ho saki. "
                        "Supabase Auth settings check karein."
                    )


# --------------------------------------------------
# 5. SUBSCRIPTION STATUS
# --------------------------------------------------

def get_subscription_status(user_id: str) -> dict[str, Any]:
    try:
        response = (
            get_supabase_client()
            .table(SUBSCRIPTIONS_TABLE)
            .select("plan,status,expires_at")
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )

        rows = response.data or []
        if not rows:
            return {"plan": "free", "status": "free", "expires_at": None}

        record = rows[0]
        status = str(record.get("status", "")).lower()
        expires_at = record.get("expires_at")

        active = status == "active"

        if expires_at:
            try:
                expiry = datetime.fromisoformat(
                    expires_at.replace("Z", "+00:00")
                )
                if expiry.tzinfo is None:
                    expiry = expiry.replace(tzinfo=timezone.utc)
                if expiry <= datetime.now(timezone.utc):
                    active = False
            except (ValueError, TypeError):
                active = False

        if not active:
            return {
                "plan": "free",
                "status": "inactive",
                "expires_at": None,
            }

        return {
            "plan": str(record.get("plan", "free")),
            "status": "active",
            "expires_at": expires_at,
        }

    except Exception:
        logger.warning("Subscription lookup failed.")
        return {"plan": "free", "status": "unknown", "expires_at": None}


# --------------------------------------------------
# 6. TASK HISTORY AND DAILY COUNT
# --------------------------------------------------

def get_today_task_count(user_id: str) -> int:
    start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    ).isoformat()

    response = (
        get_supabase_client()
        .table(TASKS_TABLE)
        .select("id", count="exact")
        .eq("user_id", user_id)
        .gte("created_at", start)
        .execute()
    )

    return int(response.count or 0)


def save_task_history(
    user_id: str, task_text: str, result_text: str
) -> None:
    get_supabase_client().table(TASKS_TABLE).insert({
        "user_id": user_id,
        "task": task_text,
        "result": result_text,
    }).execute()


def render_history(user_id: str) -> None:
    st.subheader("Task History")

    try:
        response = (
            get_supabase_client()
            .table(TASKS_TABLE)
            .select("task,result,created_at")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(20)
            .execute()
        )

        rows = response.data or []
        if not rows:
            st.info("Abhi koi task history nahi hai.")
            return

        for index, item in enumerate(rows, start=1):
            label = str(item.get("task", "Task"))[:100]
            with st.expander(f"{index}. {label}"):
                st.caption(str(item.get("created_at", "")))
                st.write(item.get("result", ""))

    except Exception:
        logger.warning("Task history retrieval failed.")
        st.error("History load nahi ho saki. Database policies check karein.")


# --------------------------------------------------
# 7. MAIN DASHBOARD
# --------------------------------------------------

def render_app(user: dict[str, str]) -> None:
    user_id = user["id"]
    email = user["email"]

    with st.sidebar:
        st.title("🤖 Multi-Agent AI")
        st.caption(f"Logged in: {email}")

        page = st.radio(
            "Menu",
            ["Dashboard", "Task History", "Subscription", "Security"],
        )

        if st.button("Logout", use_container_width=True):
            try:
                get_supabase_client().auth.sign_out()
            except Exception:
                logger.warning("Remote logout failed.")
            finally:
                clear_session()
                st.rerun()

    if page == "Dashboard":
        st.title("Parallel Multi-Agent AI System")
        st.write(
            "Apna task likhein. Aapke configured CrewAI agents "
            "task par kaam karenge."
        )

        subscription = get_subscription_status(user_id)
        paid_active = (
            subscription["status"] == "active"
            and subscription["plan"] in {"pro", "premium"}
        )

        try:
            used_today = get_today_task_count(user_id)
        except Exception:
            st.error(
                "Task count verify nahi ho saka. Database configuration "
                "check karein; security ke liye task run nahi kiya gaya."
            )
            return

        if paid_active:
            st.info(f"Plan: {subscription['plan']} — active")
        else:
            st.info(f"Free plan: {used_today}/{FREE_DAILY_LIMIT} tasks aaj")

        task_text = st.text_area(
            "Apna task likhein",
            max_chars=MAX_TASK_LENGTH,
            height=160,
            placeholder="Misal: AI ke faide aur nuqsanat explain karein...",
        )

        if st.button(
            "Run AI Agents", type="primary", use_container_width=True
        ):
            clean_task = task_text.strip()

            if not clean_task:
                st.warning("Pehle task likhein.")
                return

            if not paid_active and used_today >= FREE_DAILY_LIMIT:
                st.warning(
                    "Free daily limit complete ho gayi. Subscription page "
                    "par plan details dekhein."
                )
                return

            with st.spinner("AI agents kaam kar rahe hain..."):
                try:
                    result = run_task(clean_task)

                    if isinstance(result, dict):
                        output = result.get("final_result", result)
                    else:
                        output = result

                    result_text = str(output)

                    save_task_history(user_id, clean_task, result_text)

                    st.subheader("AI Result")
                    st.markdown(result_text)

                    if isinstance(result, dict):
                        details = {
                            key: value
                            for key, value in result.items()
                            if key in {
                                "review_result",
                                "agent_outputs",
                                "search_results",
                            }
                        }
                        if details:
                            with st.expander("Agent outputs"):
                                st.json(details)

                except Exception:
                    logger.exception("AI task execution failed.")
                    st.error(
                        "Task complete nahi ho saka. Groq API configuration, "
                        "CrewAI code aur server logs check karein."
                    )

    elif page == "Task History":
        render_history(user_id)

    elif page == "Subscription":
        st.title("Subscription Plans")
        subscription = get_subscription_status(user_id)

        st.write(f"Current plan: **{subscription['plan']}**")
        st.write(f"Status: **{subscription['status']}**")

        st.warning(
            "Paid subscription activation abhi enabled nahi hai. "
            "Payment provider aur server-side payment verification "
            "configure hone tak kisi payment ko paid plan na samjhein."
        )

    elif page == "Security":
        st.title("Account Security")
        st.markdown(
            """
            - Password aur API keys kisi ke saath share na karein.
            - API keys GitHub source code mein na likhein.
            - Supabase email verification aur RLS policies check karein.
            - Strong password use karein.
            - Account issue par password reset karein.
            """
        )


# --------------------------------------------------
# 8. ENTRY POINT
# --------------------------------------------------

def main() -> None:
    st.markdown(
        """
        <style>
        .block-container {
            padding-top: 1.8rem;
            max-width: 1200px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    try:
        get_supabase_config()
    except Exception:
        st.error(
            "Supabase setup check karein. Streamlit Secrets mein "
            "SUPABASE_URL aur SUPABASE_ANON_KEY sahi honi chahiye. "
            "URL mein /rest/v1 ya /auth/v1 path na ho."
        )
        st.stop()

    user = get_authenticated_user()

    if user is None:
        render_authentication()
    else:
        render_app(user)


if __name__ == "__main__":
    main()
