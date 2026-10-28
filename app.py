
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
# 10. OVERVIEW
# --------------------------------------------------

if page == "Overview":

    st.markdown(
        """
        <div class="hero">
            <h1>Welcome to Nexora AI</h1>
            <p>
                Plan, execute, verify, and deliver tasks
                with a coordinated multi-agent workflow.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(
            """
            <div class="panel">
                <h3>🧠 Planning</h3>
                <p>Break complex requests into clear steps.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown(
            """
            <div class="panel">
                <h3>⚙️ Execution</h3>
                <p>Generate the requested deliverable.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col3:
        st.markdown(
            """
            <div class="panel">
                <h3>✅ Quality Review</h3>
                <p>Review the output for completeness and quality.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.subheader("Your Workspace")

    try:
        records = load_task_history(limit=50)
        total_tasks = len(records)
    except Exception:
        logger.exception("Could not load task count.")
        total_tasks = 0

    metric1, metric2 = st.columns(2)

    with metric1:
        st.metric("Recent Saved Tasks", total_tasks)

    with metric2:
        st.metric("AI Agents", 4)

    if st.button("Start a New Task", type="primary"):
        st.session_state.workspace_page = "Run AI Task"
        st.rerun()


# --------------------------------------------------
# 11. RUN AI TASK
# --------------------------------------------------

elif page == "Run AI Task":

    st.markdown(
        """
        <div class="hero">
            <h1>Run an AI Task</h1>
            <p>
                Describe your goal. Nexora AI will process it
                through the configured multi-agent workflow.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.info(
        "The workflow uses Planner, Worker, Checker, and Final Reviewer. "
        "Execution time depends on the task and API availability."
    )

    with st.form("nexora_task_form"):
        user_task = st.text_area(
            "Task description",
            placeholder=(
                "Example: Create a beginner-friendly Python roadmap "
                "with weekly goals and practical projects."
            ),
            height=180,
            max_chars=MAX_TASK_LENGTH,
        )

        submitted = st.form_submit_button(
            "Run AI Agents",
            type="primary",
            use_container_width=True,
        )

    if submitted:

        clean_task = user_task.strip()

        if not clean_task:
            st.warning("Enter a task description first.")

        elif len(clean_task) > MAX_TASK_LENGTH:
            st.warning(
                f"Keep your task under {MAX_TASK_LENGTH} characters."
            )

        else:
            import time

            started_at = time.monotonic()

            try:
                with st.spinner(
                    "The AI agents are processing your task. "
                    "Please keep this page open."
                ):
                    result = run_task(clean_task)

                elapsed = round(time.monotonic() - started_at, 1)

                st.session_state["latest_task"] = {
                    "task": clean_task,
                    "result": result,
                    "elapsed_seconds": elapsed,
                }

                st.success(f"Task completed in {elapsed} seconds.")

                try:
                    save_task_history(clean_task, result)
                    st.toast("Task history saved.")
                except Exception:
                    logger.exception("Task history save failed.")
                    st.warning(
                        "The task completed, but it could not be saved "
                        "to history. Check the task_history table and "
                        "its Row Level Security policies."
                    )

            except Exception as exc:
                logger.exception("AI task failed.")
                st.error(
                    "The task could not be completed. "
                    "Review the technical message below."
                )

                # Avoid displaying environment variables or secrets.
                safe_message = str(exc)
                for secret_name in (
                    "GROQ_API_KEY",
                    "SUPABASE_ANON_KEY",
                    "SUPABASE_SERVICE_ROLE_KEY",
                ):
                    secret_value = get_setting(secret_name)
                    if secret_value:
                        safe_message = safe_message.replace(
                            secret_value,
                            "[REDACTED]",
                        )

                st.code(safe_message)


    # ----------------------------------------------
    # DISPLAY LATEST RESULT
    # ----------------------------------------------

    latest = st.session_state.get("latest_task")

    if latest:
        st.divider()
        st.subheader("Latest Result")

        st.markdown("**Task**")
        st.write(latest["task"])

        st.caption(
            f"Execution time: {latest.get('elapsed_seconds', 'N/A')} seconds"
        )

        result = latest["result"]

        if isinstance(result, dict):

            final_result = result.get("final_result")

            if final_result:
                st.markdown("### Final Answer")
                st.markdown(str(final_result))

            review_result = result.get("review_result")

            if review_result:
                with st.expander("Quality Review"):
                    st.markdown(str(review_result))

            search_results = result.get("search_results")

            if search_results:
                with st.expander("Search Evidence"):
                    st.write(search_results)

            agent_outputs = result.get("agent_outputs")

            if agent_outputs:
                with st.expander("Individual Agent Outputs"):
                    for index, item in enumerate(agent_outputs, start=1):

                        if (
                            isinstance(item, (list, tuple))
                            and len(item) >= 2
                        ):
                            title, output = item[0], item[1]
                        else:
                            title = f"Agent {index}"
                            output = item

                        st.markdown(f"**{title}**")
                        st.write(output or "No output available.")

            st.download_button(
                "Download Full Result (JSON)",
                data=json.dumps(
                    result,
                    ensure_ascii=False,
                    indent=2,
                    default=str,
                ),
                file_name="nexora_ai_result.json",
                mime="application/json",
            )

        else:
            st.write(result)


# --------------------------------------------------
# 12. TASK HISTORY
# --------------------------------------------------

elif page == "Task History":

    st.markdown(
        """
        <div class="hero">
            <h1>Task History</h1>
            <p>Review and download your previously saved tasks.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    try:
        records = load_task_history(limit=50)

        if not records:
            st.info("No saved tasks found yet.")

        else:
            st.caption(f"{len(records)} recent records")

            for index, record in enumerate(records, start=1):

                title = (record.get("task") or "Untitled task").strip()

                with st.expander(f"{index}. {title[:100]}"):

                    st.caption(
                        f"Created: {record.get('created_at', 'Unknown')}"
                    )

                    saved_result = parse_saved_result(
                        record.get("result", "")
                    )

                    if isinstance(saved_result, dict):

                        final_result = saved_result.get("final_result")

                        if final_result:
                            st.markdown(str(final_result))
                        else:
                            st.json(saved_result)

                    elif isinstance(saved_result, (list, tuple)):
                        st.json(saved_result)

                    else:
                        st.write(saved_result)

                    st.download_button(
                        "Download Result",
                        data=json.dumps(
                            saved_result,
                            ensure_ascii=False,
                            indent=2,
                            default=str,
                        ),
                        file_name=f"nexora_task_{index}.json",
                        mime="application/json",
                        key=f"history_download_{record.get('id', index)}",
                    )

    except Exception:
        logger.exception("Task history loading failed.")
        st.error(
            "Task history could not be loaded. "
            "Check the task_history table and access policies."
        )


# --------------------------------------------------
# 13. ACCOUNT
# --------------------------------------------------

elif page == "Account":

    st.markdown(
        """
        <div class="hero">
            <h1>Account</h1>
            <p>View your account details.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="panel">', unsafe_allow_html=True)

    st.write("**Email address**")
    st.write(user_email or "Not available")

    st.write("**User ID**")
    st.code(user_id)

    st.write("**Authentication provider**")
    st.write("Supabase")

    st.markdown("</div>", unsafe_allow_html=True) 
# --------------------------------------------------
# 14. SUBSCRIPTION HELPERS
# --------------------------------------------------

def get_subscription() -> dict:
    """
    Read the latest subscription record for this user.
    Expected columns: user_id, plan, status, expires_at.
    """
    try:
        response = (
            supabase.table(SUBSCRIPTIONS_TABLE)
            .select("plan,status,expires_at")
            .eq("user_id", user_id)
            .order("expires_at", desc=True)
            .limit(1)
            .execute()
        )

        records = response.data or []

        if not records:
            return {
                "plan": "Free",
                "status": "free",
                "expires_at": None,
            }

        record = records[0]
        status = str(record.get("status") or "").lower()
        plan = str(record.get("plan") or "Free")
        expires_at = record.get("expires_at")

        active = status in {"active", "trialing"}

        if expires_at:
            try:
                expiry = datetime.fromisoformat(
                    str(expires_at).replace("Z", "+00:00")
                )

                if expiry.tzinfo is None:
                    expiry = expiry.replace(tzinfo=timezone.utc)

                if expiry <= datetime.now(timezone.utc):
                    active = False

            except (ValueError, TypeError):
                active = False

        if active:
            return {
                "plan": plan,
                "status": "active",
                "expires_at": expires_at,
            }

        return {
            "plan": "Free",
            "status": "free",
            "expires_at": expires_at,
        }

    except Exception:
        logger.exception("Subscription lookup failed.")

        # Fail closed: do not grant paid access if verification fails.
        return {
            "plan": "Free",
            "status": "unverified",
            "expires_at": None,
        }


# --------------------------------------------------
# 15. DAILY TASK COUNT
# --------------------------------------------------

def count_tasks_today() -> int:
    """
    Count this user's task records created since UTC midnight.
    Assumes task_history has a created_at timestamp column.
    """
    now = datetime.now(timezone.utc)
    midnight = now.replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    )

    try:
        response = (
            supabase.table(TASKS_TABLE)
            .select("id", count="exact")
            .eq("user_id", user_id)
            .gte("created_at", midnight.isoformat())
            .execute()
        )

        return int(response.count or 0)

    except Exception:
        logger.exception("Daily task count failed.")
        return -1


# --------------------------------------------------
# 16. SUBSCRIPTION PAGE
# --------------------------------------------------

if page == "Subscription":

    st.markdown(
        """
        <div class="hero">
            <h1>Subscription</h1>
            <p>Review your current plan and available features.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    subscription = get_subscription()
    plan = subscription["plan"]
    status = subscription["status"]
    expires_at = subscription.get("expires_at")

    col1, col2 = st.columns(2)

    with col1:
        st.metric("Current Plan", plan)

    with col2:
        st.metric("Subscription Status", status.title())

    if expires_at:
        st.write(f"**Expiration date:** {expires_at}")
    else:
        st.write("**Expiration date:** Not applicable")

    st.divider()

    st.subheader("Free Plan")
    st.markdown(
        """
        - Up to 5 task submissions per day in this app.
        - Access to the configured multi-agent workflow.
        - Task history, subject to database availability.
        """
    )

    st.subheader("Premium Plan")
    st.markdown(
        """
        - Premium access requires a verified active subscription.
        - Features and limits depend on your configured plan.
        - Online payment is not currently connected.
        """
    )

    if status == "unverified":
        st.warning(
            "Your subscription could not be verified. "
            "Paid access is not granted until the database can be checked."
        )

    st.info(
        "Payments are not activated yet. Do not enter payment details "
        "in this app until an official payment provider is integrated."
    )


# --------------------------------------------------
# 17. FINAL FOOTER
# --------------------------------------------------

render_footer() 
