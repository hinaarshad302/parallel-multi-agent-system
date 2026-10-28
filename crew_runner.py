
# crew_runner.py
# Four-Agent AI System: Planner, Worker, Checker, Final Reviewer

import json
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _disable_cache_breakpoint():
    """Compatibility workaround for supported CrewAI versions."""

    def _return_message_unchanged(message, *args, **kwargs):
        if isinstance(message, dict):
            message.pop("cache_breakpoint", None)
        return message

    try:
        import crewai.llms.cache as cache_module
        cache_module.mark_cache_breakpoint = _return_message_unchanged
    except (ImportError, AttributeError):
        pass

    module_names = (
        "crewai.experimental.agent_executor",
        "crewai.agents.crew_agent_executor",
        "crewai.llms.base_llm",
    )

    for module_name in module_names:
        try:
            module = __import__(
                module_name,
                fromlist=["mark_cache_breakpoint"],
            )
            if hasattr(module, "mark_cache_breakpoint"):
                module.mark_cache_breakpoint = _return_message_unchanged
        except (ImportError, AttributeError):
            pass


_disable_cache_breakpoint()

from crewai import Crew, Process, Task

from llm_config import get_llm
from groq_search import search_web

from agents.planner_agent import create_planner_agent
from agents.worker_agent import create_worker_agent
from agents.checker_agent import create_checker_agent
from agents.final_reviewer_agent import create_final_reviewer_agent


def _output(task):
    """Safely return task output as text."""
    try:
        output = task.output
        if output is not None:
            raw = getattr(output, "raw", None)
            if raw:
                return str(raw)
            return str(output)
    except (AttributeError, TypeError):
        pass
    return ""


def _needs_web_search(user_task):
    """Decide whether the task likely needs current external evidence."""
    task_lower = user_task.lower()

    research_keywords = (
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

    return any(keyword in task_lower for keyword in research_keywords)


def run_user_task(user_task: str) -> dict:
    """Run all four agents sequentially and return the final deliverable."""

    if not isinstance(user_task, str) or not user_task.strip():
        raise ValueError("Please enter a task before running the agents.")

    started = time.time()
    user_task = user_task.strip()

    # Initialize the language model.
    logger.info("[DEBUG] Initializing LLM")
    try:
        llm = get_llm()
    except Exception as exc:
        logger.exception("LLM initialization failed")
        raise RuntimeError(
            f"LLM setup failed: {type(exc).__name__}: {str(exc)[:250]}"
        ) from exc

    # Search only when external research appears necessary.
    if _needs_web_search(user_task):
        logger.info("[DEBUG] Web search required")
        try:
            raw_search_results = search_web(
                "Research this task using reliable sources. Prefer official "
                "and primary sources. Return concise evidence and source URLs. "
                "Do not invent sources, citations, or verification results.\n\n"
                f"USER TASK:\n{user_task}"
            )

            try:
                parsed = json.loads(raw_search_results)
            except (ValueError, TypeError):
                parsed = {
                    "status": "UNKNOWN",
                    "search_response": str(raw_search_results)[:6000],
                }

            # Keep the context short to reduce tokens.
            search_results = json.dumps(
                parsed,
                ensure_ascii=False,
            )[:6000]

        except Exception as exc:
            logger.exception("Web search failed")
            search_results = json.dumps(
                {
                    "status": "ERROR",
                    "search_response": "",
                    "error": (
                        f"Search unavailable: {type(exc).__name__}. "
                        "Do not invent evidence."
                    ),
                }
            )
    else:
        logger.info("[DEBUG] Skipping web search")
        search_results = json.dumps(
            {
                "status": "SKIPPED",
                "search_response": (
                    "No external search was performed. "
                    "Use available knowledge and disclose uncertainty."
                ),
            }
        )

    # Create all four agents. Do not remove any agent.
    logger.info("[DEBUG] Creating four agents")

    planner = create_planner_agent(llm)
    worker = create_worker_agent(llm)
    checker = create_checker_agent(llm)
    final_reviewer = create_final_reviewer_agent(llm)

    # Task 1: Planner
    plan_task = Task(
        description=(
            f"USER REQUEST:\n{user_task}\n\n"
            "Create a concise plan. Identify the requested deliverable, "
            "format, language, requirements, and completion criteria. "
            "Do not write the final deliverable."
        ),
        expected_output="A concise plan and completion checklist.",
        agent=planner,
        async_execution=False,
    )

    # Task 2: Worker
    work_task = Task(
        description=(
            f"USER REQUEST:\n{user_task}\n\n"
            f"AVAILABLE SEARCH EVIDENCE:\n{search_results}\n\n"
            "Create the requested deliverable. Follow the plan and the "
            "user's requested format and language. Do not invent facts, "
            "citations, URLs, quotations, or verification. If evidence is "
            "insufficient, disclose the limitation."
        ),
        expected_output="The requested deliverable.",
        agent=worker,
        context=[plan_task],
        async_execution=False,
    )

    # Task 3: Checker
    check_task = Task(
        description=(
            f"ORIGINAL USER REQUEST:\n{user_task}\n\n"
            f"AVAILABLE SEARCH EVIDENCE:\n{search_results}\n\n"
            "Review the worker's actual deliverable in your task context. "
            "Check requirements, requested counts, format, factual claims, "
            "and evidence. Do not treat a URL alone as proof. Distinguish "
            "unsupported claims from confirmed contradictions.\n\n"
            "Return this format:\n"
            "STATUS: COMPLETE, PARTIAL, or NOT COMPLETE\n"
            "FULFILLED: Requirements satisfied.\n"
            "GAPS: Important omissions or unverified claims, or None identified.\n"
            "NEXT STEPS: Necessary corrections, or None."
        ),
        expected_output="A concise completeness and evidence review.",
        agent=checker,
        context=[work_task],
        async_execution=False,
    )

    # Task 4: Final Reviewer
    final_task = Task(
        description=(
            f"ORIGINAL USER REQUEST:\n{user_task}\n\n"
            "Prepare the final deliverable using the Planner, Worker, "
            "and Checker outputs in your task context.\n\n"
            "Read the Checker's status and gaps. Correct important issues "
            "only when supported by evidence. Do not invent sources or "
            "verification. Disclose unresolved uncertainty. Follow the "
            "original user's format and language. Return the deliverable "
            "itself, not internal review notes."
        ),
        expected_output="The final requested deliverable.",
        agent=final_reviewer,
        context=[plan_task, work_task, check_task],
        async_execution=False,
    )

    # Keep the required four-agent sequential workflow.
    crew = Crew(
        agents=[planner, worker, checker, final_reviewer],
        tasks=[plan_task, work_task, check_task, final_task],
        process=Process.sequential,
        verbose=False,
    )

    logger.info("[DEBUG] Starting four-agent workflow")

    try:
        crew.kickoff()
    except Exception as exc:
        logger.exception("Four-agent workflow failed")
        error_text = str(exc).lower()

        if (
            "429" in error_text
            or "rate_limit" in error_text
            or "rate limit" in error_text
            or "tokens per day" in error_text
        ):
            raise RuntimeError(
                "Groq ki rate/token limit khatam ho gayi hai. "
                "Quota reset hone ya available quota wale model/provider "
                "ka intezam hone ke baad dobara try karein."
            ) from exc

        raise RuntimeError(
            f"AI agents failed: {type(exc).__name__}: {str(exc)[:300]}"
        ) from exc

    logger.info(
        "[DEBUG] Four-agent workflow finished in %.1f seconds",
        time.time() - started,
    )

    final_output = _output(final_task)
    review_output = _output(check_task)

    agent_outputs = [
        ("1. Planner Agent", _output(plan_task)),
        ("2. Worker Agent", _output(work_task)),
        ("3. Checker Agent", review_output),
        ("4. Final Reviewer", final_output),
    ]

    if not final_output.strip():
        raise RuntimeError(
            "Workflow completed without a final answer. "
            "Please check the Streamlit Cloud logs."
        )

    return {
        "final_result": final_output,
        "review_result": review_output,
        "search_results": search_results,
        "agent_outputs": agent_outputs,
    }
