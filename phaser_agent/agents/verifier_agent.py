from google.adk.agents.llm_agent import LlmAgent
from google.adk.models import LiteLlm
from ..tools.commands import run_npm
from ..tools.utils import load_agent_prompt
from ..config import LITELLM_MODEL, LITELLM_KWARGS
from ..token_usage import track_tokens_after_model

def create_verifier_agent(
    model: LiteLlm | None = None,
    description: str | None = None,
    instruction: str | None = None,
) -> LlmAgent:
    prompt_cfg = load_agent_prompt("verifier_agent")
    return LlmAgent(
        model=model or LiteLlm(model=LITELLM_MODEL, **LITELLM_KWARGS),
        name="verifier_agent",
        description=description or prompt_cfg.get("description"),
        after_model_callback=track_tokens_after_model,
        instruction=instruction or prompt_cfg.get("instruction"),
        tools=[run_npm],
    )


verifier_agent = create_verifier_agent()
