
import os
import json
import streamlit as st
from supabase import create_client, Client

from crew_runner import run_user_task


# --------------------------------------------------
# 1. PAGE SETTINGS
# --------------------------------------------------

st.set_page_config(
    page_title="Parallel Multi-Agent AI System",
    page_icon="🤖",
    layout="wide",
)

st.title("🤖 Parallel Multi-Agent AI System")
st.caption("AI agents ki madad se apne tasks complete karein.")


# --------------------------------------------------
# 2. CONFIGURATION
# --------------------------------------------------

def get_secret(name: str, default: str = "") -> str:
    """Streamlit Secrets ya environment variables se value lein."""
    try:
        value = st.secrets.get(name, default)
    except Exception:
        value = default

    if not value:
        value = os.getenv(name, default)

    return str(value).strip()


@st.cache_resource
def get_supabase_client() -> Client:
    url = get_secret("SUPABASE_URL")
    key = get_secret("SUPABASE_ANON_KEY")

    if not url or not key:
        raise ValueError(
            "SUPABASE_URL aur SUPABASE_ANON_KEY "
            "Streamlit Cloud Secrets mein set karein."
        )

    if not url.startswith("https://"):
        raise ValueError(
            "SUPABASE_URL https:// se shuru hona chahiye."
        )

    if "/rest/v1" in url or "/auth/v1" in url:
        raise ValueError(
            "SUPABASE_URL mein sirf project URL dein. "
            "Aakhir mein /rest/v1 ya /auth/v1 na lagayein."
        )

    return create_client(url.rstrip("/"), key)


# --------------------------------------------------
# 3. SESSION STATE
# --------------------------------------------------

if "user" not in st.session_state:
    st.session_state.user = None

if "access_token" not in st.session_state:
    st.session_state.access_token = None

if "last_result" not in st.session_state:
    st.session_state.last_result = None


# --------------------------------------------------
# 4. SUPABASE CONNECTION
# --------------------------------------------------

try:
    supabase = get_supabase_client()
except Exception as error:
    st.error(f"Supabase configuration error: {error}")
    st.info(
        "Streamlit Cloud → App → Settings → Secrets mein "
        "SUPABASE_URL aur SUPABASE_ANON_KEY check karein."
    )
    st.stop()


# --------------------------------------------------
# 5. AUTHENTICATION
# --------------------------------------------------

def login_user(email: str, password: str):
    response = supabase.auth.sign_in_with_password(
        {
            "email": email.strip(),
            "password": password,
        }
    )
    st.session_state.user = response.user
    st.session_state.access_token = response.session.access_token


def signup_user(email: str, password: str):
    response = supabase.auth.sign_up(
        {
            "email": email.strip(),
            "password": password,
        }
    )

    if response.session and response.user:
        st.session_state.user = response.user
        st.session_state.access_token = response.session.access_token
        return "Account created and logged in."

    return (
        "Signup request received. Agar email confirmation enabled hai, "
        "to apni email check karke account confirm karein."
    )


def logout_user():
    try:
        supabase.auth.sign_out()
    except Exception:
        pass

    st.session_state.user = None
    st.session_state.access_token = None
    st.session_state.last_result = None


# --------------------------------------------------
# 6. LOGIN / SIGNUP SCREEN
# --------------------------------------------------

if st.session_state.user is None:
    login_tab, signup_tab, reset_tab = st.tabs(
        ["Login", "Create Account", "Forgot Password"]
    )

    with login_tab:
        st.subheader("Login to your account")

        with st.form("login_form"):
            email = st.text_input("Email address")
            password = st.text_input(
                "Password",
                type="password",
            )
            login_button = st.form_submit_button(
                "Login",
                use_container_width=True,
            )

        if login_button:
            if not email.strip() or not password:
                st.warning("Email aur password dono enter karein.")
            else:
                try:
                    login_user(email, password)
                    st.success("Login successful!")
                    st.rerun()
                except Exception as error:
                    st.error(
                        "Login nahi hua. Email/password check karein. "
                        "Agar email confirmation zaroori hai, pehle email "
                        "confirm karein."
                    )
                    st.caption(str(error))

    with signup_tab:
        st.subheader("Create a new account")

        with st.form("signup_form"):
            new_email = st.text_input(
                "Email address",
                key="signup_email",
            )
            new_password = st.text_input(
                "Password",
                type="password",
                key="signup_password",
            )
            confirm_password = st.text_input(
                "Confirm password",
                type="password",
            )
            signup_button = st.form_submit_button(
                "Create Account",
                use_container_width=True,
            )

        if signup_button:
            if not new_email.strip() or not new_password:
                st.warning("Email aur password enter karein.")
            elif new_password != confirm_password:
                st.error("Dono passwords match nahi karte.")
            elif len(new_password) < 8:
                st.error("Password kam az kam 8 characters ka rakhein.")
            else:
                try:
                    message = signup_user(
                        new_email,
                        new_password,
                    )
                    st.success(message)

                    if st.session_state.user is not None:
                        st.rerun()

                except Exception as error:
                    st.error(
                        "Account create nahi hua. Email check karein; "
                        "agar rate limit error aaye to baar baar retry "
                        "na karein."
                    )
                    st.caption(str(error))

    with reset_tab:
        st.subheader("Reset your password")

        with st.form("reset_form"):
            reset_email = st.text_input(
                "Your registered email",
                key="reset_email",
            )
            reset_button = st.form_submit_button(
                "Send Reset Email",
                use_container_width=True,
            )

        if reset_button:
            if not reset_email.strip():
                st.warning("Apna email enter karein.")
            else:
                try:
                    supabase.auth.reset_password_for_email(
                        reset_email.strip()
                    )
                    st.success(
                        "Agar request accept ho gayi hai, "
                        "to apni email aur spam folder check karein."
                    )
                except Exception as error:
                    st.error(
                        "Reset email send nahi hui. Rate limit ya "
                        "Supabase email settings check karein."
                    )
                    st.caption(str(error))

    st.stop()


# --------------------------------------------------
# 7. LOGGED-IN DASHBOARD
# --------------------------------------------------

user = st.session_state.user
user_email = getattr(user, "email", None) or "User"

with st.sidebar:
    st.title("Dashboard")
    st.write(f"Logged in: {user_email}")

    page = st.radio(
        "Select page",
        [
            "Run AI Task",
            "Task History",
            "Account",
        ],
    )

    st.divider()

    if st.button("Logout", use_container_width=True):
        logout_user()
        st.rerun()


# --------------------------------------------------
# 8. RUN AI TASK
# --------------------------------------------------

if page == "Run AI Task":
    st.header("Run a new AI task")

    st.write(
        "Apna task likhein. AI workflow planning, execution, "
        "checking aur final review karne ki koshish karega."
    )

    with st.form("task_form"):
        user_task = st.text_area(
            "Enter your task",
            placeholder=(
                "Example: Create a beginner-friendly Python "
                "learning roadmap."
            ),
            height=160,
        )

        run_button = st.form_submit_button(
            "Run AI Agents",
            use_container_width=True,
        )

    if run_button:
        if not user_task.strip():
            st.warning("Pehle apna task likhein.")
        else:
            try:
                with st.spinner(
                    "AI agents kaam kar rahe hain. Please wait..."
                ):
                    result = run_user_task(user_task.strip())

                st.session_state.last_result = {
                    "task": user_task.strip(),
                    "result": result,
                }

                st.success("Task processing complete!")

                # Save history when the table and RLS policies exist.
                try:
                    supabase.table("task_history").insert(
                        {
                            "user_id": str(user.id),
                            "task": user_task.strip(),
                            "result": json.dumps(
                                result,
                                ensure_ascii=False,
                                default=str,
                            ),
                        }
                    ).execute()
                except Exception as save_error:
                    st.warning(
                        "Result mil gaya, lekin history save nahi hui. "
                        "Supabase task_history table aur RLS policies "
                        "check karein."
                    )
                    st.caption(str(save_error))

            except Exception as error:
                st.error("AI task run nahi ho saka.")
                st.exception(error)

    if st.session_state.last_result:
        st.divider()
        st.subheader("Latest Result")

        result_data = st.session_state.last_result
        st.markdown("### Your Task")
        st.write(result_data["task"])

        result = result_data["result"]

        if isinstance(result, dict):
            for key, value in result.items():
                st.markdown(
                    f"### {str(key).replace('_', ' ').title()}"
                )

                if isinstance(value, (dict, list)):
                    st.json(value)
                else:
                    st.write(str(value))
        else:
            st.write(str(result))

        st.download_button(
            "Download Result",
            data=json.dumps(
                result,
                ensure_ascii=False,
                indent=2,
                default=str,
            ),
            file_name="ai_task_result.json",
            mime="application/json",
        )


# --------------------------------------------------
# 9. TASK HISTORY
# --------------------------------------------------

elif page == "Task History":
    st.header("Your Task History")

    try:
        response = (
            supabase.table("task_history")
            .select("id, task, result, created_at")
            .eq("user_id", str(user.id))
            .order("created_at", desc=True)
            .limit(50)
            .execute()
        )

        records = response.data or []

        if not records:
            st.info("Abhi tak koi saved task nahi mila.")
        else:
            st.caption("Aap ke latest 50 saved tasks.")

            for index, record in enumerate(records, start=1):
                task_title = record.get("task") or "Untitled task"

                with st.expander(
                    f"{index}. {task_title[:100]}"
                ):
                    st.caption(
                        f"Created: {record.get('created_at', 'Unknown')}"
                    )
                    saved_result = record.get("result", "")

                    if isinstance(saved_result, str):
                        try:
                            saved_result = json.loads(saved_result)
                        except (json.JSONDecodeError, TypeError):
                            pass

                    if isinstance(saved_result, (dict, list)):
                        st.json(saved_result)
                    else:
                        st.write(saved_result)

    except Exception as error:
        st.error("Task history load nahi hui.")
        st.info(
            "Supabase mein task_history table, column names, "
            "aur Row Level Security (RLS) policies verify karein."
        )
        st.caption(str(error))


# --------------------------------------------------
# 10. ACCOUNT PAGE
# --------------------------------------------------

elif page == "Account":
    st.header("Account Information")

    st.write("**Email:**", user_email)
    st.write("**User ID:**", str(user.id))
    st.write("**Authentication:** Supabase")

    st.info(
        "Is starter version mein subscription/payment system "
        "include nahi hai."
    )

st.divider()
st.caption("Parallel Multi-Agent AI System")
