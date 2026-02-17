from google.adk.agents.llm_agent import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from ..tools.work_space_manager import build_project_software, get_software_latest_version
from ..tools.filesystem import read_file, list_files
from ..tools.commands import run_npm
from ..token_usage import track_tokens_after_model

def create_build_agent(
    model: LiteLlm,
    description: str,
    instruction: str,
) -> LlmAgent:
    return LlmAgent(
        model=model,
        name="build_agent",
        description=description,
        after_model_callback=track_tokens_after_model,
        instruction=instruction,
        tools=[build_project_software, get_software_latest_version, read_file, list_files, run_npm],
    )