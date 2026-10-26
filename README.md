# Simple Parallel Multi-Agent Task System

A simple beginner MVP using Streamlit + CrewAI + Groq.

## How it works
Three independent tasks run asynchronously:
1. Planner creates a plan and completion criteria.
2. Worker creates the requested text-based deliverable.
3. Checker creates an independent completeness checklist.

A final reviewer waits for those outputs and combines them into one report.

## Limitations
This first version can generate text-based deliverables such as plans, drafts, reports, explanations, and code. It cannot automatically perform every real-world task. Live web research, email, website control, file operations, and other external actions require explicit tools, permissions, and verification.

## Deploy without installing Python locally
1. Upload this repository structure to GitHub.
2. Create an API key in https://console.groq.com/.
3. Open https://share.streamlit.io/ and connect GitHub.
4. Select this repository, branch, and `app.py` as the entrypoint.
5. In Streamlit Advanced settings / Secrets, add:
   `GROQ_API_KEY = "your-real-key"`
   Optional: `GROQ_MODEL = "openai/gpt-oss-120b"`
6. Deploy and test.

Never put your real API key in public code or commit it to GitHub.

## Dependency notes
Streamlit Cloud installs packages from `requirements.txt`; no local installation is needed. The project uses CrewAI's LLM interface with the Groq provider (`groq/openai/gpt-oss-120b`). `crewai[litellm]` includes the provider integration dependency. Package installation and live API behavior have not been tested in this environment; check Streamlit Cloud logs if the build fails.
