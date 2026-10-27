
# crew_runner.py
# Parallel Multi-Agent AI System
# Maintains compatibility workaround for CrewAI cache_breakpoint with Groq.

def _disable_cache_breakpoint():
    """Apply a compatibility workaround for cache_breakpoint when available."""

    def _return_message_unchanged(message, *args, **kwargs):
        if isinstance(message, dict):
            message.pop("cache_breakpoint", None)
        return message

    try:
        import crewai.llms.cache as cache_module
        cache_module.mark_cache_breakpoint = _return_message_unchanged
    except (ImportError, AttributeError):
        pass

    # Patch functions imported directly by CrewAI modules, if present.
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

    # Create the four agents.
    planner = create_planner_agent(llm)
    worker = create_worker_agent(llm)
    checker = create_checker_agent(llm)
    final_reviewer = create_final_reviewer_agent(llm)

    # Task 1: Planner
    plan_task = Task(
        description=(
            f"ORIGINAL USER REQUEST:\n{user_task}\n\n"
            "Create a concise plan before the work begins. "
            "Identify explicit user requirements, requested format, "
            "language, and measurable completion criteria. "
            "Do not perform the worker's task."
        ),
        expected_output=(
            "A concise plan listing the user's explicit requirements "
            "and measurable completion criteria."
        ),
        agent=planner,
        async_execution=True,
    )

    # Task 2: Worker
    work_task = Task(
        description=(
            f"ORIGINAL USER REQUEST:\n{user_task}\n\n"
            "Produce the requested deliverable directly. Follow the "
            "user's requested language, format, scope, and level of detail. "
            "Be concise unless more detail is requested.\n\n"
            "Use accurate information. Do not invent facts, references, "
            "quotes, statistics, source titles, publication dates, or URLs. "
            "If you cannot confidently support a factual claim, qualify it "
            "or clearly state the uncertainty. Do not claim to have performed "
            "external actions that were not actually performed."
        ),
        expected_output="The requested deliverable.",
        agent=worker,
        async_execution=True,
    )

    # Task 3: Checker
    check_task = Task(
        description=(
            f"ORIGINAL USER REQUEST:\n{user_task}\n\n"
            "Review the worker's actual deliverable provided in your context. "
            "Evaluate that deliverable, not the planner's notes or other "
            "agents' outputs.\n\n"

            "A. REQUIREMENT CHECK\n"
            "1. Identify the requirements explicitly stated by the user.\n"
            "2. Compare the worker's deliverable with each requirement.\n"
            "3. Count items or sections only when a specific number or format "
            "was requested.\n"
            "4. Report only important gaps supported by evidence in the "
            "deliverable. Do not invent missing content or optional rules.\n\n"

            "B. FACTS AND CITATIONS\n"
            "1. Identify important factual claims, statistics, quotations, "
            "and citations that materially affect the answer's reliability.\n"
            "2. Check whether the provided citation details appear internally "
            "consistent, including author, title, year, and URL when present.\n"
            "3. Determine whether the available evidence actually supports "
            "the associated claim. Do not assume that a citation supports a "
            "claim merely because it appears beside it.\n"
            "4. Do not claim that you opened a link, searched the web, or "
            "verified a source unless you actually had access to that source "
            "and performed the check.\n"
            "5. If source access or evidence is unavailable, label the relevant "
            "claim or citation 'UNVERIFIED' instead of calling it verified "
            "or asserting that it is false.\n"
            "6. If a source is available and clearly contradicts a claim, "
            "describe the specific mismatch. Distinguish confirmed errors "
            "from uncertainty.\n"
            "7. Do not mark a deliverable fully verified merely because it "
            "contains a bibliography or correctly formatted citations.\n\n"

            "C. FINAL STATUS\n"
            "Use COMPLETE when the explicit requirements are satisfied and "
            "no important, evidence-supported issue remains. If important "
            "requirements are unmet, use PARTIAL or NOT COMPLETE as appropriate. "
            "If source verification is necessary but unavailable, disclose "
            "that limitation clearly in GAPS; do not pretend the sources "
            "were verified. Do not fail an answer solely because optional "
            "improvements are possible.\n\n"

            "Return only this format:\n"
            "STATUS: COMPLETE, PARTIAL, or NOT COMPLETE\n"
            "FULFILLED: Briefly list the requirements satisfied.\n"
            "GAPS: List verified important gaps, factual concerns, or "
            "unverified sources when relevant; otherwise write "
            "'None identified'.\n"
            "NEXT STEPS: List necessary corrections or verification steps; "
            "if none are needed, write 'None'."
        ),
        expected_output=(
            "A concise evidence-based review of requirement completeness, "
            "factual concerns, citation limitations, and necessary corrections."
        ),
        agent=checker,
        context=[work_task],
        async_execution=False,
    )

    # Task 4: Final Reviewer
    final_task = Task(
        description=(
            f"ORIGINAL USER REQUEST:\n{user_task}\n\n"
            "Use the worker's deliverable, planner criteria, and checker's "
            "review to prepare the final answer.\n\n"
            "Return the requested deliverable itself. Preserve useful details, "
            "correct genuine issues where possible, and follow the user's "
            "requested format and language. Do not blindly accept an incorrect "
            "checker verdict. Independently compare the deliverable with the "
            "original request.\n\n"
            "Pay attention to factual claims and citations. Do not invent "
            "references or claim that a source has been verified unless the "
            "available evidence supports that statement. If an important "
            "issue cannot be resolved from the available context, avoid "
            "presenting the uncertain detail as established fact.\n\n"
            "Do not add a quality-review section unless the user requested it. "
            "Avoid unnecessary introductions, repetition, and conclusions. "
            "Never claim to have performed unavailable external actions."
        ),
        expected_output=(
            "The polished final deliverable requested by the user, "
            "following the original requirements."
        ),
        agent=final_reviewer,
        context=[plan_task, work_task, check_task],
        async_execution=False,
    )

    # Existing orchestration is retained.
    # NOTE: Process.sequential means the workflow is not truly parallel.
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

    # Avoid reporting success when the final deliverable is empty.
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
