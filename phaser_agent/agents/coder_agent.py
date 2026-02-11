from google.adk.agents.llm_agent import LlmAgent
from google.adk.models import LiteLlm
from ..tools.filesystem import read_file, write_file, edit_file, list_files, search, ensure_dir, delete_file, move_file
from ..tools.commands import run_cmd
from ..config import LITELLM_MODEL, LITELLM_KWARGS
from ..token_usage import track_tokens_after_model

def create_coder_agent(
    model: LiteLlm | None = None,
    description: str | None = None,
    instruction: str | None = None,
) -> LlmAgent:
    return LlmAgent(
        model=model or LiteLlm(model=LITELLM_MODEL, **LITELLM_KWARGS),
        name="coder_agent",
        description=description
        or "A specialist agent that writes and modifies code to implement game features.",
        after_model_callback=track_tokens_after_model,
        instruction=instruction
        or """
        You are the Coder Agent.

        Input: project_id and a single task_description.
        Goal: implement the task by editing code under game_project/.

        Use tools:
        - Prefer edit_file for small changes (unified diff hunks or a line-range selector).
        - Use write_file only for new files or small rewrites.
        - Use read_file/list_files only when needed and keep context minimal.
        - Use search to locate symbols/strings across the workspace when needed.
        - Use run_cmd only when necessary and keep commands minimal.

        IMPORTANT: When using tools, ensure your JSON arguments are NOT wrapped in a list. 
        Correct: {"project_id": "...", ...}
        Incorrect: [{"project_id": "...", ...}]
        """.strip(),
        tools=[read_file, write_file, edit_file, list_files, search, run_cmd, delete_file, move_file, ensure_dir],
    )


coder_agent = create_coder_agent()
