from google.adk.agents.llm_agent import Agent
from google.adk.models import LLMRegistry, LiteLlm
from .tools import init_game_project, read_file, write_file, list_files

# Register DeepSeek model via LiteLLM
# Use _register to manually map the model name to the LiteLlm adapter
# Note: LiteLLM expects 'openai/...' or similar for custom providers if not standard.
# However, if we configure api_base in .env, we might just need 'openai/deepseek-chat'
# or simply ensure the model name passed to LiteLLM is recognizable.
# For DeepSeek via OpenAI-compatible endpoint, LiteLLM usually wants 'openai/<model_name>'
# or just 'deepseek/<model_name>' if it has a specific provider.
# Let's try registering 'deepseek-chat' but using 'openai/deepseek-chat' as the internal model for LiteLLM?
# No, Agent() takes `model`. LLMRegistry resolves `model` string to a Class.
# The Class (LiteLlm) is instantiated with `model="deepseek-chat"`.
# LiteLlm then calls `completion(model="deepseek-chat")`.
# If LiteLlm complains "LLM Provider NOT provided", it means "deepseek-chat" isn't enough.
# We should probably use "openai/deepseek-chat" as the model name if we are using OpenAI compatibility.
LLMRegistry._register("openai/deepseek-chat", LiteLlm)

root_agent = Agent(
    model='openai/deepseek-chat', 
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
