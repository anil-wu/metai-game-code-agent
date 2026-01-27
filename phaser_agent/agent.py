from google.adk.agents.llm_agent import Agent
from google.adk.models import LLMRegistry, LiteLlm
from .tools import init_game_project, read_file, write_file, list_files

# Register DeepSeek model via LiteLLM
# LLMRegistry.register returns a decorator, so we call it with the pattern
# and then call the result with the class to register.
LLMRegistry.register("deepseek-chat")(LiteLlm)

root_agent = Agent(
    model='deepseek-chat', 
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
