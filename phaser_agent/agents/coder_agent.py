from google.adk.agents.llm_agent import LlmAgent
from google.adk.models import LiteLlm
from ..tools.filesystem import read_file, write_file, edit_file, list_files, search, ensure_dir, delete_file, move_file
from ..tools.commands import run_cmd
from ..tools.utils import load_agent_prompt
from ..config import LITELLM_MODEL, LITELLM_KWARGS
from ..token_usage import track_tokens_after_model

def create_coder_agent(
    model: LiteLlm | None = None,
    description: str | None = None,
    instruction: str | None = None,
) -> LlmAgent:
    prompt_cfg = load_agent_prompt("coder_agent")
    return LlmAgent(
        model=model or LiteLlm(model=LITELLM_MODEL, **LITELLM_KWARGS),
        name="coder_agent",
        description=description or prompt_cfg.get("description"),
        after_model_callback=track_tokens_after_model,
        instruction=instruction or prompt_cfg.get("instruction"),
        tools=[read_file, write_file, edit_file, list_files, search, run_cmd, delete_file, move_file, ensure_dir],
    )


coder_agent = create_coder_agent()
