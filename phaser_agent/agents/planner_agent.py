from google.adk.agents.llm_agent import LlmAgent
from google.adk.models import LiteLlm
from ..tools.filesystem import write_file, read_file
from ..config import LITELLM_MODEL, LITELLM_KWARGS
from ..token_usage import track_tokens_after_model

def create_planner_agent(
    model: LiteLlm | None = None,
    description: str | None = None,
    instruction: str | None = None,
) -> LlmAgent:
    return LlmAgent(
        model=model or LiteLlm(model=LITELLM_MODEL, **LITELLM_KWARGS),
        name="planner_agent",
        description=description
        or "A specialist agent that generates a development plan (plan.txt) based on the spec.",
        after_model_callback=track_tokens_after_model,
        instruction=instruction
        or """
        You are the Planner Agent.

        Input: project_id.
        - Read artifacts/spec.txt via read_file.
        - Write plain-text artifacts/plan.txt via write_file.
        - Produce 3-8 incremental checklist tasks.

        IMPORTANT: When using tools, ensure your JSON arguments are NOT wrapped in a list. 
        Correct: {"project_id": "...", ...}
        Incorrect: [{"project_id": "...", ...}]
        """.strip(),
        tools=[write_file, read_file],
    )


planner_agent = create_planner_agent()
