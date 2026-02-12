from google.adk.agents.llm_agent import LlmAgent
from google.adk.models import LiteLlm
from ..tools import (
    create_remote_project,
    list_projects,
    ensure_workspace_dir,
    pull_software_version,
    update_software_version,
    get_sandbox_workspace_info,
    get_user_project_software_info,
)
from ..token_usage import track_tokens_after_model

def create_work_space_manager_agent(
    model: LiteLlm,
    description: str,
    instruction: str,
) -> LlmAgent:
    return LlmAgent(
        model=model,
        name="work_space_manager_agent",
        description=description,
        after_model_callback=track_tokens_after_model,
        instruction=instruction,
        tools=[
            create_remote_project,
            list_projects,
            ensure_workspace_dir,
            pull_software_version,
            update_software_version,
            get_sandbox_workspace_info,
            get_user_project_software_info,
        ],
    )
