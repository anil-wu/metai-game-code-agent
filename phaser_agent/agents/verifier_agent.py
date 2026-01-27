from google.adk.agents.llm_agent import LlmAgent
from google.adk.models import LiteLlm
from ..tools.commands import run_npm

verifier_agent = LlmAgent(
    model=LiteLlm(model='deepseek/deepseek-chat'),
    name="verifier_agent",
    description="A specialist agent that verifies the project build health.",
    instruction="""
    You are the Verifier Agent.

    Input: project_id.
    Action: run_npm(project_id, "run build").
    Output: report success or a concise failure summary (key error lines).

    IMPORTANT: When using tools, ensure your JSON arguments are NOT wrapped in a list. 
    Correct: {"project_id": "...", ...}
    Incorrect: [{"project_id": "...", ...}]
    """,
    tools=[run_npm]
)
