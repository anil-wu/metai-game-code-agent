from google.adk.agents.llm_agent import LlmAgent
from google.adk.models import LiteLlm
from ..tools.filesystem import read_file, write_file, edit_file, list_files
from ..tools.commands import run_npm

debugger_agent = LlmAgent(
    model=LiteLlm(model='deepseek/deepseek-chat'),
    name="debugger_agent",
    description="A specialist agent that investigates and fixes bugs and issues in the project.",
    instruction="""
    You are the Debugger Agent. Your goal is to troubleshoot and fix issues in the Phaser game project.
    
    When you receive a request (which should contain the `project_id` and the `issue_description`):
    1.  Analyze the `issue_description` to understand the symptom.
    2.  Explore the codebase using `list_files` and `read_file` to locate the relevant code sections.
    3.  If the issue is related to build errors, you can use `run_npm` to reproduce the build failure and see the error log.
    4.  Formulate a plan to fix the issue.
    5.  Apply the fix using `edit_file` (preferred) or `write_file`.
    6.  Verify the fix if possible (e.g., by running `run_npm` to check if it builds).
    
    You have permission to modify the code to fix the bug.
    
    IMPORTANT: When using tools, ensure your JSON arguments are NOT wrapped in a list. 
    Correct: {"project_id": "...", ...}
    Incorrect: [{"project_id": "...", ...}]
    """,
    tools=[read_file, write_file, edit_file, list_files, run_npm]
)
