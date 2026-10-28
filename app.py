
import os
import json
import logging
import time

import streamlit as st
from supabase import create_client, Client
from crew_runner import run_user_task

# --------------------------------------------------
# 1. PAGE CONFIGURATION
# --------------------------------------------------

st.set_page_config(
    page_title="Parallel AI Studio",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("parallel_ai")


# --------------------------------------------------
# 2. PROFESSIONAL UI
# --------------------------------------------------

st.markdown("""
<style>
    .stApp {
        background: linear-gradient(135deg, #f7f9ff 0%, #eef2ff 100%);
    }
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #111827 0%, #1e293b 100%);
    }
    [data-testid="stSidebar"] * {
        color: #f8fafc;
    }
    .hero {
        padding: 28px;
        border-radius: 20px;
        color: white;
        background: linear-gradient(120deg, #4338ca, #7c3aed, #2563eb);
        margin-bottom: 22px;
    }
    .hero h1 {
        color: white;
        margin-bottom: 8px;
    }
    .hero p {
        color: #e0e7ff;
        font-size: 1.05rem;
    }
    .panel {
        background: white;
        border: 1px solid #e5e7eb;
        border-radius: 16px;
        padding: 20px;
        margin-bottom: 16px;
        box-shadow: 0 5px 18px rgba(15, 23, 42, .04);
    }
    div.stButton > button,
    div.stFormSubmitButton > button {
        border-radius: 10px;
        font-weight: 600;
        min-height: 42px;
    }
    h1, h2, h3 {
        letter-spacing: -0.4px;
    }
</style>
""", unsafe_allow_html=True)


# --------------------------------------------------
# 3. CONFIGURATION
# --------------------------------------------------

def get_secret(name: str, default: str = "") -> str:
    try:
        value = st.secrets.get(name, default)
    except Exception:
        value = default

    if not value:
        value = os.getenv(name, default)

    return str(value).strip()


@st.cache_resource
def get_supabase_client() -> Client:
    url = get_secret("SUPABASE_URL").rstrip("/")
    key = get_secret("SUPABASE_ANON_KEY")

    if not url or not key:
        raise ValueError(
            "Streamlit Secrets mein SUPABASE_URL aur "
            "SUPABASE_ANON_KEY configure karein."
        )

    if not url.startswith("https://"):
        raise ValueError("SUPABASE_URL HTTPS project URL hona chahiye.")

    if "/rest/v1" in url or "/auth/v1" in url:
        raise ValueError(
            "URL mein /rest/v1 ya /auth/v1 add na karein."
        )

    return create_client(url, key)


try:
    supabase = get_supabase_client()
except Exception as exc:
    logger.exception("Supabase configuration failed")
    st.error("Supabase configuration check karni hogi.")
    st.code(str(exc))
    st.stop()


# --------------------------------------------------
# 4. SESSION STATE
# --------------------------------------------------

for key, default in {
    "user": None,
    "last_result": None,
    "task_running": False,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default


# --------------------------------------------------
# 5. AUTHENTICATION HELPERS
# --------------------------------------------------

def login_user(email: str, password: str):
    response = supabase.auth.sign_in_with_password({
        "email": email.strip(),
        "password": password,
    })
    st.session_state.user = response.user


def signup_user(email: str, password: str):
    response = supabase.auth.sign_up({
        "email": email.strip(),
        "password": password,
    })

    if response.session and response.user:
        st.session_state.user = response.user
        return True

    return False


def logout_user():
    try:
        supabase.auth.sign_out()
    except Exception:
        logger.warning("Supabase sign-out request failed")

    st.session_state.user = None
    st.session_state.last_result = None
    st.session_state.task_running = False


def show_auth_error(exc: Exception, action: str):
    message = str(exc)
    logger.warning("%s failed: %s", action, message)

    lower_message = message.lower()

    if "429" in lower_message or "rate limit" in lower_message:
        st.error(
            "Supabase ki request limit poori ho gayi hai. "
            "Baar baar retry na karein; kuch waqt baad koshish karein."
        )
    elif "invalid login credentials" in lower_message:
        st.error(
            "Email ya password ghalat hai, ya account confirmation "
            "abhi complete nahi hui."
        )
    elif "email not confirmed" in lower_message:
        st.error("Pehle apni email mein confirmation link open karein.")
    else:
        st.error(f"{action} complete nahi hua. Error details:")
        st.code(message)


# --------------------------------------------------
# 6. LOGIN / SIGNUP SCREEN
# --------------------------------------------------

if st.session_state.user is None:

    st.markdown("""
    <div class="hero">
        <h1>🤖 Parallel AI Studio</h1>
        <p>Plan. Execute. Verify. Deliver.</p>
        <p>Apne tasks ko multi-agent AI workflow ke zariye complete karein.</p>
    </div>
    """, unsafe_allow_html=True)

    login_tab, signup_tab, reset_tab = st.tabs([
        "🔐 Login",
        "✨ Create Account",
        "🔑 Forgot Password",
    ])

    with login_tab:
        st.subheader("Welcome back")

        with st.form("login_form"):
            email = st.text_input("Email address")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button(
                "Login",
                use_container_width=True,
            )

        if submitted:
            if not email.strip() or not password:
                st.warning("Email aur password enter karein.")
            else:
                try:
                    login_user(email, password)
                    st.rerun()
                except Exception as exc:
                    show_auth_error(exc, "Login")

    with signup_tab:
        st.subheader("Create your account")

        with st.form("signup_form"):
            new_email = st.text_input("Email address", key="new_email")
            new_password = st.text_input(
                "Password",
                type="password",
                key="new_password",
            )
            confirm_password = st.text_input(
                "Confirm password",
                type="password",
            )
            submitted = st.form_submit_button(
                "Create Account",
                use_container_width=True,
            )

        if submitted:
            if not new_email.strip() or not new_password:
                st.warning("Email aur password dono enter karein.")
            elif new_password != confirm_password:
                st.error("Dono passwords match nahi karte.")
            elif len(new_password) < 8:
                st.error("Password kam az kam 8 characters ka hona chahiye.")
            else:
                try:
                    logged_in = signup_user(new_email, new_password)

                    if logged_in:
                        st.success("Account create ho gaya.")
                        st.rerun()
                    else:
                        st.success(
                            "Signup request accept hui. Apni email check "
                            "karein aur confirmation complete karein."
                        )
                except Exception as exc:
                    show_auth_error(exc, "Signup")

    with reset_tab:
        st.subheader("Reset your password")

        with st.form("reset_form"):
            reset_email = st.text_input("Registered email address")
            submitted = st.form_submit_button(
                "Send Reset Email",
                use_container_width=True,
            )

        if submitted:
            if not reset_email.strip():
                st.warning("Apna email enter karein.")
            else:
                try:
                    supabase.auth.reset_password_for_email(
                        reset_email.strip(),
                        options={
                            "redirect_to": get_secret("APP_URL")
                            or "https://parallel-multi-agent-system-kijnmteevpxi38tvdrrafi.streamlit.app"
                        },
                    )
                    st.success(
                        "Agar request accept ho gayi hai, email aur spam "
                        "folder check karein."
                    )
                except Exception as exc:
                    show_auth_error(exc, "Password reset")

    st.stop()


# --------------------------------------------------
# 7. DASHBOARD NAVIGATION
# --------------------------------------------------

user = st.session_state.user
user_email = getattr(user, "email", None) or "User"
user_id = str(user.id)

with st.sidebar:
    st.markdown("## 🤖 AI Studio")
    st.caption("Multi-Agent Workspace")
    st.divider()

    st.write("**Signed in as**")
    st.caption(user_email)

    page = st.radio(
        "WORKSPACE",
        ["Overview", "Run AI Task", "Task History", "Account"],
        label_visibility="visible",
    )

    st.divider()
    st.caption("Planner → Worker → Checker → Reviewer")

    if st.button("🚪 Logout", use_container_width=True):
        logout_user()
        st.rerun()


# --------------------------------------------------
# 8. OVERVIEW
# --------------------------------------------------

if page == "Overview":

    st.markdown("""
    <div class="hero">
        <h1>Parallel Multi-Agent AI System</h1>
        <p>Your workspace for AI-powered task planning and execution.</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(
            '<div class="panel"><h3>🧠 Planning</h3>'
            '<p>Break a request into clear steps.</p></div>',
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown(
            '<div class="panel"><h3>⚙️ Execution</h3>'
            '<p>Generate the requested deliverable.</p></div>',
            unsafe_allow_html=True,
        )

    with col3:
        st.markdown(
            '<div class="panel"><h3>✅ Review</h3>'
            '<p>Check completeness and evidence.</p></div>',
            unsafe_allow_html=True,
        )

    st.subheader("Get started")
    st.write(
        "Run AI Task page par ja kar apna task enter karein. "
        "Task History page par saved results dekh sakte hain."
    )

    if st.button("Start a New Task", type="primary"):
        st.session_state.last_result = None
        st.rerun()


# --------------------------------------------------
# 9. RUN AI TASK
# --------------------------------------------------

elif page == "Run AI Task":

    st.markdown("""
    <div class="hero">
        <h1>⚡ Run an AI Task</h1>
        <p>Apni requirement likhein aur AI workflow start karein.</p>
    </div>
    """, unsafe_allow_html=True)

    st.info(
        "Workflow mein web search aur chaar agents shamil hain. "
        "Complex tasks ko complete hone mein waqt lag sakta hai."
    )

    with st.form("task_form"):
        user_task = st.text_area(
            "What would you like the AI agents to do?",
            placeholder=(
                "Example: Create a beginner-friendly Python learning "
                "roadmap with weekly goals and practice projects."
            ),
            height=180,
        )

        run_button = st.form_submit_button(
            "🚀 Run AI Agents",
            type="primary",
            use_container_width=True,
        )

    if run_button:
        if not user_task.strip():
            st.warning("Pehle apna task enter karein.")
        elif len(user_task.strip()) > 12000:
            st.warning("Task 12,000 characters se chhota rakhein.")
        else:
            start_time = time.monotonic()

            try:
                with st.spinner(
                    "AI agents kaam kar rahe hain. "
                    "Is tab ko band na karein..."
                ):
                    result = run_user_task(user_task.strip())

                elapsed = time.monotonic() - start_time

                st.session_state.last_result = {
                    "task": user_task.strip(),
                    "result": result,
                    "elapsed_seconds": round(elapsed, 1),
                }

                st.success(
                    f"Task complete! Time: {elapsed:.1f} seconds"
                )

                try:
                    supabase.table("task_history").insert({
                        "user_id": user_id,
                        "task": user_task.strip(),
                        "result": json.dumps(
                            result,
                            ensure_ascii=False,
                            default=str,
                        ),
                    }).execute()

                    st.toast("Task history saved.")

                except Exception:
                    logger.exception("Task history save failed")
                    st.warning(
                        "Result complete hai, lekin history save nahi hui. "
                        "Supabase table aur RLS policies check karein."
                    )

            except Exception as exc:
                logger.exception("AI task execution failed")
                st.error(
                    "AI task complete nahi ho saka. Technical details "
                    "neeche hain."
                )
                st.code(str(exc))

    saved = st.session_state.last_result

    if saved:
        st.divider()
        st.subheader("📄 Latest Result")

        st.markdown("**Your task**")
        st.write(saved["task"])

        st.caption(
            f"Execution time: {saved.get('elapsed_seconds', 'N/A')} seconds"
        )

        result = saved["result"]

        if isinstance(result, dict):
            if result.get("final_result"):
                st.markdown("### ✨ Final Answer")
                st.markdown(str(result["final_result"]))

            if result.get("review_result"):
                with st.expander("✅ Quality Review"):
                    st.markdown(str(result["review_result"]))

            if result.get("search_results"):
                with st.expander("🌐 Search Evidence"):
                    st.write(result["search_results"])

            if result.get("agent_outputs"):
                with st.expander("🧠 Individual Agent Outputs"):
                    for title, output in result["agent_outputs"]:
                        st.markdown(f"**{title}**")
                        st.write(output or "No output available.")

            st.download_button(
                "⬇️ Download Full Result (JSON)",
                data=json.dumps(
                    result,
                    ensure_ascii=False,
                    indent=2,
                    default=str,
                ),
                file_name="parallel_ai_result.json",
                mime="application/json",
            )
        else:
            st.write(result)


# --------------------------------------------------
# 10. TASK HISTORY
# --------------------------------------------------

elif page == "Task History":

    st.markdown("""
    <div class="hero">
        <h1>📚 Task History</h1>
        <p>Apne pehle complete kiye gaye tasks dekhein.</p>
    </div>
    """, unsafe_allow_html=True)

    try:
        response = (
            supabase.table("task_history")
            .select("id, task, result, created_at")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(50)
            .execute()
        )

        records = response.data or []

        if not records:
            st.info("Abhi tak koi saved task nahi mila.")
        else:
            st.caption(f"{len(records)} latest records")

            for index, record in enumerate(records, start=1):
                task_title = record.get("task") or "Untitled task"

                with st.expander(f"{index}. {task_title[:100]}"):
                    st.caption(
                        f"Created: {record.get('created_at', 'Unknown')}"
                    )

                    saved_result = record.get("result", "")

                    if isinstance(saved_result, str):
                        try:
                            saved_result = json.loads(saved_result)
                        except (json.JSONDecodeError, TypeError):
                            pass

                    if isinstance(saved_result, dict):
                        if saved_result.get("final_result"):
                            st.markdown(
                                str(saved_result["final_result"])
                            )
                        else:
                            st.json(saved_result)
                    elif isinstance(saved_result, list):
                        st.json(saved_result)
                    else:
                        st.write(saved_result)

                    st.download_button(
                        "Download This Result",
                        data=json.dumps(
                            saved_result,
                            ensure_ascii=False,
                            indent=2,
                            default=str,
                        ),
                        file_name=f"task_{index}.json",
                        mime="application/json",
                        key=f"download_history_{record.get('id', index)}",
                    )

    except Exception as exc:
        logger.exception("Task history loading failed")
        st.error("Task history load nahi ho saki.")
        st.caption(str(exc))


# --------------------------------------------------
# 11. ACCOUNT
# --------------------------------------------------

elif page == "Account":

    st.markdown("""
    <div class="hero">
        <h1>👤 Account</h1>
        <p>Aapki account information.</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.write("**Email address**")
    st.write(user_email)

    st.write("**User ID**")
    st.code(user_id)

    st.write("**Authentication provider**")
    st.write("Supabase")

    st.markdown("</div>", unsafe_allow_html=True)

    st.info(
        "Subscription aur payment features abhi is replacement mein "
        "implement nahi hain. Inhein add karne se pehle existing "
        "subscriptions table aur payment requirements verify karni hongi."
    )


# --------------------------------------------------
# 12. FOOTER
# --------------------------------------------------

st.divider()
st.caption("Parallel AI Studio • CrewAI + Groq + Streamlit")
