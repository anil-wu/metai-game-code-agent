import json
import os
import ssl
import urllib.error
import urllib.parse
import urllib.request
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

def _state_set(state: Any, key: str, value: Any) -> bool:
    setter = getattr(state, "set", None)
    if callable(setter):
        try:
            setter(key, value)
            return True
        except TypeError:
            try:
                setter(key, value, None)
                return True
            except Exception:
                return False
        except Exception:
            return False
    if isinstance(state, dict):
        state[key] = value
        return True
    return False

def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    text = str(value).strip().lower()
    return text in {"1", "true", "yes", "y", "on"}

def _ssl_context_for_url(url: str, state: Any) -> ssl.SSLContext | None:
    if not isinstance(url, str) or not url:
        return None
    try:
        parsed = urllib.parse.urlparse(url)
        scheme = parsed.scheme.lower()
        hostname = (parsed.hostname or "").lower()
    except Exception:
        scheme = ""
        hostname = ""
    if scheme != "https":
        return None

    force_verify_env = os.getenv("SPARKPLAY_TLS_VERIFY") or os.getenv("SPARKX_TLS_VERIFY") or ""

    insecure_env = os.getenv("SPARKPLAY_TLS_INSECURE") or os.getenv("SPARKX_TLS_INSECURE") or ""
    if _truthy(insecure_env):
        return ssl._create_unverified_context()

    tls_insecure_state = _state_get(state, "user:tls_insecure")
    if _truthy(tls_insecure_state):
        return ssl._create_unverified_context()

    tls_verify_state = _state_get(state, "user:tls_verify")
    if tls_verify_state is not None and not _truthy(tls_verify_state):
        return ssl._create_unverified_context()

    if hostname in {"localhost", "127.0.0.1", "::1"} and not _truthy(force_verify_env) and tls_verify_state is None:
        return ssl._create_unverified_context()

    ca_bundle = _state_get(state, "user:ca_bundle")
    if not isinstance(ca_bundle, str) or not ca_bundle.strip():
        ca_bundle = (os.getenv("SPARKPLAY_CA_BUNDLE") or os.getenv("REQUESTS_CA_BUNDLE") or "").strip()
    if ca_bundle:
        try:
            return ssl.create_default_context(cafile=ca_bundle)
        except Exception:
            return ssl.create_default_context()
    return ssl.create_default_context()

def _resp(
    status: str,
    status_code: int,
    message: str,
    data: Any = None,
) -> Dict[str, Any]:
    
    dict_data = {"status": status, "status_code": status_code, "message": message, "data": data}
    print("resp---------->>:", dict_data)
    return dict_data

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
        return _resp("success", 200, "项目ID不存在", None)

    base = _state_get(state, "user:api_base_url")
    if isinstance(base, str):
        base = base.strip().rstrip("/")
    else:
        base = ""
    if not base:
        return _resp("error", 400, "API base URL is required", None)

    pid_str = str(project_id).strip()
    if not pid_str or "/" in pid_str or "\\" in pid_str:
        return _resp("error", 400, "project_id is invalid", None)

    url = f"{base}/api/v1/projects/{pid_str}"
    headers = {"Accept": "application/json"}
    if isinstance(token, str) and token:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=10, context=_ssl_context_for_url(url, state)) as resp:
            status_code = getattr(resp, "status", None) or 200
            raw = resp.read()
    except urllib.error.HTTPError as e:
        status_code = getattr(e, "code", None)
        raw = e.read()
        try:
            text = raw.decode("utf-8", errors="replace") if raw else ""
        except Exception:
            text = ""
        return _resp("error", int(status_code or 500), (text or f"HTTP {status_code}").strip(), None)
    except Exception as e:
        return _resp("error", 500, str(e), None)

    try:
        data = json.loads(raw.decode("utf-8")) if raw else None
    except Exception:
        data = None

    if 200 <= int(status_code) < 300:
        return _resp("success", int(status_code), "ok", {"project": data})

    return _resp("error", int(status_code or 500), "请求项目失败", {"project": data})

def create_project_info(
    project_name: str,
    project_description: str,
    project_type: str,
    tool_context: Any = None,
) -> Dict[str, Any]:
    state = getattr(tool_context, "state", None) if tool_context is not None else None
    token = _state_get(state, "user:token")
    if not isinstance(token, str) or not token.strip():
        token = None
    user_id = _state_get(state, "user:user_id")
    base = _state_get(state, "user:api_base_url")
    if isinstance(base, str):
        base = base.strip().rstrip("/")
    else:
        base = ""

    args = {"project_name": project_name, "project_description": project_description, "project_type": project_type, "user_id": user_id}
    print("create_project_info----------------------------->>:", {"token": token, "args": args})

    if not base:
        return _resp("error", 400, "API base URL is required", None)
    if not isinstance(user_id, int) and not (isinstance(user_id, str) and user_id.strip().isdigit()):
        return _resp("error", 400, "user_id is required", None)
    if not isinstance(project_name, str) or not project_name.strip():
        return _resp("error", 400, "project_name is required", None)
    if not isinstance(project_description, str):
        project_description = ""

    try:
        user_id_int = int(user_id)
    except Exception:
        return _resp("error", 400, "user_id is invalid", None)

    url = f"{base}/api/v1/projects"
    payload = {"userId": user_id_int, "name": project_name.strip(), "description": project_description}
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    if isinstance(token, str) and token:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(url, headers=headers, data=json.dumps(payload).encode("utf-8"), method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10, context=_ssl_context_for_url(url, state)) as resp:
            status_code = getattr(resp, "status", None) or 200
            raw = resp.read()
    except urllib.error.HTTPError as e:
        status_code = getattr(e, "code", None)
        raw = e.read()
        try:
            text = raw.decode("utf-8", errors="replace") if raw else ""
        except Exception:
            text = ""
        return _resp("error", int(status_code or 500), (text or f"HTTP {status_code}").strip(), None)
    except Exception as e:
        return _resp("error", 500, str(e), None)

    try:
        data = json.loads(raw.decode("utf-8")) if raw else None
    except Exception:
        data = None

    if 200 <= int(status_code) < 300:
        project_id = data.get("id") if isinstance(data, dict) else None
        if project_id is not None:
            _state_set(state, "user:project_id", project_id)
        return _resp("success", int(status_code), "ok", {"project": data})

    return _resp("error", int(status_code or 500), "创建项目失败", {"project": data})


def update_project_info(
    project_name: str,
    project_description: str,
    project_type: str,
    tool_context: Any = None,
) -> Dict[str, Any]:
    state = getattr(tool_context, "state", None) if tool_context is not None else None
    token = _state_get(state, "user:token")
    if not isinstance(token, str) or not token.strip():
        token = None
    project_id = _state_get(state, "user:project_id")
    api_user_id = _state_get(state, "user:user_id")
    base = _state_get(state, "user:api_base_url")
    if isinstance(base, str):
        base = base.strip().rstrip("/")
    else:
        base = ""

    args = {
        "project_name": project_name,
        "project_description": project_description,
        "project_type": project_type,
        "state_user_id": api_user_id,
    }
    print("update_project_info----------------------------->>:", {"token": token, "args": args})

    if not base:
        return _resp("error", 400, "API base URL is required", None)
    if project_id is None or project_id == 0 or (isinstance(project_id, str) and not project_id.strip()):
        return _resp("error", 400, "project_id is required", None)
    if not isinstance(project_name, str) or not project_name.strip():
        return _resp("error", 400, "project_name is required", None)
    if not isinstance(project_description, str):
        project_description = ""

    pid_str = str(project_id).strip()
    if not pid_str or "/" in pid_str or "\\" in pid_str:
        return _resp("error", 400, "project_id is invalid", None)

    url = f"{base}/api/v1/projects/{pid_str}"
    payload: Dict[str, Any] = {"name": project_name.strip(), "description": project_description}
    if isinstance(project_type, str) and project_type.strip() in {"active", "archived"}:
        payload["status"] = project_type.strip()

    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    if isinstance(token, str) and token:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(url, headers=headers, data=json.dumps(payload).encode("utf-8"), method="PUT")
    try:
        with urllib.request.urlopen(req, timeout=10, context=_ssl_context_for_url(url, state)) as resp:
            status_code = getattr(resp, "status", None) or 200
            raw = resp.read()
    except urllib.error.HTTPError as e:
        status_code = getattr(e, "code", None)
        raw = e.read()
        try:
            text = raw.decode("utf-8", errors="replace") if raw else ""
        except Exception:
            text = ""
        return _resp("error", int(status_code or 500), (text or f"HTTP {status_code}").strip(), None)
    except Exception as e:
        return _resp("error", 500, str(e), None)

    try:
        data = json.loads(raw.decode("utf-8")) if raw else None
    except Exception:
        data = None

    if 200 <= int(status_code) < 300:
        return _resp("success", int(status_code), "ok", {"result": data})

    return _resp("error", int(status_code or 500), "更新项目失败", {"result": data})


def create_project_workspace(
    tool_context: Any = None,
) -> Dict[str, Any]:
    state = getattr(tool_context, "state", None) if tool_context is not None else None
    token = _state_get(state, "user:token")
    if not isinstance(token, str) or not token.strip():
        token = None
    api_user_id = _state_get(state, "user:user_id")
    project_id = _state_get(state, "user:project_id")
    if project_id is None or project_id == 0 or (isinstance(project_id, str) and not project_id.strip()):
        return _resp("error", 400, "project_id is required", None)
    args = {"state_user_id": api_user_id, "project_id": project_id}
    print("create_project_workspace----------------------------->>:", {"token": token, "args": args})
    return _resp("success", 200, "ok", {"token": token})


def pull_project_software(
    file_id: int,
    version_id: int | None = None,
    version_number: int | None = None,
    tool_context: Any = None,
) -> Dict[str, Any]:
    state = getattr(tool_context, "state", None) if tool_context is not None else None
    token = _state_get(state, "user:token")
    if not isinstance(token, str) or not token.strip():
        token = None
    api_user_id = _state_get(state, "user:user_id")
    project_id = _state_get(state, "user:project_id")
    if project_id is None or project_id == 0 or (isinstance(project_id, str) and not project_id.strip()):
        return _resp("error", 400, "project_id is required", None)
    args = {
        "project_id": project_id,
        "file_id": file_id,
        "version_id": version_id,
        "version_number": version_number,
        "state_user_id": api_user_id,
    }
    print("pull_project_software----------------------------->>:", {"token": token, "args": args})
    return _resp("success", 200, "ok", {"token": token})


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
    return _resp("success", 200, "ok", {"token": token})
