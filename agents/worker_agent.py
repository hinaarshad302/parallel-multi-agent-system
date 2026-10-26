
from crewai import Agent


def create_worker_agent(llm):
    return Agent(
        role="Task Worker",
        goal="Create the most useful deliverable possible for the user's task.",
        backstory=(
            "You are a capable generalist. You can draft, explain, summarize, plan, and generate code. "
            "Be clear about limitations when the task needs tools that are not connected."
        ),
        llm=llm,
        allow_delegation=False,
        verbose=False,
    )
