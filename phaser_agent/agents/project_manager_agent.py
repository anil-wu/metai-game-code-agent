from google.adk.agents.llm_agent import LlmAgent
from google.adk.models.lite_llm import LiteLlm

from ..tools.project_manager_tools import (
    get_project_info,
    create_project,
    get_local_project_info,
    create_software,
    pull_project,
    push_project,
)
from ..tools.work_space_manager import create_workspace
from ..token_usage import track_tokens_after_model


def create_project_manager_agent(
    model: LiteLlm,
    description: str,
    instruction: str,
) -> LlmAgent:
    return LlmAgent(
        model=model,
        name="project_manager_agent",
        description=description,
        after_model_callback=track_tokens_after_model,
        instruction=instruction,
        tools=[
            get_project_info,
            create_project,
            get_local_project_info,
            create_workspace,
            create_software,
            pull_project,
            push_project,
        ],
    )
