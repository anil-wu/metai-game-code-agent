import shutil
import re
import json
import hashlib
import os
import ssl
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from typing import Dict, Any
from phaser_agent.config import WORKSPACE_ROOT, TEMPLATE_PATH, FIXED_PROJECT_ID, DIR_GAME, DIR_ARTIFACTS, DIR_BUILD, DIR_LOGS
from .utils import get_target_path

def create_project(prompt: str = "game") -> Dict[str, Any]:
    """Creates a new project directory or reuses the fixed project.
    
    Args:
        prompt: User's description (unused for ID generation now).
    """
    project_id = FIXED_PROJECT_ID
    
    try:
        WORKSPACE_ROOT.mkdir(parents=True, exist_ok=True)
        target_dir = WORKSPACE_ROOT / project_id
        
        # Create main project directory
        target_dir.mkdir(parents=True, exist_ok=True)

        # Create subdirectories
        (target_dir / DIR_GAME).mkdir(parents=True, exist_ok=True)
        (target_dir / DIR_ARTIFACTS).mkdir(parents=True, exist_ok=True)
        (target_dir / DIR_BUILD).mkdir(parents=True, exist_ok=True)
        (target_dir / DIR_LOGS).mkdir(parents=True, exist_ok=True)
        
        return {
            "status": "success",
            "project_id": project_id,
            "path": str(target_dir),
            "message": f"Project {project_id} structure created at {target_dir}"
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

def bootstrap_project(project_id: str) -> Dict[str, Any]:
    """Initializes the project with the Phaser starter template.
    
    Args:
        project_id: The ID of the project to bootstrap.
    """
    try:
        project_root = get_target_path("", project_id)
        if not project_root.exists():
            return {"status": "error", "message": f"Project {project_id} does not exist"}
            
        if not TEMPLATE_PATH.exists():
            return {"status": "error", "message": f"Template not found at {TEMPLATE_PATH}"}
        
        game_dir = project_root / DIR_GAME
        package_json_path = game_dir / "package.json"

        if not package_json_path.exists():
            shutil.copytree(TEMPLATE_PATH, game_dir, dirs_exist_ok=True)
            return {
                "status": "success",
                "message": f"Template bootstrapped to {project_id}/{DIR_GAME}. Next: Run 'run_npm' to install dependencies."
            }

        required_dev_deps = {
            "eslint": "^8.57.0",
            "@typescript-eslint/parser": "^8.54.0",
            "@typescript-eslint/eslint-plugin": "^8.54.0",
        }
        required_lint_script = "eslint . --ext .ts,.tsx --max-warnings=0"
        updated = False

        try:
            with package_json_path.open("r", encoding="utf-8") as f:
                pkg = json.load(f)
        except Exception:
            pkg = {}

        scripts = pkg.setdefault("scripts", {})
        if scripts.get("lint") != required_lint_script:
            if "lint" not in scripts:
                scripts["lint"] = required_lint_script
                updated = True

        dev_deps = pkg.setdefault("devDependencies", {})
        for name, version in required_dev_deps.items():
            if name not in dev_deps:
                dev_deps[name] = version
                updated = True

        if updated:
            package_json_path.write_text(json.dumps(pkg, indent=2) + "\n", encoding="utf-8")

        eslint_config_path = game_dir / ".eslintrc.cjs"
        if not eslint_config_path.exists():
            template_eslint_config = TEMPLATE_PATH / ".eslintrc.cjs"
            if template_eslint_config.exists():
                shutil.copy2(template_eslint_config, eslint_config_path)
            else:
                eslint_config_path.write_text(
                    "module.exports = {\n"
                    "  root: true,\n"
                    "  env: { browser: true, es2020: true },\n"
                    "  parser: '@typescript-eslint/parser',\n"
                    "  parserOptions: { ecmaVersion: 'latest', sourceType: 'module' },\n"
                    "  plugins: ['@typescript-eslint'],\n"
                    "  extends: ['eslint:recommended', 'plugin:@typescript-eslint/recommended'],\n"
                    "  ignorePatterns: ['dist', 'node_modules']\n"
                    "}\n",
                    encoding="utf-8",
                )
            updated = True
        
        return {
            "status": "success", 
            "message": (
                f"Project {project_id} already bootstrapped. "
                f"Ensured eslint baseline: {'updated' if updated else 'no changes'}."
            )
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

def _api_base() -> str:
    base = (os.getenv("SPARKX_API_BASE_URL") or "").strip().rstrip("/")
    if base:
        return base
    base = (os.getenv("SPARK_API_BASE") or "").strip().rstrip("/")
    if base:
        return base
    base = (os.getenv("AGENT_CONFIG_API_BASE") or "").strip().rstrip("/")
    if base:
        return base
    base = (os.getenv("API_BASE") or "").strip().rstrip("/")
    return base

def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    text = str(value).strip().lower()
    return text in {"1", "true", "yes", "y", "on"}

def _ssl_context_for_url(url: str) -> ssl.SSLContext | None:
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

    if hostname in {"localhost", "127.0.0.1", "::1"} and not _truthy(force_verify_env):
        return ssl._create_unverified_context()

    ca_bundle = (os.getenv("SPARKPLAY_CA_BUNDLE") or os.getenv("REQUESTS_CA_BUNDLE") or "").strip()
    if ca_bundle:
        try:
            return ssl.create_default_context(cafile=ca_bundle)
        except Exception:
            return ssl.create_default_context()
    return ssl.create_default_context()

def _resolve_token(token: str | None) -> str | None:
    if token and str(token).strip():
        return str(token).strip()
    env_token = (os.getenv("SPARK_API_TOKEN") or "").strip()
    if env_token:
        return env_token
    return (os.getenv("AGENT_CONFIG_TOKEN") or "").strip() or None

def _api_request(
    method: str,
    path: str,
    token: str | None = None,
    query: Dict[str, Any] | None = None,
    body: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    base = _api_base()
    if not base:
        return {"status": "error", "message": "API base URL is required"}
    url = f"{base}{path}"
    if query:
        query_str = urllib.parse.urlencode({k: v for k, v in query.items() if v is not None})
        if query_str:
            url = f"{url}?{query_str}"
    headers = {"Accept": "application/json"}
    auth_token = _resolve_token(token)
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, headers=headers, data=data, method=method.upper())
    try:
        with urllib.request.urlopen(req, timeout=10, context=_ssl_context_for_url(url)) as resp:
            status_code = getattr(resp, "status", None) or 200
            raw = resp.read()
    except urllib.error.HTTPError as e:
        status_code = getattr(e, "code", None)
        raw = e.read()
        try:
            text = raw.decode("utf-8", errors="replace") if raw else ""
        except Exception:
            text = ""
        return {
            "status": "error",
            "status_code": status_code,
            "message": text or f"HTTP {status_code}",
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
    try:
        payload = json.loads(raw.decode("utf-8")) if raw else None
    except Exception:
        payload = None
    if status_code and 200 <= int(status_code) < 300:
        return {"status": "success", "status_code": status_code, "data": payload}
    return {
        "status": "error",
        "status_code": status_code,
        "message": payload,
        "data": payload,
    }

def _upload_bytes_to_signed_url(
    upload_url: str,
    data: bytes,
    content_type: str,
) -> Dict[str, Any]:
    if not upload_url or not str(upload_url).strip():
        return {"status": "error", "message": "upload_url is required"}
    resolved_content_type = str(content_type).strip() if content_type else ""
    if not resolved_content_type:
        return {"status": "error", "message": "content_type is required"}
    try:
        req = urllib.request.Request(
            str(upload_url).strip(),
            data=data,
            method="PUT",
            headers={"Content-Type": resolved_content_type},
        )
        with urllib.request.urlopen(req, timeout=30, context=_ssl_context_for_url(str(upload_url).strip())) as resp:
            status_code = getattr(resp, "status", None) or 200
            resp.read()
        if 200 <= int(status_code) < 300:
            return {"status": "success", "status_code": status_code}
        return {"status": "error", "status_code": status_code, "message": f"HTTP {status_code}"}
    except urllib.error.HTTPError as e:
        status_code = getattr(e, "code", None)
        raw = e.read()
        try:
            text = raw.decode("utf-8", errors="replace") if raw else ""
        except Exception:
            text = ""
        return {
            "status": "error",
            "status_code": status_code,
            "message": text or f"HTTP {status_code}",
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

def preupload_file(
    project_id: int | str,
    name: str,
    file_category: str,
    file_format: str,
    size_bytes: int,
    file_hash: str,
    content_type: str | None = None,
    token: str | None = None,
) -> Dict[str, Any]:
    if not project_id and project_id != 0:
        return {"status": "error", "message": "project_id is required"}
    if not name or not str(name).strip():
        return {"status": "error", "message": "name is required"}
    if not file_category or not str(file_category).strip():
        return {"status": "error", "message": "file_category is required"}
    if not file_format or not str(file_format).strip():
        return {"status": "error", "message": "file_format is required"}
    if size_bytes is None or int(size_bytes) < 0:
        return {"status": "error", "message": "size_bytes is required"}
    if not file_hash or not str(file_hash).strip():
        return {"status": "error", "message": "file_hash is required"}

    body: Dict[str, Any] = {
        "projectId": int(project_id),
        "name": str(name).strip(),
        "fileCategory": str(file_category).strip(),
        "fileFormat": str(file_format).strip(),
        "sizeBytes": int(size_bytes),
        "hash": str(file_hash).strip(),
    }
    if content_type is not None and str(content_type).strip():
        body["contentType"] = str(content_type).strip()
    return _api_request("POST", "/api/v1/files/preupload", token=token, body=body)

def upload_file_bytes(
    project_id: int | str,
    name: str,
    data: bytes,
    file_category: str,
    file_format: str,
    content_type: str | None = None,
    token: str | None = None,
) -> Dict[str, Any]:
    if data is None:
        return {"status": "error", "message": "data is required"}
    if not isinstance(data, (bytes, bytearray)):
        return {"status": "error", "message": "data must be bytes"}

    resolved_bytes = bytes(data)
    resolved_hash = hashlib.sha256(resolved_bytes).hexdigest()
    resolved_size = len(resolved_bytes)

    pre = preupload_file(
        project_id=project_id,
        name=name,
        file_category=file_category,
        file_format=file_format,
        size_bytes=resolved_size,
        file_hash=resolved_hash,
        content_type=content_type,
        token=token,
    )
    if pre.get("status") != "success":
        return pre
    pre_data = pre.get("data") or {}
    upload_url = pre_data.get("uploadUrl")
    signed_content_type = pre_data.get("contentType") or content_type or "application/octet-stream"

    put_result = _upload_bytes_to_signed_url(
        upload_url=str(upload_url).strip() if upload_url is not None else "",
        data=resolved_bytes,
        content_type=str(signed_content_type).strip(),
    )
    if put_result.get("status") != "success":
        return put_result

    return {
        "status": "success",
        "file_id": pre_data.get("fileId"),
        "file_version_id": pre_data.get("versionId"),
        "version_number": pre_data.get("versionNumber"),
        "hash": resolved_hash,
        "size_bytes": resolved_size,
        "content_type": signed_content_type,
        "upload_status_code": put_result.get("status_code"),
        "preupload": pre_data,
    }

def upload_text_file(
    project_id: int | str,
    name: str,
    content: str,
    file_format: str,
    token: str | None = None,
    content_type: str | None = None,
) -> Dict[str, Any]:
    if content is None:
        return {"status": "error", "message": "content is required"}
    resolved_content_type = content_type
    if resolved_content_type is None or not str(resolved_content_type).strip():
        resolved_content_type = "text/plain"
    return upload_file_bytes(
        project_id=project_id,
        name=name,
        data=str(content).encode("utf-8"),
        file_category="text",
        file_format=file_format,
        content_type=resolved_content_type,
        token=token,
    )

def upload_software_manifest_json(
    project_id: int | str,
    manifest_json: str,
    token: str | None = None,
    name: str = "software_manifest.json",
) -> Dict[str, Any]:
    return upload_text_file(
        project_id=project_id,
        name=name,
        content=manifest_json,
        file_format="json",
        token=token,
        content_type="application/json",
    )

def create_remote_project(
    user_id: int,
    name: str,
    description: str,
    token: str | None = None,
) -> Dict[str, Any]:
    if not user_id:
        return {"status": "error", "message": "user_id is required"}
    if not name or not str(name).strip():
        return {"status": "error", "message": "name is required"}
    if description is None or not str(description).strip():
        return {"status": "error", "message": "description is required"}
    return _api_request(
        "POST",
        "/api/v1/projects",
        token=token,
        body={
            "userId": int(user_id),
            "name": str(name).strip(),
            "description": str(description).strip(),
        },
    )

def list_projects(
    token: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> Dict[str, Any]:
    result = _api_request(
        "GET",
        "/api/v1/projects",
        token=token,
        query={"page": int(page), "pageSize": int(page_size)},
    )
    if result.get("status") != "success":
        return result
    items = (result.get("data") or {}).get("list") or []

    def parse_dt(value: Any) -> datetime | None:
        if not isinstance(value, str):
            return None
        raw = value.strip()
        if not raw:
            return None
        candidates = [
            raw,
            raw.replace(" ", "T"),
            raw.replace("Z", "+00:00"),
            raw.replace(" ", "T").replace("Z", "+00:00"),
        ]
        for c in candidates:
            try:
                return datetime.fromisoformat(c)
            except Exception:
                continue
        return None

    latest = None
    for item in items:
        if not isinstance(item, dict):
            continue
        latest = item if latest is None else latest
        if latest is item:
            continue
        left_dt = parse_dt(item.get("createdAt"))
        right_dt = parse_dt(latest.get("createdAt"))
        if left_dt is not None and right_dt is not None:
            if left_dt > right_dt:
                latest = item
            continue
        left_id = item.get("id")
        right_id = latest.get("id")
        if isinstance(left_id, int) and isinstance(right_id, int) and left_id > right_id:
            latest = item

    return {
        "status": "success",
        "projects": items,
        "latest_project": latest,
        "latest_project_id": latest.get("id") if isinstance(latest, dict) else None,
        "data": result.get("data"),
        "status_code": result.get("status_code"),
    }

def ensure_workspace_dir(
    user_id: int,
    project_id: int | str,
) -> Dict[str, Any]:
    if not user_id:
        return {"status": "error", "message": "user_id is required"}
    if not project_id and project_id != 0:
        return {"status": "error", "message": "project_id is required"}
    try:
        workspace_dir = (WORKSPACE_ROOT / str(int(user_id)) / str(project_id)).resolve()
        workspace_root = WORKSPACE_ROOT.resolve()
        if os.path.commonpath([str(workspace_root), str(workspace_dir)]) != str(workspace_root):
            return {"status": "error", "message": "workspace_dir escapes WORKSPACE_ROOT"}

        existed = workspace_dir.exists()
        workspace_dir.mkdir(parents=True, exist_ok=True)
        if not workspace_dir.is_dir():
            return {"status": "error", "message": "workspace_dir is not a directory"}

        fd, tmp_path = tempfile.mkstemp(prefix=".writable_check_", dir=str(workspace_dir))
        os.close(fd)
        os.unlink(tmp_path)

        return {
            "status": "success",
            "workspace_dir": str(workspace_dir),
            "existed": existed,
            "created": not existed,
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

def pull_software_version(
    project_id: int | str,
    file_id: int,
    version_id: int | None = None,
    version_number: int | None = None,
    token: str | None = None,
) -> Dict[str, Any]:
    if not file_id:
        return {"status": "error", "message": "file_id is required"}
    query: Dict[str, Any] = {}
    if version_id is not None:
        query["versionId"] = int(version_id)
    if version_number is not None:
        query["versionNumber"] = int(version_number)
    result = _api_request(
        "GET",
        f"/api/v1/files/{int(file_id)}/download",
        token=token,
        query=query,
    )
    result["project_id"] = project_id
    return result

def update_software_version(
    file_id: int,
    version_number: int | None = None,
    token: str | None = None,
) -> Dict[str, Any]:
    if not file_id:
        return {"status": "error", "message": "file_id is required"}
    resolved_version = version_number
    if resolved_version is None:
        versions = _api_request(
            "GET",
            f"/api/v1/files/{int(file_id)}/versions",
            token=token,
            query={"page": 1, "pageSize": 50},
        )
        if versions.get("status") != "success":
            return versions
        items = (versions.get("data") or {}).get("list") or []
        if not items:
            return {"status": "error", "message": "no versions available"}
        resolved_version = max(
            (int(item.get("versionNumber")) for item in items if item.get("versionNumber") is not None),
            default=None,
        )
        if resolved_version is None:
            return {"status": "error", "message": "versionNumber not found"}
    return _api_request(
        "POST",
        f"/api/v1/files/{int(file_id)}/rollback",
        token=token,
        body={"versionNumber": int(resolved_version)},
    )

def get_sandbox_workspace_info(
    project_id: int | str,
    token: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> Dict[str, Any]:
    if not project_id:
        return {"status": "error", "message": "project_id is required"}
    project = _api_request("GET", f"/api/v1/projects/{int(project_id)}", token=token)
    if project.get("status") != "success":
        return {
            "status": "error",
            "workspace_exists": False,
            "message": project.get("message") or "workspace not found",
        }
    files = _api_request(
        "GET",
        f"/api/v1/projects/{int(project_id)}/files",
        token=token,
        query={"page": int(page), "pageSize": int(page_size)},
    )
    if files.get("status") != "success":
        return {
            "status": "error",
            "workspace_exists": True,
            "project": project.get("data"),
            "message": files.get("message") or "failed to load files",
        }
    items = (files.get("data") or {}).get("list") or []
    version_numbers = [
        int(item.get("versionNumber"))
        for item in items
        if item.get("versionNumber") is not None
    ]
    latest_version = max(version_numbers) if version_numbers else None
    return {
        "status": "success",
        "workspace_exists": True,
        "project": project.get("data"),
        "files": items,
        "latest_version_number": latest_version,
    }

def get_user_project_software_info(
    project_id: int | str,
    token: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> Dict[str, Any]:
    if not project_id:
        return {"status": "error", "message": "project_id is required"}
    softwares = _api_request(
        "GET",
        f"/api/v1/projects/{int(project_id)}/softwares",
        token=token,
        query={"page": int(page), "pageSize": int(page_size)},
    )
    if softwares.get("status") != "success":
        return softwares
    items = (softwares.get("data") or {}).get("list") or []
    software_ids = [str(item.get("id")) for item in items if item.get("id") is not None]
    if not software_ids:
        return {"status": "success", "softwares": items, "latest_manifests": []}
    manifests = _api_request(
        "GET",
        f"/api/v1/projects/{int(project_id)}/software_manifests",
        token=token,
        query={"software_ids": ",".join(software_ids)},
    )
    if manifests.get("status") != "success":
        return {
            "status": "error",
            "softwares": items,
            "message": manifests.get("message") or "failed to load software manifests",
            "data": manifests.get("data"),
        }
    latest_manifests = (manifests.get("data") or {}).get("list") or []
    manifest_map = {
        int(item.get("softwareId")): item for item in latest_manifests if item.get("softwareId") is not None
    }
    software_infos = []
    for item in items:
        software_id = item.get("id")
        manifest = manifest_map.get(int(software_id)) if software_id is not None else None
        software_infos.append(
            {
                "softwareId": software_id,
                "name": item.get("name"),
                "description": item.get("description"),
                "technologyStack": item.get("technologyStack"),
                "templateId": item.get("templateId"),
                "manifestFileVersionId": manifest.get("manifestFileVersionId") if manifest else None,
            }
        )
    return {"status": "success", "softwares": software_infos}

def ensure_project_software(
    project_id: int | str,
    name: str,
    description: str | None = None,
    template_id: int | None = None,
    technology_stack: str | None = None,
    token: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> Dict[str, Any]:
    if not project_id and project_id != 0:
        return {"status": "error", "message": "project_id is required"}
    if not name or not str(name).strip():
        return {"status": "error", "message": "name is required"}

    normalized_name = str(name).strip()
    list_result = _api_request(
        "GET",
        f"/api/v1/projects/{int(project_id)}/softwares",
        token=token,
        query={"page": int(page), "pageSize": int(page_size)},
    )
    if list_result.get("status") != "success":
        return list_result
    items = (list_result.get("data") or {}).get("list") or []
    for item in items:
        if isinstance(item, dict) and (item.get("name") == normalized_name):
            return {
                "status": "success",
                "created": False,
                "software": item,
                "status_code": list_result.get("status_code"),
            }

    resolved_description = "" if description is None else str(description)
    resolved_technology_stack = (
        str(technology_stack).strip()
        if technology_stack is not None and str(technology_stack).strip()
        else "game engine is phaser"
    )
    body: Dict[str, Any] = {
        "name": normalized_name,
        "description": resolved_description,
        "technologyStack": resolved_technology_stack,
    }
    if template_id is not None:
        body["templateId"] = int(template_id)

    create_result = _api_request(
        "POST",
        f"/api/v1/projects/{int(project_id)}/softwares",
        token=token,
        body=body,
    )
    if create_result.get("status") != "success":
        return create_result
    return {
        "status": "success",
        "created": True,
        "software": create_result.get("data"),
        "status_code": create_result.get("status_code"),
    }

def ensure_software_manifest(
    project_id: int | str,
    software_id: int | str,
    manifest_file_id: int,
    manifest_file_version_id: int,
    version_number: int | None = None,
    version_description: str | None = None,
    token: str | None = None,
) -> Dict[str, Any]:
    if not project_id and project_id != 0:
        return {"status": "error", "message": "project_id is required"}
    if not software_id and software_id != 0:
        return {"status": "error", "message": "software_id is required"}
    if not manifest_file_id:
        return {"status": "error", "message": "manifest_file_id is required"}
    if not manifest_file_version_id:
        return {"status": "error", "message": "manifest_file_version_id is required"}

    list_result = _api_request(
        "GET",
        f"/api/v1/projects/{int(project_id)}/software_manifests",
        token=token,
        query={"software_ids": str(int(software_id))},
    )
    if list_result.get("status") != "success":
        return list_result

    items = (list_result.get("data") or {}).get("list") or []
    existing = None
    latest_version_number = 0
    for item in items:
        if not isinstance(item, dict):
            continue
        if item.get("softwareId") == int(software_id):
            existing = item
            if item.get("versionNumber"):
                latest_version_number = max(latest_version_number, int(item.get("versionNumber")))
            break

    if (
        isinstance(existing, dict)
        and existing.get("hasRecord") is True
        and existing.get("manifestFileVersionId") == int(manifest_file_version_id)
    ):
        return {
            "status": "success",
            "created": False,
            "manifest": existing,
            "data": list_result.get("data"),
            "status_code": list_result.get("status_code"),
        }

    resolved_version_number = version_number if version_number is not None else (latest_version_number + 1)

    body: Dict[str, Any] = {
        "projectId": int(project_id),
        "softwareId": int(software_id),
        "manifestFileId": int(manifest_file_id),
        "manifestFileVersionId": int(manifest_file_version_id),
        "versionNumber": int(resolved_version_number),
    }
    if version_description is not None and str(version_description).strip():
        body["versionDescription"] = str(version_description).strip()

    create_result = _api_request(
        "POST",
        "/api/v1/software-manifests",
        token=token,
        body=body,
    )
    if create_result.get("status") != "success":
        return create_result
    return {
        "status": "success",
        "created": True,
        "manifest": create_result.get("data"),
        "status_code": create_result.get("status_code"),
    }

def ensure_software_manifest_from_snapshot(
    project_id: int | str,
    software_id: int | str,
    software_manifest_json: str,
    version_number: int | None = None,
    version_description: str | None = None,
    token: str | None = None,
    manifest_file_name: str = "software_manifest.json",
) -> Dict[str, Any]:
    upload_result = upload_software_manifest_json(
        project_id=project_id,
        manifest_json=software_manifest_json,
        token=token,
        name=manifest_file_name,
    )
    if upload_result.get("status") != "success":
        return upload_result

    file_id = upload_result.get("file_id")
    file_version_id = upload_result.get("file_version_id")
    if file_id is None or file_version_id is None:
        return {"status": "error", "message": "missing manifest file id/version id after upload"}

    ensure_result = ensure_software_manifest(
        project_id=project_id,
        software_id=software_id,
        manifest_file_id=int(file_id),
        manifest_file_version_id=int(file_version_id),
        version_number=version_number,
        version_description=version_description,
        token=token,
    )
    if ensure_result.get("status") != "success":
        return ensure_result

    return {
        "status": "success",
        "upload": upload_result,
        "manifest_record": ensure_result,
        "created": ensure_result.get("created"),
        "manifest": ensure_result.get("manifest"),
    }

def create_build_version(
    project_id: int | str,
    software_manifest_id: int | str,
    build_version_file_id: int,
    build_version_file_version_id: int,
    description: str | None = None,
    token: str | None = None,
) -> Dict[str, Any]:
    print(f"create_build_version-----》》: {project_id}, {software_manifest_id}, {build_version_file_id}, {build_version_file_version_id}, {description}")

    if not project_id and project_id != 0:
        return {"status": "error", "message": "project_id is required"}
    if not software_manifest_id and software_manifest_id != 0:
        return {"status": "error", "message": "software_manifest_id is required"}
    if not build_version_file_id:
        return {"status": "error", "message": "build_version_file_id is required"}
    if not build_version_file_version_id:
        return {"status": "error", "message": "build_version_file_version_id is required"}

    body: Dict[str, Any] = {
        "projectId": int(project_id),
        "softwareManifestId": int(software_manifest_id),
        "buildVersionFileId": int(build_version_file_id),
        "buildVersionFileVersionId": int(build_version_file_version_id),
    }
    if description is not None and str(description).strip():
        body["description"] = str(description).strip()

    return _api_request(
        "POST",
        "/api/v1/build-versions",
        token=token,
        body=body,
    )
