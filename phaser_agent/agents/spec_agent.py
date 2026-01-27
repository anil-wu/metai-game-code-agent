from litellm import completion

class SpecAgent:
    def __init__(self, model_name='deepseek/deepseek-chat'):
        self.model_name = model_name
        self.system_prompt = """
You are a generic Game Design Spec Agent.
Your goal is to take a short game description and output a detailed Requirement Specification (Spec).

Output Format:
The output must be a plain text document (not JSON) with the following sections:
1. **Game Overview**: A high-level summary.
2. **Core Gameplay Loop**: Step-by-step player interaction.
3. **Controls**: Input mappings (Keyboard/Mouse).
4. **Win/Loss Conditions**: How the game ends.
5. **Entities & Assets**: List of sprites, sounds, and objects needed.
6. **Technical Constraints**: Phaser 3, TypeScript, Vite.

Do not include any conversational filler. Just output the spec content.
"""

    def generate_spec(self, game_idea: str) -> str:
        response = completion(
            model=self.model_name,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": f"Game Idea: {game_idea}\n\nGenerate the spec."}
            ]
        )
        return response.choices[0].message.content

spec_agent = SpecAgent()
