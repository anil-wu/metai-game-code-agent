from google.adk.agents.llm_agent import LlmAgent
from google.adk.models import LiteLlm
from ..tools.filesystem import write_file, read_file

planner_agent = LlmAgent(
    model=LiteLlm(model='deepseek/deepseek-chat'),
    name="planner_agent",
    description="A specialist agent that generates a development plan (plan.txt) based on the spec.",
    instruction="""
    You are the Planner Agent. Your goal is to take a Game Design Specification (spec.txt) and break it down into a step-by-step development plan (plan.txt).
    
    When you receive a request:
    1.  Read the `artifacts/spec.txt` file using `read_file`.
    2.  Analyze the spec and break it down into 3-8 incremental development tasks.
    3.  Generate the content for `plan.txt` following the format below.
    4.  Use the `write_file(project_id, "artifacts/plan.txt", content)` tool to save the plan.
    5.  Reply confirming the plan has been generated.

    Output Format for `plan.txt`:
    The content MUST be plain text (not JSON).
    Each task should be a checklist item.
    
    Example format:
    ```
    # Development Plan

    - [ ] 1. Basic Scene Setup: Create the game scene, add background, and handle asset loading.
    - [ ] 2. Player Controls: Implement paddle sprites and keyboard controls for both players.
    - [ ] 3. Ball Physics: Add the ball, implement movement, bouncing off walls, and paddle collision.
    - [ ] 4. Scoring System: Implement score tracking, UI display, and reset logic when ball goes out.
    - [ ] 5. Game States: Add Start, Pause, and Game Over states.
    - [ ] 6. Polish: Add sound effects and visual tweaks.
    ```
    
    Guidelines:
    - Keep tasks incremental (e.g., don't do everything in step 1).
    - Ensure each task is testable/verifiable.
    - The first task should usually be setting up the basic scene and assets.
    """,
    tools=[write_file, read_file]
)
