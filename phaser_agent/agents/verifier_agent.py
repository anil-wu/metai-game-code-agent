from google.adk.agents.llm_agent import LlmAgent
from google.adk.models import LiteLlm
from ..tools.commands import run_npm

verifier_agent = LlmAgent(
    model=LiteLlm(model='deepseek/deepseek-chat'),
    name="verifier_agent",
    description="A specialist agent that verifies the project build health.",
    instruction="""
    You are the Verifier Agent. Your goal is to verify that the project builds successfully.
    
    When you receive a request (which should contain the `project_id`):
    1.  Run `npm run build` using the `run_npm` tool for the given `project_id`.
    2.  Analyze the output.
    3.  If the build succeeds, report success.
    4.  If the build fails, report the failure and the error message from stderr/stdout.
    
    Do not attempt to fix the code yet, just report the build status.

    IMPORTANT: When using tools, ensure your JSON arguments are NOT wrapped in a list. 
    Correct: {"project_id": "...", ...}
    Incorrect: [{"project_id": "...", ...}]
    """,
    tools=[run_npm]
)
