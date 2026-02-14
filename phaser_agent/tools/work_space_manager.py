import json
import os
import shutil
import ssl
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from typing import Any, Dict
from phaser_agent.config import WORKSPACE_ROOT, DIR_GAME, DIR_ARTIFACTS, DIR_BUILD, DIR_LOGS

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
    token = tool_context.state["user:token"]
    project_id = tool_context.state["user:project_id"]
    if not project_id or project_id == 0:
        return _resp("success", 200, "项目ID不存在", None)

    base = tool_context.state["user:api_base_url"]
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
    token = tool_context.state["user:token"]
    if not isinstance(token, str) or not token.strip():
        token = None
    user_id = tool_context.state["user:user_id"]
    base = tool_context.state["user:api_base_url"]  

    try:
        user_id_int = int(user_id)
    except Exception:
        return _resp("error", 400, "user_id is invalid", None)

    args = {"project_name": project_name, "project_description": project_description, "project_type": project_type, "user_id": user_id_int}
    print("create_project_info----------------------------->>:", {"token": token, "args": args})

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
        project_id = data.get("id")
        tool_context.state["user:project_id"] = project_id  
        return _resp("success", int(status_code), "ok", {"project_id": project_id})

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
    if api_user_id is None or api_user_id == 0 or (isinstance(api_user_id, str) and not str(api_user_id).strip()):
        return _resp("error", 400, "user_id is required", None)

    try:
        user_id_int = int(api_user_id)
    except Exception:
        return _resp("error", 400, "user_id is invalid", None)

    pid_str = str(project_id).strip()
    if not pid_str or "/" in pid_str or "\\" in pid_str:
        return _resp("error", 400, "project_id is invalid", None)

    try:
        workspace_root = os.path.abspath(str(WORKSPACE_ROOT))
        workspace_dir = os.path.abspath(os.path.join(workspace_root, str(user_id_int), pid_str))
        if os.path.commonpath([workspace_root, workspace_dir]) != workspace_root:
            return _resp("error", 400, "workspace_dir escapes WORKSPACE_ROOT", None)

        existed = os.path.exists(workspace_dir)
        os.makedirs(workspace_dir, exist_ok=True)
        if not os.path.isdir(workspace_dir):
            return _resp("error", 500, "workspace_dir is not a directory", None)

        created_subdirs: Dict[str, str] = {}
        for name in (DIR_GAME, DIR_ARTIFACTS, DIR_BUILD, DIR_LOGS):
            subdir = os.path.join(workspace_dir, name)
            os.makedirs(subdir, exist_ok=True)
            created_subdirs[name] = subdir

        fd, tmp_path = tempfile.mkstemp(prefix=".writable_check_", dir=workspace_dir)
        os.close(fd)
        os.unlink(tmp_path)

        tool_context.state["user:workspace_dir"] = workspace_dir
        tool_context.state["user:workspace_game_dir"] = created_subdirs.get(DIR_GAME)
        tool_context.state["user:workspace_artifacts_dir"] = created_subdirs.get(DIR_ARTIFACTS)
        tool_context.state["user:workspace_build_dir"] = created_subdirs.get(DIR_BUILD)
        tool_context.state["user:workspace_logs_dir"] = created_subdirs.get(DIR_LOGS)

        print("create_project_workspace----------------------------->>:")
        return _resp(
            "success",
            200,
            "创建成功",
            {
            },
        )
    except Exception as e:
        return _resp("error", 500, str(e), None)


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


def init_project_workspace(
    template_name: str,
    tool_context: Any = None,
) -> Dict[str, Any]:
    print("init_project_workspace----------------------------->>:", {"template_name": template_name})

    state = getattr(tool_context, "state", None) if tool_context is not None else None
    token = _state_get(state, "user:token")
    if not isinstance(token, str) or not token.strip():
        token = None

    if not isinstance(template_name, str) or not template_name.strip():
        return _resp("error", 400, "template_name is required", None)

    base = _state_get(state, "user:api_base_url")
    if isinstance(base, str):
        base = base.strip().rstrip("/")
    else:
        base = ""
    if not base:
        return _resp("error", 400, "API base URL is required", None)

    # workspace_dir = tool_context.state.get("user:workspace_dir")
    workspace_game_dir = tool_context.state.get("user:workspace_game_dir")
    workspace_artifacts_dir = tool_context.state.get("user:workspace_artifacts_dir")

    os.makedirs(workspace_game_dir, exist_ok=True)
    os.makedirs(workspace_artifacts_dir, exist_ok=True)

    headers = {"Accept": "application/json"}
    if isinstance(token, str) and token:
        headers["Authorization"] = f"Bearer {token}"

    def http_get_json(url: str, timeout: int = 10) -> tuple[int, Any, str]:
        print("http_get_json----------------------------->>:", {"url": url, "headers": headers})
        req = urllib.request.Request(url, headers=headers, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=timeout, context=_ssl_context_for_url(url, state)) as resp:
                status_code = getattr(resp, "status", None) or 200
                raw = resp.read()
        except urllib.error.HTTPError as e:
            status_code = getattr(e, "code", None) or 500
            raw = e.read()
        except Exception as e:
            return 500, None, str(e)

        text = ""
        try:
            text = raw.decode("utf-8", errors="replace") if raw else ""
        except Exception:
            text = ""

        try:
            data = json.loads(text) if text else None
        except Exception:
            data = None

        return int(status_code or 500), data, text

    tpl_name = template_name.strip()
    tpl_name_encoded = urllib.parse.quote(tpl_name, safe="")
    url = f"{base}/api/v1/software-templates/by-name/{tpl_name_encoded}"
    status_code, payload, text = http_get_json(url, timeout=10)
    if not (200 <= int(status_code) < 300):
        if int(status_code) == 404:
            return _resp("error", 404, f"template not found: {tpl_name}", None)
        return _resp("error", int(status_code), (text or f"HTTP {status_code}").strip(), None)

    if not isinstance(payload, dict):
        return _resp("error", 500, "invalid template response", {"payload": payload})

    found_template = payload

    archive_file_id = found_template.get("archiveFileId")
    try:
        archive_file_id_int = int(archive_file_id)
    except Exception:
        return _resp("error", 500, "template archiveFileId is invalid", {"template": found_template})

    download_meta_url = f"{base}/api/v1/files/{archive_file_id_int}/download"
    status_code, meta, text = http_get_json(download_meta_url, timeout=10)
    if not (200 <= int(status_code) < 300):
        return _resp("error", int(status_code), (text or f"HTTP {status_code}").strip(), None)

    download_url = None
    if isinstance(meta, dict):
        download_url = meta.get("downloadUrl")
    if not isinstance(download_url, str) or not download_url.strip():
        return _resp("error", 500, "downloadUrl is missing", {"meta": meta})

    download_url = download_url.strip()

    try:
        parsed_api = urllib.parse.urlparse(base)
        parsed_dl = urllib.parse.urlparse(download_url)
        same_host = (parsed_api.hostname or "").lower() == (parsed_dl.hostname or "").lower()
    except Exception:
        same_host = False

    dl_headers = {"User-Agent": "SparkPlay-Agent"}
    if same_host and isinstance(token, str) and token:
        dl_headers["Authorization"] = f"Bearer {token}"

    zip_name = f"template_{archive_file_id_int}.zip"
    local_zip_path = os.path.join(workspace_artifacts_dir, zip_name)

    try:
        req = urllib.request.Request(download_url, headers=dl_headers, method="GET")
        with urllib.request.urlopen(req, timeout=60, context=_ssl_context_for_url(download_url, state)) as resp:
            with open(local_zip_path, "wb") as f:
                shutil.copyfileobj(resp, f)
    except Exception as e:
        return _resp("error", 500, f"download failed: {e}", {"download_url": download_url})

    if not zipfile.is_zipfile(local_zip_path):
        return _resp("error", 400, "template archive is not a zip file", {"zip_path": local_zip_path})

    extract_dir = os.path.join(workspace_artifacts_dir, f".extract_{archive_file_id_int}")
    try:
        if os.path.exists(extract_dir):
            shutil.rmtree(extract_dir, ignore_errors=True)
        os.makedirs(extract_dir, exist_ok=True)

        extract_dir_abs = os.path.abspath(extract_dir)

        def safe_extract(zf: zipfile.ZipFile) -> int:
            extracted = 0
            for info in zf.infolist():
                name = info.filename.replace("\\", "/")
                if not name or name.startswith("/"):
                    name = name.lstrip("/")
                if not name:
                    continue
                if name.endswith("/"):
                    dest_dir = os.path.abspath(os.path.join(extract_dir_abs, name))
                    if os.path.commonpath([extract_dir_abs, dest_dir]) != extract_dir_abs:
                        raise ValueError("zip path traversal detected")
                    os.makedirs(dest_dir, exist_ok=True)
                    continue

                dest_path = os.path.abspath(os.path.join(extract_dir_abs, name))
                if os.path.commonpath([extract_dir_abs, dest_path]) != extract_dir_abs:
                    raise ValueError("zip path traversal detected")

                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                with zf.open(info, "r") as src, open(dest_path, "wb") as dst:
                    shutil.copyfileobj(src, dst)
                extracted += 1
            return extracted

        with zipfile.ZipFile(local_zip_path, "r") as zf:
            extracted_files = safe_extract(zf)

        entries = [e for e in os.listdir(extract_dir) if e and e not in {"__MACOSX"}]
        if len(entries) == 1 and os.path.isdir(os.path.join(extract_dir, entries[0])):
            extract_root = os.path.join(extract_dir, entries[0])
        else:
            extract_root = extract_dir

        moved = 0
        for name in os.listdir(extract_root):
            src = os.path.join(extract_root, name)
            dst = os.path.join(workspace_game_dir, name)
            if os.path.exists(dst):
                if os.path.isdir(dst) and not os.path.islink(dst):
                    shutil.rmtree(dst, ignore_errors=True)
                else:
                    try:
                        os.unlink(dst)
                    except Exception:
                        shutil.rmtree(dst, ignore_errors=True)
            shutil.move(src, dst)
            moved += 1

        shutil.rmtree(extract_dir, ignore_errors=True)

        return _resp(
            "success",
            200,
            "ok",
            {
                "template": found_template,
                "archive_file_id": archive_file_id_int,
                "download_url": download_url,
                "zip_path": local_zip_path,
                "workspace_game_dir": workspace_game_dir,
                "extracted_files": extracted_files,
                "moved_entries": moved,
            },
        )
    except Exception as e:
        return _resp("error", 500, str(e), {"zip_path": local_zip_path, "extract_dir": extract_dir})
