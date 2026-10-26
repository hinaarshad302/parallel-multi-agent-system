
from crewai import Agent


def create_final_reviewer_agent(llm):
    return Agent(
        role="Final Reviewer",
        goal="Combine the parallel agent outputs and assess whether the deliverable satisfies the original task.",
        backstory=(
            "You are honest and evidence-focused. Compare the worker's deliverable against the planner's steps "
            "and checker's checklist. Report COMPLETE, PARTIAL, or NOT COMPLETE. Never hide missing work, "
            "and never claim external actions happened without verifiable evidence."
        ),
        llm=llm,
        allow_delegation=False,
        verbose=False,
    )
