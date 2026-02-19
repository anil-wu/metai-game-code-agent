from google.adk.agents.llm_agent import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from ..tools.work_space_manager import (
    get_tool_context_info,
    check_user_credentials,
    scan_user_workspace,
    check_project_info,
    create_project_info,
    update_project_info,
    create_project_workspace,
    pull_project_software,
    commit_project_software,
    check_workspace_status,
)
from ..tools.project_manager_tools import create_software
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
            get_tool_context_info,
            check_user_credentials,
            scan_user_workspace,
            check_workspace_status,
            check_project_info,
            create_project_info,
            update_project_info,
            create_project_workspace,
            create_software,
            pull_project_software,
            commit_project_software,
        ],
    )
