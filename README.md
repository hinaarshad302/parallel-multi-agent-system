# Nexora AI — Parallel Multi-Agent AI Workspace

A professional AI workspace built with Python, CrewAI, Groq API, Streamlit, and Supabase. Nexora AI uses multiple AI agents to plan tasks, generate solutions, review outputs, and deliver structured results through a simple web interface.

## 🚀 Live Application

**Live Demo:**  
https://parallel-multi-agent-system-kijnmteevpxi38tvdrrafi.streamlit.app/

**GitHub Repository:**  
https://github.com/hinaarshad302/parallel-multi-agent-system

---

## 📌 Project Overview

Nexora AI is a parallel multi-agent AI system designed to divide complex tasks into smaller steps and process them through specialized AI agents.

Instead of relying on a single AI response, the system uses a coordinated workflow in which agents can plan, execute, review, and improve the final output.

The application provides a user-friendly Streamlit interface for submitting AI tasks, viewing generated results, and accessing task history.

## ✨ Key Features

- **Multi-Agent Workflow:** Coordinates multiple AI agents to process tasks.
- **Task Planning:** Breaks user requests into manageable steps.
- **AI Task Execution:** Generates responses using supported AI models.
- **Quality Review:** Reviews generated output before presenting the final result.
- **Task History:** Provides an interface for viewing previously saved tasks.
- **User Authentication:** Supports account-related functionality through Supabase.
- **Modern Dashboard:** Includes an overview, task studio, history, subscription, and account pages.
- **Structured Results:** Displays final responses and available agent outputs.
- **Search Evidence:** Provides a section for search evidence when available.
- **Streamlit Interface:** Runs through a browser-based application.

## 🛠️ Technology Stack

| Technology | Purpose |
|---|---|
| Python | Main programming language |
| CrewAI | Multi-agent orchestration |
| Groq API | AI model access |
| Streamlit | Web application interface |
| Supabase | Authentication and backend data services |
| Git and GitHub | Version control and source code hosting |

## 🤖 Multi-Agent Architecture

The application uses specialized agents to process a task through a coordinated workflow.

### 1. Planner Agent
Analyzes the user's request and identifies the steps needed to complete the task.

### 2. Worker Agent
Works on the task using the plan and generates the required content or solution.

### 3. Checker Agent
Reviews the work for quality, completeness, and potential issues.

### 4. Final Reviewer Agent
Uses the available task outputs and review context to prepare the final response.

### Workflow

User Request → Planner → Worker → Checker → Final Reviewer → Final Result

The exact execution order and available agent outputs depend on the implementation in the project code.

## 📂 Application Pages

### Overview
Displays the main dashboard and introduces the available application features.

### Run AI Task
Allows users to enter a task, run the multi-agent workflow, and view the generated result and agent outputs.

### Task History
Provides an interface to search and review previously saved tasks.

### Subscription
Displays the subscription interface and current plan information. Payment activation depends on the application's configured payment functionality.

### Account
Displays account-related information and provides available account actions.

## 📁 Project Structure

The project may contain additional files depending on the current repository version.

```text
parallel-multi-agent-system/
│
├── app.py
├── crew_runner.py
├── requirements.txt
├── README.md
└── .streamlit/
    └── secrets.toml
```

**Important:** Keep `.streamlit/secrets.toml` and all API keys private. Never upload secret credentials to a public GitHub repository.

## ⚙️ Installation and Setup

Follow these steps to run the project locally.

### Step 1: Clone the Repository

Open a terminal and run:

```bash
git clone https://github.com/hinaarshad302/parallel-multi-agent-system.git
```

Move into the project folder:

```bash
cd parallel-multi-agent-system
```

### Step 2: Create a Virtual Environment

```bash
python -m venv venv
```

Activate it on Windows:

```bash
venv\Scripts\activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Configure Environment Secrets

Create a file named `secrets.toml` inside the `.streamlit` directory.

Example:

```toml
GROQ_API_KEY = "your_groq_api_key"
SUPABASE_URL = "your_supabase_project_url"
SUPABASE_KEY = "your_supabase_key"
```

Replace the example values with your actual credentials. Use the correct secret names expected by your application code.

Do not commit real credentials to GitHub.

### Step 5: Run the Application

```bash
streamlit run app.py
```

The application should open in your browser. If it does not, follow the local URL shown in the terminal.

## 🔐 Authentication and Database

Supabase is used for the application's authentication and backend data functionality.

Before deploying the application, verify that:

- Supabase project credentials are configured correctly.
- Authentication flows work as expected.
- User-specific data is associated with the correct account.
- Database tables and columns match the application code.
- Row Level Security (RLS) policies protect private user data.
- Secret keys are stored securely in the deployment environment.

Task history and account features depend on the application's current database implementation and configuration.

## 🧪 Testing Checklist

Use this checklist after making changes or deploying a new version.

- [ ] Application opens successfully.
- [ ] Overview page displays correctly.
- [ ] User authentication works.
- [ ] Run AI Task accepts a user request.
- [ ] The multi-agent workflow executes successfully.
- [ ] Final results display correctly.
- [ ] Agent outputs display when available.
- [ ] Task history saves and displays the required results.
- [ ] Subscription page opens correctly.
- [ ] Account page opens correctly.
- [ ] Sidebar navigation works.
- [ ] Application works on desktop and mobile screens.

## 🚀 Deployment

The application is deployed through Streamlit Community Cloud.

Live application:

https://parallel-multi-agent-system-kijnmteevpxi38tvdrrafi.streamlit.app/

For deployment updates:

1. Make changes to the project locally or in GitHub.
2. Commit and push the changes to the connected repository.
3. Check the Streamlit deployment logs if the application fails to update or encounters an error.
4. Test the live application after deployment.

Configure all required secrets in the Streamlit application's settings rather than storing them in public source files.

## 🔮 Future Improvements

Potential future enhancements include:

- Improved parallel execution and agent coordination.
- More detailed workflow progress indicators.
- Better task-history storage and result retrieval.
- Export options for generated reports.
- Additional AI models and provider integrations.
- More comprehensive error handling and logging.
- Enhanced authentication and account management.
- Subscription management and payment integration.
- Automated testing and performance monitoring.

## 📊 Project Status

Nexora AI is an ongoing multi-agent AI application. Its available features depend on the current codebase, API configuration, database setup, and deployment environment.

The live application should be tested regularly to confirm that all pages and workflows are functioning correctly.

---

**Developed as a Python-based multi-agent AI project using CrewAI, Groq, Streamlit, and Supabase.**
