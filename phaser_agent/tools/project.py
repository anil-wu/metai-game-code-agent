import shutil
import re
from datetime import datetime
from typing import Dict, Any
from phaser_agent.config import WORKSPACE_ROOT, TEMPLATE_PATH, FIXED_PROJECT_ID, DIR_GAME, DIR_ARTIFACTS, DIR_BUILD, DIR_LOGS
from .utils import get_target_path

def create_project(prompt: str = "game") -> Dict[str, Any]:
    """Creates a new project directory or reuses the fixed project.
    
    Args:
        prompt: User's description (unused for ID generation now).
    """
    project_id = FIXED_PROJECT_ID
    
    try:
        WORKSPACE_ROOT.mkdir(parents=True, exist_ok=True)
        target_dir = WORKSPACE_ROOT / project_id
        
        # Create main project directory
        target_dir.mkdir(parents=True, exist_ok=True)

        # Create subdirectories
        (target_dir / DIR_GAME).mkdir(parents=True, exist_ok=True)
        (target_dir / DIR_ARTIFACTS).mkdir(parents=True, exist_ok=True)
        (target_dir / DIR_BUILD).mkdir(parents=True, exist_ok=True)
        (target_dir / DIR_LOGS).mkdir(parents=True, exist_ok=True)
        
        return {
            "status": "success",
            "project_id": project_id,
            "path": str(target_dir),
            "message": f"Project {project_id} structure created at {target_dir}"
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

def bootstrap_project(project_id: str) -> Dict[str, Any]:
    """Initializes the project with the Phaser starter template.
    
    Args:
        project_id: The ID of the project to bootstrap.
    """
    try:
        project_root = get_target_path("", project_id)
        if not project_root.exists():
            return {"status": "error", "message": f"Project {project_id} does not exist"}
            
        if not TEMPLATE_PATH.exists():
            return {"status": "error", "message": f"Template not found at {TEMPLATE_PATH}"}
        
        game_dir = project_root / DIR_GAME

        # Check if already bootstrapped (e.g. check for package.json)
        if (game_dir / "package.json").exists():
            return {
                "status": "success",
                "message": f"Project {project_id} already contains package.json in {DIR_GAME}. Skipping bootstrap to prevent overwrite."
            }

        # Copy template contents to game_dir
        shutil.copytree(TEMPLATE_PATH, game_dir, dirs_exist_ok=True)
        
        return {
            "status": "success", 
            "message": f"Template bootstrapped to {project_id}/{DIR_GAME}. Next: Run 'run_npm' to install dependencies."
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
