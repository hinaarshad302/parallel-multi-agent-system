
# crew_runner.py
# Parallel Multi-Agent AI System
# CrewAI + Groq + Browser Search + Streamlit

def _disable_cache_breakpoint():
    """Apply a compatibility workaround for cache_breakpoint."""

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
    """Safely retrieve a task's raw output."""
    try:
        if task.output is not None:
            return task.output.raw or ""
    except (AttributeError, TypeError):
        pass

    return ""


def run_user_task(user_task: str) -> dict:
    """Run the user's request through the four-agent workflow."""

    if not isinstance(user_task, str) or not user_task.strip():
        raise ValueError("Please enter a task before running the agents.")

    llm = get_llm()

    # Step 1: Search for evidence using Groq Browser Search.
    # Search errors are retained and disclosed to the agents.
    search_results = search_web(
        "Research the user's task using reliable web sources. "
        "Prefer official and primary sources. Return source titles, "
        "URLs, relevant evidence, and explain which claims the evidence "
        "supports. Do not invent sources. Clearly label unverified claims.\n\n"
        f"USER TASK:\n{user_task}"
    )

    # Create the four agents.
    planner = create_planner_agent(llm)
    worker = create_worker_agent(llm)
    checker = create_checker_agent(llm)
    final_reviewer = create_final_reviewer_agent(llm)

    # Task 1: Planner
    plan_task = Task(
        description=(
            f"ORIGINAL USER REQUEST:\n{user_task}\n\n"
            "Create a concise plan before work begins. Identify the user's "
            "requirements, requested format, language, and completion criteria. "
            "For factual research tasks, include a step to use the supplied "
            "web search evidence. Do not perform the worker's task."
        ),
        expected_output=(
            "A concise plan listing the user's requirements and "
            "measurable completion criteria."
        ),
        agent=planner,
        async_execution=True,
    )

    # Task 2: Worker
    work_task = Task(
        description=(
            f"ORIGINAL USER REQUEST:\n{user_task}\n\n"
            f"WEB SEARCH RESULTS:\n{search_results}\n\n"
            "Produce the requested deliverable. Follow the user's requested "
            "language, format, scope, and level of detail.\n\n"
            "For factual research, use the supplied web search results as "
            "evidence. Cite relevant source titles and URLs when appropriate. "
            "Only connect a source to a claim when the supplied evidence "
            "supports that connection. Do not invent facts, references, "
            "quotes, statistics, publication dates, or URLs.\n\n"
            "If the search returned an error, no useful evidence, or "
            "insufficient evidence for a claim, clearly mark that claim "
            "or source as UNVERIFIED. Do not say that a source was verified "
            "unless the available evidence supports that statement. "
            "Do not claim to have performed external actions that did not occur."
        ),
        expected_output="The requested deliverable, with appropriate evidence.",
        agent=worker,
        context=[plan_task],
        async_execution=True,
    )

    # Task 3: Checker
    check_task = Task(
        description=(
            f"ORIGINAL USER REQUEST:\n{user_task}\n\n"
            f"WEB SEARCH RESULTS:\n{search_results}\n\n"
            "Review the worker's actual deliverable and the supplied search "
            "evidence. Evaluate the deliverable, not merely its appearance.\n\n"

            "A. REQUIREMENT CHECK\n"
            "1. Identify the requirements explicitly stated by the user.\n"
            "2. Compare the deliverable with each requirement.\n"
            "3. Count items only when a specific number or format was requested.\n"
            "4. Report important gaps supported by evidence.\n\n"

            "B. FACTS AND CITATIONS\n"
            "1. Identify important factual claims and citations.\n"
            "2. Compare each relevant citation with the supplied search results.\n"
            "3. Check whether the source title, URL, and available evidence "
            "match the claim it is used to support.\n"
            "4. A search result, source title, or URL alone does not prove "
            "that every claim is correct.\n"
            "5. Do not claim to have opened or independently verified a source "
            "unless the supplied evidence shows that this occurred.\n"
            "6. If evidence is missing or insufficient, label the relevant "
            "claim or citation UNVERIFIED.\n"
            "7. If the evidence clearly contradicts a claim, explain the "
            "specific contradiction. Do not confuse uncertainty with an error.\n"
            "8. Never mark all citations verified merely because citations "
            "are present or correctly formatted.\n\n"

            "C. FINAL STATUS\n"
            "Use COMPLETE when the explicit requirements are met and no "
            "important evidence-supported issue remains. Use PARTIAL or "
            "NOT COMPLETE when important requirements are unmet. If source "
            "verification is necessary but evidence is unavailable, disclose "
            "the limitation in GAPS and do not pretend verification succeeded.\n\n"

            "Return only this format:\n"
            "STATUS: COMPLETE, PARTIAL, or NOT COMPLETE\n"
            "FULFILLED: Requirements satisfied.\n"
            "GAPS: Important gaps, contradictions, or unverified claims.\n"
            "NEXT STEPS: Necessary corrections or checks, or None."
        ),
        expected_output=(
            "An evidence-based review of requirements, claims, citations, "
            "limitations, and necessary corrections."
        ),
        agent=checker,
        context=[work_task],
        async_execution=False,
    )

    # Task 4: Final Reviewer
    final_task = Task(
        description=(
            f"ORIGINAL USER REQUEST:\n{user_task}\n\n"
            f"WEB SEARCH RESULTS:\n{search_results}\n\n"
            "Use the worker's deliverable, planner criteria, and checker's "
            "review to prepare the final answer. Return the requested "
            "deliverable itself, not an internal review report.\n\n"
            "Correct genuine issues where possible. Do not invent references "
            "or claim that sources are verified without supporting evidence. "
            "If an important factual claim cannot be supported by the supplied "
            "evidence, qualify it or label it UNVERIFIED. Do not blindly accept "
            "an incorrect checker verdict.\n\n"
            "Follow the user's requested language, format, and level of detail. "
            "Do not add a quality-review section unless requested. "
            "Never claim to have performed unavailable external actions."
        ),
        expected_output=(
            "The polished deliverable requested by the user, with honest "
            "citation and evidence limitations."
        ),
        agent=final_reviewer,
        context=[plan_task, work_task, check_task],
        async_execution=False,
    )

    # Existing sequential orchestration is retained.
    # Note: this is not true parallel execution.
    crew = Crew(
        agents=[
            planner,
            worker,
            checker,
            final_reviewer,
        ],
        tasks=[
            plan_task,
            work_task,
            check_task,
            final_task,
        ],
        process=Process.sequential,
        verbose=False,
    )

    crew.kickoff()

    final_output = _output(final_task)
    review_output = _output(check_task)

    if not final_output.strip():
        raise RuntimeError(
            "The workflow finished without producing a final answer. "
            "Please try again."
        )

    return {
        "final_result": final_output,
        "review_result": review_output,
        "agent_outputs": [
            ("1. Planner Agent", _output(plan_task)),
            ("2. Worker Agent", _output(work_task)),
            ("3. Checker Agent", review_output),
            ("4. Final Reviewer", final_output),
        ],
    }
