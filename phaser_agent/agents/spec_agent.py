from google.adk.agents.llm_agent import LlmAgent
from google.adk.models import LiteLlm
from ..tools.filesystem import write_file
from ..config import LITELLM_MODEL, LITELLM_KWARGS

spec_agent = LlmAgent(
    model=LiteLlm(model=LITELLM_MODEL, **LITELLM_KWARGS),
    name="spec_agent",
    description="A specialist agent that generates detailed Game Design Specifications (spec.txt).",
    instruction="""
    You are the Spec Agent.

    Input: project_id and a game idea.
    Output: write plain-text artifacts/spec.txt via write_file.
    Include: overview, core loop, controls, win/loss, entities/assets, constraints.
    Do not ask for clarification.

    IMPORTANT: When using tools, ensure your JSON arguments are NOT wrapped in a list. 
    Correct: {"project_id": "...", ...}
    Incorrect: [{"project_id": "...", ...}]
    """,
    tools=[write_file]
)
