import shutil
from typing import Dict, Any
from phaser_agent.config import WORKSPACE_ROOT, TEMPLATE_PATH
from .utils import get_target_path

def init_game_project(project_id: str = "current_game") -> str:
    """Initializes a new Phaser game project from template.
    
    Args:
        project_id: The ID of the project to initialize.
    """
    try:
        WORKSPACE_ROOT.mkdir(parents=True, exist_ok=True)
        # Use get_target_path to get the project root securely? 
        # But get_target_path might expect the dir to exist or check traversal.
        # Let's use simple join for creation, relying on isalnum check if possible.
        
        if not project_id or not project_id.replace("_", "").replace("-", "").isalnum():
             return "Error: Invalid project_id"

        target_dir = WORKSPACE_ROOT / project_id
        
        if target_dir.exists():
            shutil.rmtree(target_dir)
        
        if not TEMPLATE_PATH.exists():
            return f"Error: Template not found at {TEMPLATE_PATH}"
            
        shutil.copytree(TEMPLATE_PATH, target_dir)
        return f"Success: Created new project at {target_dir}. Run 'npm install' and 'npm run dev' inside."
    except Exception as e:
        return f"Error: {str(e)}"
