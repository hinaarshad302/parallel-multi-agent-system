
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
            "User task:\n"
            f"{user_task}\n\n"
            "Create a numbered plan, list assumptions, and define clear "
            "criteria for completing the task."
        ),
        expected_output=(
            "A numbered plan, assumptions, and completion criteria."
        ),
        agent=planner,
        async_execution=True,
    )

    # Task 2: Worker
    work_task = Task(
        description=(
            "User task:\n"
            f"{user_task}\n\n"
            "Create the requested deliverable as completely as possible. "
            "It may be a draft, explanation, plan, report, or code. "
            "Do not claim to have performed external actions or used "
            "tools that are unavailable."
        ),
        expected_output=(
            "The requested deliverable with any limitations clearly stated."
        ),
        agent=worker,
        async_execution=True,
    )

    # Task 3: Independent quality checklist
    check_task = Task(
        description=(
            "User task:\n"
            f"{user_task}\n\n"
            "Create an independent quality checklist. List the requirements, "
            "possible omissions, and evidence needed to confirm completion. "
            "You have not seen the worker's deliverable yet, so do not claim "
            "that you have reviewed it."
        ),
        expected_output=(
            "An independent checklist and completion criteria."
        ),
        agent=checker,
        async_execution=True,
    )

    # Task 4: Final review
    final_task = Task(
        description=(
            "Original user task:\n"
            f"{user_task}\n\n"
            "Review the plan, worker deliverable, and independent checklist. "
            "Present the useful final deliverable and compare it with the "
            "criteria. Start with one status: COMPLETE, PARTIAL, or "
            "NOT COMPLETE. If incomplete, list missing parts and next steps. "
            "Never invent tool execution or claim external actions happened."
        ),
        expected_output=(
            "Final deliverable, honest completion status, missing parts, "
            "and next steps."
        ),
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

    return {
        "final_result": final_output,
        "review_result": final_output,
        "agent_outputs": [
            ("1. Planner Agent", _output(plan_task)),
            ("2. Worker Agent", _output(work_task)),
            ("3. Checker Agent", _output(check_task)),
            ("4. Final Reviewer", final_output),
        ],
    }
