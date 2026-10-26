
from crewai import Agent


def create_planner_agent(llm):
    return Agent(
        role="Task Planner",
        goal="Understand the user's task and create a clear step-by-step plan with completion criteria.",
        backstory=(
            "You are a practical planner. Break broad tasks into understandable steps, "
            "state assumptions, and never claim that external actions were performed."
        ),
        llm=llm,
        allow_delegation=False,
        verbose=False,
    )
