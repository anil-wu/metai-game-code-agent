import os
from typing import Dict, Any
from phaser_agent.config import MAX_READ_CHARS, MAX_LIST_FILES, IGNORED_DIR_NAMES, WORKSPACE_ROOT
from .utils import get_target_path

def read_file(project_id: str, file_path: str) -> Dict[str, Any]:
    """Reads the content of a file in the workspace."""
    try:
        target = get_target_path(file_path, project_id)
        if not target.exists():
            return {"status": "error", "message": "File not found"}
            
        with open(target, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read(MAX_READ_CHARS + 1)
            truncated = len(content) > MAX_READ_CHARS
            if truncated:
                content = content[:MAX_READ_CHARS]
            return {"status": "success", "content": content, "truncated": truncated}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def write_file(project_id: str, file_path: str, content: str) -> Dict[str, Any]:
    """Writes content to a file, creating directories if needed."""
    try:
        target = get_target_path(file_path, project_id)
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, 'w', encoding='utf-8') as f:
            f.write(content)
        return {"status": "success", "message": f"Written to {file_path}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def edit_file(project_id: str, file_path: str, search_content: str, replace_content: str) -> Dict[str, Any]:
    """Edits a file by replacing specific content (Diff/Patch)."""
    try:
        target = get_target_path(file_path, project_id)
        if not target.exists():
            return {"status": "error", "message": "File not found"}
        
        with open(target, 'r', encoding='utf-8') as f:
            content = f.read()
        
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

def list_files(project_id: str, directory: str = "") -> Dict[str, Any]:
    """Lists files in a directory within the workspace."""
    try:
        target = get_target_path(directory, project_id)
        if not target.exists():
            return {"status": "error", "message": "Directory not found"}
        
        files = []
        truncated = False
        
        # We need to list relative to the project root, not the target dir if it's a subdir
        # But wait, the original code listed relative to WORKSPACE_ROOT. 
        # Here we should list relative to project root.
        project_root = get_target_path("", project_id)

        for root, dirnames, filenames in os.walk(target):
            dirnames[:] = [d for d in dirnames if d not in IGNORED_DIR_NAMES]
            for name in filenames:
                full_path = os.path.join(root, name)
                rel_path = os.path.relpath(full_path, project_root)
                files.append(rel_path)
                if len(files) >= MAX_LIST_FILES:
                    truncated = True
                    break
            if truncated:
                break
        
        return {"status": "success", "files": files, "truncated": truncated}
    except Exception as e:
        return {"status": "error", "message": str(e)}
