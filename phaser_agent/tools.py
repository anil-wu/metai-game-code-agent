
import os
import shutil
import subprocess
from pathlib import Path

# Configuration
WORKSPACE_ROOT = Path("workspaces")
TEMPLATE_PATH = Path("templates/phaser-starter")
MAX_LIST_FILES = 2000
MAX_READ_CHARS = 200_000
IGNORED_DIR_NAMES = {
    ".git",
    ".adk",
    ".vite",
    "node_modules",
    "dist",
    "build",
    "coverage",
}

def _get_target_path(path_str: str) -> Path:
    """Helper to ensure paths are within workspace"""
    # For MVP, we assume a single active session 'current_game' or user provides path
    # Let's simplify: path_str is relative to WORKSPACE_ROOT
    target = WORKSPACE_ROOT / path_str
    # Security check could go here
    return target

def init_game_project(project_name: str = "current_game") -> str:
    """Initializes a new Phaser game project from template."""
    WORKSPACE_ROOT.mkdir(parents=True, exist_ok=True)
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
        with open(target, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read(MAX_READ_CHARS + 1)
            truncated = len(content) > MAX_READ_CHARS
            if truncated:
                content = content[:MAX_READ_CHARS]
            return {"status": "success", "content": content, "truncated": truncated}
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

def edit_file(file_path: str, search_content: str, replace_content: str) -> dict:
    """Edits a file by replacing specific content (Diff/Patch).
    
    Args:
        file_path: The file to edit.
        search_content: The exact content block to find and replace.
        replace_content: The new content to insert.
    """
    target = _get_target_path(file_path)
    if not target.exists():
        return {"status": "error", "message": "File not found"}
    
    try:
        with open(target, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Normalize line endings to avoid issues (optional but good)
        # For this MVP, we assume exact match.
        
        if search_content not in content:
             return {
                 "status": "error", 
                 "message": "Search content not found. Ensure you are using the EXACT text block from the file, including indentation."
             }
        
        new_content = content.replace(search_content, replace_content, 1)
        
        with open(target, 'w', encoding='utf-8') as f:
            f.write(new_content)
            
        return {"status": "success", "message": f"Successfully patched {file_path}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def list_files(directory: str = "") -> dict:
    """Lists files in a directory within the workspace."""
    target = _get_target_path(directory)
    if not target.exists():
        return {"status": "error", "message": "Directory not found"}
    
    files = []
    truncated = False
    for root, dirnames, filenames in os.walk(target):
        dirnames[:] = [d for d in dirnames if d not in IGNORED_DIR_NAMES]
        for name in filenames:
            rel_path = os.path.relpath(os.path.join(root, name), WORKSPACE_ROOT)
            files.append(rel_path)
            if len(files) >= MAX_LIST_FILES:
                truncated = True
                break
        if truncated:
            break
    
    return {"status": "success", "files": files, "truncated": truncated}

def run_command(command: str, working_dir: str = "current_game") -> dict:
    """Executes a shell command in the workspace.
    
    Args:
        command: The command to execute (e.g., 'npm install').
        working_dir: Relative path within workspace to run command in.
    """
    target_cwd = _get_target_path(working_dir)
    if not target_cwd.exists():
        return {"status": "error", "message": f"Directory {working_dir} does not exist"}

    try:
        # Use shell=True for flexibility, but be careful in prod
        result = subprocess.run(
            command,
            cwd=target_cwd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=300 # 5 minutes timeout for installs
        )
        return {
            "status": "success" if result.returncode == 0 else "error",
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
