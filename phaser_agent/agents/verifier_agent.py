from google.adk.agents.llm_agent import LlmAgent
from google.adk.models import LiteLlm
from ..tools.commands import run_npm
from ..config import LITELLM_MODEL, LITELLM_KWARGS
from ..token_usage import track_tokens_after_model

verifier_agent = LlmAgent(
    model=LiteLlm(model=LITELLM_MODEL, **LITELLM_KWARGS),
    name="verifier_agent",
    description="A specialist agent that verifies the project build health.",
    after_model_callback=track_tokens_after_model,
    instruction="""
    You are the Verifier Agent.

    Input: project_id.
    Action:
    - run_npm(project_id, "run build")
    - run_npm(project_id, "run lint")
    Output: report success only if both pass; otherwise report which step failed and a concise failure summary (key error lines).

    IMPORTANT: When using tools, ensure your JSON arguments are NOT wrapped in a list. 
    Correct: {"project_id": "...", ...}
    Incorrect: [{"project_id": "...", ...}]
    """,
    tools=[run_npm]
)
