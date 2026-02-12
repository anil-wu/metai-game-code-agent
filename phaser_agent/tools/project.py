import shutil
import re
import json
import os
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
    base = (os.getenv("SPARK_API_BASE") or "").strip().rstrip("/")
    if base:
        return base
    base = (os.getenv("AGENT_CONFIG_API_BASE") or "").strip().rstrip("/")
    if base:
        return base
    base = (os.getenv("API_BASE") or "").strip().rstrip("/")
    return base

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
        with urllib.request.urlopen(req, timeout=10) as resp:
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
