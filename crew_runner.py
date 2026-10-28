
# crew_runner.py
# Nexora AI - Four-Agent Parallel Multi-Agent System
# Planner -> Worker -> Checker -> Final Reviewer

import json
import logging
import time

from crewai import Crew, Process, Task

from llm_config import get_llm
from groq_search import search_web

from agents.planner_agent import create_planner_agent
from agents.worker_agent import create_worker_agent
from agents.checker_agent import create_checker_agent
from agents.final_reviewer_agent import create_final_reviewer_agent


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("crew_runner")

# Input and context limits to help control token usage.
MAX_USER_TASK_CHARS = 4000
MAX_SEARCH_CHARS = 1500
MAX_OUTPUT_CHARS = 6000


def _output(task):
    """Safely extract task output as plain text."""
    try:
        output = getattr(task, "output", None)

        if output is None:
            return ""

        raw = getattr(output, "raw", None)
        text = str(raw if raw is not None else output)

        return text[:MAX_OUTPUT_CHARS]
    except Exception:
        logger.exception("Could not extract task output")
        return ""


def _needs_web_search(user_task):
    """Determine whether the task likely needs current web evidence."""
    keywords = (
        "latest",
        "current",
        "today",
        "news",
        "research",
        "search the web",
        "find sources",
        "citations",
        "references",
        "verify",
        "fact-check",
        "recent",
        "2026",
        "2025",
        "compare websites",
    )

    task_lower = user_task.lower()
    return any(word in task_lower for word in keywords)


def _get_search_results(user_task):
    """Fetch and limit search evidence before passing it to agents."""
    if not _needs_web_search(user_task):
        return (
            "Web search was not performed. "
            "Do not claim that external sources were verified."
        )

    try:
        query = (
            "Find concise, relevant evidence for this task. "
            "Prefer official and primary sources. Return source URLs. "
            "Do not invent citations or sources.\n\n"
            f"USER TASK:\n{user_task[:2000]}"
        )

        raw_results = search_web(query)

        if isinstance(raw_results, (dict, list)):
            text = json.dumps(
                raw_results,
                ensure_ascii=False,
                default=str,
            )
        else:
            text = str(raw_results)

        # Limit evidence sent to the LLM.
        return text[:MAX_SEARCH_CHARS]

    except Exception as exc:
        logger.exception("Web search failed")
        return (
            "Web search unavailable. "
            f"Error type: {type(exc).__name__}. "
            "Do not invent sources or claim verification."
        )


def run_user_task(user_task: str) -> dict:
    """Execute the four-agent workflow and return the final result."""

    if not isinstance(user_task, str) or not user_task.strip():
        raise ValueError("Please enter a task before running the agents.")

    user_task = user_task.strip()

    if len(user_task) > MAX_USER_TASK_CHARS:
        raise ValueError(
            f"Your task is too long ({len(user_task)} characters). "
            f"Please keep it under {MAX_USER_TASK_CHARS} characters."
        )

    started = time.time()

    # Step 1: Initialize the model.
    logger.info("Initializing language model")

    try:
        llm = get_llm()
    except Exception as exc:
        logger.exception("LLM initialization failed")
        raise RuntimeError(
            "LLM setup failed. Check llm_config.py and your API key. "
            f"Details: {type(exc).__name__}: {str(exc)[:200]}"
        ) from exc

    # Step 2: Gather limited search evidence.
    search_results = _get_search_results(user_task)

    # Step 3: Create all four agents.
    logger.info("Creating four agents")

    try:
        planner = create_planner_agent(llm)
        worker = create_worker_agent(llm)
        checker = create_checker_agent(llm)
        final_reviewer = create_final_reviewer_agent(llm)
    except Exception as exc:
        logger.exception("Agent creation failed")
        raise RuntimeError(
            f"Agent setup failed: {type(exc).__name__}: {str(exc)[:200]}"
        ) from exc

    # Task 1: Planner.
    plan_task = Task(
        description=(
            f"USER REQUEST:\n{user_task}\n\n"
            "Create a short plan with the deliverable, format, language, "
            "requirements and completion criteria. "
            "Use no more than 8 concise bullet points. "
            "Do not create the final deliverable."
        ),
        expected_output="A concise plan of no more than 8 bullet points.",
        agent=planner,
        async_execution=False,
    )

    # Task 2: Worker.
    work_task = Task(
        description=(
            f"USER REQUEST:\n{user_task}\n\n"
            f"SEARCH EVIDENCE (may be incomplete):\n{search_results}\n\n"
            "Follow the Planner's plan in your task context. "
            "Produce the requested deliverable directly. "
            "Follow the user's language and format. "
            "Do not invent facts, citations or URLs. "
            "Keep the response focused and avoid repeating the request."
        ),
        expected_output="The requested deliverable, clearly formatted.",
        agent=worker,
        context=[plan_task],
        async_execution=False,
    )

    # Task 3: Checker.
    check_task = Task(
        description=(
            f"USER REQUEST:\n{user_task}\n\n"
            "Review the Worker's deliverable in your task context. "
            "Check whether it follows the request, format and language. "
            "Identify important omissions, unsupported claims and errors. "
            "Do not rewrite the complete deliverable.\n\n"
            "Return a concise report in this format:\n"
            "STATUS: COMPLETE, PARTIAL, or NOT COMPLETE\n"
            "ISSUES: Important issues, or None identified\n"
            "CORRECTIONS: Necessary corrections, or None\n"
            "EVIDENCE LIMITS: Unverified claims, or None identified"
        ),
        expected_output="A short quality-check report.",
        agent=checker,
        context=[work_task],
        async_execution=False,
    )

    # Task 4: Final Reviewer.
    # The Checker already has the Worker's output in its context.
    # Passing only check_task here helps avoid duplicating the full
    # Worker output in the Final Reviewer's explicit context.
    final_task = Task(
        description=(
            f"ORIGINAL USER REQUEST:\n{user_task}\n\n"
            "Use the Checker report in your task context. "
            "Produce the final deliverable requested by the user. "
            "Apply necessary corrections only when supported. "
            "Preserve the user's requested language and format. "
            "Do not output internal agent notes or a review report. "
            "Do not invent evidence. Disclose material uncertainty."
        ),
        expected_output="The final user-facing deliverable.",
        agent=final_reviewer,
        context=[check_task],
        async_execution=False,
    )

    # Step 4: Run the four agents in order.
    crew = Crew(
        agents=[planner, worker, checker, final_reviewer],
        tasks=[plan_task, work_task, check_task, final_task],
        process=Process.sequential,
        verbose=False,
    )

    logger.info("Starting four-agent workflow")

    try:
        crew.kickoff()
    except Exception as exc:
        logger.exception("Four-agent workflow failed")

        error_text = str(exc).lower()

        if any(
            phrase in error_text
            for phrase in (
                "rate_limit",
                "rate limit",
                "tokens per minute",
                "tokens per day",
                "request too large",
                "429",
            )
        ):
            raise RuntimeError(
                "Groq token/rate limit error. The request may still be "
                "too large for the available quota. Reduce agent prompts "
                "and task context, or use a model/provider with sufficient "
                "available limits. Check llm_config.py and agent files."
            ) from exc

        raise RuntimeError(
            f"AI workflow failed: {type(exc).__name__}: {str(exc)[:300]}"
        ) from exc

    elapsed = round(time.time() - started, 2)

    # Step 5: Collect outputs.
    plan_output = _output(plan_task)
    worker_output = _output(work_task)
    review_output = _output(check_task)
    final_output = _output(final_task)

    # A final reviewer can occasionally return empty output.
    # In that case, preserve the Worker's deliverable rather than
    # discarding a useful result.
    if not final_output.strip() and worker_output.strip():
        logger.warning(
            "Final Reviewer returned empty output; using Worker output"
        )
        final_output = worker_output

    if not final_output.strip():
        raise RuntimeError(
            "The workflow finished without a usable final answer. "
            "Check the Streamlit logs and model configuration."
        )

    agent_outputs = [
        ("1. Planner Agent", plan_output),
        ("2. Worker Agent", worker_output),
        ("3. Checker Agent", review_output),
        ("4. Final Reviewer", final_output),
    ]

    logger.info("Workflow finished in %s seconds", elapsed)

    return {
        "final_result": final_output,
        "review_result": review_output,
        "search_results": search_results,
        "agent_outputs": agent_outputs,
        "elapsed_seconds": elapsed,
    }
