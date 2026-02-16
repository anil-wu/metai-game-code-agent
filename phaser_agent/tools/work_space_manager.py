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

    tls_insecure_state = _state_get(state, "tls_insecure")
    if _truthy(tls_insecure_state):
        return ssl._create_unverified_context()

    tls_verify_state = _state_get(state, "tls_verify")
    if tls_verify_state is not None and not _truthy(tls_verify_state):
        return ssl._create_unverified_context()

    if hostname in {"localhost", "127.0.0.1", "::1"} and not _truthy(force_verify_env) and tls_verify_state is None:
        return ssl._create_unverified_context()

    ca_bundle = _state_get(state, "ca_bundle")
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
    token = tool_context.state["token"]
    project_id = tool_context.state["project_id"]
    if not project_id or project_id == 0:
        return _resp("success", 200, "项目ID不存在, 请创建新项目", None)

    base = tool_context.state["api_base_url"]
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
    token = tool_context.state["token"]
    if not isinstance(token, str) or not token.strip():
        token = None
    user_id = tool_context.state["user_id"]
    base = tool_context.state["api_base_url"]  

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
        tool_context.state["project_id"] = project_id  
        return _resp("success", int(status_code), "ok", {"project_id": project_id})

    return _resp("error", int(status_code or 500), "创建项目失败", {"project": data})


def update_project_info(
    project_name: str,
    project_description: str,
    project_type: str,
    tool_context: Any = None,
) -> Dict[str, Any]:
    state = getattr(tool_context, "state", None) if tool_context is not None else None
    token = _state_get(state, "token")
    if not isinstance(token, str) or not token.strip():
        token = None
    project_id = _state_get(state, "project_id")
    api_user_id = _state_get(state, "user_id")
    base = _state_get(state, "api_base_url")
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
    token = _state_get(state, "token")
    if not isinstance(token, str) or not token.strip():
        token = None
    api_user_id = _state_get(state, "user_id")
    project_id = _state_get(state, "project_id")
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

        tool_context.state["workspace_dir"] = workspace_dir
        tool_context.state["workspace_game_dir"] = created_subdirs.get(DIR_GAME)
        tool_context.state["workspace_artifacts_dir"] = created_subdirs.get(DIR_ARTIFACTS)
        tool_context.state["workspace_build_dir"] = created_subdirs.get(DIR_BUILD)
        tool_context.state["workspace_logs_dir"] = created_subdirs.get(DIR_LOGS)

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
    token = _state_get(state, "token")
    if not isinstance(token, str) or not token.strip():
        token = None
    api_user_id = _state_get(state, "user_id")
    project_id = _state_get(state, "project_id")
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
    tool_context: Any,
    software_name: str,
    version_description: str,
) -> Dict[str, Any]:
    import hashlib
    import time

    state = getattr(tool_context, "state", None) if tool_context is not None else None

    token = _state_get(state, "token")
    if not isinstance(token, str) or not token.strip():
        return _resp("error", 401, "token is required", None)

    project_id = _state_get(state, "project_id")
    if not project_id:
        return _resp("error", 400, "project_id is required", None)

    base = _state_get(state, "api_base_url")
    if isinstance(base, str):
        base = base.strip().rstrip("/")
    else:
        base = ""
    if not base:
        return _resp("error", 400, "API base URL is required", None)

    if not isinstance(software_name, str) or not software_name.strip():
        return _resp("error", 400, "software_name is required", None)

    workspace_game_dir = _state_get(state, "workspace_game_dir")
    if not workspace_game_dir:
        return _resp("error", 400, "workspace_game_dir is required", None)

    software_dir = os.path.join(workspace_game_dir, software_name.strip())
    if not os.path.exists(software_dir):
        return _resp("error", 404, f"software directory not found: {software_dir}", None)

    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    def http_get_json(url: str, timeout: int = 10) -> tuple:
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

    def http_post_json(url: str, data: dict, timeout: int = 10) -> tuple:
        post_headers = dict(headers)
        post_headers["Content-Type"] = "application/json"
        body = json.dumps(data).encode("utf-8")
        req = urllib.request.Request(url, headers=post_headers, data=body, method="POST")
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
            resp_data = json.loads(text) if text else None
        except Exception:
            resp_data = None

        return int(status_code or 500), resp_data, text

    def calculate_file_hash(file_path: str) -> str:
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def get_file_category_and_format(file_path: str) -> tuple:
        ext = os.path.splitext(file_path)[1].lower()
        format_map = {
            ".ts": ("text", "typescript"),
            ".js": ("text", "javascript"),
            ".json": ("text", "json"),
            ".html": ("text", "html"),
            ".css": ("text", "css"),
            ".png": ("image", "png"),
            ".jpg": ("image", "jpeg"),
            ".jpeg": ("image", "jpeg"),
            ".gif": ("image", "gif"),
            ".mp3": ("audio", "mp3"),
            ".mp4": ("video", "mp4"),
            ".zip": ("archive", "zip"),
            ".txt": ("text", "txt"),
            ".md": ("text", "markdown"),
        }
        return format_map.get(ext, ("binary", ext.lstrip(".") or "bin"))

    def get_content_type_by_format(file_format: str) -> str:
        type_map = {
            "typescript": "text/plain",
            "javascript": "application/javascript",
            "json": "application/json",
            "html": "text/html",
            "css": "text/css",
            "png": "image/png",
            "jpeg": "image/jpeg",
            "gif": "image/gif",
            "mp3": "audio/mpeg",
            "mp4": "video/mp4",
            "zip": "application/zip",
            "txt": "text/plain",
            "markdown": "text/markdown",
        }
        return type_map.get(file_format.lower(), "application/octet-stream")

    print("commit_project_software----------------------------->>:", {"software_name": software_name, "version_description": version_description})

    # ========== 2. 查找 Software 信息 ==========
    list_url = f"{base}/api/v1/projects/{project_id}/softwares"
    status_code, resp_data, text = http_get_json(list_url, timeout=10)
    if not (200 <= int(status_code) < 300):
        return _resp("error", int(status_code), f"list softwares failed: {text}", None)

    software_id = None
    for sw in resp_data.get("list", []):
        if sw.get("name") == software_name.strip():
            software_id = sw.get("id")
            break

    if not software_id:
        return _resp("error", 404, f"software not found: {software_name}", None)

    # ========== 3. 获取最新 Manifest 元数据（从远程） ==========
    manifests_url = f"{base}/api/v1/projects/{project_id}/software_manifests?software_ids={software_id}"
    status_code, manifests_resp, text = http_get_json(manifests_url, timeout=10)
    if not (200 <= int(status_code) < 300):
        return _resp("error", int(status_code), f"get software manifests failed: {text}", None)

    manifest_item = None
    for item in manifests_resp.get("list", []):
        if item.get("softwareId") == software_id and item.get("hasRecord"):
            manifest_item = item
            break

    is_first_commit = manifest_item is None
    manifest_file_id = None

    if is_first_commit:
        current_manifest = {"engine": {"name": "phaser", "version": "3.60.0"}, "entry": "src/main.ts", "files": [], "folders": ["src", "assets"]}
    else:
        manifest_file_id = manifest_item.get("manifestFileId")

        # ========== 4. 获取 Manifest 文件内容（从远程） ==========
        content_url = f"{base}/api/v1/files/{manifest_file_id}/content"
        req = urllib.request.Request(content_url, headers=headers, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=10, context=_ssl_context_for_url(content_url, state)) as resp:
                manifest_content = resp.read().decode("utf-8")
                current_manifest = json.loads(manifest_content)
        except Exception as e:
            return _resp("error", 500, f"get manifest content failed: {e}", None)

    # ========== 5. 扫描本地文件并检测变更 ==========
    EXCLUDE_DIRS = {"node_modules", ".git", "__pycache__", ".cache", "dist", "build"}
    EXCLUDE_FILES = {".DS_Store", "Thumbs.db", "manifest.json"}

    remote_files_map = {f["path"]: f for f in current_manifest.get("files", [])}

    changed_files = []
    unchanged_files = []

    for root, dirs, files in os.walk(software_dir):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]

        for filename in files:
            if filename in EXCLUDE_FILES:
                continue

            file_path = os.path.join(root, filename)
            rel_path = os.path.relpath(file_path, software_dir).replace("\\", "/")

            file_hash = calculate_file_hash(file_path)
            file_size = os.path.getsize(file_path)

            if rel_path in remote_files_map:
                if remote_files_map[rel_path].get("hash") != file_hash:
                    changed_files.append({"path": rel_path, "local_path": file_path, "hash": file_hash, "size": file_size, "action": "modified"})
                else:
                    unchanged_files.append(remote_files_map[rel_path])
            else:
                changed_files.append({"path": rel_path, "local_path": file_path, "hash": file_hash, "size": file_size, "action": "added"})

    # 检测删除的文件
    local_paths = set()
    for root, dirs, files in os.walk(software_dir):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for filename in files:
            if filename not in EXCLUDE_FILES:
                file_path = os.path.join(root, filename)
                rel_path = os.path.relpath(file_path, software_dir).replace("\\", "/")
                local_paths.add(rel_path)

    deleted_files = [remote_files_map[p] for p in remote_files_map if p not in local_paths]

    if not changed_files and not deleted_files:
        return _resp("success", 200, "no changes to commit", {"softwareId": software_id, "softwareName": software_name, "changedCount": 0, "deletedCount": 0})

    # ========== 6. 上传变动文件 ==========
    uploaded_files = []
    preupload_url = f"{base}/api/v1/files/preupload"

    for file_info in changed_files:
        file_path = file_info["local_path"]
        rel_path = file_info["path"]
        file_hash = file_info["hash"]
        file_size = file_info["size"]

        category, file_format = get_file_category_and_format(file_path)

        # 预上传
        preupload_payload = {"projectId": project_id, "name": rel_path, "fileCategory": category, "fileFormat": file_format, "sizeBytes": file_size, "hash": file_hash, "contentType": get_content_type_by_format(file_format)}

        status_code, preupload_data, text = http_post_json(preupload_url, preupload_payload, timeout=10)
        if not (200 <= int(status_code) < 300):
            return _resp("error", int(status_code), f"preupload failed for {rel_path}: {text}", None)

        upload_url = preupload_data.get("uploadUrl")
        file_id = preupload_data.get("fileId")
        version_id = preupload_data.get("versionId")
        version_number = preupload_data.get("versionNumber")

        # 上传到 OSS
        try:
            with open(file_path, "rb") as f:
                content = f.read()

            upload_headers = {"Content-Type": preupload_payload["contentType"]}
            req = urllib.request.Request(upload_url, data=content, headers=upload_headers, method="PUT")
            with urllib.request.urlopen(req, timeout=60) as resp:
                if resp.status not in (200, 201):
                    return _resp("error", resp.status, f"upload failed for {rel_path}", None)
        except Exception as e:
            return _resp("error", 500, f"upload failed for {rel_path}: {e}", None)

        uploaded_files.append({"path": rel_path, "fileId": file_id, "versionId": version_id, "versionNumber": version_number, "hash": file_hash, "size": file_size, "lastModified": time.strftime("%Y-%m-%dT%H:%M:%SZ")})

    # ========== 7. 生成新 Manifest 内容 ==========
    # 构建完整的文件快照：未变更文件保持远程信息 + 新上传文件使用新信息
    all_files_map = {}
    
    # 先添加所有未变更的文件（保持远程的完整版本信息）
    for f in unchanged_files:
        all_files_map[f["path"]] = f
    
    # 再添加新上传的文件（覆盖同名文件）
    for f in uploaded_files:
        all_files_map[f["path"]] = f
    
    # 移除已删除的文件
    for deleted in deleted_files:
        if deleted["path"] in all_files_map:
            del all_files_map[deleted["path"]]
    
    # 转换为列表并排序
    new_files_list = sorted(all_files_map.values(), key=lambda x: x["path"])

    # 收集 folders（从当前所有文件路径中提取）
    folders = set()
    for f in new_files_list:
        dir_path = os.path.dirname(f["path"])
        if dir_path:
            # 只保留顶级目录
            top_folder = dir_path.split("/")[0]
            if top_folder:
                folders.add(top_folder)
    
    # 如果没有文件夹，使用默认的
    if not folders:
        folders = {"src", "assets"}

    new_manifest = {
        "engine": current_manifest.get("engine", {"name": "phaser", "version": "3.60.0"}),
        "entry": current_manifest.get("entry", "src/main.ts"),
        "files": new_files_list,
        "folders": sorted(list(folders)),
        "commitInfo": {
            "versionDescription": version_description or f"Commit at {time.strftime('%Y-%m-%d %H:%M:%S')}",
            "changedFiles": [{"path": f["path"], "action": f.get("action", "modified")} for f in changed_files],
            "deletedFiles": [f["path"] for f in deleted_files],
            "committedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "totalFiles": len(new_files_list)
        },
    }

    # ========== 8. 上传新 Manifest 文件 ==========
    manifest_json = json.dumps(new_manifest, ensure_ascii=False, indent=2)
    manifest_bytes = manifest_json.encode("utf-8")
    manifest_hash = hashlib.sha256(manifest_bytes).hexdigest()

    manifest_preupload_payload = {"projectId": project_id, "name": f"{software_name.strip()}_manifest.json", "fileCategory": "text", "fileFormat": "json", "sizeBytes": len(manifest_bytes), "hash": manifest_hash, "contentType": "application/json"}

    status_code, manifest_preupload_data, text = http_post_json(preupload_url, manifest_preupload_payload, timeout=10)
    if not (200 <= int(status_code) < 300):
        return _resp("error", int(status_code), f"preupload manifest failed: {text}", None)

    manifest_upload_url = manifest_preupload_data.get("uploadUrl")
    new_manifest_file_id = manifest_preupload_data.get("fileId")
    new_manifest_version_id = manifest_preupload_data.get("versionId")

    # 上传 manifest 到 OSS
    try:
        req = urllib.request.Request(manifest_upload_url, data=manifest_bytes, headers={"Content-Type": "application/json"}, method="PUT")
        with urllib.request.urlopen(req, timeout=30) as resp:
            if resp.status not in (200, 201):
                return _resp("error", resp.status, "upload manifest failed", None)
    except Exception as e:
        return _resp("error", 500, f"upload manifest failed: {e}", None)

    # 保存 manifest 到本地（缓存）
    manifest_local_path = os.path.join(software_dir, "manifest.json")
    with open(manifest_local_path, "w", encoding="utf-8") as f:
        f.write(manifest_json)

    # ========== 9. 创建 Software Manifest 记录 ==========
    create_manifest_payload = {"projectId": project_id, "softwareId": software_id, "manifestFileId": new_manifest_file_id, "manifestFileVersionId": new_manifest_version_id, "versionDescription": version_description or f"Commit at {time.strftime('%Y-%m-%d %H:%M:%S')}"}

    manifest_url = f"{base}/api/v1/software-manifests"
    status_code, manifest_resp, text = http_post_json(manifest_url, create_manifest_payload, timeout=10)
    if not (200 <= int(status_code) < 300):
        return _resp("error", int(status_code), f"create software manifest failed: {text}", None)

    # ========== 10. 返回结果 ==========
    return _resp(
        "success",
        200,
        "commit successful",
        {
            "softwareId": software_id,
            "softwareName": software_name,
            "manifestId": manifest_resp.get("manifestId"),
            "manifestFileId": new_manifest_file_id,
            "manifestFileVersionId": new_manifest_version_id,
            "versionDescription": version_description,
            "changedFiles": [{"path": f["path"], "action": f.get("action", "modified")} for f in changed_files],
            "deletedFiles": [f["path"] for f in deleted_files],
            "changedCount": len(changed_files),
            "deletedCount": len(deleted_files),
            "isFirstCommit": is_first_commit,
        },
    )


def init_project_workspace(
    template_name: str,
    software_name: str,
    tool_context: Any = None,
) -> Dict[str, Any]:
    print("init_project_workspace----------------------------->>:", {"template_name": template_name, "software_name": software_name})

    state = getattr(tool_context, "state", None) if tool_context is not None else None
    token = _state_get(state, "token")
    if not isinstance(token, str) or not token.strip():
        token = None

    if not isinstance(template_name, str) or not template_name.strip():
        return _resp("error", 400, "template_name is required", None)

    if not isinstance(software_name, str) or not software_name.strip():
        return _resp("error", 400, "software_name is required", None)

    base = _state_get(state, "api_base_url")
    if isinstance(base, str):
        base = base.strip().rstrip("/")
    else:
        base = ""
    if not base:
        return _resp("error", 400, "API base URL is required", None)

    # workspace_dir = tool_context.state.get("workspace_dir")
    workspace_game_dir_base = tool_context.state.get("workspace_game_dir")
    workspace_artifacts_dir = tool_context.state.get("workspace_artifacts_dir")

    # 软件工程目录: workspace_game_dir/software_name
    workspace_game_dir = os.path.join(workspace_game_dir_base, software_name.strip())
    tool_context.state["workspace_game_dir"] = workspace_game_dir_base
    tool_context.state["software_name"] = software_name.strip()

    os.makedirs(workspace_game_dir, exist_ok=True)
    os.makedirs(workspace_artifacts_dir, exist_ok=True)

    headers = {"Accept": "application/json"}
    if isinstance(token, str) and token:
        headers["Authorization"] = f"Bearer {token}"

    def http_get_json(url: str, timeout: int = 10) -> tuple[int, Any, str]:
        # print("http_get_json----------------------------->>:", {"url": url, "headers": headers})
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

    def http_post_json(url: str, data: dict, timeout: int = 10) -> tuple[int, Any, str]:
        post_headers = dict(headers)
        post_headers["Content-Type"] = "application/json"
        body = json.dumps(data).encode("utf-8")
        req = urllib.request.Request(url, headers=post_headers, data=body, method="POST")
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
            resp_data = json.loads(text) if text else None
        except Exception:
            resp_data = None

        return int(status_code or 500), resp_data, text

    tpl_name = template_name.strip()
    tpl_name_encoded = urllib.parse.quote(tpl_name, safe="")
    url = f"{base}/api/v1/software-templates/by-name/{tpl_name_encoded}"
    print("init_project_workspace---------------请求模板信息-------------->>:", {"url": url})
    status_code, payload, text = http_get_json(url, timeout=10)
    if not (200 <= int(status_code) < 300):
        if int(status_code) == 404:
            return _resp("error", 404, f"template not found: {tpl_name}", None)
        return _resp("error", int(status_code), (text or f"HTTP {status_code}").strip(), None)

    if not isinstance(payload, dict):
        return _resp("error", 500, "invalid template response", {"payload": payload})

    found_template = payload

    print("init_project_workspace---------------获得模板信息-------------->>:", {"template": found_template})

    archive_file_id = found_template.get("archiveFileId")
    try:
        archive_file_id_int = int(archive_file_id)
    except Exception:
        return _resp("error", 500, "template archiveFileId is invalid", {"template": found_template})

    download_meta_url = f"{base}/api/v1/files/{archive_file_id_int}/download-template"
    print("init_project_workspace---------------请求模板下载信息-------------->>:", {"url": download_meta_url})
    status_code, meta, text = http_get_json(download_meta_url, timeout=10)
    if not (200 <= int(status_code) < 300):
        return _resp("error", int(status_code), (text or f"HTTP {status_code}").strip(), None)

    print("init_project_workspace---------------获得模板下载信息-------------->>:", {"meta": meta})

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

        # ========== 创建 Software ==========
        project_id = _state_get(state, "project_id")
        if not project_id:
            return _resp("error", 400, "project_id is required in state", None)

        create_software_payload = {
            "name": software_name.strip(),
            "description": f"Created from template: {template_name}",
            "templateId": archive_file_id_int,
            "status": "active"
        }

        create_software_url = f"{base}/api/v1/projects/{project_id}/softwares"
        print("init_project_workspace---------------创建 Software-------------->>:", {"url": create_software_url, "payload": create_software_payload})
        status_code, software_data, text = http_post_json(create_software_url, create_software_payload, timeout=10)
        if not (200 <= int(status_code) < 300):
            return _resp("error", int(status_code), f"create software failed: {text}", None)

        software_id = software_data.get("softwareId")
        if not software_id:
            return _resp("error", 500, "softwareId not in response", {"data": software_data})

        print("init_project_workspace---------------Software 创建成功-------------->>:", {"software": software_data})

        # ========== 创建初始 Manifest ==========
        # 构建初始 manifest 内容（files 为空）
        initial_manifest = {
            "engine": {
                "name": template_name.lower(),
                "version": "unknown"
            },
            "entry": "src/main.ts",
            "files": [],
            "folders": ["src", "assets"]
        }

        # 1. 上传 manifest 文件到文件系统
        manifest_json = json.dumps(initial_manifest, ensure_ascii=False, indent=2)
        manifest_bytes = manifest_json.encode('utf-8')
        import hashlib
        manifest_hash = hashlib.sha256(manifest_bytes).hexdigest()

        # 预上传获取 URL
        preupload_payload = {
            "projectId": project_id,
            "name": f"{software_name.strip()}_manifest.json",
            "fileCategory": "text",
            "fileFormat": "json",
            "sizeBytes": len(manifest_bytes),
            "hash": manifest_hash,
            "contentType": "application/json"
        }

        preupload_url = f"{base}/api/v1/files/preupload"
        print("init_project_workspace---------------预上传 Manifest-------------->>:", {"url": preupload_url})
        status_code, preupload_data, text = http_post_json(preupload_url, preupload_payload, timeout=10)
        if not (200 <= int(status_code) < 300):
            return _resp("error", int(status_code), f"preupload manifest failed: {text}", None)

        upload_url = preupload_data.get("uploadUrl")
        file_id = preupload_data.get("fileId")
        version_id = preupload_data.get("versionId")

        if not upload_url or not file_id or not version_id:
            return _resp("error", 500, "preupload response missing required fields", {"data": preupload_data})

        # 上传文件到 OSS
        upload_headers = {"Content-Type": "application/json"}
        try:
            req = urllib.request.Request(upload_url, data=manifest_bytes, headers=upload_headers, method="PUT")
            with urllib.request.urlopen(req, timeout=30) as resp:
                if resp.status not in (200, 201):
                    return _resp("error", resp.status, "upload manifest to OSS failed", None)
        except Exception as e:
            return _resp("error", 500, f"upload manifest failed: {e}", None)

        print("init_project_workspace---------------Manifest 文件上传成功-------------->>:", {"fileId": file_id, "versionId": version_id})

        # 2. 创建 SoftwareManifest 记录
        create_manifest_payload = {
            "projectId": project_id,
            "softwareId": software_id,
            "manifestFileId": file_id,
            "manifestFileVersionId": version_id,
            "versionDescription": "Initial manifest"
        }

        create_manifest_url = f"{base}/api/v1/software-manifests"
        print("init_project_workspace---------------创建 SoftwareManifest-------------->>:", {"url": create_manifest_url})
        status_code, manifest_data, text = http_post_json(create_manifest_url, create_manifest_payload, timeout=10)
        if not (200 <= int(status_code) < 300):
            return _resp("error", int(status_code), f"create manifest failed: {text}", None)

        print("init_project_workspace---------------SoftwareManifest 创建成功-------------->>:", {"manifest": manifest_data})

        # 保存 manifest 到本地工作区
        manifest_path = os.path.join(workspace_game_dir, "manifest.json")
        with open(manifest_path, "w", encoding="utf-8") as f:
            f.write(manifest_json)

        print("init_project_workspace---------------Manifest 保存到本地-------------->>:", {"path": manifest_path})

        return _resp(
            "success",
            200,
            "ok",
            {
                "template": found_template,
                "software": software_data,
                "manifest": manifest_data,
                "archive_file_id": archive_file_id_int,
                "download_url": download_url,
                "zip_path": local_zip_path,
                "workspace_game_dir": workspace_game_dir,
                "manifest_path": manifest_path,
                "extracted_files": extracted_files,
                "moved_entries": moved,
            },
        )
    except Exception as e:
        return _resp("error", 500, str(e), {"zip_path": local_zip_path, "extract_dir": extract_dir})


def check_workspace_status(
    tool_context: Any = None,
) -> Dict[str, Any]:
    state = getattr(tool_context, "state", None) if tool_context is not None else None

    # 1. Check Project Info
    project_id = _state_get(state, "project_id")
    has_project_info = bool(project_id and str(project_id).strip() != "0")

    # 2. Check Local Workspace
    workspace_dir = _state_get(state, "workspace_dir")
    has_workspace = bool(workspace_dir and os.path.isdir(workspace_dir))

    # 3. Check Local Software Engineering
    workspace_game_dir = _state_get(state, "workspace_game_dir")
    has_software = False
    software_name = None

    if has_workspace and workspace_game_dir and os.path.isdir(workspace_game_dir):
        try:
            # Scan for subdirectories in game dir
            subdirs = [d for d in os.listdir(workspace_game_dir) if os.path.isdir(os.path.join(workspace_game_dir, d))]
            # Filter out hidden dirs
            subdirs = [d for d in subdirs if not d.startswith(".")]
            
            # Try to find a directory with manifest.json, otherwise take the first one
            found_candidate = None
            for d in subdirs:
                if os.path.exists(os.path.join(workspace_game_dir, d, "manifest.json")):
                    software_name = d
                    has_software = True
                    break
                if not found_candidate:
                    found_candidate = d
            
            if not has_software and found_candidate:
                software_name = found_candidate
                has_software = True

            # 保存 software_name 到 tool_context
            if software_name and tool_context is not None:
                tool_context.state["software_name"] = software_name

        except Exception:
            pass

    if has_project_info and has_workspace and has_software:
        return _resp(
            "success",
            200,
            "workspace status check passed",
            {
                "project_id": project_id,
                "software_name": software_name,
                "workspace_dir": workspace_dir,
                "workspace_game_dir": workspace_game_dir,
                "workspace_artifacts_dir": _state_get(state, "workspace_artifacts_dir"),
                "workspace_build_dir": _state_get(state, "workspace_build_dir"),
                "workspace_logs_dir": _state_get(state, "workspace_logs_dir"),
            }
        )
    
    # Construct error detail
    missing = []
    if not has_project_info:
        missing.append("Project Info (user:project_id)")
    if not has_workspace:
        missing.append("Local Workspace (user:workspace_dir)")
    if not has_software:
        missing.append("Local Software Engineering (subdirectory in game dir)")

    return _resp(
        "error",
        404,
        f"Workspace status check failed. Missing: {', '.join(missing)}",
        {
            "has_project_info": has_project_info,
            "has_workspace": has_workspace,
            "has_software": has_software,
            "project_id": project_id,
            "workspace_dir": workspace_dir,
            "workspace_game_dir": workspace_game_dir,
        }
    )


def build_project_software(
    software_name: str,
    build_command: str = "run build",
    build_output_subdir: str = "dist",
    tool_context: Any = None,
) -> Dict[str, Any]:
    """
    构建软件工程，将构建产物复制到构建目录。
    
    Args:
        software_name: 软件名称，对应 workspace_game_dir 下的子目录。
        build_command: npm 构建命令，默认为 "run build"。
        build_output_subdir: 构建输出子目录，默认为 "dist"。
        tool_context: 工具上下文，包含用户状态。
        
    Returns:
        响应字典，包含构建结果。
    """
    from .commands import run_npm
    
    state = getattr(tool_context, "state", None) if tool_context is not None else None
    if state is None:
        return _resp("error", 400, "tool_context.state is required", None)
    
    workspace_game_dir = _state_get(state, "workspace_game_dir")
    workspace_build_dir = _state_get(state, "workspace_build_dir")
    
    if not workspace_game_dir or not isinstance(workspace_game_dir, str):
        return _resp("error", 400, "workspace_game_dir is required", None)
    if not workspace_build_dir or not isinstance(workspace_build_dir, str):
        return _resp("error", 400, "workspace_build_dir is required", None)
    
    software_name = software_name.strip()
    if not software_name:
        return _resp("error", 400, "software_name is required", None)
    
    source_dir = os.path.join(workspace_game_dir, software_name)
    build_output_dir = os.path.join(workspace_build_dir, software_name)
    
    if not os.path.isdir(source_dir):
        return _resp("error", 404, f"Source directory not found: {source_dir}", None)
    
    # 确保构建输出目录存在
    os.makedirs(build_output_dir, exist_ok=True)
    
    # 运行构建命令
    npm_result = run_npm(build_command, tool_context)
    if npm_result.get("status") == "error":
        return _resp(
            "error",
            500,
            f"Build failed: {npm_result.get('message', 'Unknown error')}",
            {
                "stdout": npm_result.get("stdout"),
                "stderr": npm_result.get("stderr"),
                "summary": npm_result.get("summary"),
                "returncode": npm_result.get("returncode"),
            }
        )
    
    # 查找构建输出目录（默认为 source_dir/dist）
    potential_output_dirs = [
        os.path.join(source_dir, build_output_subdir),
        os.path.join(source_dir, "dist"),
        os.path.join(source_dir, "build"),
        os.path.join(source_dir, "out"),
    ]
    
    build_output_source = None
    for dir_path in potential_output_dirs:
        if os.path.isdir(dir_path):
            build_output_source = dir_path
            break
    
    if build_output_source is None:
        # 没有找到构建输出目录，可能构建命令没有生成输出目录
        return _resp(
            "success",
            200,
            "Build completed but no output directory found. Build artifacts may be in source directory.",
            {
                "build_command": build_command,
                "source_dir": source_dir,
                "build_output_dir": build_output_dir,
                "npm_result": npm_result,
            }
        )
    
    # 复制构建产物到构建输出目录
    try:
        # 清空目标目录
        if os.path.exists(build_output_dir):
            shutil.rmtree(build_output_dir)
        os.makedirs(build_output_dir, exist_ok=True)
        
        # 复制文件
        shutil.copytree(build_output_source, build_output_dir, dirs_exist_ok=True)
    except Exception as e:
        return _resp(
            "error",
            500,
            f"Failed to copy build artifacts: {str(e)}",
            {
                "build_output_source": build_output_source,
                "build_output_dir": build_output_dir,
                "npm_result": npm_result,
            }
        )
    
    return _resp(
        "success",
        200,
        "Build completed successfully",
        {
            "software_name": software_name,
            "build_command": build_command,
            "source_dir": source_dir,
            "build_output_dir": build_output_dir,
            "build_output_source": build_output_source,
            "npm_result": npm_result,
        }
    )
