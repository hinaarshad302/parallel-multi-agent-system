
"""
Parallel Multi-Agent AI System
Security-first Streamlit application.

Important:
- This is a hardened application baseline, NOT a security audit.
- Payments are not activated by this file.
- Configure Supabase Auth, RLS, database policies, secrets and
  server-side payment verification before production billing.
"""

from __future__ import annotations

import os
import re
import logging
from datetime import datetime, timezone
from typing import Any

import streamlit as st
from supabase import create_client, Client

from crew_runner import run_task


# ---------------------------------------------------------
# 1. APPLICATION CONFIGURATION
# ---------------------------------------------------------

st.set_page_config(
    page_title="Parallel Multi-Agent AI System",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("parallel_agents")

MAX_TASK_LENGTH = 5000
FREE_DAILY_LIMIT = 5
TASKS_TABLE = "task_history"
SUBSCRIPTIONS_TABLE = "subscriptions"


# ---------------------------------------------------------
# 2. SAFE CONFIGURATION ACCESS
# ---------------------------------------------------------

def get_setting(name: str, default: str = "") -> str:
    """Read configuration from Streamlit secrets or environment."""
    try:
        value = st.secrets.get(name, None)
        if value is not None:
            return str(value).strip()
    except Exception:
        pass

    return os.environ.get(name, default).strip()


def get_supabase_config() -> tuple[str, str]:
    url = get_setting("SUPABASE_URL")
    key = get_setting("SUPABASE_ANON_KEY")

    if not url or not key:
        raise RuntimeError("Supabase configuration is missing.")

    if not url.startswith("https://"):
        raise RuntimeError("Invalid Supabase URL configuration.")

    return url, key


def get_supabase_client() -> Client:
    """
    Create a session-scoped client.
    Do not cache a mutable authenticated client across users.
    """
    url, key = get_supabase_config()
    client = create_client(url, key)

    access_token = st.session_state.get("access_token")
    if access_token:
        client.postgrest.auth(access_token)

    return client


# ---------------------------------------------------------
# 3. SESSION STATE
# ---------------------------------------------------------

DEFAULTS = {
    "authenticated": False,
    "access_token": None,
    "refresh_token": None,
    "user_id": None,
    "user_email": None,
    "page": "Dashboard",
}

for key, value in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = value


def clear_session() -> None:
    """Clear locally stored authentication state."""
    for key, value in DEFAULTS.items():
        st.session_state[key] = value


def validate_email(email: str) -> bool:
    return bool(
        re.fullmatch(
            r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@"
            r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
            r"(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)+",
            email,
        )
    )


def get_authenticated_user() -> dict[str, Any] | None:
    """
    Verify the access token with Supabase Auth.
    Do not trust only a session_state user ID.
    """
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

        # Always use the ID returned by verified Auth.
        st.session_state.user_id = str(user.id)
        st.session_state.user_email = getattr(user, "email", None)

        return {
            "id": str(user.id),
            "email": getattr(user, "email", "") or "",
        }

    except Exception:
        logger.warning("Authentication verification failed.")
        clear_session()
        return None


# ---------------------------------------------------------
# 4. LOGIN AND SIGNUP
# ---------------------------------------------------------

def save_auth_session(response: Any) -> bool:
    session = getattr(response, "session", None)
    user = getattr(response, "user", None)

    if not session or not user:
        return False

    access_token = getattr(session, "access_token", None)
    refresh_token = getattr(session, "refresh_token", None)

    if not access_token or not refresh_token:
        return False

    st.session_state.authenticated = True
    st.session_state.access_token = access_token
    st.session_state.refresh_token = refresh_token
    st.session_state.user_id = str(user.id)
    st.session_state.user_email = getattr(user, "email", "") or ""

    return True


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
                    client = get_supabase_client()
                    response = client.auth.sign_in_with_password(
                        {"email": email, "password": password}
                    )

                    if save_auth_session(response):
                        st.success("Login successful.")
                        st.rerun()
                    else:
                        st.error(
                            "Login complete nahi hua. Email verification "
                            "ya account status check karein."
                        )

                except Exception:
                    logger.warning("Login attempt failed.")
                    st.error(
                        "Login nahi ho saka. Email/password check karein "
                        "ya kuch dair baad dobara try karein."
                    )

    with signup_tab:
        with st.form("signup_form"):
            new_email = st.text_input(
                "Email address", max_chars=254
            ).strip().lower()
            new_password = st.text_input(
                "Password (minimum 12 characters)",
                type="password",
                max_chars=256,
            )
            confirm_password = st.text_input(
                "Confirm password", type="password", max_chars=256
            )

            accepted = st.checkbox(
                "I agree to the website Terms and Privacy Policy."
            )

            signup = st.form_submit_button(
                "Create Account", use_container_width=True
            )

        if signup:
            if not validate_email(new_email):
                st.error("Valid email address enter karein.")
            elif len(new_password) < 12:
                st.error("Password kam az kam 12 characters ka rakhein.")
            elif new_password != confirm_password:
                st.error("Dono passwords match nahi karte.")
            elif not accepted:
                st.error("Terms aur Privacy Policy accept karein.")
            else:
                try:
                    client = get_supabase_client()
                    response = client.auth.sign_up(
                        {
                            "email": new_email,
                            "password": new_password,
                        }
                    )

                    if save_auth_session(response):
                        st.success("Account create ho gaya.")
                        st.rerun()
                    else:
                        st.success(
                            "Signup request submit ho gayi. Apni email "
                            "check karein aur verification complete karein."
                        )

                except Exception:
                    logger.warning("Signup request failed.")
                    st.error(
                        "Account create nahi ho saka. Dobara try karein."
                    )

    with reset_tab:
        with st.form("reset_form"):
            reset_email = st.text_input(
                "Account email", max_chars=254
            ).strip().lower()
            reset_submit = st.form_submit_button("Send Reset Email")

        if reset_submit:
            if not validate_email(reset_email):
                st.error("Valid email address enter karein.")
            else:
                try:
                    client = get_supabase_client()
                    client.auth.reset_password_email(reset_email)
                    st.success(
                        "Agar account maujood hai, password reset email "
                        "bhej di jayegi. Inbox aur spam folder check karein."
                    )
                except Exception:
                    logger.warning("Password reset request failed.")
                    st.info(
                        "Request process nahi ho saki. Kuch dair baad "
                        "dobara try karein."
                    )


# ---------------------------------------------------------
# 5. SUBSCRIPTION STATUS
# ---------------------------------------------------------

def get_subscription_status(user_id: str) -> dict[str, Any]:
    """
    Read subscription status from the database.
    Never accept a plan or paid status from a browser form.
    The database must have RLS policies restricting rows by auth.uid().
    """
    try:
        client = get_supabase_client()
        response = (
            client.table(SUBSCRIPTIONS_TABLE)
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
            return {"plan": "free", "status": "inactive", "expires_at": None}

        return {
            "plan": str(record.get("plan", "free")),
            "status": "active",
            "expires_at": expires_at,
        }

    except Exception:
        # Fail closed: do not grant paid features when DB checks fail.
        logger.error("Subscription status lookup failed.")
        return {"plan": "free", "status": "unknown", "expires_at": None}


# ---------------------------------------------------------
# 6. TASK QUOTA AND HISTORY
# ---------------------------------------------------------

def get_today_task_count(user_id: str) -> int:
    """Count today's task records using the authenticated database role."""
    try:
        client = get_supabase_client()
        start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        ).isoformat()

        response = (
            client.table(TASKS_TABLE)
            .select("id", count="exact")
            .eq("user_id", user_id)
            .gte("created_at", start)
            .execute()
        )

        return int(response.count or 0)

    except Exception:
        logger.error("Task quota lookup failed.")
        raise RuntimeError("Task limit verify nahi ho saka.")


def save_task_history(
    user_id: str,
    task_text: str,
    result_text: str,
) -> None:
    """Save task history only for the verified user."""
    client = get_supabase_client()
    client.table(TASKS_TABLE).insert(
        {
            "user_id": user_id,
            "task": task_text,
            "result": result_text,
        }
    ).execute()


def render_history(user_id: str) -> None:
    st.subheader("Task History")

    try:
        client = get_supabase_client()
        response = (
            client.table(TASKS_TABLE)
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
        logger.error("Task history retrieval failed.")
        st.error("History load nahi ho saki. Database policies check karein.")


# ---------------------------------------------------------
# 7. MAIN APPLICATION
# ---------------------------------------------------------

def render_app(user: dict[str, Any]) -> None:
    user_id = user["id"]
    email = user["email"]

    with st.sidebar:
        st.title("🤖 Multi-Agent AI")
        st.caption(f"Logged in: {email}")

        selected_page = st.radio(
            "Menu",
            ["Dashboard", "Task History", "Subscription", "Security"],
        )
        st.session_state.page = selected_page

        if st.button("Logout", use_container_width=True):
            try:
                get_supabase_client().auth.sign_out()
            except Exception:
                logger.warning("Remote logout request failed.")
            finally:
                clear_session()
                st.rerun()

    if selected_page == "Dashboard":
        st.title("Parallel Multi-Agent AI System")
        st.write(
            "Apna task likhein. System aapke configured CrewAI agents "
            "ke zariye result generate karega."
        )

        subscription = get_subscription_status(user_id)
        paid_active = subscription["status"] == "active"

        try:
            used_today = get_today_task_count(user_id)
        except Exception:
            st.error(
                "Task limit verify nahi ho saki. Security ke liye task "
                "run nahi kiya gaya."
            )
            return

        if paid_active:
            st.info(
                f"Plan: {subscription['plan']} — active. "
                "Paid plan ki limit server-side enforce honi chahiye."
            )
        else:
            st.info(
                f"Free plan: {used_today}/{FREE_DAILY_LIMIT} tasks aaj."
            )

        task_text = st.text_area(
            "Apna task likhein",
            max_chars=MAX_TASK_LENGTH,
            height=160,
            placeholder="Misal: AI ke faide aur nuqsanat explain karein...",
        )

        run_clicked = st.button(
            "Run AI Agents",
            type="primary",
            use_container_width=True,
        )

        if run_clicked:
            clean_task = task_text.strip()

            if not clean_task:
                st.warning("Pehle task likhein.")
                return

            if len(clean_task) > MAX_TASK_LENGTH:
                st.error("Task bohat lamba hai.")
                return

            if not paid_active and used_today >= FREE_DAILY_LIMIT:
                st.warning(
                    "Aapki free daily limit complete ho gayi. "
                    "Subscription page par plan details dekhein."
                )
                return

            # This UI-level count is not a robust concurrency-safe quota.
            # Enforce real quotas atomically in a trusted server/database
            # function before enabling public production access.
            with st.spinner("AI agents kaam kar rahe hain..."):
                try:
                    result = run_task(clean_task)

                    if isinstance(result, dict):
                        output = result.get("final_result")
                        if output is None:
                            output = result
                    else:
                        output = result

                    result_text = str(output)

                    save_task_history(user_id, clean_task, result_text)

                    st.subheader("AI Result")
                    st.markdown(result_text)

                    if isinstance(result, dict):
                        with st.expander("Agent outputs"):
                            st.json(
                                {
                                    key: value
                                    for key, value in result.items()
                                    if key in {
                                        "review_result",
                                        "agent_outputs",
                                        "search_results",
                                    }
                                }
                            )

                except Exception:
                    # Avoid rendering stack traces or secrets to users.
                    logger.exception("AI task execution failed.")
                    st.error(
                        "Task complete nahi ho saka. API configuration "
                        "aur server logs administrator check kare."
                    )

    elif selected_page == "Task History":
        render_history(user_id)

    elif selected_page == "Subscription":
        st.title("Subscription Plans")
        subscription = get_subscription_status(user_id)

        st.write(f"Current plan: **{subscription['plan']}**")
        st.write(f"Status: **{subscription['status']}**")

        st.markdown(
            """
            ### Payment safety

            - JazzCash/Easypaisa payment abhi is page se process nahi hoti.
            - Payment screenshot ya user-entered transaction ID se plan
              activate nahi hona chahiye.
            - Subscription sirf verified server-side payment callback
              aur database transaction ke baad activate honi chahiye.
            """
        )

        st.warning(
            "Paid subscription activation disabled hai jab tak verified "
            "payment backend configure na ho."
        )

    elif selected_page == "Security":
        st.title("Account Security")

        st.markdown(
            """
            - Apna password kisi ke saath share na karein.
            - API keys ko GitHub code mein na likhein.
            - Supabase par email verification enable rakhein.
            - Strong password aur available MFA options use karein.
            - Suspicious activity par logout karein aur password reset karein.
            """
        )

        st.caption(
            "Account deletion, session revocation, MFA enforcement aur "
            "security audit logs ke liye dedicated backend configuration "
            "aur testing abhi zaroori hai."
        )


# ---------------------------------------------------------
# 8. ENTRY POINT
# ---------------------------------------------------------

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
            "Supabase setup missing hai. Streamlit Secrets mein "
            "SUPABASE_URL aur SUPABASE_ANON_KEY configure karein."
        )
        st.stop()

    user = get_authenticated_user()

    if not user:
        render_authentication()
        return

    render_app(user)


if __name__ == "__main__":
    main()
