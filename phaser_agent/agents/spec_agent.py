from google.adk.agents.llm_agent import LlmAgent
from google.adk.models import LiteLlm
from ..tools.filesystem import write_file
from ..config import LITELLM_MODEL, LITELLM_KWARGS
from ..token_usage import track_tokens_after_model

def create_spec_agent(
    model: LiteLlm | None = None,
    description: str | None = None,
    instruction: str | None = None,
) -> LlmAgent:
    return LlmAgent(
        model=model or LiteLlm(model=LITELLM_MODEL, **LITELLM_KWARGS),
        name="spec_agent",
        description=description
        or "A specialist agent that generates detailed Game Design Specifications (spec.txt).",
        after_model_callback=track_tokens_after_model,
        instruction=instruction
        or """
        You are the Spec Agent.

        Input: project_id and a game idea.
        Output: write plain-text artifacts/spec.txt via write_file.
        Include: overview, core loop, controls, win/loss, entities/assets, constraints.
        Do not ask for clarification.

        IMPORTANT: When using tools, ensure your JSON arguments are NOT wrapped in a list. 
        Correct: {"project_id": "...", ...}
        Incorrect: [{"project_id": "...", ...}]
        """.strip(),
        tools=[write_file],
    )


spec_agent = create_spec_agent()
