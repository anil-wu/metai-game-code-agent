from google.adk.agents.llm_agent import LlmAgent
from google.adk.models import LiteLlm
from ..tools.filesystem import read_file, write_file, edit_file, list_files
from ..config import LITELLM_MODEL, LITELLM_KWARGS

coder_agent = LlmAgent(
    model=LiteLlm(model=LITELLM_MODEL, **LITELLM_KWARGS),
    name="coder_agent",
    description="A specialist agent that writes and modifies code to implement game features.",
    instruction="""
    You are the Coder Agent.

    Input: project_id and a single task_description.
    Goal: implement the task by editing code under game_project/.

    Use tools:
    - Prefer edit_file for small changes (unified diff hunks or a line-range selector).
    - Use write_file only for new files or small rewrites.
    - Use read_file/list_files only when needed and keep context minimal.

    Do not run builds or tests.

    IMPORTANT: When using tools, ensure your JSON arguments are NOT wrapped in a list. 
    Correct: {"project_id": "...", ...}
    Incorrect: [{"project_id": "...", ...}]
    """,
    tools=[read_file, write_file, edit_file, list_files]
)
