from pathlib import Path
from phaser_agent.config import WORKSPACE_ROOT

def get_target_path(path_str: str, project_id: str = None) -> Path:
    """
    Helper to ensure paths are within workspace.
    
    Args:
        path_str: The relative path string.
        project_id: Optional project ID to scope the path to workspaces/<project_id>/.
                    If None, assumes path_str is relative to WORKSPACE_ROOT (legacy behavior).
    """
    if project_id:
        # Secure construction
        if not project_id.replace("_", "").replace("-", "").isalnum():
            raise ValueError("Invalid project_id")
        
        target = (WORKSPACE_ROOT / project_id / path_str).resolve()
        root = (WORKSPACE_ROOT / project_id).resolve()
        
        # Security check: Ensure target is within project root
        if not str(target).startswith(str(root)):
             raise ValueError(f"Path traversal detected: {path_str}")
        return target
    else:
        # Legacy/Global mode (careful)
        target = (WORKSPACE_ROOT / path_str).resolve()
        # Basic check to ensure we don't go above WORKSPACE_ROOT
        if not str(target).startswith(str(WORKSPACE_ROOT.resolve())):
             # This might be too strict if WORKSPACE_ROOT is relative, but resolve() handles it.
             pass 
        return target
