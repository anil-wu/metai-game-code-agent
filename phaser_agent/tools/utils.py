import json
import os
from pathlib import Path
from phaser_agent.config import WORKSPACE_ROOT

def _norm_abs(path: Path) -> str:
    return os.path.normcase(os.path.abspath(str(path)))

def _is_within(target: Path, root: Path) -> bool:
    try:
        return os.path.commonpath([_norm_abs(target), _norm_abs(root)]) == _norm_abs(root)
    except ValueError:
        return False

def get_target_path(path_str: str, project_id: str = None) -> Path:
    """
    Helper to ensure paths are within workspace.
    
    Args:
        path_str: The relative path string.
        project_id: Optional project ID to scope the path to workspaces/<project_id>/.
                    If None, assumes path_str is relative to WORKSPACE_ROOT (legacy behavior).
    """
    candidate = Path(path_str)
    if candidate.is_absolute() or candidate.drive:
        raise ValueError("Absolute paths are not allowed")

    if project_id:
        if not project_id.replace("_", "").replace("-", "").isalnum():
            raise ValueError("Invalid project_id")
        
        root = (WORKSPACE_ROOT / project_id).resolve()
        target = (root / path_str).resolve()
        if not _is_within(target, root):
            raise ValueError(f"Path traversal detected: {path_str}")
        return target
    else:
        root = WORKSPACE_ROOT.resolve()
        target = (root / path_str).resolve()
        if not _is_within(target, root):
            raise ValueError(f"Path traversal detected: {path_str}")
        return target


def load_agent_prompt(agent_name: str) -> dict[str, str]:
    path = Path(__file__).resolve().parents[1] / "agents_prompts.json"
    try:
        raw = path.read_text(encoding="utf-8")
    except Exception:
        return {}
    try:
        payload = json.loads(raw)
    except Exception:
        return {}
    if not isinstance(payload, list):
        return {}

    for item in payload:
        if not isinstance(item, dict):
            continue
        name = item.get("name") or item.get("名称")
        if not isinstance(name, str) or name.strip() != agent_name:
            continue

        description = item.get("description") or item.get("描述")
        instruction = item.get("instruction") or item.get("指令")

        out: dict[str, str] = {}
        if isinstance(description, str) and description.strip():
            out["description"] = description
        if isinstance(instruction, str) and instruction.strip():
            out["instruction"] = instruction
        return out

    return {}
