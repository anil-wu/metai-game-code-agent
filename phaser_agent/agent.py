from google.adk.agents.llm_agent import Agent
from google.adk.models import LiteLlm
from .patches import apply_patches
from .config import LITELLM_MODEL, LITELLM_KWARGS

# Apply patches to fix LiteLLM issues with DeepSeek (list-wrapped tool args)
apply_patches()

from .tools import create_project, bootstrap_project, run_npm, read_file, write_file, edit_file, list_files
from .agents.spec_agent import spec_agent
from .agents.verifier_agent import verifier_agent
from .agents.planner_agent import planner_agent
from .agents.coder_agent import coder_agent
from .agents.debugger_agent import debugger_agent

# Instantiate LiteLlm directly with the provider-prefixed model name
# This follows the ADK documentation for LiteLLM integration: https://adk.wiki/agents/models/litellm/
# And DeepSeek provider docs: https://docs.litellm.ai/docs/providers/deepseek
# Using 'deepseek/' prefix tells LiteLLM to use the native DeepSeek provider and DEEPSEEK_API_KEY

root_agent = Agent(
    model=LiteLlm(model=LITELLM_MODEL, **LITELLM_KWARGS),
    name='phaser_agent',
    description="Orchestrator Agent for Phaser 3 Game Development",
    instruction="""
    You are the Orchestrator Agent for Phaser 3 game development.

    Always operate within a workspace `project_id`.

    Bootstrap (once per project):
    - create_project(prompt)
    - bootstrap_project(project_id)
    - run_npm(project_id, "install")

    Build a game incrementally:
    - Ask spec_agent to write artifacts/spec.txt.
    - Ask planner_agent to write artifacts/plan.txt.
    - For the next unchecked task in artifacts/plan.txt:
      - Ask coder_agent to implement it.
      - Ask verifier_agent to run npm build and eslint.
      - If verification passes, mark the task done in plan.txt via edit_file.
      - If verification fails, ask coder_agent to fix using the error summary, then verify again.

    Bugs:
    - Delegate investigation and fixes to debugger_agent, then verify build.

    IMPORTANT: Tool arguments must be a JSON object, not wrapped in a list.
    """,
    tools=[create_project, bootstrap_project, run_npm, read_file, write_file, edit_file, list_files],
    sub_agents=[spec_agent, verifier_agent, planner_agent, coder_agent, debugger_agent]
)
