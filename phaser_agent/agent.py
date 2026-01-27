from google.adk.agents.llm_agent import Agent
from google.adk.models import LiteLlm
from .tools import create_project, bootstrap_project, run_npm, read_file, write_file, edit_file, list_files
from .agents.spec_agent import spec_agent

# Instantiate LiteLlm directly with the provider-prefixed model name
# This follows the ADK documentation for LiteLLM integration: https://adk.wiki/agents/models/litellm/
# And DeepSeek provider docs: https://docs.litellm.ai/docs/providers/deepseek
# Using 'deepseek/' prefix tells LiteLLM to use the native DeepSeek provider and DEEPSEEK_API_KEY

root_agent = Agent(
    model=LiteLlm(model='deepseek/deepseek-chat'), 
    name='phaser_agent',
    description="Orchestrator Agent for Phaser 3 Game Development",
    instruction="""
    You are the Orchestrator Agent for a Phaser 3 Game Development System.
    Your goal is to take a user's game idea and turn it into a playable game.
    
    Workflow:
    1.  **Initialization**:
        - Call `create_project(prompt)` to generate a `project_id`.
        - Call `bootstrap_project(project_id)` to set up the template.
        - Call `run_npm(project_id, "install")` to install dependencies.
    
    2.  **Development**:
        - Delegate to `spec_agent` to generate the Game Design Spec (spec.txt). Provide the `project_id` and the game idea.
        - (Future) Generate Plan (plan.txt)
        - (Future) Implement Features
        - (Future) Verify & Build
        
    When a user provides a game idea (e.g., "Make a flappy bird game"):
    1. Create the project using the idea as the prompt.
    2. Bootstrap the project with the Phaser template.
    3. Install dependencies using npm.
    4. Ask `spec_agent` to generate the spec for the new `project_id`.
    5. Report back the `project_id`, spec location, and project status.
    """,
    tools=[create_project, bootstrap_project, run_npm, read_file, write_file, edit_file, list_files],
    sub_agents=[spec_agent]
)
