
"""Parallel Multi-Agent AI System
Streamlit + Supabase + CrewAI + Groq
"""

from __future__ import annotations

import logging
import os
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlsplit

import streamlit as st
from supabase import Client, create_client
from crew_runner import run_user_task

# =========================================================
# 1. CONFIGURATION
# =========================================================

st.set_page_config(
    page_title="Parallel AI | Workspace",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("parallel_ai")

APP_URL = (
    "https://parallel-multi-agent-system-kijnmteevpxi38tvdrrafi.streamlit.app/"
)
TASKS_TABLE = "task_history"
SUBSCRIPTIONS_TABLE = "subscriptions"
FREE_DAILY_LIMIT = 5
MAX_TASK_LENGTH = 5000

# =========================================================
# 2. PROFESSIONAL LIGHT THEME
# =========================================================

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');

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
        background: var(--page);
        color: var(--text);
        font-family: 'DM Sans', Arial, sans-serif;
    }

    [data-testid="stHeader"] {
        background: rgba(244,247,252,.96);
    }

    [data-testid="stSidebar"] {
        background: #fff;
        border-right: 1px solid var(--border);
    }

    [data-testid="stSidebar"] * {
        color: var(--text);
    }

    .block-container {
        max-width: 1250px;
        padding-top: 2rem;
        padding-bottom: 3rem;
    }

    h1, h2, h3 {
        font-family: 'Space Grotesk', Arial, sans-serif;
        color: #172554;
        letter-spacing: -.02em;
    }

    h1 { font-size: clamp(2rem, 4vw, 2.8rem); }
    h2 { font-size: 2rem; }
    h3 { font-size: 1.4rem; }

    p, label, .stMarkdown {
        color: #334155;
        font-size: 16px;
        line-height: 1.7;
    }

    [data-testid="stCaptionContainer"] {
        color: #475569;
        font-size: 14px;
    }

    [data-testid="stTextInput"] input,
    [data-testid="stTextArea"] textarea {
        background: #fff;
        color: #172033;
        border: 1px solid #cbd5e1;
        border-radius: 10px;
        font-size: 16px;
        min-height: 44px;
    }

    [data-testid="stTextInput"] input::placeholder,
    [data-testid="stTextArea"] textarea::placeholder {
        color: #64748b;
        opacity: 1;
    }

    [data-testid="stMetric"] {
        background: #fff;
        border: 1px solid var(--border);
        border-radius: 15px;
        padding: 1rem;
        box-shadow: 0 3px 12px rgba(15,23,42,.04);
    }

    [data-testid="stMetricLabel"] { color: #475569; }
    [data-testid="stMetricValue"] {
        color: #172554;
        font-family: 'Space Grotesk', sans-serif;
    }

    .stButton > button,
    [data-testid="stFormSubmitButton"] button {
        border-radius: 10px;
        min-height: 45px;
        font-size: 16px;
        font-weight: 700;
    }

    .stButton > button[kind="primary"],
    [data-testid="stFormSubmitButton"] button[kind="primary"] {
        background: var(--primary);
        color: white;
        border: 1px solid var(--primary);
    }

    .stButton > button[kind="primary"]:hover,
    [data-testid="stFormSubmitButton"] button[kind="primary"]:hover {
        background: var(--primary-dark);
        color: white;
    }

    [data-testid="stTabs"] button {
        color: #334155;
        font-size: 16px;
        font-weight: 600;
    }

    [data-testid="stExpander"] {
        background: white;
        border: 1px solid var(--border);
        border-radius: 12px;
    }

    .hero {
        padding: 1.8rem;
        margin-bottom: 1.4rem;
        border-radius: 20px;
        border: 1px solid #c7d2fe;
        background: linear-gradient(120deg, #fff, #eaf0ff);
        box-shadow: 0 5px 24px rgba(30,41,59,.05);
    }

    .eyebrow {
        color: #4338ca;
        text-transform: uppercase;
        letter-spacing: .13em;
        font-size: 13px;
        font-weight: 700;
        margin-bottom: 10px;
    }

    .hero-title {
        color: #172554;
        font-family: 'Space Grotesk', sans-serif;
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
        .block-container { padding: 1rem .8rem 2rem; }
        .hero { padding: 1.2rem; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# =========================================================
# 3. SUPABASE CONFIGURATION
# =========================================================

def get_setting(name: str, default: str = "") -> str:
    try:
        value = st.secrets.get(name)
        if value is not None:
            return str(value).strip()
    except Exception:
        pass

    return os.environ.get(name, default).strip()


def get_supabase_config() -> tuple[str, str]:
    raw_url = get_setting("SUPABASE_URL")
    key = get_setting("SUPABASE_ANON_KEY")

    if not raw_url or not key:
        raise RuntimeError(
            "SUPABASE_URL ya SUPABASE_ANON_KEY missing hai."
        )

    parsed = urlsplit(raw_url)

    if (
        parsed.scheme != "https"
        or not parsed.netloc
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.path.rstrip("/")
    ):
        raise RuntimeError(
            "SUPABASE_URL mein sirf project ka HTTPS URL dein."
        )

    return f"{parsed.scheme}://{parsed.netloc}", key


@st.cache_resource
def create_supabase_client() -> Client:
    url, key = get_supabase_config()
    return create_client(url, key)


def get_supabase_client() -> Client:
    client = create_supabase_client()
    token = st.session_state.get("access_token")

    if token:
        client.postgrest.auth(token)

    return client


# =========================================================
# 4. SESSION AND VALIDATION
# =========================================================

DEFAULTS = {
    "access_token": None,
    "refresh_token": None,
    "user_id": None,
    "user_email": None,
}

for key, value in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = value


def clear_session() -> None:
    for key, value in DEFAULTS.items():
        st.session_state[key] = value


def validate_email(email: str) -> bool:
    email = email.strip()

    if len(email) > 254:
        return False

    pattern = (
        r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@"
        r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
        r"(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)+"
    )

    return bool(re.fullmatch(pattern, email))


def save_auth_session(response: Any) -> bool:
    session = getattr(response, "session", None)
    user = getattr(response, "user", None)

    if not session or not user or not getattr(user, "id", None):
        return False

    access_token = getattr(session, "access_token", None)
    refresh_token = getattr(session, "refresh_token", None)

    if not access_token:
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

        return {
            "id": str(user.id),
            "email": getattr(user, "email", "") or "",
        }

    except Exception:
        logger.warning("Session verification failed.")
        clear_session()
        return None


# =========================================================
# 5. LOGIN, SIGNUP AND PASSWORD RESET
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
                Sign in to your workspace and let your configured AI
                agents help you complete complex tasks.
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
                            "Login session nahi mili. Email verification "
                            "enabled ho to apna inbox check karein."
                        )

                except Exception:
                    logger.exception("Login request failed.")
                    st.error(
                        "Login nahi ho saka. Email, password aur "
                        "Supabase Auth settings check karein."
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
                            "Signup request process ho gayi. Email inbox "
                            "aur spam folder mein verification link check karein."
                        )
                        st.info(
                            "Supabase Authentication > URL Configuration "
                            "mein Site URL aur Redirect URLs mein app URL "
                            "allowed hona chahiye."
                        )

                except Exception:
                    logger.exception("Signup request failed.")
                    st.error(
                        "Account create nahi ho saka. Agar bohat dafa "
                        "signup try kiya hai to kuch der baad dobara try karein."
                    )

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
                    get_supabase_client().auth.reset_password_for_email(
                        email,
                        options={"redirect_to": APP_URL},
                    )
                    st.success(
                        "Agar account maujood hai to reset email bhej di jayegi. "
                        "Inbox aur spam folder check karein."
                    )
                except Exception:
                    logger.exception("Password reset request failed.")
                    st.error(
                        "Reset request process nahi ho saki. "
                        "Supabase Auth settings check karein."
                    )


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
        plan = str(record.get("plan", "free")).lower()
        status = str(record.get("status", "")).lower()
        expires_at = record.get("expires_at")

        if plan not in {"free", "pro", "premium"}:
            return {
                "plan": "free",
                "status": "inactive",
                "expires_at": None,
            }

        active = status == "active" and plan in {"pro", "premium"}

        if active and expires_at:
            try:
                expiry = datetime.fromisoformat(
                    expires_at.replace("Z", "+00:00")
                )
                if expiry.tzinfo is None:
                    expiry = expiry.replace(tzinfo=timezone.utc)
                if expiry <= datetime.now(timezone.utc):
                    active = False
            except (ValueError, TypeError, AttributeError):
                active = False

        if not active:
            return {
                "plan": "free",
                "status": "inactive" if status != "free" else "free",
                "expires_at": None,
            }

        return {
            "plan": plan,
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
    now = datetime.now(timezone.utc)
    start = now.replace(
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
    st.caption("Apne pichle tasks aur AI-generated results dekhein.")

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
            task_label = str(item.get("task", "Task"))[:100]

            with st.expander(f"{index}. {task_label}"):
                st.caption(str(item.get("created_at", "")))
                st.markdown(str(item.get("result", "")))

    except Exception:
        logger.exception("History retrieval failed.")
        st.error(
            "History load nahi ho saki. Database table aur RLS policies check karein."
        )


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
                Apna task likhein aur configured CrewAI agents se
                AI-generated result hasil karein.
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
            "Task count verify nahi ho saka. Database settings check karein."
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

    with st.form("ai_task_form"):
        task_text = st.text_area(
            "Apna task likhein",
            max_chars=MAX_TASK_LENGTH,
            height=200,
            placeholder=(
                "Example: Explain artificial intelligence, give five "
                "real-life examples, and describe its advantages."
            ),
            help="Goal, context aur required output clearly likhein.",
        )

        run_clicked = st.form_submit_button(
            "Run AI Agents  →",
            type="primary",
            use_container_width=True,
        )

    if not run_clicked:
        return

    clean_task = task_text.strip()

    if not clean_task:
        st.warning("Pehle apna task likhein.")
        return

    if subscription["status"] == "unknown":
        st.error(
            "Subscription status verify nahi ho saka. Filhal task run nahi "
            "kiya gaya. Database configuration check karein."
        )
        return

    if not paid_active and used_today >= FREE_DAILY_LIMIT:
        st.warning(
            "Aaj ki free task limit complete ho gayi. Subscription page "
            "par available plan details dekhein."
        )
        return

    try:
        with st.spinner("AI agents kaam kar rahe hain. Please wait..."):
            result = run_user_task(clean_task)

        if isinstance(result, dict):
            output = result.get("final_result", result)
        else:
            output = result

        result_text = (
            output if isinstance(output, str) else str(output)
        )

        if not result_text.strip():
            st.error("AI agents ne empty result return kiya.")
            return

        try:
            save_task_history(user_id, clean_task, result_text)
        except Exception:
            logger.exception("Task history save failed.")
            st.warning(
                "Result generate ho gaya, lekin history save nahi ho saki."
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
            "CrewAI code aur deployment logs check karein."
        )


# =========================================================
# 9. SUBSCRIPTION PAGE
# =========================================================

def render_subscription(user_id: str) -> None:
    st.title("Subscription Plans")
    st.caption("Apna current plan aur usage limits dekhein.")

    subscription = get_subscription_status(user_id)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Free")
        st.markdown("## $0")
        st.write("5 tasks per day")
        st.write("AI task workspace")
        st.write("Task history")
        st.write("Basic account features")
        st.info("Free plan available.")

    with col2:
        st.markdown("### Pro")
        st.markdown("## Coming soon")
        st.write("Higher task limits")
        st.write("Advanced usage options")
        st.write("Premium plan features")
        st.warning("Paid subscription activation is not configured.")

    st.divider()
    st.write(f"**Current plan:** {subscription['plan']}")
    st.write(f"**Status:** {subscription['status']}")

    st.warning(
        "Payments aur paid-plan activation abhi configure nahi hain. "
        "Payment provider aur trusted server-side verification ke baghair "
        "kisi payment ko paid plan nahi samjha jayega."
    )


# =========================================================
# 10. SECURITY PAGE
# =========================================================

def render_security() -> None:
    st.title("Account Security")
    st.caption("Apne account aur API credentials ko secure rakhein.")

    st.markdown(
        """
        ### Security checklist

        - Strong aur unique password use karein.
        - Password kisi ke saath share na karein.
        - Groq API key source code mein na likhein.
        - Supabase secrets Streamlit Cloud Secrets mein rakhein.
        - Database tables par Row Level Security enabled rakhein.
        - API keys screenshots ya public repository mein share na karein.
        - Account access ka issue ho to password reset karein.
        """
    )

    st.info(
        "Apna password, Supabase secret key ya Groq API key kisi ke "
        "saath share na karein."
    )


# =========================================================
# 11. APP NAVIGATION
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
                logger.warning("Remote logout failed.")
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
