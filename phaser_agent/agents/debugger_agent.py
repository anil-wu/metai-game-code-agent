from google.adk.agents.llm_agent import LlmAgent
from google.adk.models import LiteLlm
from ..tools.filesystem import read_file, write_file, edit_file, list_files
from ..tools.commands import run_npm

debugger_agent = LlmAgent(
    model=LiteLlm(model='deepseek/deepseek-chat'),
    name="debugger_agent",
    description="A specialist agent that investigates and fixes bugs and issues in the project.",
    instruction="""
    You are the Debugger Agent.

    Input: project_id and issue_description.
    Goal: identify root cause and apply a minimal fix.

    Use tools:
    - read_file/list_files to locate relevant code (keep context minimal).
    - edit_file preferred; write_file only when needed.
    - run_npm allowed to reproduce and verify build issues.
    
    IMPORTANT: When using tools, ensure your JSON arguments are NOT wrapped in a list. 
    Correct: {"project_id": "...", ...}
    Incorrect: [{"project_id": "...", ...}]
    """,
    tools=[read_file, write_file, edit_file, list_files, run_npm]
)
