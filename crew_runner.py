
# crew_runner.py
# Compatibility workaround for CrewAI cache_breakpoint with Groq.

def _disable_cache_breakpoint():
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

    planner = create_planner_agent(llm)
    worker = create_worker_agent(llm)
    checker = create_checker_agent(llm)
    final_reviewer = create_final_reviewer_agent(llm)

    # Task 1: Planner
    plan_task = Task(
        description=(
            f"User request:\n{user_task}\n\n"
            "Create a concise plan. Identify the user's explicit "
            "requirements and measurable completion criteria. "
            "Do not perform the worker's task."
        ),
        expected_output="A concise plan and completion criteria.",
        agent=planner,
        async_execution=True,
    )

    # Task 2: Worker
    work_task = Task(
        description=(
            f"User request:\n{user_task}\n\n"
            "Produce the requested deliverable directly. Follow the "
            "requested language, format, and level of detail. Be concise "
            "unless more detail is requested. Avoid unnecessary "
            "introductions, repetition, and conclusions. Never claim to "
            "have performed unavailable external actions."
        ),
        expected_output="The requested deliverable.",
        agent=worker,
        async_execution=True,
    )

    
    # Task 3: Checker reviews only the actual requested deliverable.
    check_task = Task(
        description=(
            f"ORIGINAL USER REQUEST:\n{user_task}\n\n"
            "Review the worker's actual deliverable provided in your context. "
            "The worker deliverable is the answer being evaluated. Do not "
            "count the planner's notes, checker instructions, or other "
            "agent outputs as part of that answer.\n\n"
            "Evaluate only requirements explicitly stated by the user. "
            "If the user requested exactly five bullet points, count the "
            "bullets in the worker's deliverable itself. Do not count bullets "
            "in other agents' outputs. Do not invent a second list, separator, "
            "introduction, conclusion, or word limit unless it is actually "
            "present in the worker's deliverable or explicitly required.\n\n"
            "If all explicit requirements are satisfied, use STATUS: COMPLETE "
            "and GAPS: None identified. Do not mark an answer incomplete "
            "because optional improvements are possible.\n\n"
            "Return only this format:\n"
            "STATUS: COMPLETE, PARTIAL, or NOT COMPLETE\n"
            "FULFILLED: Briefly list requirements met.\n"
            "GAPS: Verified unmet requirements, or 'None identified'.\n"
            "NEXT STEPS: Necessary corrections, or 'None'."
        ),
        expected_output=(
            "A concise and accurate review of the worker's actual deliverable."
        ),
        agent=checker,
        context=[work_task],
        async_execution=False,
    )

    # Task 4: Final reviewer
    final_task = Task(
        description=(
            f"Original user request:\n{user_task}\n\n"
            "Use the worker's deliverable, planner criteria, and "
            "checker's review to produce the final answer.\n\n"
            "Return the requested deliverable itself. Preserve useful "
            "details, correct genuine issues where possible, and follow "
            "the requested format and language. Be concise by default "
            "and detailed when requested.\n\n"
            "Independently verify the deliverable against the original "
            "request. Do not blindly accept an incorrect checker verdict. "
            "Do not add a quality-review section unless requested. "
            "Do not add unnecessary introductions or conclusions. "
            "Never invent facts or claim unavailable actions were done."
        ),
        expected_output="The polished final deliverable requested by the user.",
        agent=final_reviewer,
        context=[plan_task, work_task, check_task],
        async_execution=False,
    )

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
