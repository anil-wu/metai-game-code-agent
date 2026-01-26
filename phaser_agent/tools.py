
import os
import shutil
from pathlib import Path

# Configuration
WORKSPACE_ROOT = Path("workspaces")
TEMPLATE_PATH = Path("templates/phaser-starter")

def _get_target_path(path_str: str) -> Path:
    """Helper to ensure paths are within workspace"""
    # For MVP, we assume a single active session 'current_game' or user provides path
    # Let's simplify: path_str is relative to WORKSPACE_ROOT
    target = WORKSPACE_ROOT / path_str
    # Security check could go here
    return target

def init_game_project(project_name: str = "current_game") -> str:
    """Initializes a new Phaser game project from template."""
    target_dir = WORKSPACE_ROOT / project_name
    
    if target_dir.exists():
        shutil.rmtree(target_dir)
    
    if not TEMPLATE_PATH.exists():
        return f"Error: Template not found at {TEMPLATE_PATH}"
        
    shutil.copytree(TEMPLATE_PATH, target_dir)
    return f"Success: Created new project at {target_dir}. Run 'npm install' and 'npm run dev' inside."

def read_file(file_path: str) -> dict:
    """Reads the content of a file in the workspace."""
    target = _get_target_path(file_path)
    if not target.exists():
        return {"status": "error", "message": "File not found"}
        
    try:
        with open(target, 'r', encoding='utf-8') as f:
            return {"status": "success", "content": f.read()}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def write_file(file_path: str, content: str) -> dict:
    """Writes content to a file, creating directories if needed."""
    target = _get_target_path(file_path)
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, 'w', encoding='utf-8') as f:
            f.write(content)
        return {"status": "success", "message": f"Written to {file_path}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def list_files(directory: str = "") -> dict:
    """Lists files in a directory within the workspace."""
    target = _get_target_path(directory)
    if not target.exists():
        return {"status": "error", "message": "Directory not found"}
    
    files = []
    for root, _, filenames in os.walk(target):
        for name in filenames:
            rel_path = os.path.relpath(os.path.join(root, name), WORKSPACE_ROOT)
            files.append(rel_path)
    
    return {"status": "success", "files": files}
