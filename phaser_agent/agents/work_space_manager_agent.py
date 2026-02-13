from google.adk.agents.llm_agent import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from ..tools.work_space_manager import (
    check_project_info,
    create_project_info,
    update_project_info,
    create_project_workspace,
    pull_project_software,
    commit_project_software,
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
            check_project_info,
            create_project_info,
            update_project_info,
            create_project_workspace,
            pull_project_software,
            commit_project_software,
        ],
    )
