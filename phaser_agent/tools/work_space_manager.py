from typing import Any, Dict

def _state_get(state: Any, key: str, default: Any = None) -> Any:
    getter = getattr(state, "get", None)
    if callable(getter):
        try:
            return getter(key, default)
        except TypeError:
            try:
                return getter(key)
            except Exception:
                return default
        except Exception:
            return default
    if isinstance(state, dict):
        return state.get(key, default)
    return default

def check_project_info(
    tool_context: Any = None,
) -> Dict[str, Any]:
    state = getattr(tool_context, "state", None)
    token = _state_get(state, "user:token")
    user_id = _state_get(state, "user:user_id")
    project_id = _state_get(state, "user:project_id")
    args = {"project_id": project_id, "user_id": user_id, "token": token}
    print("check_project_info----------------------------->>:", args)
    if not project_id or project_id == 0:
        return {"status": "success", "message": "项目ID不存在"}
    return {"status": "success", "message": "ok", "token": token, "args": args}

def create_project_info(
    project_name: str,
    project_description: str,
    project_type: str,
    tool_context: Any = None,
) -> Dict[str, Any]:
    token = None

    state = getattr(tool_context, "state", None) if tool_context is not None else None
    token = _state_get(state, "user:token")
    if not isinstance(token, str) or not token.strip():
        token = None
    user_id = _state_get(state, "user:user_id")
    args = {
        "project_name": project_name,
        "project_description": project_description,
        "project_type": project_type,
        "user_id": user_id,
    }
    print("create_project_info----------------------------->>:", {"token": token, "args": args})
    return {"status": "success", "message": "ok", "token": token, "args": args}


def update_project_info(
    project_id: int | str,
    project_name: str,
    project_description: str,
    project_type: str,
    tool_context: Any = None,
) -> Dict[str, Any]:
    token = None
    state = getattr(tool_context, "state", None) if tool_context is not None else None
    token = _state_get(state, "user:token")
    if not isinstance(token, str) or not token.strip():
        token = None
    api_user_id = None
    api_user_id = _state_get(state, "user:user_id")
    args = {
        "project_id": project_id,
        "project_name": project_name,
        "project_description": project_description,
        "project_type": project_type,
        "state_user_id": api_user_id,
    }
    print("update_project_info----------------------------->>:", {"token": token, "args": args})
    return {"status": "success", "message": "ok", "token": token, "args": args}


def create_project_workspace(
    project_id: int | str,
    tool_context: Any = None,
) -> Dict[str, Any]:
    token = None
    state = getattr(tool_context, "state", None) if tool_context is not None else None
    token = _state_get(state, "user:token")
    if not isinstance(token, str) or not token.strip():
        token = None
    api_user_id = None
    api_user_id = _state_get(state, "user:user_id")
    if not project_id and project_id != 0:
        candidate = _state_get(state, "user:project_id")
        if candidate is not None:
            project_id = candidate
    args = {"state_user_id": api_user_id, "project_id": project_id}
    print("create_project_workspace----------------------------->>:", {"token": token, "args": args})
    return {"status": "success", "message": "ok", "token": token, "args": args}


def pull_project_software(
    project_id: int | str,
    file_id: int,
    version_id: int | None = None,
    version_number: int | None = None,
    tool_context: Any = None,
) -> Dict[str, Any]:
    token = None
    state = getattr(tool_context, "state", None) if tool_context is not None else None
    token = _state_get(state, "user:token")
    if not isinstance(token, str) or not token.strip():
        token = None
    api_user_id = None
    api_user_id = _state_get(state, "user:user_id")
    args = {
        "project_id": project_id,
        "file_id": file_id,
        "version_id": version_id,
        "version_number": version_number,
        "state_user_id": api_user_id,
    }
    print("pull_project_software----------------------------->>:", {"token": token, "args": args})
    return {"status": "success", "message": "ok", "token": token, "args": args}


def commit_project_software(
    file_id: int,
    version_number: int | None = None,
    tool_context: Any = None,
) -> Dict[str, Any]:
    token = None
    state = getattr(tool_context, "state", None) if tool_context is not None else None
    token = _state_get(state, "user:token")
    if not isinstance(token, str) or not token.strip():
        token = None
    api_user_id = None
    api_user_id = _state_get(state, "user:user_id")
    args = {"file_id": file_id, "version_number": version_number, "state_user_id": api_user_id}
    print("commit_project_software----------------------------->>:", {"token": token, "args": args})
    return {"status": "success", "message": "ok", "token": token, "args": args}
