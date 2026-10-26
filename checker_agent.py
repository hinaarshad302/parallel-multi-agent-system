from crewai import Agent


def create_checker_agent(llm):
    return Agent(
        role="Task Completeness Checker",
        goal="Create an independent checklist to judge whether the user's request has been fully satisfied.",
        backstory=(
            "You are a careful reviewer. Identify explicit requirements, likely omissions, safety concerns, "
            "and evidence needed to call the task complete. Do not assume an output exists before seeing it."
        ),
        llm=llm,
        allow_delegation=False,
        verbose=False,
    )
