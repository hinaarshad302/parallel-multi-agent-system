import streamlit as st
from crew_runner import run_user_task

st.set_page_config(page_title="Simple Multi-Agent System", page_icon="🤖", layout="wide")

st.title("🤖 Simple Multi-Agent Task System")
st.write(
    "Apna task likhein. Teen AI agents parallel mein task ko plan, execute aur check karenge. "
    "Phir ek final reviewer unke results ko combine karega."
)

with st.expander("System kaise kaam karta hai?"):
    st.markdown(
        """
        1. **Planner Agent** — task ke steps aur completion checklist banata hai.
        2. **Worker Agent** — user ke task ka requested text-based output banata hai.
        3. **Checker Agent** — task ko evaluate karne ke liye independent checklist banata hai.
        4. **Final Reviewer** — teenon outputs ko dekh kar final result aur gaps report karta hai.

        Pehle teen agents parallel mein kaam karte hain. Final Reviewer unke complete hone ke baad result banata hai.
        """
    )

st.warning(
    "First version text-based tasks ke liye hai. Yeh apne aap har website operate, email send, "
    "file delete, ya live internet research nahi kar sakta. External actions ke liye tools aur permissions add karni hongi."
)

task = st.text_area(
    "Apna task yahan likhein",
    placeholder="Example: Create a beginner-friendly 4-week Python learning roadmap with weekly goals and practice tasks.",
    height=160,
)

if st.button("Run Agents", type="primary", use_container_width=True):
    if not task.strip():
        st.error("Pehle apna task likhein.")
    elif len(task.strip()) < 8:
        st.error("Please task thora detail mein likhein.")
    else:
        try:
            with st.spinner("Agents parallel mein kaam kar rahe hain. Thora wait karein..."):
                result = run_user_task(task.strip())

            st.success("Workflow run complete.")
            st.subheader("Final Result")
            st.markdown(result["final_result"] or "Final reviewer ne output return nahi kiya.")

            st.subheader("Quality / Completeness Review")
            st.markdown(result["review_result"] or "Review output available nahi.")

            with st.expander("Individual agent results dekhein"):
                for title, output in result["agent_outputs"]:
                    st.markdown(f"### {title}")
                    st.markdown(output or "Agent ne output return nahi kiya.")
        except Exception as exc:
            st.error("App task run nahi kar saka. Neeche error diya gaya hai.")
            st.code(str(exc))
            st.markdown(
                "Check karein: Streamlit Secrets mein `GROQ_API_KEY`, Groq model access, "
                "API limits, aur Streamlit Cloud build logs."
            )
