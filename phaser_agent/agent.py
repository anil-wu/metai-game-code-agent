from google.adk.agents.llm_agent import Agent
from google.adk.models import LiteLlm
from .tools import init_game_project, read_file, write_file, list_files

# Instantiate LiteLlm directly with the provider-prefixed model name
# This follows the ADK documentation for LiteLLM integration: https://adk.wiki/agents/models/litellm/
# And DeepSeek provider docs: https://docs.litellm.ai/docs/providers/deepseek
# Using 'deepseek/' prefix tells LiteLLM to use the native DeepSeek provider and DEEPSEEK_API_KEY

root_agent = Agent(
    model=LiteLlm(model='deepseek/deepseek-chat'), 
    name='phaser_agent',
    description="A specialist in Phaser 3 game development.",
    instruction="""
    You are an expert Phaser 3 Game Developer Agent.
    Your goal is to assist the user in building and modifying HTML5 games.
    
    Capabilities:
    1. Initialize new projects using `init_game_project`.
    2. Read existing code using `read_file`.
    3. Modify or create code using `write_file`.
    4. Explore the project structure using `list_files`.
    
    Workflow:
    - When asked to start, initialize the project.
    - When asked to add a feature, READ the relevant file first (usually src/main.ts), 
      then WRITE the updated code.
    - Always ensure the code is valid TypeScript/Phaser 3 syntax.
    """,
    tools=[init_game_project, read_file, write_file, list_files],
)
