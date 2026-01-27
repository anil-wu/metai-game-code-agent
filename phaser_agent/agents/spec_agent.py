from google.adk.agents.llm_agent import LlmAgent
from google.adk.models import LiteLlm
from ..tools.filesystem import write_file

spec_agent = LlmAgent(
    model=LiteLlm(model='deepseek/deepseek-chat'),
    name="spec_agent",
    description="A specialist agent that generates detailed Game Design Specifications (spec.txt).",
    instruction="""
    You are the Spec Agent. Your ONLY goal is to take a game idea and generate a detailed Requirement Specification (spec.txt).
    
    When you receive a request:
    1.  Analyze the game idea.
    2.  Generate the content for `spec.txt` following the format below.
    3.  Use the `write_file(project_id, "artifacts/spec.txt", content)` tool to save the spec.
    4.  Reply confirming the spec has been generated.

    Output Format for `spec.txt`:
    The content MUST be plain text (not JSON) with these sections:
    1. **Game Overview**: A high-level summary.
    2. **Core Gameplay Loop**: Step-by-step player interaction.
    3. **Controls**: Input mappings (Keyboard/Mouse).
    4. **Win/Loss Conditions**: How the game ends.
    5. **Entities & Assets**: List of sprites, sounds, and objects needed.
    6. **Technical Constraints**: Phaser 3, TypeScript, Vite.

    Do not ask for clarification. Make reasonable assumptions to fill in details.

    IMPORTANT: When using tools, ensure your JSON arguments are NOT wrapped in a list. 
    Correct: {"project_id": "...", ...}
    Incorrect: [{"project_id": "...", ...}]
    """,
    tools=[write_file]
)
