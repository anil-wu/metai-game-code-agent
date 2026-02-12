from google.adk.agents.llm_agent import LlmAgent
from google.adk.models import LiteLlm
from ..tools.filesystem import read_file, write_file, edit_file, list_files, search, ensure_dir, delete_file, move_file
from ..tools.commands import run_cmd
from ..token_usage import track_tokens_after_model

def create_coder_agent(
    model: LiteLlm,
    description: str,
    instruction: str,
) -> LlmAgent:
    return LlmAgent(
        model=model,
        name="coder_agent",
        description=description,
        after_model_callback=track_tokens_after_model,
        instruction=instruction,
        tools=[read_file, write_file, edit_file, list_files, search, run_cmd, delete_file, move_file, ensure_dir],
    )
