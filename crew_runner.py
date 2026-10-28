
# crew_runner.py
# CrewAI + Groq Browser Search + Streamlit

import time
import logging

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
    """Return a task's output safely as text."""
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


def run_user_task(user_task: str) -> dict:
    """Run Planner, Worker, Checker, and Final Reviewer in order."""

    if not isinstance(user_task, str) or not user_task.strip():
        raise ValueError("Please enter a task before running the agents.")

    started = time.time()
    user_task = user_task.strip()

    logger.info("[DEBUG] Starting get_llm()")
    llm = get_llm()
    logger.info(
        "[DEBUG] get_llm completed in %.1f seconds",
        time.time() - started,
    )

    # Search evidence is collected once and shared with relevant agents.
    logger.info("[DEBUG] Starting web search")
    search_started = time.time()

    try:
        search_results = search_web(
            "Research this task using reliable web sources. Prefer official "
            "and primary sources. Return source titles, URLs, relevant evidence, "
            "and explain which claims each source supports. Do not invent sources. "
            "Clearly disclose anything that could not be verified.\n\n"
            f"USER TASK:\n{user_task}"
        )
    except Exception:
        logger.exception("[DEBUG] Web search failed")
        search_results = (
            '{"status":"ERROR","search_response":"",'
            '"error":"Web search failed. See application logs."}'
        )

    logger.info(
        "[DEBUG] Web search returned in %.1f seconds",
        time.time() - search_started,
    )

    # Create agents.
    logger.info("[DEBUG] Creating agents")
    planner = create_planner_agent(llm)
    worker = create_worker_agent(llm)
    checker = create_checker_agent(llm)
    final_reviewer = create_final_reviewer_agent(llm)
    logger.info("[DEBUG] Agents created")

    # Task 1: Planner
    plan_task = Task(
        description=(
            f"USER REQUEST:\n{user_task}\n\n"
            "Create a concise plan with explicit requirements, expected "
            "format, language, and completion criteria. For research tasks, "
            "include evidence checking. Do not produce the final deliverable."
        ),
        expected_output="A concise plan and completion checklist.",
        agent=planner,
        async_execution=False,
    )

    # Task 2: Worker
    work_task = Task(
        description=(
            f"USER REQUEST:\n{user_task}\n\n"
            f"WEB SEARCH EVIDENCE:\n{search_results}\n\n"
            "Create the requested deliverable. Follow the user's format, "
            "language, and scope. Use the supplied evidence for factual "
            "research when relevant. A source title or URL alone does not "
            "prove a claim. Never invent citations, quotations, statistics, "
            "URLs, or verification results. If evidence is missing or "
            "insufficient, label the affected claim UNVERIFIED. If search "
            "failed, disclose that limitation. Do not claim that you "
            "performed actions that did not occur."
        ),
        expected_output="The requested deliverable with honest evidence labels.",
        agent=worker,
        context=[plan_task],
        async_execution=False,
    )

    # Task 3: Checker
    check_task = Task(
        description=(
            f"ORIGINAL USER REQUEST:\n{user_task}\n\n"
            f"WEB SEARCH EVIDENCE:\n{search_results}\n\n"
            "Review the actual worker deliverable available in your task "
            "context. Compare it with the original request and the evidence.\n\n"
            "Check these items:\n"
            "1. Are explicit requirements and requested counts satisfied?\n"
            "2. Are important factual claims supported by the supplied evidence?\n"
            "3. Do cited titles and URLs match the claims they support?\n"
            "4. Distinguish a confirmed contradiction from missing evidence.\n"
            "5. Mark a claim UNVERIFIED when evidence is insufficient. Do not "
            "claim to have independently opened or verified a source unless "
            "the supplied evidence establishes that.\n"
            "6. Do not mark claims verified just because citations are present.\n\n"
            "Return this format only:\n"
            "STATUS: COMPLETE, PARTIAL, or NOT COMPLETE\n"
            "FULFILLED: Requirements satisfied.\n"
            "GAPS: Important unmet requirements, contradictions, or unverified "
            "claims. Write None identified if there are none.\n"
            "NEXT STEPS: Necessary corrections. Write None if no action is needed."
        ),
        expected_output="An evidence-based quality and completeness review.",
        agent=checker,
        context=[work_task],
        async_execution=False,
    )

    # Task 4: Final Reviewer
    final_task = Task(
        description=(
            f"ORIGINAL USER REQUEST:\n{user_task}\n\n"
            f"WEB SEARCH EVIDENCE:\n{search_results}\n\n"
            "Prepare the final deliverable requested by the user, using the "
            "actual Planner, Worker, and Checker outputs supplied in your "
            "task context.\n\n"
            "MANDATORY RULES:\n"
            "1. Read the Checker's STATUS, GAPS, and NEXT STEPS.\n"
            "2. Correct important issues identified by the Checker.\n"
            "3. Correct a claim only when supplied evidence supports the "
            "correction. Otherwise disclose uncertainty.\n"
            "4. Label unsupported factual claims UNVERIFIED, or remove them "
            "if they are not needed.\n"
            "5. Do not describe a source as verified merely because a URL or "
            "title exists. Never invent sources or verification results.\n"
            "6. Respect the user's requested language, format, and scope.\n"
            "7. Return the deliverable itself, not an internal review report."
        ),
        expected_output=(
            "The requested final deliverable, with checker issues addressed "
            "and evidence limitations clearly disclosed."
        ),
        agent=final_reviewer,
        context=[plan_task, work_task, check_task],
        async_execution=False,
    )

    crew = Crew(
        agents=[planner, worker, checker, final_reviewer],
        tasks=[plan_task, work_task, check_task, final_task],
        process=Process.sequential,
        verbose=True,
    )

    logger.info("[DEBUG] Starting crew.kickoff()")

    try:
        crew.kickoff()
    except Exception as exc:
        logger.exception("[DEBUG] Crew execution failed")
        raise RuntimeError(
            f"AI agents failed: {type(exc).__name__}: {str(exc)[:300]}"
        ) from exc

    logger.info(
        "[DEBUG] crew.kickoff() finished in %.1f seconds",
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
            "Workflow finished without a final answer. "
            "Check Streamlit Cloud logs for technical details."
        )

    return {
        "final_result": final_output,
        "review_result": review_output,
        "search_results": search_results,
        "agent_outputs": agent_outputs,
    }
