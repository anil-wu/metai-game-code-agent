import shutil
import re
from datetime import datetime
from typing import Dict, Any
from phaser_agent.config import WORKSPACE_ROOT, TEMPLATE_PATH, FIXED_PROJECT_ID
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
        
        if target_dir.exists():
            return {
                "status": "success",
                "project_id": project_id,
                "path": str(target_dir),
                "message": f"Project {project_id} already exists. Reusing it."
            }
            
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
        
        # Check if already bootstrapped (e.g. check for package.json)
        if (target_dir / "package.json").exists():
            return {
                "status": "success",
                "message": f"Project {project_id} already contains package.json. Skipping bootstrap to prevent overwrite."
            }

        # Copy template contents to target_dir
        shutil.copytree(TEMPLATE_PATH, target_dir, dirs_exist_ok=True)
        
        return {
            "status": "success", 
            "message": f"Template bootstrapped to {project_id}. Next: Run 'run_npm' to install dependencies."
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
