"""
Parallel Multi-Agent AI System
Streamlit + Supabase + CrewAI + Groq
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


# =========================================================
# 1. APP CONFIGURATION
# =========================================================

st.set_page_config(
    page_title="Parallel AI | Multi-Agent Workspace",
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

# Your deployed Streamlit app URL
APP_URL = (
    "https://parallel-multi-agent-system-kijnmteevpxi38tvdrrafi.streamlit.app/"
)


# =========================================================
# 2. LIGHT, PROFESSIONAL DESIGN
# =========================================================

st.markdown(
    """
    <style>
    @import url(
      'https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap'
    );

    :root {
        --page: #f4f7fc;
        --surface: #ffffff;
        --text: #172033;
        --muted: #475569;
        --border: #dce3ef;
        --primary: #4f46e5;
        --primary-dark: #3730a3;
    }

    .stApp {
        background: var(--page) !important;
        color: var(--text) !important;
        font-family: 'DM Sans', Arial, sans-serif !important;
        font-size: 17px !important;
    }

    [data-testid="stHeader"] {
        background: rgba(244, 247, 252, .96) !important;
    }

    [data-testid="stSidebar"] {
        background: #ffffff !important;
        border-right: 1px solid var(--border) !important;
    }

    [data-testid="stSidebar"] * {
        color: var(--text) !important;
    }

    .block-container {
        max-width: 1250px;
        padding-top: 2rem;
        padding-bottom: 3rem;
    }

    h1, h2, h3 {
        font-family: 'Space Grotesk', Arial, sans-serif !important;
        color: #172554 !important;
        letter-spacing: -.025em;
    }

    h1 {
        font-size: clamp(2rem, 4vw, 2.8rem) !important;
    }

    h2 {
        font-size: 2rem !important;
    }

    h3 {
        font-size: 1.45rem !important;
    }

    p, label, .stMarkdown {
        color: #334155;
        font-size: 16px !important;
        line-height: 1.7 !important;
    }

    [data-testid="stCaptionContainer"] {
        color: #475569 !important;
        font-size: 14px !important;
    }

    [data-testid="stTextInput"] input,
    [data-testid="stTextArea"] textarea {
        background: #ffffff !important;
        color: #172033 !important;
        border: 1px solid #cbd5e1 !important;
        border-radius: 10px !important;
        font-size: 16px !important;
        min-height: 44px;
    }

    [data-testid="stTextInput"] input::placeholder,
    [data-testid="stTextArea"] textarea::placeholder {
        color: #64748b !important;
        opacity: 1 !important;
    }

    [data-testid="stTextInput"] input:focus,
    [data-testid="stTextArea"] textarea:focus {
        border-color: #6366f1 !important;
        box-shadow: 0 0 0 1px #6366f1 !important;
    }

    [data-testid="stMetric"] {
        background: #ffffff !important;
        border: 1px solid var(--border) !important;
        border-radius: 16px !important;
        padding: 1rem !important;
        box-shadow: 0 3px 12px rgba(15, 23, 42, .04);
    }

    [data-testid="stMetricLabel"] {
        color: #475569 !important;
        font-size: 14px !important;
    }

    [data-testid="stMetricValue"] {
        color: #172554 !important;
        font-size: 2rem !important;
        font-family: 'Space Grotesk', sans-serif !important;
    }

    .stButton > button,
    [data-testid="stFormSubmitButton"] button {
        border-radius: 10px !important;
        min-height: 45px !important;
        font-size: 16px !important;
        font-weight: 700 !important;
        transition: all .15s ease;
    }

    .stButton > button[kind="primary"],
    [data-testid="stFormSubmitButton"] button[kind="primary"] {
        background: var(--primary) !important;
        color: #ffffff !important;
        border: 1px solid var(--primary) !important;
    }

    .stButton > button[kind="primary"]:hover,
    [data-testid="stFormSubmitButton"] button[kind="primary"]:hover {
        background: var(--primary-dark) !important;
        border-color: var(--primary-dark) !important;
    }

    [data-testid="stTabs"] button {
        color: #334155 !important;
        font-size: 16px !important;
        font-weight: 600 !important;
    }

    [data-testid="stExpander"] {
        background: #ffffff !important;
        border: 1px solid var(--border) !important;
        border-radius: 12px !important;
    }

    [data-testid="stAlert"] {
        border-radius: 12px !important;
    }

    [data-testid="stProgressBar"] > div > div {
        background: #4f46e5 !important;
    }

    .hero {
        padding: 1.8rem;
        margin-bottom: 1.4rem;
        border-radius: 20px;
        border: 1px solid #c7d2fe;
        background: linear-gradient(120deg, #ffffff, #eaf0ff);
        box-shadow: 0 5px 24px rgba(30, 41, 59, .05);
    }

    .eyebrow {
        color: #4338ca;
        text-transform: uppercase;
        letter-spacing: .14em;
        font-size: 13px;
        font-weight: 700;
        margin-bottom: 10px;
    }

    .hero-title {
        font-family: 'Space Grotesk', sans-serif;
        color: #172554;
        font-size: clamp(2rem, 4vw, 2.8rem);
        font-weight: 700;
        line-height: 1.2;
    }

    .hero-copy {
        color: #334155;
        font-size: 17px;
        line-height: 1.7;
        margin-top: 12px;
    }

    .section-kicker {
        color: #4338ca;
        font-size: 13px;
        text-transform: uppercase;
        letter-spacing: .12em;
        font-weight: 700;
        margin: 1rem 0 .6rem;
    }

    .footer-note {
        color: #64748b;
        font-size: 13px;
        text-align: center;
        padding-top: 2rem;
    }

    @media (max-width: 700px) {
        .block-container {
            padding: 1rem .8rem 2rem;
        }

        .hero {
            padding: 1.2rem;
            border-radius: 15px;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# 3. SUPABASE SETTINGS
# =========================================================

def get_setting(name: str, default: str = "") -> str:
    try:
        value = st.secrets.get(name)
        if value is not None:
            return str(value).strip()
    except Exception:
        pass

    return os.environ.get(name, default).strip()


def normalize_supabase_url(raw_url: str) -> str:
    parsed = urlsplit(raw_url.strip())

    if parsed.scheme != "https" or not parsed.netloc:
        raise RuntimeError("Supabase HTTPS URL valid nahi hai.")

    if (
        parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        raise RuntimeError("Supabase URL configuration check karein.")

    path = parsed.path.rstrip("/")

    for suffix in ("/rest/v1", "/auth/v1"):
        if path.endswith(suffix):
            path = path[:-len(suffix)].rstrip("/")

    if path:
        raise RuntimeError(
            "SUPABASE_URL mein sirf project URL hona chahiye."
        )

    return urlunsplit((parsed.scheme, parsed.netloc, "", "", ""))


def get_supabase_config() -> tuple[str, str]:
    raw_url = get_setting("SUPABASE_URL")
    key = get_setting("SUPABASE_ANON_KEY")

    if not raw_url or not key:
        raise RuntimeError(
            "Supabase URL ya publishable/anon key missing hai."
        )

    return normalize_supabase_url(raw_url), key


def get_supabase_client() -> Client:
    url, key = get_supabase_config()
    client = create_client(url, key)

    token = st.session_state.get("access_token")
    if token:
        client.postgrest.auth(token)

    return client


# =========================================================
# 4. SESSION AND EMAIL VALIDATION
# =========================================================

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
        response = get_supabase_client().auth.get_user(token)
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


# =========================================================
# 5. AUTHENTICATION: LOGIN, SIGNUP, RESET PASSWORD
# =========================================================

def render_authentication() -> None:
    st.markdown(
        """
        <div class="hero">
          <div class="eyebrow">PARALLEL AI WORKSPACE</div>
          <div class="hero-title">
            Your AI team.<br>Your ideas. Better results.
          </div>
          <div class="hero-copy">
            Sign in to your workspace and let your configured AI agents
            help you complete complex tasks.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    login_tab, signup_tab, reset_tab = st.tabs(
        ["Login", "Create Account", "Forgot Password"]
    )

    with login_tab:
        with st.form("login_form"):
            email = st.text_input(
                "Email address", max_chars=254
            ).strip().lower()

            password = st.text_input(
                "Password", type="password", max_chars=256
            )

            submitted = st.form_submit_button(
                "Login to Workspace",
                type="primary",
                use_container_width=True,
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
                            "enabled hai to inbox check karein."
                        )

                except Exception as exc:
                    logger.exception("Login request failed.")
                    st.error("Login nahi ho saka.")
                    st.code(str(exc))

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
                "Confirm password",
                type="password",
                max_chars=256,
            )

            accepted = st.checkbox(
                "I agree to the website Terms and Privacy Policy."
            )

            submitted = st.form_submit_button(
                "Create Account",
                type="primary",
                use_container_width=True,
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
                        {
                            "email": email,
                            "password": password,
                            "options": {
                                "email_redirect_to": APP_URL,
                            },
                        }
                    )

                    if save_auth_session(response):
                        st.success("Account create ho gaya.")
                        st.rerun()
                    else:
                        st.success(
                            "Signup request process ho gayi. Apni email "
                            "check karein aur verification link par click karein."
                        )
                        st.info(
                            "Agar verification link localhost par jata hai, "
                            "Supabase Authentication > URL Configuration "
                            "mein Site URL aur Redirect URLs dobara check karein."
                        )

                except Exception as exc:
                    logger.exception("Signup request failed.")
                    st.error("Account create nahi ho saka.")
                    st.warning("Error detail (password share na karein):")
                    st.code(str(exc))

    with reset_tab:
        with st.form("reset_form"):
            email = st.text_input(
                "Account email", max_chars=254
            ).strip().lower()

            submitted = st.form_submit_button(
                "Send Reset Email",
                use_container_width=True,
            )

        if submitted:
            if not validate_email(email):
                st.error("Valid email address enter karein.")
            else:
                try:
                    get_supabase_client().auth.reset_password_email(
                        email,
                        options={"redirect_to": APP_URL},
                    )
                    st.success(
                        "Agar account maujood hai to reset email bhej di jayegi. "
                        "Inbox aur spam folder check karein."
                    )
                except Exception as exc:
                    logger.exception("Password reset request failed.")
                    st.error("Password reset request process nahi ho saki.")
                    st.code(str(exc))


# =========================================================
# 6. SUBSCRIPTION STATUS
# =========================================================

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
            return {
                "plan": "free",
                "status": "free",
                "expires_at": None,
            }

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
        logger.exception("Subscription lookup failed.")
        return {
            "plan": "free",
            "status": "unknown",
            "expires_at": None,
        }


# =========================================================
# 7. TASK HISTORY AND DAILY COUNT
# =========================================================

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
    user_id: str,
    task_text: str,
    result_text: str,
) -> None:
    (
        get_supabase_client()
        .table(TASKS_TABLE)
        .insert(
            {
                "user_id": user_id,
                "task": task_text,
                "result": result_text,
            }
        )
        .execute()
    )


def render_history(user_id: str) -> None:
    st.title("Task History")
    st.caption("Review your previous AI tasks and generated results.")

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
                st.markdown(item.get("result", ""))

    except Exception:
        logger.exception("Task history retrieval failed.")
        st.error("History load nahi ho saki. Database policies check karein.")


# =========================================================
# 8. DASHBOARD AND AI TASK EXECUTION
# =========================================================

def render_dashboard(user: dict[str, str]) -> None:
    user_id = user["id"]

    st.markdown(
        """
        <div class="hero">
          <div class="eyebrow">AI WORKSPACE · MULTI-AGENT ORCHESTRATION</div>
          <div class="hero-title">
            Turn complex tasks into<br>clear results.
          </div>
          <div class="hero-copy">
            Apna task likhein. Aapke configured CrewAI agents task par
            kaam karenge. Clear instructions dein aur AI-generated
            result hasil karein.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    subscription = get_subscription_status(user_id)
    paid_active = (
        subscription["status"] == "active"
        and subscription["plan"] in {"pro", "premium"}
    )

    try:
        used_today = get_today_task_count(user_id)
    except Exception:
        logger.exception("Daily task count failed.")
        st.error(
            "Task count verify nahi ho saka. Database configuration check karein."
        )
        return

    remaining = max(0, FREE_DAILY_LIMIT - used_today)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "CURRENT PLAN",
            subscription["plan"].upper() if paid_active else "FREE",
        )

    with col2:
        st.metric("TASKS USED TODAY", used_today)

    with col3:
        st.metric(
            "TASKS REMAINING",
            "Unlimited" if paid_active else remaining,
        )

    if not paid_active:
        st.progress(min(used_today / FREE_DAILY_LIMIT, 1.0))
        st.caption(
            f"{used_today} of {FREE_DAILY_LIMIT} free daily tasks used"
        )

    st.markdown(
        '<div class="section-kicker">01 / Describe your task</div>',
        unsafe_allow_html=True,
    )

    task_text = st.text_area(
        "Apna task likhein",
        max_chars=MAX_TASK_LENGTH,
        height=200,
        placeholder=(
            "Example: Explain artificial intelligence, give five real-life "
            "examples, and describe its advantages and disadvantages."
        ),
        help="Behtar result ke liye goal, context aur required output likhein.",
    )

    run_clicked = st.button(
        "Run AI Agents  →",
        type="primary",
        use_container_width=True,
    )

    if run_clicked:
        clean_task = task_text.strip()

        if not clean_task:
            st.warning("Pehle task likhein.")
            return

        if not paid_active and used_today >= FREE_DAILY_LIMIT:
            st.warning(
                "Free daily limit complete ho gayi. "
                "Subscription page par plan details dekhein."
            )
            return

        try:
            with st.spinner(
                "AI agents kaam kar rahe hain. Please wait..."
            ):
                result = run_task(clean_task)

            if isinstance(result, dict):
                output = result.get("final_result", result)
            else:
                output = result

            result_text = str(output)

            try:
                save_task_history(user_id, clean_task, result_text)
            except Exception:
                logger.exception("Task history save failed.")
                st.warning(
                    "Result generate ho gaya, lekin history mein save nahi ho saka."
                )

            st.markdown(
                '<div class="section-kicker">02 / Generated output</div>',
                unsafe_allow_html=True,
            )
            st.subheader("Your AI Result")

            with st.container(border=True):
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
                    with st.expander("View agent details"):
                        st.json(details)

        except Exception:
            logger.exception("AI task execution failed.")
            st.error(
                "Task complete nahi ho saka. Groq API configuration, "
                "CrewAI code aur server logs check karein."
            )


# =========================================================
# 9. SUBSCRIPTION PAGE
# =========================================================

def render_subscription(user_id: str) -> None:
    st.title("Subscription Plans")
    st.caption("Check your current plan and usage limits.")

    subscription = get_subscription_status(user_id)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Free")
        st.markdown("## $0")
        st.write("• 5 tasks per day")
        st.write("• AI task workspace")
        st.write("• Task history")
        st.write("• Basic account features")
        st.info("Free plan available.")

    with col2:
        st.markdown("### Pro")
        st.markdown("## Coming soon")
        st.write("• Higher task limits")
        st.write("• Advanced usage options")
        st.write("• Premium plan features")
        st.warning("Paid subscription activation is not configured yet.")

    st.divider()
    st.write(f"**Current plan:** {subscription['plan']}")
    st.write(f"**Status:** {subscription['status']}")

    st.warning(
        "Payments aur paid-plan activation abhi enabled nahi hain. "
        "Payment provider aur server-side verification configure hone "
        "tak kisi payment ko paid plan na samjhein."
    )


# =========================================================
# 10. SECURITY PAGE
# =========================================================

def render_security() -> None:
    st.title("Account Security")
    st.caption("Keep your account and application credentials secure.")

    st.markdown(
        """
        ### Security checklist

        - Strong, unique password use karein.
        - Password kisi ke saath share na karein.
        - Groq API key GitHub source code mein na likhein.
        - Supabase secrets Streamlit Cloud Secrets mein rakhein.
        - Database tables par Row Level Security enabled rakhein.
        - API keys screenshots ya public repository mein share na karein.
        - Account access ka issue ho to password reset karein.
        """
    )

    st.info(
        "Apna password, Supabase secret key ya Groq API key kisi ke saath share na karein."
    )


# =========================================================
# 11. MAIN APP NAVIGATION
# =========================================================

def render_app(user: dict[str, str]) -> None:
    user_id = user["id"]
    email = user["email"]

    with st.sidebar:
        st.markdown("## 🤖 Parallel AI")
        st.caption("Multi-Agent Workspace")
        st.divider()

        st.caption("SIGNED IN AS")
        st.write(email)

        page = st.radio(
            "NAVIGATION",
            [
                "Dashboard",
                "Task History",
                "Subscription",
                "Security",
            ],
        )

        st.divider()

        if st.button("Logout", use_container_width=True):
            try:
                get_supabase_client().auth.sign_out()
            except Exception:
                logger.exception("Remote logout failed.")
            finally:
                clear_session()
                st.rerun()

    if page == "Dashboard":
        render_dashboard(user)
    elif page == "Task History":
        render_history(user_id)
    elif page == "Subscription":
        render_subscription(user_id)
    elif page == "Security":
        render_security()


# =========================================================
# 12. APPLICATION ENTRY POINT
# =========================================================

def main() -> None:
    try:
        get_supabase_config()
    except Exception:
        logger.exception("Supabase configuration check failed.")
        st.error(
            "Supabase setup check karein. Streamlit Cloud Secrets mein "
            "SUPABASE_URL aur SUPABASE_ANON_KEY sahi honi chahiye."
        )
        st.stop()

    user = get_authenticated_user()

    if user is None:
        render_authentication()
    else:
        render_app(user)

    st.markdown(
        """
        <div class="footer-note">
            Parallel Multi-Agent AI System · AI-powered task workspace
        </div>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
