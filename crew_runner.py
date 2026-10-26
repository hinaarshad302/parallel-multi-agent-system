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

    # These three tasks have the same input and no dependencies on each other.
    # CrewAI can run async tasks concurrently; the final synchronous task waits for their outputs.
    plan_task = Task(
        description=(
            "User task:\n{user_task}\n\n"
            "Independently understand this task. Produce a numbered plan, list assumptions, "
            "and define observable criteria that would show the task is complete."
        ).format(user_task=user_task),
        expected_output="Numbered plan, assumptions, and completion criteria.",
        agent=planner,
        async_execution=True,
    )

    work_task = Task(
        description=(
            "User task:\n{user_task}\n\n"
            "Create the requested deliverable as completely as possible. This may be a draft, "
            "explanation, plan, report, or code. Do not claim to have used external tools or "
            "performed real-world actions that are not available in this application."
        ).format(user_task=user_task),
        expected_output="The requested deliverable, with limitations clearly stated.",
        agent=worker,
        async_execution=True,
    )

    check_task = Task(
        description=(
            "User task:\n{user_task}\n\n"
            "Independently create a quality checklist for this request. List explicit requirements, "
            "important omissions to watch for, and what evidence would be needed to call the work complete. "
            "You have not seen the worker's deliverable yet, so do not claim to have checked it."
        ).format(user_task=user_task),
        expected_output="An independent checklist and completion criteria.",
        agent=checker,
        async_execution=True,
    )

    final_task = Task(
        description=(
            "Original user task:\n{user_task}\n\n"
            "Review all three outputs in your context: plan, worker deliverable, and independent checklist. "
            "Present the useful deliverable and compare it against the criteria. Start with one status: "
            "COMPLETE, PARTIAL, or NOT COMPLETE. If incomplete, list the missing parts and next steps. "
            "Do not invent tool execution or claim that external actions happened."
        ).format(user_task=user_task),
        expected_output="Final deliverable, honest completion status, gaps, and next steps.",
        agent=final_reviewer,
        context=[plan_task, work_task, check_task],
        async_execution=False,
    )

    crew = Crew(
        agents=[planner, worker, checker, final_reviewer],
        tasks=[plan_task, work_task, check_task, final_task],
        process=Process.sequential,
        verbose=False,
    )
    crew.kickoff()

    return {
        "final_result": _output(final_task),
        "review_result": _output(final_task),
        "agent_outputs": [
            ("1. Planner Agent (parallel)", _output(plan_task)),
            ("2. Worker Agent (parallel)", _output(work_task)),
            ("3. Checker Agent (parallel)", _output(check_task)),
            ("4. Final Reviewer (after parallel tasks)", _output(final_task)),
        ],
    }
