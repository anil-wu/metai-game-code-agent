from google.adk.agents.llm_agent import LlmAgent
from google.adk.models import LiteLlm
from ..tools.filesystem import read_file, write_file, edit_file, list_files

coder_agent = LlmAgent(
    model=LiteLlm(model='deepseek/deepseek-chat'),
    name="coder_agent",
    description="A specialist agent that writes and modifies code to implement game features.",
    instruction="""
    You are the Coder Agent. Your goal is to implement game features by modifying the codebase.
    
    When you receive a request (which should contain the `project_id` and the `task_description`):
    1.  Explore the codebase if needed using `list_files` and `read_file` to understand the current state.
        - Source code is in `game_project/src/`.
    2.  Implement the requested feature by modifying existing files or creating new ones.
        - Use `edit_file` for small changes (preferred).
        - Use `write_file` for new files or rewriting small files.
    3.  Ensure your changes are consistent with the Phaser 3 framework and TypeScript.
    
    You do NOT run the build or verify. You only write code.
    """,
    tools=[read_file, write_file, edit_file, list_files]
)
