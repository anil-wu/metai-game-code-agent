from google.adk.agents.llm_agent import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from ..tools.filesystem import read_file, write_file, edit_file, list_files
from ..tools.commands import run_npm
from ..token_usage import track_tokens_after_model

def create_debugger_agent(
    model: LiteLlm,
    description: str,
    instruction: str,
) -> LlmAgent:
    return LlmAgent(
        model=model,
        name="debugger_agent",
        description=description,
        after_model_callback=track_tokens_after_model,
        instruction=instruction,
        tools=[read_file, write_file, edit_file, list_files, run_npm],
    )
