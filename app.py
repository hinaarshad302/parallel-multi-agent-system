
"""
Nexora AI
Parallel Multi-Agent AI System
Streamlit application with Supabase authentication.
Online payments are not activated.
"""

from __future__ import annotations

import json
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
    page_title="Nexora AI | Multi-Agent AI System",
    page_icon="🌐",
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
        raise RuntimeError("Enter a valid HTTPS Supabase project URL.")

    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise RuntimeError("Check the Supabase URL configuration.")

    path = parsed.path.rstrip("/")

    for suffix in ("/rest/v1", "/auth/v1"):
        if path.endswith(suffix):
            path = path[:-len(suffix)].rstrip("/")

    if path:
        raise RuntimeError(
            "SUPABASE_URL must contain only the Supabase project URL. "
            "Remove the extra URL path."
        )

    return urlunsplit((parsed.scheme, parsed.netloc, "", "", ""))


def get_supabase_config() -> tuple[str, str]:
    raw_url = get_setting("SUPABASE_URL")
    key = get_setting("SUPABASE_ANON_KEY")

    if not raw_url or not key:
        raise RuntimeError("Supabase configuration is missing.")

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


def render_footer() -> None:
    """Display the Nexora AI footer."""
    st.markdown(
        """
        <footer class="app-footer">
            <div class="footer-brand">Nexora AI</div>
            <div class="footer-description">
                AI-powered task planning, execution, and review.
            </div>
            <div class="footer-copyright">
                © 2026 Nexora AI. All rights reserved.
            </div>
        </footer>
        """,
        unsafe_allow_html=True,
    )   
# --------------------------------------------------
# 4. PROFESSIONAL NEXORA AI DESIGN
# --------------------------------------------------

st.markdown(
    """
    <style>
    :root {
        --nexora-teal: #2dd4bf;
        --nexora-dark: #071b22;
        --nexora-text: #102a32;
        --nexora-muted: #64748b;
        --nexora-border: #dbe7e9;
    }

    .stApp {
        background: linear-gradient(135deg, #f8fcfc 0%, #edf7f7 100%);
        color: var(--nexora-text);
    }

    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #071b22 0%, #10333a 100%);
    }

    [data-testid="stSidebar"] * {
        color: #f0fdfa;
    }

    .hero {
        padding: 30px;
        border-radius: 20px;
        color: #ffffff;
        background: linear-gradient(120deg, #071b22, #115e59, #0f766e);
        margin-bottom: 24px;
        border: 1px solid rgba(45, 212, 191, .25);
    }

    .hero h1 {
        color: #ffffff;
        margin: 0 0 10px 0;
        font-size: 2.2rem;
    }

    .hero p {
        color: #ccfbf1;
        margin-bottom: 4px;
        font-size: 1rem;
    }

    .panel {
        background: #ffffff;
        border: 1px solid var(--nexora-border);
        border-radius: 16px;
        padding: 20px;
        margin-bottom: 16px;
        box-shadow: 0 5px 18px rgba(7, 27, 34, .05);
    }

    .brand {
        font-size: 1.65rem;
        font-weight: 800;
        color: #2dd4bf;
        letter-spacing: -.5px;
    }

    .app-footer {
        margin-top: 40px;
        padding: 24px 12px;
        text-align: center;
        border-top: 1px solid #cbdede;
        color: #64748b;
    }

    .footer-brand {
        font-size: 1.15rem;
        font-weight: 800;
        color: #0f766e;
        margin-bottom: 5px;
    }

    .footer-description,
    .footer-copyright {
        font-size: .85rem;
        margin-top: 5px;
    }

    div.stButton > button,
    div.stFormSubmitButton > button {
        border-radius: 10px;
        font-weight: 650;
        min-height: 42px;
        border: 1px solid #0f766e;
    }

    div.stButton > button[kind="primary"],
    div.stFormSubmitButton > button[kind="primary"] {
        background: #0f766e;
        color: #ffffff;
    }

    div.stButton > button[kind="primary"]:hover,
    div.stFormSubmitButton > button[kind="primary"]:hover {
        background: #115e59;
        border-color: #115e59;
    }

    h1, h2, h3 {
        letter-spacing: -.4px;
    }

    [data-testid="stMetric"] {
        background: #ffffff;
        padding: 16px;
        border-radius: 14px;
        border: 1px solid #dbe7e9;
    }

    @media (max-width: 700px) {
        .hero {
            padding: 20px;
        }

        .hero h1 {
            font-size: 1.7rem;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# --------------------------------------------------
# 5. AUTHENTICATION ACTIONS
# --------------------------------------------------

def login_user(email: str, password: str) -> bool:
    client = get_supabase_client()

    response = client.auth.sign_in_with_password({
        "email": email.strip().lower(),
        "password": password,
    })

    return save_auth_session(response)


def signup_user(email: str, password: str) -> bool:
    client = get_supabase_client()

    response = client.auth.sign_up({
        "email": email.strip().lower(),
        "password": password,
    })

    return save_auth_session(response)


def send_password_reset(email: str) -> None:
    client = get_supabase_client()

    redirect_url = get_setting("APP_URL")

    options = {}
    if redirect_url:
        options["redirect_to"] = redirect_url

    client.auth.reset_password_for_email(
        email.strip().lower(),
        **({"options": options} if options else {}),
    )


def logout_user() -> None:
    try:
        token = st.session_state.get("access_token")
        if token:
            get_supabase_client().auth.sign_out()
    except Exception:
        logger.warning("Remote sign-out failed.")

    clear_session()


def show_auth_error(exc: Exception, action: str) -> None:
    """Show helpful messages without exposing secrets."""
    logger.warning("%s failed: %s", action, type(exc).__name__)

    message = str(exc).lower()

    if "invalid login credentials" in message:
        st.error("Invalid email or password. Please try again.")
    elif "email not confirmed" in message:
        st.error("Please confirm your email address before signing in.")
    elif "already registered" in message or "user already registered" in message:
        st.error("An account with this email may already exist.")
    elif "rate limit" in message or "429" in message:
        st.error("Too many requests. Please wait before trying again.")
    else:
        st.error(
            f"{action} could not be completed. "
            "Check your connection and Supabase configuration."
        )


# --------------------------------------------------
# 6. LOGIN / SIGNUP / PASSWORD RESET
# --------------------------------------------------

current_user = get_authenticated_user()

if current_user is None:

    st.markdown(
        """
        <div class="hero">
            <div class="brand">🧠 Nexora AI</div>
            <h1>Intelligent Workflows. Better Results.</h1>
            <p>
                Plan, execute, verify, and deliver with a
                coordinated multi-agent AI system.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    login_tab, signup_tab, reset_tab = st.tabs([
        "Sign In",
        "Create Account",
        "Forgot Password",
    ])

    # ------------------------------
    # SIGN IN
    # ------------------------------

    with login_tab:
        st.subheader("Welcome back")
        st.caption("Sign in to access your AI workspace.")

        with st.form("nexora_login_form"):
            email = st.text_input(
                "Email address",
                key="login_email",
                placeholder="you@example.com",
            )

            password = st.text_input(
                "Password",
                type="password",
                key="login_password",
            )

            submitted = st.form_submit_button(
                "Sign In",
                type="primary",
                use_container_width=True,
            )

        if submitted:
            if not validate_email(email.strip()):
                st.warning("Enter a valid email address.")
            elif not password:
                st.warning("Enter your password.")
            else:
                try:
                    if login_user(email, password):
                        st.rerun()
                    else:
                        st.error(
                            "Sign-in did not return a valid session. "
                            "Check your email confirmation settings."
                        )
                except Exception as exc:
                    show_auth_error(exc, "Sign in")

    # ------------------------------
    # CREATE ACCOUNT
    # ------------------------------

    with signup_tab:
        st.subheader("Create your account")
        st.caption("Create an account to start using Nexora AI.")

        with st.form("nexora_signup_form"):
            new_email = st.text_input(
                "Email address",
                key="signup_email",
                placeholder="you@example.com",
            )

            new_password = st.text_input(
                "Create password",
                type="password",
                key="signup_password",
            )

            confirm_password = st.text_input(
                "Confirm password",
                type="password",
                key="signup_confirm_password",
            )

            submitted = st.form_submit_button(
                "Create Account",
                type="primary",
                use_container_width=True,
            )

        if submitted:
            if not validate_email(new_email.strip()):
                st.warning("Enter a valid email address.")
            elif len(new_password) < 8:
                st.warning(
                    "Your password must contain at least 8 characters."
                )
            elif new_password != confirm_password:
                st.error("The passwords do not match.")
            else:
                try:
                    logged_in = signup_user(new_email, new_password)

                    if logged_in:
                        st.success("Your account has been created.")
                        st.rerun()
                    else:
                        st.success(
                            "Your registration request was accepted. "
                            "Check your email to confirm your account, "
                            "then sign in."
                        )
                except Exception as exc:
                    show_auth_error(exc, "Account creation")

    # ------------------------------
    # PASSWORD RESET
    # ------------------------------

    with reset_tab:
        st.subheader("Reset your password")
        st.caption("Receive a password-reset link by email.")

        with st.form("nexora_reset_form"):
            reset_email = st.text_input(
                "Registered email address",
                key="reset_email",
                placeholder="you@example.com",
            )

            submitted = st.form_submit_button(
                "Send Reset Link",
                use_container_width=True,
            )

        if submitted:
            if not validate_email(reset_email.strip()):
                st.warning("Enter a valid email address.")
            else:
                try:
                    send_password_reset(reset_email)
                    st.success(
                        "If the request was accepted, a reset link "
                        "will be sent to the registered email address."
                    )
                except Exception as exc:
                    show_auth_error(exc, "Password reset")

    render_footer()
    st.stop()  
# --------------------------------------------------
# 7. AUTHENTICATED WORKSPACE
# --------------------------------------------------

user_id = current_user["id"]
user_email = current_user["email"]

try:
    supabase = get_supabase_client()
except Exception:
    logger.exception("Supabase connection failed.")
    st.error("Unable to connect to the database. Check configuration.")
    render_footer()
    st.stop()


# --------------------------------------------------
# 8. SIDEBAR NAVIGATION
# --------------------------------------------------

with st.sidebar:
    st.markdown(
        '<div class="brand">🧠 Nexora AI</div>',
        unsafe_allow_html=True,
    )
    st.caption("Parallel Multi-Agent Workspace")
    st.divider()

    st.caption("SIGNED IN AS")
    st.write(user_email)

    page = st.radio(
        "WORKSPACE",
        [
            "Overview",
            "Run AI Task",
            "Task History",
            "Subscription",
            "Account",
        ],
        key="workspace_page",
    )

    st.divider()
    st.caption("Planner → Worker → Checker → Final Reviewer")

    if st.button("Sign Out", use_container_width=True):
        logout_user()
        st.rerun()


# --------------------------------------------------
# 9. HELPER: TASK HISTORY
# --------------------------------------------------

def load_task_history(limit: int = 50) -> list[dict]:
    response = (
        supabase.table(TASKS_TABLE)
        .select("id, task, result, created_at")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )

    return response.data or []


def save_task_history(task: str, result: Any) -> None:
    serialized_result = json.dumps(
        result,
        ensure_ascii=False,
        default=str,
    )

    supabase.table(TASKS_TABLE).insert({
        "user_id": user_id,
        "task": task,
        "result": serialized_result,
    }).execute()


def parse_saved_result(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value

    return value



# --------------------------------------------------
# 10. WORKSPACE PAGES
# --------------------------------------------------

if page == "Overview":
    st.markdown(
        """
        <div class="hero">
            <h1>Welcome to Nexora AI</h1>
            <p>Plan, execute, verify, and deliver tasks with AI agents.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(
            '<div class="panel"><h3>🧠 Planning</h3>'
            '<p>Break tasks into clear steps.</p></div>',
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown(
            '<div class="panel"><h3>⚙️ Execution</h3>'
            '<p>Generate useful results.</p></div>',
            unsafe_allow_html=True,
        )

    with col3:
        st.markdown(
            '<div class="panel"><h3>✅ Quality Review</h3>'
            '<p>Review results for quality.</p></div>',
            unsafe_allow_html=True,
        )

    try:
        records = load_task_history(limit=50)
        total_tasks = len(records)
    except Exception:
        logger.exception("Could not load task count.")
        total_tasks = 0

    col1, col2 = st.columns(2)
    col1.metric("Recent Saved Tasks", total_tasks)
    col2.metric("AI Agents", 4)

    if st.button("Start a New Task", type="primary"):
        st.session_state.workspace_page = "Run AI Task"
        st.rerun()

    latest = st.session_state.get("latest_task")

    if latest:
        st.divider()
        st.subheader("Latest Result")
        st.write(latest.get("task", "Task unavailable"))

        result = latest.get("result")

        if isinstance(result, dict):
            final_result = result.get("final_result")

            if final_result:
                st.markdown("### Final Answer")
                st.markdown(str(final_result))
            else:
                st.warning("No final answer was returned.")

            review = result.get("review_result")
            if review:
                with st.expander("Quality Review"):
                    st.write(review)

            outputs = result.get("agent_outputs")
            if outputs:
                with st.expander("Individual Agent Outputs"):
                    st.write(outputs)

        elif result is not None:
            st.write(result)


elif page == "Run AI Task":
    st.title("Run AI Task")
    st.write("Enter a task for Nexora AI.")

    task = st.text_area(
        "Describe your task",
        max_chars=MAX_TASK_LENGTH,
        placeholder="Example: Explain AI in simple words.",
        key="new_ai_task",
    )

    if st.button("Run AI Task", type="primary"):
        if not task.strip():
            st.warning("Please enter a task.")
        else:
            try:
                with st.spinner("AI agents are working..."):
                    started = datetime.now(timezone.utc)
                    result = run_task(task.strip())
                    elapsed = (
                        datetime.now(timezone.utc) - started
                    ).total_seconds()

                    st.session_state["latest_task"] = {
                        "task": task.strip(),
                        "result": result,
                        "elapsed_seconds": round(elapsed, 2),
                    }

                    try:
                        save_task_history(task.strip(), result)
                        st.success("Task completed and saved.")
                    except Exception:
                        logger.exception("Could not save task.")
                        st.warning(
                            "Task completed, but saving failed. "
                            "Check Supabase permissions and table columns."
                        )

                    st.rerun()

            except Exception as exc:
                logger.exception("AI task execution failed.")
                st.error("The AI task failed. Please check the logs.")
                st.caption(f"Error type: {type(exc).__name__}")

    latest = st.session_state.get("latest_task")
    if latest:
        st.divider()
        st.subheader("Latest Result")
        st.write(latest.get("task", ""))

        result = latest.get("result")
        if isinstance(result, dict):
            answer = result.get("final_result")
            if answer:
                st.markdown(answer)
            else:
                st.json(result)
        elif result is not None:
            st.write(result)


elif page == "Task History":
    st.title("Task History")

    try:
        records = load_task_history(limit=50)

        if not records:
            st.info("No saved tasks yet.")
        else:
            st.caption(f"{len(records)} recent task(s)")

            for index, record in enumerate(records, start=1):
                title = record.get("task") or f"Task {index}"

                with st.expander(title):
                    st.caption(
                        f"Created: {record.get('created_at', 'Unknown')}"
                    )

                    saved_result = parse_saved_result(
                        record.get("result")
                    )

                    if isinstance(saved_result, (dict, list)):
                        st.json(saved_result)
                    else:
                        st.write(saved_result or "No result saved.")

    except Exception:
        logger.exception("Could not load task history.")
        st.error(
            "Could not load history. Check the task_history table "
            "and its permissions in Supabase."
        )


elif page == "Subscription":
    st.title("Subscription")
    st.subheader("Free Plan")
    st.write(f"Daily task limit: {FREE_DAILY_LIMIT} tasks")
    st.info(
        "Online payments are not activated yet. "
        "Subscription purchases are currently unavailable."
    )


elif page == "Account":
    st.title("Account")

    st.text_input(
        "Email address",
        value=user_email,
        disabled=True,
    )

    st.text_input(
        "User ID",
        value=user_id,
        disabled=True,
    )

    st.divider()

    if st.button("Sign Out", type="primary"):
        logout_user()
        st.rerun()

    render_footer()
