
import streamlit as st
from datetime import datetime
from crew_runner import run_user_task

# ==================== PAGE CONFIG ====================
st.set_page_config(
    page_title="Multi-Agent AI Workspace",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ==================== SESSION STATE ====================
if "navigation" not in st.session_state:
    st.session_state["navigation"] = "Dashboard"

if "task_history" not in st.session_state:
    st.session_state["task_history"] = []

if "last_result" not in st.session_state:
    st.session_state["last_result"] = None


def navigate_to(page):
    st.session_state["navigation"] = page


# ==================== PROFESSIONAL DESIGN ====================
st.markdown(
    """
    <style>
    /* Sidebar width: approximately 30% */
   
[data-testid="stSidebar"] {
    width: 22vw !important;
    min-width: 220px !important;
    max-width: 300px !important;
}


    [data-testid="stSidebar"] > div:first-child {
        background: linear-gradient(180deg, #111827, #1E293B);
        border-right: 1px solid #334155;
    }

    [data-testid="stSidebar"] * {
        color: #F8FAFC;
    }

    .stApp {
        background-color: #F6F8FC;
    }

    [data-testid="stMainBlockContainer"] {
        padding-top: 2rem;
        padding-bottom: 3rem;
    }

    .hero {
        background: linear-gradient(125deg, #172554, #4338CA);
        padding: 30px;
        border-radius: 18px;
        color: white;
        margin-bottom: 24px;
    }

    .hero h1, .hero p {
        color: white !important;
    }

    .metric-card {
        background: white;
        padding: 20px;
        border: 1px solid #E2E8F0;
        border-radius: 14px;
        min-height: 115px;
    }

    .metric-label {
        color: #64748B;
        font-size: 14px;
    }

    .metric-value {
        color: #172554;
        font-size: 28px;
        font-weight: 700;
        margin-top: 8px;
    }

    .agent-card {
        background: white;
        padding: 18px;
        border: 1px solid #E2E8F0;
        border-radius: 14px;
        margin-bottom: 12px;
    }

    div.stButton > button {
        border-radius: 9px;
        min-height: 42px;
    }

    div.stButton > button[kind="primary"] {
        font-weight: 600;
    }

    @media (max-width: 768px) {
        [data-testid="stSidebar"] {
            width: 80vw !important;
            min-width: 0 !important;
            max-width: 80vw !important;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ==================== SIDEBAR ====================
with st.sidebar:
    st.markdown("# 🤖 Multi-Agent")
    st.caption("AI WORKSPACE")
    st.divider()

    st.radio(
        "NAVIGATION",
        [
            "Dashboard",
            "New Task",
            "Agent Workflow",
            "Task History",
            "Settings",
        ],
        key="navigation",
    )

    st.divider()
    st.markdown("### 🧠 YOUR AI TEAM")

    st.markdown("🗺️ **Planner Agent**")
    st.caption("Plans task steps")

    st.markdown("⚙️ **Worker Agent**")
    st.caption("Creates the requested output")

    st.markdown("🔍 **Checker Agent**")
    st.caption("Checks completeness")

    st.markdown("📝 **Final Reviewer**")
    st.caption("Combines the results")

    st.divider()
    st.caption("Powered by Groq + CrewAI")
    st.caption("Text-based AI task system")


# ==================== DASHBOARD ====================
page = st.session_state["navigation"]
history = st.session_state["task_history"]

if page == "Dashboard":

    st.markdown(
        """
        <div class="hero">
            <h1>AI Multi-Agent Workspace</h1>
            <p>
                Manage tasks, coordinate your AI agents,
                and review results in one workspace.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.subheader("📊 Dashboard Overview")

    total_tasks = len(history)
    completed_tasks = sum(
        1 for item in history if item.get("status") == "Completed"
    )
    failed_tasks = sum(
        1 for item in history if item.get("status") == "Failed"
    )

    active_agents = 0

    c1, c2, c3, c4 = st.columns(4)

    metrics = [
        (c1, "Total Tasks", total_tasks),
        (c2, "Completed", completed_tasks),
        (c3, "Failed", failed_tasks),
        (c4, "Active Agents", active_agents),
    ]

    for column, label, value in metrics:
        with column:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-label">{label}</div>
                    <div class="metric-value">{value}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.write("")
    st.subheader("🚀 Quick Actions")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(
            """
            <div class="agent-card">
                <h3>✨ Create a New Task</h3>
                <p>Give your AI team a task to complete.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.button(
            "Create Task →",
            key="dashboard_new_task",
            type="primary",
            use_container_width=True,
            on_click=navigate_to,
            args=("New Task",),
        )

    with col2:
        st.markdown(
            """
            <div class="agent-card">
                <h3>🧩 Explore Agent Workflow</h3>
                <p>Learn how the four agents work together.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.button(
            "View Workflow →",
            key="dashboard_workflow",
            use_container_width=True,
            on_click=navigate_to,
            args=("Agent Workflow",),
        )

    st.caption(
        "Dashboard counts represent tasks recorded in this session. "
        "Persistent history will require database or file storage."
    )


# ==================== NEW TASK ====================
elif page == "New Task":

    st.title("🚀 Create a New Task")
    st.write(
        "Apna task detail mein likhein. AI agents aapke task par kaam karenge."
    )

    task = st.text_area(
        "What would you like your AI team to do?",
        placeholder=(
            "Example: Create a beginner-friendly 4-week Python "
            "learning roadmap with weekly goals and practice tasks."
        ),
        height=180,
        key="user_task",
    )

    st.caption(
        "Tip: Task mein apna goal aur required output clearly likhein."
    )

    if st.button(
        "🚀 Run AI Agents",
        type="primary",
        use_container_width=True,
    ):
        if not task.strip():
            st.error("Pehle apna task likhein.")

        elif len(task.strip()) < 8:
            st.error("Please task thora detail mein likhein.")

        else:
            started_at = datetime.now()

            try:
                with st.spinner(
                    "AI agents kaam kar rahe hain. Please wait..."
                ):
                    result = run_user_task(task.strip())

                if not isinstance(result, dict):
                    raise ValueError(
                        "Backend se expected result format nahi mila."
                    )

                final_result = result.get("final_result") or ""
                review_result = result.get("review_result") or ""
                agent_outputs = result.get("agent_outputs") or []

                task_record = {
                    "task": task.strip(),
                    "status": "Completed",
                    "time": started_at.strftime("%Y-%m-%d %H:%M:%S"),
                    "final_result": final_result,
                    "review_result": review_result,
                    "agent_outputs": agent_outputs,
                }

                st.session_state["last_result"] = task_record
                st.session_state["task_history"].insert(0, task_record)

                st.success("Workflow run complete!")

            except Exception as exc:
                task_record = {
                    "task": task.strip(),
                    "status": "Failed",
                    "time": started_at.strftime("%Y-%m-%d %H:%M:%S"),
                    "final_result": "",
                    "review_result": "",
                    "agent_outputs": [],
                }

                st.session_state["task_history"].insert(0, task_record)

                st.error("Task run nahi ho saka.")
                st.caption(
                    "Groq API key, model access, API limits aur "
                    "Streamlit Cloud logs check karein."
                )

                with st.expander("Technical error details"):
                    st.code(str(exc))

    # Display the most recent successful result
    last_result = st.session_state.get("last_result")

    if last_result:
        st.divider()
        st.subheader("📄 Task Results")

        tab1, tab2, tab3 = st.tabs(
            ["Final Answer", "Quality Review", "Agent Outputs"]
        )

        with tab1:
            st.markdown(
                last_result.get("final_result")
                or "Final reviewer ne output return nahi kiya."
            )

            if last_result.get("final_result"):
                st.download_button(
                    "⬇️ Download Final Answer",
                    data=last_result["final_result"],
                    file_name="final_result.md",
                    mime="text/markdown",
                    use_container_width=True,
                )

        with tab2:
            st.markdown(
                last_result.get("review_result")
                or "Review output available nahi."
            )

        with tab3:
            outputs = last_result.get("agent_outputs", [])

            if outputs:
                for title, output in outputs:
                    with st.expander(str(title)):
                        st.markdown(
                            output or "Agent ne output return nahi kiya."
                        )
            else:
                st.info("Individual agent outputs available nahi hain.")


# ==================== AGENT WORKFLOW ====================
elif page == "Agent Workflow":

    st.title("🧩 Agent Workflow")
    st.write("Har agent ka apna specific role hai.")

    agents = [
        (
            "1. 🗺️ Planner Agent",
            "User ke task ko chhote steps aur checklist mein divide karta hai.",
        ),
        (
            "2. ⚙️ Worker Agent",
            "User ki requirements ke mutabiq requested output banata hai.",
        ),
        (
            "3. 🔍 Checker Agent",
            "Task ki requirements aur completeness check karne ke liye report banata hai.",
        ),
        (
            "4. 📝 Final Reviewer",
            "Available outputs ko combine karke final result aur gaps report karta hai.",
        ),
    ]

    for title, description in agents:
        st.markdown(
            f"""
            <div class="agent-card">
                <h3>{title}</h3>
                <p>{description}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.info(
        "Parallel execution ka actual implementation crew_runner.py "
        "aur agent files par depend karta hai. Is page par abhi "
        "live agent status ya real-time progress track nahi hoti."
    )


# ==================== TASK HISTORY ====================
elif page == "Task History":

    st.title("🕘 Task History")
    st.write("Is session mein run kiye gaye tasks.")

    if not history:
        st.info("Abhi koi task history available nahi hai.")

    else:
        st.caption(f"Recorded tasks: {len(history)}")

        if st.button("🗑️ Clear Session History"):
            st.session_state["task_history"] = []
            st.session_state["last_result"] = None
            st.rerun()

        for index, item in enumerate(history):
            status = item.get("status", "Unknown")

            with st.expander(
                f"{status} · {item.get('time', 'Unknown time')} · "
                f"{item.get('task', 'Untitled task')[:65]}"
            ):
                st.write("**Task:**", item.get("task", ""))
                st.write("**Status:**", status)

                if item.get("final_result"):
                    st.markdown("### Final Result")
                    st.markdown(item["final_result"])

                    st.download_button(
                        "Download this result",
                        data=item["final_result"],
                        file_name=f"task_result_{index + 1}.md",
                        mime="text/markdown",
                        key=f"history_download_{index}",
                    )

    st.caption(
        "Note: Yeh history filhal current Streamlit session tak limited hai. "
        "Permanent history ke liye database ya persistent storage chahiye."
    )


# ==================== SETTINGS ====================
elif page == "Settings":

    st.title("⚙️ Settings")

    st.subheader("🔌 Groq API Connection")

    try:
        api_key_configured = bool(st.secrets.get("GROQ_API_KEY", ""))
    except Exception:
        api_key_configured = False

    if api_key_configured:
        st.success("Groq API key configured hai.")
    else:
        st.warning(
            "GROQ_API_KEY nahi mili. Streamlit Cloud Secrets check karein."
        )

    st.write("**Model configuration**")
    st.code('GROQ_MODEL = "openai/gpt-oss-120b"', language="toml")

    st.caption(
        "Yeh displayed model naam example configuration hai. "
        "Actual model crew_runner.py ya llm_config.py se bhi set ho sakta hai."
    )

    st.divider()

    st.subheader("ℹ️ System Limitations")

    st.markdown(
        """
        - Task history abhi permanent database mein save nahi hoti.
        - Live progress aur token usage tracking abhi implement nahi hain.
        - Failed agent ko alag se retry karne ka feature abhi implement nahi hai.
        - Website operation, email sending aur live research ke liye
          additional tools aur permissions chahiye.
        """
    )
