import json
from pathlib import Path
from typing import Dict, Any, Optional
from phaser_agent.config import DIR_GAME
from .utils import get_target_path

def read_local_manifest(
    project_id: Optional[str] = None,
    tool_context: Any = None,
) -> Dict[str, Any]:
    """
    Reads the local manifest.json file from the project workspace.
    This helps the agent understand the project structure, entry point, and assets.
    """
    try:
        state = getattr(tool_context, "state", {}) if tool_context else {}
        
        if not project_id:
            project_id = state.get("user:project_id")
        if not project_id:
            return {"status": "error", "message": "project_id is required"}
            
        workspace_game_dir = state.get("user:workspace_game_dir")
        
        if workspace_game_dir:
            root_path = Path(workspace_game_dir)
        else:
            root_path = get_target_path(DIR_GAME, str(project_id))
            
        manifest_path = root_path / "manifest.json"
        
        if not manifest_path.exists():
            return {
                "status": "error", 
                "message": "manifest.json not found in project root",
                "path": str(manifest_path)
            }
            
        with open(manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        return {
            "status": "success",
            "manifest": data,
            "path": str(manifest_path)
        }
        
    except Exception as e:
        return {"status": "error", "message": str(e)}
