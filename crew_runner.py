# crew_runner.py
# Nexora AI - Five-Agent Hybrid Multi-Agent System
# Planner -> Worker + Research (Parallel) -> Checker -> Final Reviewer

import json
import logging
import time

from crewai import Crew, Process, Task

from llm_config import get_llm
from groq_search import search_web

from agents.planner_agent import create_planner_agent
from agents.worker_agent import create_worker_agent
from agents.research_agent import create_research_agent
from agents.checker_agent import create_checker_agent
from agents.final_reviewer_agent import create_final_reviewer_agent


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("crew_runner")


# Groq compatibility fix
try:
    import crewai.llms.cache as crew_cache
    crew_cache.mark_cache_breakpoint = lambda msg: msg
except Exception:
    logging.exception("Could not apply Groq compatibility patch")


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
        result = str(raw if raw is not None else output)

        return result[:MAX_OUTPUT_CHARS]

    except Exception:
        logger.exception("Could not extract task output")
        return ""


def _needs_web_search(user_task):
    """Check whether the task needs current or reliable web research."""

    keywords = (
        "latest",
        "current",
        "today",
        "news",
        "research",
        "search the web",
        "find sources",
        "reliable information",
        "reliable sources",
        "credible sources",
        "trusted sources",
        "authoritative sources",
        "use reliable",
        "evidence",
        "citation",
        "citations",
        "reference",
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
    """Fetch relevant search evidence when needed."""

    if not _needs_web_search(user_task):
        return (
            "Web search was not performed for this task. "
            "Do not claim that external sources were verified."
        )

    try:
        query = (
            "Find concise and relevant evidence for this task. "
            "Prefer official and primary sources. Return source URLs. "
            "Never invent citations or sources.\n\n"
            f"USER TASK:\n{user_task[:2000]}"
        )

        raw_results = search_web(query)

        if isinstance(raw_results, (dict, list)):
            result_text = json.dumps(
                raw_results,
                ensure_ascii=False,
                default=str,
            )
        else:
            result_text = str(raw_results)

        return result_text[:MAX_SEARCH_CHARS]

    except Exception as exc:
        logger.exception("Web search failed")

        return (
            "Web search was unavailable. "
            f"Error type: {type(exc).__name__}. "
            "Do not invent sources or claim verification."
        )


def run_user_task(user_task: str) -> dict:
    """Run the five-agent hybrid workflow."""

    if not isinstance(user_task, str) or not user_task.strip():
        raise ValueError("Please enter a task before running the agents.")

    user_task = user_task.strip()

    if len(user_task) > MAX_USER_TASK_CHARS:
        raise ValueError(
            f"Your task is too long ({len(user_task)} characters). "
            f"Please keep it under {MAX_USER_TASK_CHARS} characters."
        )

    started = time.time()

    # STEP 1: Initialize language model
    logger.info("Initializing language model")

    try:
        llm = get_llm()

    except Exception as exc:
        logger.exception("LLM initialization failed")

        raise RuntimeError(
            "LLM setup failed. Check llm_config.py and GROQ_API_KEY. "
            f"Details: {type(exc).__name__}: {str(exc)[:200]}"
        ) from exc

    # STEP 2: Collect research evidence
    logger.info("Collecting research evidence")

    search_results = _get_search_results(user_task)

    # STEP 3: Create five agents
    logger.info("Creating five agents")

    try:
        planner = create_planner_agent(llm)
        worker = create_worker_agent(llm)
        researcher = create_research_agent(llm)
        checker = create_checker_agent(llm)
        final_reviewer = create_final_reviewer_agent(llm)

    except Exception as exc:
        logger.exception("Agent creation failed")

        raise RuntimeError(
            f"Agent setup failed: {type(exc).__name__}: {str(exc)[:200]}"
        ) from exc

    # STEP 4: Planner task
    plan_task = Task(
        description=(
            f"USER REQUEST:\n{user_task}\n\n"
            "Understand the user's requirements and prepare a clear plan. "
            "Identify the expected deliverable, format, language and "
            "completion criteria. Use no more than 8 bullet points. "
            "Do not produce the final answer."
        ),
        expected_output="A concise task plan with completion criteria.",
        agent=planner,
        async_execution=False,
    )

    # STEP 5A: Worker task
    # This task runs asynchronously.
    work_task = Task(
        description=(
            f"USER REQUEST:\n{user_task}\n\n"
            "Follow the Planner's task plan in your context. "
            "Create the requested deliverable directly. "
            "Follow the user's requested language and format. "
            "Do not invent facts, sources or URLs. "
            "Keep the output clear and useful."
        ),
        expected_output="The requested deliverable.",
        agent=worker,
        context=[plan_task],
        async_execution=True,
    )

    # STEP 5B: Research task
    # This runs in parallel with the Worker task.
    research_task = Task(
        description=(
            f"USER REQUEST:\n{user_task}\n\n"
            f"AVAILABLE RESEARCH EVIDENCE:\n{search_results}\n\n"
            "Follow the Planner's task plan. Analyze the available "
            "evidence relevant to the user's request. "
            "Identify supported facts, source titles and URLs when "
            "available. Explain evidence limitations. "
            "Never invent sources, statistics or citations. "
            "If no external research was performed, clearly state that. "
            "Keep your report concise."
        ),
        expected_output=(
            "A concise research report containing relevant evidence, "
            "sources and limitations."
        ),
        agent=researcher,
        context=[plan_task],
        async_execution=True,
    )

    # STEP 6: Checker waits for both parallel tasks.
    check_task = Task(
        description=(
            f"ORIGINAL USER REQUEST:\n{user_task}\n\n"
            "Review the Worker's deliverable and Researcher's report "
            "in your task context. Check the requested format, language, "
            "requirements, important facts and evidence limitations. "
            "Identify important omissions or contradictions. "
            "Do not invent facts or treat unverified claims as confirmed.\n\n"
            "Return a concise report using this format:\n"
            "STATUS: COMPLETE, PARTIAL, or NOT COMPLETE\n"
            "ISSUES: Important issues, or None identified\n"
            "CORRECTIONS: Necessary corrections, or None\n"
            "EVIDENCE LIMITS: Unverified claims, or None identified"
        ),
        expected_output="A quality-check report with status and issues.",
        agent=checker,
        context=[work_task, research_task],
        async_execution=False,
    )

    # STEP 7: Final Reviewer receives all previous outputs.
    final_task = Task(
        description=(
            f"ORIGINAL USER REQUEST:\n{user_task}\n\n"
            "Read all previous agent outputs carefully. "
            "Prepare the final answer requested by the user. "
            "Use the Checker's feedback to improve the answer. "
            "Do not invent facts, sources or URLs. "
            "Only use references that are present in the Researcher's report. "
            "If no web search was performed, do not add citations or references. "
            "Clearly mention that external sources were not verified. "
            "Keep the answer clear and follow the user's requested format."
        ),
        expected_output="The final reviewed user-facing deliverable.",
        agent=final_reviewer,
        context=[
            plan_task,
            work_task,
            research_task,
            check_task,
        ],
        async_execution=False,
    )

    # STEP 8: Run the hybrid workflow.
    # Worker and Researcher run concurrently.
    crew = Crew(
        agents=[
            planner,
            worker,
            researcher,
            checker,
            final_reviewer,
        ],
        tasks=[
            plan_task,
            work_task,
            research_task,
            check_task,
            final_task,
        ],
        process=Process.sequential,
        verbose=False,
    )

    logger.info("Starting five-agent hybrid workflow")

    try:
        crew.kickoff()

    except Exception as exc:
        logger.exception("Five-agent workflow failed")

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
                "Groq rate limit or token quota reached. "
                "Try again after the limit resets or check your "
                "Groq account limits."
            ) from exc

        raise RuntimeError(
            f"AI workflow failed: {type(exc).__name__}: {str(exc)[:300]}"
        ) from exc

    # STEP 9: Collect all agent outputs.
    plan_output = _output(plan_task)
    worker_output = _output(work_task)
    research_output = _output(research_task)
    review_output = _output(check_task)
    final_output = _output(final_task)

    # Preserve Worker output if Final Reviewer returns empty output.
    if not final_output.strip() and worker_output.strip():
        logger.warning(
            "Final Reviewer returned empty output. Using Worker output."
        )
        final_output = worker_output

    if not final_output.strip():
        raise RuntimeError(
            "The workflow finished without a usable final answer. "
            "Check the Streamlit logs and model configuration."
        )

    elapsed = round(time.time() - started, 2)

    agent_outputs = [
        ("1. Planner Agent", plan_output),
        ("2. Worker Agent", worker_output),
        ("3. Research Agent", research_output),
        ("4. Checker Agent", review_output),
        ("5. Final Reviewer", final_output),
    ]

    logger.info("Workflow completed in %s seconds", elapsed)

    return {
        "final_result": final_output,
        "review_result": review_output,
        "search_results": search_results,
        "agent_outputs": agent_outputs,
        "elapsed_seconds": elapsed,
    }
