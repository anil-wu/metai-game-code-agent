from ..agents.spec_agent import spec_agent
from .filesystem import write_file

def generate_spec(project_id: str, game_idea: str) -> str:
    """
    Generates a spec.txt for the given game idea.
    
    Args:
        project_id: The project ID.
        game_idea: The game description/idea.
        
    Returns:
        The path to the generated spec file.
    """
    spec_content = spec_agent.generate_spec(game_idea)
    
    # Save to workspaces/<project_id>/agent/spec.txt
    file_path = "agent/spec.txt"
    write_file(project_id, file_path, spec_content)
    return f"Spec generated at {file_path}"
