import shutil
import re
from datetime import datetime
from typing import Dict, Any
from phaser_agent.config import WORKSPACE_ROOT, TEMPLATE_PATH
from .utils import get_target_path

def create_project(prompt: str = "game") -> Dict[str, Any]:
    """Creates a new project directory based on the user's prompt.
    
    Generates a unique project_id and creates the folder in workspaces/.
    
    Args:
        prompt: User's description or name for the game.
    """
    # Generate project_id: YYYYMMDD_HHMMSS_namehint
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Clean prompt to get a name hint, take first 20 chars of alphanumeric
    name_hint = re.sub(r'[^a-zA-Z0-9]', '', prompt)[:20] or "game"
    project_id = f"{timestamp}_{name_hint}"
    
    try:
        WORKSPACE_ROOT.mkdir(parents=True, exist_ok=True)
        target_dir = WORKSPACE_ROOT / project_id
        
        # Ensure we don't overwrite existing (unlikely with timestamp)
        if target_dir.exists():
            return {"status": "error", "message": f"Project {project_id} already exists"}
            
        target_dir.mkdir(parents=True, exist_ok=False)
        
        return {
            "status": "success",
            "project_id": project_id,
            "path": str(target_dir),
            "message": f"Project {project_id} created at {target_dir}"
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

def bootstrap_project(project_id: str) -> Dict[str, Any]:
    """Initializes the project with the Phaser starter template.
    
    Args:
        project_id: The ID of the project to bootstrap.
    """
    try:
        target_dir = get_target_path("", project_id)
        if not target_dir.exists():
            return {"status": "error", "message": f"Project {project_id} does not exist"}
            
        if not TEMPLATE_PATH.exists():
            return {"status": "error", "message": f"Template not found at {TEMPLATE_PATH}"}
        
        # Copy template contents to target_dir
        # dirs_exist_ok=True allows copying into existing dir (which create_project made)
        shutil.copytree(TEMPLATE_PATH, target_dir, dirs_exist_ok=True)
        
        return {
            "status": "success", 
            "message": f"Template bootstrapped to {project_id}. Next: Run 'run_npm' to install dependencies."
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
