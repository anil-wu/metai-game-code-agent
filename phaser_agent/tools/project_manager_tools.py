import hashlib
import json
import os
import shutil
import time
import urllib.error
import urllib.parse
import urllib.request
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
    if state is None:
        return False
    try:
        state[key] = value
        return True
    except Exception:
        pass
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


def _ssl_context_for_url(url: str, state: Any = None) -> Any:
    import ssl
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

    if state is not None:
        tls_insecure_state = _state_get(state, "tls_insecure")
        if _truthy(tls_insecure_state):
            return ssl._create_unverified_context()
        tls_verify_state = _state_get(state, "tls_verify")
        if tls_verify_state is not None and not _truthy(tls_verify_state):
            return ssl._create_unverified_context()

    if hostname in {"localhost", "127.0.0.1", "::1"} and not _truthy(force_verify_env):
        if state is None or _state_get(state, "tls_verify") is None:
            return ssl._create_unverified_context()

    ca_bundle = ""
    if state is not None:
        ca_bundle = _state_get(state, "ca_bundle") or ""
    if not isinstance(ca_bundle, str) or not ca_bundle.strip():
        ca_bundle = (os.getenv("SPARKPLAY_CA_BUNDLE") or os.getenv("REQUESTS_CA_BUNDLE") or "").strip()
    if ca_bundle:
        try:
            return ssl.create_default_context(cafile=ca_bundle)
        except Exception:
            return ssl.create_default_context()
    return ssl.create_default_context()


def _resp(status: str, status_code: int, message: str, data: Any = None) -> Dict[str, Any]:
    return {"status": status, "status_code": status_code, "message": message, "data": data}


def _http_get_json(url: str, headers: Dict[str, str], state: Any, timeout: int = 10) -> tuple:
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


def _http_post_json(url: str, headers: Dict[str, str], body: Dict[str, Any], state: Any, timeout: int = 10) -> tuple:
    post_headers = dict(headers)
    post_headers["Content-Type"] = "application/json"
    body_bytes = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, headers=post_headers, data=body_bytes, method="POST")
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


def _get_base_headers(token: str | None) -> Dict[str, str]:
    headers = {"Accept": "application/json"}
    if isinstance(token, str) and token.strip():
        headers["Authorization"] = f"Bearer {token.strip()}"
    return headers


def _calculate_file_hash(file_path: str) -> str:
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def _get_file_category_and_format(file_path: str) -> tuple:
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


def _get_content_type_by_format(file_format: str) -> str:
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


def get_project_info(tool_context: Any = None) -> Dict[str, Any]:
    state = getattr(tool_context, "state", None) if tool_context is not None else None
    token = _state_get(state, "token")
    project_id = _state_get(state, "project_id")
    base = _state_get(state, "api_base_url")

    print(f"get_project_info----->>: project_id={project_id}, base={base}")
    if not project_id or str(project_id).strip() in ("", "0"):
        return _resp("error", 400, "project_id is required", None)

    if isinstance(base, str):
        base = base.strip().rstrip("/")
    else:
        base = ""
    if not base:
        return _resp("error", 400, "api_base_url is required", None)

    pid_str = str(project_id).strip()
    headers = _get_base_headers(token)

    project_url = f"{base}/api/v1/projects/{pid_str}"
    status_code, project_data, text = _http_get_json(project_url, headers, state)
    if not (200 <= status_code < 300):
        return _resp("error", status_code, f"获取项目信息失败: {text}", None)

    softwares_url = f"{base}/api/v1/projects/{pid_str}/softwares"
    status_code, softwares_data, text = _http_get_json(softwares_url, headers, state)
    softwares_list = []
    if 200 <= status_code < 300 and isinstance(softwares_data, dict):
        softwares_list = softwares_data.get("list", [])

    return _resp("success", 200, "获取项目信息成功", {
        "project": project_data,
        "softwares": softwares_list,
        "software_count": len(softwares_list),
    })


def create_project(
    project_name: str,
    description: str = "",
    tool_context: Any = None,
) -> Dict[str, Any]:
    state = getattr(tool_context, "state", None) if tool_context is not None else None
    token = _state_get(state, "token")
    user_id = _state_get(state, "user_id")
    base = _state_get(state, "api_base_url")
    print(f"create_project----->>: project_name={project_name}, description={description}, base={base}")
    if not isinstance(project_name, str) or not project_name.strip():
        return _resp("error", 400, "project_name is required", None)

    if not user_id:
        return _resp("error", 400, "user_id is required", None)

    if isinstance(base, str):
        base = base.strip().rstrip("/")
    else:
        base = ""
    if not base:
        return _resp("error", 400, "api_base_url is required", None)

    try:
        user_id_int = int(user_id)
    except (ValueError, TypeError):
        return _resp("error", 400, "user_id is invalid", None)

    headers = _get_base_headers(token)
    payload = {
        "userId": user_id_int,
        "name": project_name.strip(),
        "description": description.strip() if isinstance(description, str) else "",
    }

    url = f"{base}/api/v1/projects"
    status_code, project_data, text = _http_post_json(url, headers, payload, state)
    if not (200 <= status_code < 300):
        return _resp("error", status_code, f"创建项目失败: {text}", None)

    new_project_id = project_data.get("id") if isinstance(project_data, dict) else None
    if not new_project_id:
        return _resp("error", 500, "创建项目失败: 未返回项目ID", None)

    _state_set(state, "project_id", new_project_id)

    workspace_root = os.path.abspath(str(WORKSPACE_ROOT))
    workspace_dir = os.path.abspath(os.path.join(workspace_root, str(user_id_int), str(new_project_id)))

    try:
        os.makedirs(workspace_dir, exist_ok=True)
        workspace_game_dir = os.path.join(workspace_dir, DIR_GAME)
        workspace_artifacts_dir = os.path.join(workspace_dir, DIR_ARTIFACTS)
        workspace_build_dir = os.path.join(workspace_dir, DIR_BUILD)
        workspace_logs_dir = os.path.join(workspace_dir, DIR_LOGS)

        os.makedirs(workspace_game_dir, exist_ok=True)
        os.makedirs(workspace_artifacts_dir, exist_ok=True)
        os.makedirs(workspace_build_dir, exist_ok=True)
        os.makedirs(workspace_logs_dir, exist_ok=True)

        _state_set(state, "workspace_dir", workspace_dir)
        _state_set(state, "workspace_game_dir", workspace_game_dir)
        _state_set(state, "workspace_artifacts_dir", workspace_artifacts_dir)
        _state_set(state, "workspace_build_dir", workspace_build_dir)
        _state_set(state, "workspace_logs_dir", workspace_logs_dir)
    except Exception as e:
        return _resp("error", 500, f"创建工作空间失败: {e}", None)

    return _resp("success", 200, "项目创建成功", {
        "project_id": new_project_id,
        "project": project_data,
        "workspace": {
            "workspace_dir": workspace_dir,
            "workspace_game_dir": workspace_game_dir,
            "workspace_artifacts_dir": workspace_artifacts_dir,
            "workspace_build_dir": workspace_build_dir,
            "workspace_logs_dir": workspace_logs_dir,
        },
    })


def create_workspaces(
    project_id: int,
    tool_context: Any = None,
) -> Dict[str, Any]:
    state = getattr(tool_context, "state", None) if tool_context is not None else None
    user_id = _state_get(state, "user_id")

    print(f"create_workspaces----->>: project_id={project_id}, user_id={user_id}")

    if not user_id:
        return _resp("error", 400, "user_id is required", None)

    if not project_id:
        return _resp("error", 400, "project_id is required", None)

    try:
        user_id_int = int(user_id)
        project_id_int = int(project_id)
    except (ValueError, TypeError):
        return _resp("error", 400, "user_id or project_id is invalid", None)

    workspace_root = os.path.abspath(str(WORKSPACE_ROOT))
    workspace_dir = os.path.abspath(os.path.join(workspace_root, str(user_id_int), str(project_id_int)))

    if os.path.exists(workspace_dir):
        return _resp("success", 200, "工作空间已存在", {
            "project_id": project_id_int,
            "workspace": {
                "workspace_dir": workspace_dir,
                "workspace_game_dir": os.path.join(workspace_dir, DIR_GAME),
                "workspace_artifacts_dir": os.path.join(workspace_dir, DIR_ARTIFACTS),
                "workspace_build_dir": os.path.join(workspace_dir, DIR_BUILD),
                "workspace_logs_dir": os.path.join(workspace_dir, DIR_LOGS),
            },
            "created": False,
        })

    try:
        os.makedirs(workspace_dir, exist_ok=True)
        workspace_game_dir = os.path.join(workspace_dir, DIR_GAME)
        workspace_artifacts_dir = os.path.join(workspace_dir, DIR_ARTIFACTS)
        workspace_build_dir = os.path.join(workspace_dir, DIR_BUILD)
        workspace_logs_dir = os.path.join(workspace_dir, DIR_LOGS)

        os.makedirs(workspace_game_dir, exist_ok=True)
        os.makedirs(workspace_artifacts_dir, exist_ok=True)
        os.makedirs(workspace_build_dir, exist_ok=True)
        os.makedirs(workspace_logs_dir, exist_ok=True)

        _state_set(state, "workspace_dir", workspace_dir)
        _state_set(state, "workspace_game_dir", workspace_game_dir)
        _state_set(state, "workspace_artifacts_dir", workspace_artifacts_dir)
        _state_set(state, "workspace_build_dir", workspace_build_dir)
        _state_set(state, "workspace_logs_dir", workspace_logs_dir)
    except Exception as e:
        return _resp("error", 500, f"创建工作空间失败: {e}", None)

    return _resp("success", 200, "工作空间创建成功", {
        "project_id": project_id_int,
        "workspace": {
            "workspace_dir": workspace_dir,
            "workspace_game_dir": workspace_game_dir,
            "workspace_artifacts_dir": workspace_artifacts_dir,
            "workspace_build_dir": workspace_build_dir,
            "workspace_logs_dir": workspace_logs_dir,
        },
        "created": True,
    })


def check_workspaces(
    project_id: int,
    tool_context: Any = None,
) -> Dict[str, Any]:
    state = getattr(tool_context, "state", None) if tool_context is not None else None
    user_id = _state_get(state, "user_id")

    print(f"check_workspaces----->>: project_id={project_id}, user_id={user_id}")

    if not user_id:
        return _resp("error", 400, "user_id is required", None)

    if not project_id:
        return _resp("error", 400, "project_id is required", None)

    try:
        user_id_int = int(user_id)
        project_id_int = int(project_id)
    except (ValueError, TypeError):
        return _resp("error", 400, "user_id or project_id is invalid", None)

    workspace_root = os.path.abspath(str(WORKSPACE_ROOT))
    workspace_dir = os.path.abspath(os.path.join(workspace_root, str(user_id_int), str(project_id_int)))

    dirs_to_check = {
        "workspace_dir": workspace_dir,
        "workspace_game_dir": os.path.join(workspace_dir, DIR_GAME),
        "workspace_artifacts_dir": os.path.join(workspace_dir, DIR_ARTIFACTS),
        "workspace_build_dir": os.path.join(workspace_dir, DIR_BUILD),
        "workspace_logs_dir": os.path.join(workspace_dir, DIR_LOGS),
    }

    check_results = {}
    missing_dirs = []
    all_exist = True

    for dir_name, dir_path in dirs_to_check.items():
        exists = os.path.isdir(dir_path)
        check_results[dir_name] = {
            "path": dir_path,
            "exists": exists,
        }
        if not exists:
            missing_dirs.append(dir_name)
            all_exist = False

    overall_status = "complete" if all_exist else "incomplete"

    return _resp("success", 200, "工作空间检查完成", {
        "project_id": project_id_int,
        "workspace_dir": workspace_dir,
        "overall_status": overall_status,
        "all_dirs_exist": all_exist,
        "missing_dirs": missing_dirs,
        "check_results": check_results,
    })


def get_local_project_info(tool_context: Any = None) -> Dict[str, Any]:
    state = getattr(tool_context, "state", None) if tool_context is not None else None
    workspace_dir = _state_get(state, "workspace_dir")
    workspace_game_dir = _state_get(state, "workspace_game_dir")
    print(f"get_local_project_info----->>: workspace_dir={workspace_dir}, workspace_game_dir={workspace_game_dir}")
    if not workspace_dir:
        return _resp("error", 400, "workspace_dir is required", None)

    if not os.path.exists(workspace_dir):
        return _resp("error", 404, "工作空间不存在 ", None)

    workspace_root = os.path.abspath(str(WORKSPACE_ROOT))

    def _relative_path(path: str) -> str:
        if not path:
            return path
        abs_path = os.path.abspath(path)
        if abs_path.startswith(workspace_root):
            return os.path.relpath(abs_path, workspace_root)
        return path

    software_projects = []

    if workspace_game_dir and os.path.isdir(workspace_game_dir):
        for software_name in os.listdir(workspace_game_dir):
            software_path = os.path.join(workspace_game_dir, software_name)
            if not os.path.isdir(software_path):
                continue

            manifest_path = os.path.join(software_path, "manifest.json")
            has_manifest = os.path.exists(manifest_path)
            manifest_content = None

            if has_manifest:
                try:
                    with open(manifest_path, "r", encoding="utf-8") as f:
                        manifest_content = json.load(f)
                except Exception:
                    manifest_content = None

            files_count = 0
            folders = []
            if manifest_content and isinstance(manifest_content, dict):
                files_list = manifest_content.get("files", [])
                files_count = len(files_list) if isinstance(files_list, list) else 0
                folders = manifest_content.get("folders", [])

            software_projects.append({
                "name": software_name,
                "path": _relative_path(software_path),
                "has_manifest": has_manifest,
                "manifest": manifest_content,
                "files_count": files_count,
                "folders": folders,
            })

    return _resp("success", 200, "获取本地工程信息成功", {
        "workspace_dir": _relative_path(workspace_dir),
        "workspace_exists": True,
        "software_projects": software_projects,
        "software_count": len(software_projects),
    })


def create_software(
    software_name: str,
    template_name: str = "2d_game_client_phaser",
    tool_context: Any = None,
) -> Dict[str, Any]:
    state = getattr(tool_context, "state", None) if tool_context is not None else None
    token = _state_get(state, "token")
    project_id = _state_get(state, "project_id")
    base = _state_get(state, "api_base_url")
    workspace_game_dir_base = _state_get(state, "workspace_game_dir")
    workspace_artifacts_dir = _state_get(state, "workspace_artifacts_dir")

    print(f"create_software----->>: software_name={software_name}, template_name={template_name}, project_id={project_id}, base={base}, workspace_game_dir_base={workspace_game_dir_base}, workspace_artifacts_dir={workspace_artifacts_dir}")
    if not isinstance(software_name, str) or not software_name.strip():
        return _resp("error", 400, "software_name is required", None)

    if not project_id:
        return _resp("error", 400, "project_id is required", None)

    if isinstance(base, str):
        base = base.strip().rstrip("/")
    else:
        base = ""
    if not base:
        return _resp("error", 400, "api_base_url is required", None)

    software_name = software_name.strip()
    template_name = template_name.strip() if isinstance(template_name, str) else "phaser-blank"

    workspace_game_dir = os.path.join(workspace_game_dir_base, software_name)
    if os.path.exists(workspace_game_dir):
        return _resp("error", 409, f"软件工程已存在: {software_name}", None)

    os.makedirs(workspace_game_dir, exist_ok=True)

    headers = _get_base_headers(token)

    tpl_name_encoded = urllib.parse.quote(template_name, safe="")
    tpl_url = f"{base}/api/v1/software-templates/by-name/{tpl_name_encoded}"
    status_code, template_data, text = _http_get_json(tpl_url, headers, state)
    if not (200 <= status_code < 300):
        if status_code == 404:
            return _resp("error", 404, f"模板不存在: {template_name}", None)
        return _resp("error", status_code, f"获取模板失败: {text}", None)

    archive_file_id = template_data.get("archiveFileId") if isinstance(template_data, dict) else None
    if not archive_file_id:
        return _resp("error", 500, "模板缺少 archiveFileId", None)

    download_url = f"{base}/api/v1/files/{archive_file_id}/content"

    try:
        parsed_api = urllib.parse.urlparse(base)
        parsed_dl = urllib.parse.urlparse(download_url)
        same_host = (parsed_api.hostname or "").lower() == (parsed_dl.hostname or "").lower()
    except Exception:
        same_host = False

    dl_headers = {"User-Agent": "SparkPlay-Agent"}
    if same_host and isinstance(token, str) and token.strip():
        dl_headers["Authorization"] = f"Bearer {token.strip()}"

    zip_name = f"template_{archive_file_id}.zip"
    local_zip_path = os.path.join(workspace_artifacts_dir, zip_name)

    try:
        req = urllib.request.Request(download_url, headers=dl_headers, method="GET")
        with urllib.request.urlopen(req, timeout=60, context=_ssl_context_for_url(download_url, state)) as resp:
            with open(local_zip_path, "wb") as f:
                shutil.copyfileobj(resp, f)
    except Exception as e:
        return _resp("error", 500, f"下载模板失败: {e}", None)

    import zipfile
    if not zipfile.is_zipfile(local_zip_path):
        return _resp("error", 400, "模板归档不是有效的 zip 文件", None)

    extract_dir = os.path.join(workspace_artifacts_dir, f".extract_{archive_file_id}")
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

        create_software_payload = {
            "name": software_name,
            "description": f"Created from template: {template_name}",
            "templateId": archive_file_id,
            "status": "active",
        }

        create_software_url = f"{base}/api/v1/projects/{project_id}/softwares"
        status_code, software_data, text = _http_post_json(create_software_url, headers, create_software_payload, state)
        if not (200 <= status_code < 300):
            return _resp("error", status_code, f"创建软件工程失败: {text}", None)

        software_id = software_data.get("softwareId") if isinstance(software_data, dict) else None
        if not software_id:
            return _resp("error", 500, "创建软件工程失败: 未返回 softwareId", None)

        initial_manifest = {
            "engine": {"name": template_name.lower(), "version": "unknown"},
            "entry": "src/main.ts",
            "files": [],
            "folders": ["src", "assets"],
        }

        manifest_json = json.dumps(initial_manifest, ensure_ascii=False, indent=2)
        manifest_bytes = manifest_json.encode("utf-8")
        manifest_hash = hashlib.sha256(manifest_bytes).hexdigest()

        preupload_payload = {
            "projectId": project_id,
            "name": f"{software_name}_manifest.json",
            "fileCategory": "text",
            "fileFormat": "json",
            "sizeBytes": len(manifest_bytes),
            "hash": manifest_hash,
            "contentType": "application/json",
        }

        preupload_url = f"{base}/api/v1/files/preupload"
        status_code, preupload_data, text = _http_post_json(preupload_url, headers, preupload_payload, state)
        if not (200 <= status_code < 300):
            return _resp("error", status_code, f"预上传 manifest 失败: {text}", None)

        upload_url = preupload_data.get("uploadUrl")
        file_id = preupload_data.get("fileId")
        version_id = preupload_data.get("versionId")

        if not upload_url or not file_id or not version_id:
            return _resp("error", 500, "预上传响应缺少必要字段", None)

        upload_headers = {"Content-Type": "application/json"}
        try:
            req = urllib.request.Request(upload_url, data=manifest_bytes, headers=upload_headers, method="PUT")
            with urllib.request.urlopen(req, timeout=30, context=_ssl_context_for_url(upload_url, state)) as resp:
                if resp.status not in (200, 201):
                    return _resp("error", resp.status, "上传 manifest 到 OSS 失败", None)
        except Exception as e:
            return _resp("error", 500, f"上传 manifest 失败: {e}", None)

        create_manifest_payload = {
            "projectId": project_id,
            "softwareId": software_id,
            "manifestFileId": file_id,
            "manifestFileVersionId": version_id,
            "versionNumber": 1,
            "versionDescription": "Initial manifest",
        }

        create_manifest_url = f"{base}/api/v1/software-manifests"
        status_code, manifest_data, text = _http_post_json(create_manifest_url, headers, create_manifest_payload, state)
        if not (200 <= status_code < 300):
            return _resp("error", status_code, f"创建 manifest 记录失败: {text}", None)

        manifest_id = manifest_data.get("manifestId") if isinstance(manifest_data, dict) else None

        _state_set(state, "software_id", software_id)
        _state_set(state, "software_manifest_id", manifest_id)
        _state_set(state, "software_name", software_name)

        manifest_path = os.path.join(workspace_game_dir, "manifest.json")
        with open(manifest_path, "w", encoding="utf-8") as f:
            f.write(manifest_json)

        return _resp("success", 200, "工程初始化成功", {
            "software_name": software_name,
            "software_dir": workspace_game_dir,
            "template_name": template_name,
            "files_created": extracted_files,
            "software_id": software_id,
            "manifest_id": manifest_id,
            "manifest": initial_manifest,
        })

    except Exception as e:
        return _resp("error", 500, f"初始化工程失败: {e}", None)


def pull_project(
    software_name: str,
    version_number: int | None = None,
    tool_context: Any = None,
) -> Dict[str, Any]:
    state = getattr(tool_context, "state", None) if tool_context is not None else None
    token = _state_get(state, "token")
    project_id = _state_get(state, "project_id")
    base = _state_get(state, "api_base_url")
    workspace_game_dir_base = _state_get(state, "workspace_game_dir")
    
    print(f"pull_project----->>: software_name={software_name}, version_number={version_number}, project_id={project_id}, base={base}, workspace_game_dir_base={workspace_game_dir_base}")
    if not isinstance(software_name, str) or not software_name.strip():
        return _resp("error", 400, "software_name is required", None)

    if not project_id:
        return _resp("error", 400, "project_id is required", None)

    if isinstance(base, str):
        base = base.strip().rstrip("/")
    else:
        base = ""
    if not base:
        return _resp("error", 400, "api_base_url is required", None)
    
    if not workspace_game_dir_base:
        return _resp("error", 400, "workspace_game_dir is required, please create local workspace first using create_workspace", None)
    
    software_name = software_name.strip()
    software_dir = os.path.join(workspace_game_dir_base, software_name)

    if not os.path.exists(software_dir):
        os.makedirs(software_dir, exist_ok=True)

    headers = _get_base_headers(token)

    softwares_url = f"{base}/api/v1/projects/{project_id}/softwares"
    print(f"softwares_url={softwares_url}")
    status_code, softwares_data, text = _http_get_json(softwares_url, headers, state)
    if not (200 <= status_code < 300):
        return _resp("error", status_code, f"获取软件工程列表失败: {text}", None)

    software_id = None
    softwares_list = softwares_data.get("list", []) if isinstance(softwares_data, dict) else []
    for sw in softwares_list:
        if sw.get("name") == software_name:
            software_id = sw.get("id")
            break

    if not software_id:
        return _resp("error", 404, f"软件工程不存在: {software_name}", None)

    manifests_url = f"{base}/api/v1/projects/{project_id}/software_manifests?software_ids={software_id}"
    print(f"manifests_url={manifests_url}")
    status_code, manifests_data, text = _http_get_json(manifests_url, headers, state)
    if not (200 <= status_code < 300):
        return _resp("error", status_code, f"获取 manifest 列表失败: {text}", None)

    manifest_item = None
    manifests_list = manifests_data.get("list", []) if isinstance(manifests_data, dict) else []
    for item in manifests_list:
        if item.get("softwareId") == software_id and item.get("hasRecord"):
            if version_number is None or item.get("versionNumber") == version_number:
                manifest_item = item
                break

    if not manifest_item:
        return _resp("error", 404, "远程无版本记录", None)

    manifest_file_id = manifest_item.get("manifestFileId")
    pulled_version = manifest_item.get("versionNumber")

    content_url = f"{base}/api/v1/files/{manifest_file_id}/content"
    print(f"content_url={content_url}")
    req = urllib.request.Request(content_url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=30, context=_ssl_context_for_url(content_url, state)) as resp:
            manifest_content = resp.read().decode("utf-8")
            remote_manifest = json.loads(manifest_content)
    except Exception as e:
        return _resp("error", 500, f"获取 manifest 内容失败: {e}", None)

    local_manifest_path = os.path.join(software_dir, "manifest.json")
    local_manifest = None
    if os.path.exists(local_manifest_path):
        try:
            with open(local_manifest_path, "r", encoding="utf-8") as f:
                local_manifest = json.load(f)
        except Exception:
            local_manifest = None

    local_files_map = {}
    if local_manifest and isinstance(local_manifest, dict):
        for f in local_manifest.get("files", []):
            if isinstance(f, dict) and "path" in f:
                local_files_map[f["path"]] = f

    remote_files_map = {}
    if remote_manifest and isinstance(remote_manifest, dict):
        for f in remote_manifest.get("files", []):
            if isinstance(f, dict) and "path" in f:
                remote_files_map[f["path"]] = f

    files_updated = 0
    files_added = 0
    files_unchanged = 0
    files_deleted = 0

    for rel_path, remote_file in remote_files_map.items():
        local_path = os.path.join(software_dir, rel_path)
        remote_hash = remote_file.get("hash", "")
        remote_file_id = remote_file.get("fileId")
        print(f"remote_file_id={remote_file_id}")
        print(f"local_path={local_path}")
        # print(f"remote_hash={remote_hash}")

        need_download = False
        if not os.path.exists(local_path):
            need_download = True
            files_added += 1
        else:
            local_hash = _calculate_file_hash(local_path)
            if local_hash != remote_hash:
                need_download = True
                files_updated += 1
            else:
                files_unchanged += 1

        if need_download and remote_file_id:
            file_content_url = f"{base}/api/v1/files/{remote_file_id}/content"
            req = urllib.request.Request(file_content_url, headers=headers, method="GET")
            try:
                with urllib.request.urlopen(req, timeout=60, context=_ssl_context_for_url(file_content_url, state)) as resp:
                    file_content = resp.read()
                os.makedirs(os.path.dirname(local_path), exist_ok=True)
                with open(local_path, "wb") as f:
                    f.write(file_content)
            except Exception as e:
                pass

    for rel_path in local_files_map:
        if rel_path not in remote_files_map:
            local_path = os.path.join(software_dir, rel_path)
            if os.path.exists(local_path):
                try:
                    os.unlink(local_path)
                    files_deleted += 1
                except Exception:
                    pass

    with open(local_manifest_path, "w", encoding="utf-8") as f:
        json.dump(remote_manifest, f, ensure_ascii=False, indent=2)

    _state_set(state, "software_id", software_id)
    _state_set(state, "software_manifest_id", manifest_item.get("manifestId"))
    _state_set(state, "software_name", software_name)

    return _resp("success", 200, "拉取成功", {
        "software_name": software_name,
        "pulled_version": pulled_version,
        "files_updated": files_updated,
        "files_added": files_added,
        "files_unchanged": files_unchanged,
        "files_deleted": files_deleted,
        "manifest_updated": True,
    })


def push_project(
    software_name: str,
    version_description: str = "",
    tool_context: Any = None,
) -> Dict[str, Any]:
    
    state = getattr(tool_context, "state", None) if tool_context is not None else None
    token = _state_get(state, "token")
    project_id = _state_get(state, "project_id")
    base = _state_get(state, "api_base_url")
    workspace_game_dir_base = _state_get(state, "workspace_game_dir")

    print(f"push_project----->>: state type={type(state)}, state={state}")
    print(f"push_project----->>: software_name={software_name}, version_description={version_description}, project_id={project_id}, base={base}")
    print(f"push_project----->>: workspace_game_dir_base={workspace_game_dir_base}")

    if not isinstance(software_name, str) or not software_name.strip():
        return _resp("error", 400, "software_name is required", None)

    if not project_id:
        return _resp("error", 400, "project_id is required", None)

    if isinstance(base, str):
        base = base.strip().rstrip("/")
    else:
        base = ""
    if not base:
        return _resp("error", 400, "api_base_url is required", None)

    software_name = software_name.strip()
    software_dir = os.path.join(workspace_game_dir_base, software_name)
    if not os.path.exists(software_dir):
        return _resp("error", 404, f"本地工程不存在: {software_name}", None)

    headers = _get_base_headers(token)

    softwares_url = f"{base}/api/v1/projects/{project_id}/softwares"
    status_code, softwares_data, text = _http_get_json(softwares_url, headers, state)
    if not (200 <= status_code < 300):
        return _resp("error", status_code, f"获取软件工程列表失败: {text}", None)

    software_id = None
    softwares_list = softwares_data.get("list", []) if isinstance(softwares_data, dict) else []
    for sw in softwares_list:
        if sw.get("name") == software_name:
            software_id = sw.get("id")
            break

    if not software_id:
        return _resp("error", 404, f"软件工程不存在: {software_name}", None)

    manifests_url = f"{base}/api/v1/projects/{project_id}/software_manifests?software_ids={software_id}"
    status_code, manifests_data, text = _http_get_json(manifests_url, headers, state)

    manifest_item = None
    latest_version_number = 0
    if 200 <= status_code < 300:
        manifests_list = manifests_data.get("list", []) if isinstance(manifests_data, dict) else []
        for item in manifests_list:
            if item.get("softwareId") == software_id and item.get("hasRecord"):
                manifest_item = item
                if item.get("versionNumber"):
                    latest_version_number = max(latest_version_number, int(item.get("versionNumber")))
                break

    is_first_push = manifest_item is None
    new_version_number = latest_version_number + 1

    if is_first_push:
        current_manifest = {
            "engine": {"name": "phaser", "version": "3.60.0"},
            "entry": "src/main.ts",
            "files": [],
            "folders": ["src", "assets"],
        }
    else:
        manifest_file_id = manifest_item.get("manifestFileId")
        content_url = f"{base}/api/v1/files/{manifest_file_id}/content"
        req = urllib.request.Request(content_url, headers=headers, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=30, context=_ssl_context_for_url(content_url, state)) as resp:
                manifest_content = resp.read().decode("utf-8")
                current_manifest = json.loads(manifest_content)
        except Exception as e:
            return _resp("error", 500, f"获取 manifest 内容失败: {e}", None)

    EXCLUDE_DIRS = {"node_modules", ".git", "__pycache__", ".cache", "dist", "build"}
    EXCLUDE_FILES = {".DS_Store", "Thumbs.db", "manifest.json"}

    remote_files_map = {}
    if current_manifest and isinstance(current_manifest, dict):
        for f in current_manifest.get("files", []):
            if isinstance(f, dict) and "path" in f:
                remote_files_map[f["path"]] = f

    changed_files = []
    unchanged_files = []

    for root, dirs, files in os.walk(software_dir):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]

        for filename in files:
            if filename in EXCLUDE_FILES:
                continue

            file_path = os.path.join(root, filename)
            rel_path = os.path.relpath(file_path, software_dir).replace("\\", "/")

            file_hash = _calculate_file_hash(file_path)
            file_size = os.path.getsize(file_path)

            if rel_path in remote_files_map:
                if remote_files_map[rel_path].get("hash") != file_hash:
                    changed_files.append({
                        "path": rel_path,
                        "local_path": file_path,
                        "hash": file_hash,
                        "size": file_size,
                        "action": "modified",
                    })
                else:
                    unchanged_files.append(remote_files_map[rel_path])
            else:
                changed_files.append({
                    "path": rel_path,
                    "local_path": file_path,
                    "hash": file_hash,
                    "size": file_size,
                    "action": "added",
                })

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
        return _resp("success", 200, "无变更需要推送", {
            "softwareId": software_id,
            "softwareName": software_name,
            "changedCount": 0,
            "deletedCount": 0,
        })

    uploaded_files = []
    preupload_url = f"{base}/api/v1/files/preupload"

    for file_info in changed_files:
        file_path = file_info["local_path"]
        rel_path = file_info["path"]
        file_hash = file_info["hash"]
        file_size = file_info["size"]

        category, file_format = _get_file_category_and_format(file_path)
        content_type = _get_content_type_by_format(file_format)

        preupload_payload = {
            "projectId": project_id,
            "name": rel_path,
            "fileCategory": category,
            "fileFormat": file_format,
            "sizeBytes": file_size,
            "hash": file_hash,
            "contentType": content_type,
        }

        status_code, preupload_data, text = _http_post_json(preupload_url, headers, preupload_payload, state)
        if not (200 <= status_code < 300):
            return _resp("error", status_code, f"预上传失败 {rel_path}: {text}", None)

        upload_url = preupload_data.get("uploadUrl")
        file_id = preupload_data.get("fileId")
        version_id = preupload_data.get("versionId")

        try:
            with open(file_path, "rb") as f:
                content = f.read()

            upload_headers = {"Content-Type": content_type}
            req = urllib.request.Request(upload_url, data=content, headers=upload_headers, method="PUT")
            with urllib.request.urlopen(req, timeout=60, context=_ssl_context_for_url(upload_url, state)) as resp:
                if resp.status not in (200, 201):
                    return _resp("error", resp.status, f"上传失败 {rel_path}", None)
        except Exception as e:
            return _resp("error", 500, f"上传失败 {rel_path}: {e}", None)

        uploaded_files.append({
            "path": rel_path,
            "fileId": file_id,
            "versionId": version_id,
            "hash": file_hash,
            "size": file_size,
            "lastModified": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        })

    all_files_map = {}

    for f in unchanged_files:
        all_files_map[f["path"]] = f

    for f in uploaded_files:
        all_files_map[f["path"]] = f

    for deleted in deleted_files:
        if deleted["path"] in all_files_map:
            del all_files_map[deleted["path"]]

    new_files_list = sorted(all_files_map.values(), key=lambda x: x["path"])

    folders = set()
    for f in new_files_list:
        dir_path = os.path.dirname(f["path"])
        if dir_path:
            top_folder = dir_path.split("/")[0]
            if top_folder:
                folders.add(top_folder)

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
            "totalFiles": len(new_files_list),
        },
    }

    manifest_json = json.dumps(new_manifest, ensure_ascii=False, indent=2)
    manifest_bytes = manifest_json.encode("utf-8")
    manifest_hash = hashlib.sha256(manifest_bytes).hexdigest()

    manifest_preupload_payload = {
        "projectId": project_id,
        "name": f"{software_name}_manifest.json",
        "fileCategory": "text",
        "fileFormat": "json",
        "sizeBytes": len(manifest_bytes),
        "hash": manifest_hash,
        "contentType": "application/json",
    }

    status_code, manifest_preupload_data, text = _http_post_json(preupload_url, headers, manifest_preupload_payload, state)
    if not (200 <= status_code < 300):
        return _resp("error", status_code, f"预上传 manifest 失败: {text}", None)

    manifest_upload_url = manifest_preupload_data.get("uploadUrl")
    new_manifest_file_id = manifest_preupload_data.get("fileId")
    new_manifest_version_id = manifest_preupload_data.get("versionId")

    try:
        req = urllib.request.Request(manifest_upload_url, data=manifest_bytes, headers={"Content-Type": "application/json"}, method="PUT")
        with urllib.request.urlopen(req, timeout=30, context=_ssl_context_for_url(manifest_upload_url, state)) as resp:
            if resp.status not in (200, 201):
                return _resp("error", resp.status, "上传 manifest 失败", None)
    except Exception as e:
        return _resp("error", 500, f"上传 manifest 失败: {e}", None)

    manifest_local_path = os.path.join(software_dir, "manifest.json")
    with open(manifest_local_path, "w", encoding="utf-8") as f:
        f.write(manifest_json)

    create_manifest_payload = {
        "projectId": project_id,
        "softwareId": software_id,
        "manifestFileId": new_manifest_file_id,
        "manifestFileVersionId": new_manifest_version_id,
        "versionNumber": new_version_number,
        "versionDescription": version_description or f"Commit at {time.strftime('%Y-%m-%d %H:%M:%S')}",
    }

    manifest_url = f"{base}/api/v1/software-manifests"
    status_code, manifest_resp, text = _http_post_json(manifest_url, headers, create_manifest_payload, state)
    if not (200 <= status_code < 300):
        return _resp("error", status_code, f"创建 manifest 记录失败: {text}", None)

    _state_set(state, "software_id", software_id)
    _state_set(state, "software_manifest_id", manifest_resp.get("manifestId"))
    _state_set(state, "software_name", software_name)

    return _resp("success", 200, "推送成功", {
        "software_name": software_name,
        "new_version": new_version_number,
        "files_uploaded": len(uploaded_files),
        "files_modified": len([f for f in changed_files if f.get("action") == "modified"]),
        "files_added": len([f for f in changed_files if f.get("action") == "added"]),
        "files_unchanged": len(unchanged_files),
        "manifest_id": manifest_resp.get("manifestId"),
        "version_number": new_version_number,
    })
