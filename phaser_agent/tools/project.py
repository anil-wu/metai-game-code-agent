import shutil
import re
import json
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
