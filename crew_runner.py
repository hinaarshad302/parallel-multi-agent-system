
# Workaround for CrewAI cache_breakpoint bug with Groq
try:
    import crewai.llms.cache as _crewai_cache
    _crewai_cache.mark_cache_breakpoint = lambda msg: msg
except (ImportError, AttributeError):
    pass

from crewai import Crew, Process, Task
from llm_config import get_llm
from agents.planner_agent import create_planner_agent
from agents.worker_agent import create_worker_agent
from agents.checker_agent import create_checker_agent
from agents.final_reviewer_agent import create_final_reviewer_agent


def _output(task):
    try:
        return task.output.raw if task.output else ""
    except Exception:
        return ""


def run_user_task(user_task: str) -> dict:
    llm = get_llm()

    planner = create_planner_agent(llm)
    worker = create_worker_agent(llm)
    checker = create_checker_agent(llm)
    final_reviewer = create_final_reviewer_agent(llm)

    # Task 1: Planner
    plan_task = Task(
        description=(
            f"User request:\n{user_task}\n\n"
            "Create a concise plan, identify essential requirements, "
            "and define measurable completion criteria. "
            "Avoid unnecessary explanation."
        ),
        expected_output="A concise plan and completion criteria.",
        agent=planner,
        async_execution=True,
    )

    # Task 2: Worker
    work_task = Task(
        description=(
            f"User request:\n{user_task}\n\n"
            "Produce the requested deliverable directly. "
            "Follow the user's requested language, format, and level "
            "of detail. Be concise unless detail is requested. "
            "Avoid repetition, irrelevant introductions, and unnecessary "
            "conclusions. Never claim to perform unavailable external actions."
        ),
        expected_output="The requested deliverable.",
        agent=worker,
        async_execution=True,
    )

    # Task 3: Checker reviews the actual work
    check_task = Task(
        description=(
            f"Original user request:\n{user_task}\n\n"
            "Review the planner's criteria and the worker's actual "
            "deliverable using the context provided.\n\n"
            "Return a concise quality review in this format:\n"
            "STATUS: COMPLETE, PARTIAL, or NOT COMPLETE\n"
            "FULFILLED: Briefly list the important requirements met.\n"
            "GAPS: List only genuine missing or incorrect requirements. "
            "Write 'None identified' if no important gaps remain.\n"
            "NEXT STEPS: Include only necessary actions, or 'None'.\n\n"
            "Judge against the user's actual request. Do not treat optional "
            "improvements as mandatory. Do not repeat the full deliverable. "
            "Do not invent problems or claim checks you did not perform."
        ),
        expected_output=(
            "A concise status, fulfilled requirements, genuine gaps, "
            "and necessary next steps."
        ),
        agent=checker,
        context=[plan_task, work_task],
        async_execution=False,
    )

    # Task 4: Final answer
    final_task = Task(
        description=(
            f"Original user request:\n{user_task}\n\n"
            "Use the plan, worker deliverable, and quality review in your "
            "context to produce the final answer.\n\n"
            "Return the requested deliverable itself. Preserve useful "
            "details, correct genuine issues where possible, and follow "
            "the requested format and language. Be concise by default "
            "and detailed when requested.\n\n"
            "Do not repeat the quality review, checklist, status, or next "
            "steps as separate sections unless the user specifically asks "
            "for them. Do not add an unnecessary introduction or conclusion. "
            "Never invent facts, tool usage, or completed external actions."
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
