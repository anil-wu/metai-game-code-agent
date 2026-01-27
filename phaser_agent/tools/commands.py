import subprocess
import shutil
import os
import shlex
import sys
from pathlib import Path
from typing import Dict, Any

# Security constraints
ALLOWED_NPM_COMMANDS = {
    "install",
    "run build",
    "run dev",
    "run preview"
}

def run_npm(project_id: str, args: str) -> Dict[str, Any]:
    """
    Executes an npm command within the project workspace safely.
    
    Args:
        project_id: The ID of the project (folder name in workspaces/).
        args: The arguments to pass to npm (e.g., 'install', 'run build').
        
    Returns:
        Dict containing status, stdout, stderr, and returncode.
    """
    # 1. Validate project_id
    if not project_id or not project_id.replace("_", "").replace("-", "").isalnum():
        return {"status": "error", "message": "Invalid project_id"}

    workspace_root = WORKSPACE_ROOT.resolve()
    project_dir = (workspace_root / project_id).resolve()
    
    # Security: Ensure we don't traverse up
    if not str(project_dir).startswith(str(workspace_root)):
         return {"status": "error", "message": "Invalid project path traversal"}

    if not project_dir.exists():
        return {"status": "error", "message": f"Project directory {project_id} not found"}

    # 2. Validate args (Allowlist)
    clean_args = args.strip()
    is_allowed = False
    for cmd in ALLOWED_NPM_COMMANDS:
        if clean_args == cmd or clean_args.startswith(cmd + " "):
            is_allowed = True
            break
    
    if not is_allowed:
        return {
            "status": "error", 
            "message": f"Command not allowed. Allowed: {', '.join(ALLOWED_NPM_COMMANDS)}"
        }
    
    # 3. Construct command safely
    npm_cmd = shutil.which("npm")
    if not npm_cmd:
        return {"status": "error", "message": "npm executable not found"}
        
    # On Windows, shutil.which might return just 'npm', which needs shell=True to run if it's a .cmd
    # Or we can append .cmd if on windows.
    if sys.platform == "win32" and not npm_cmd.lower().endswith(".cmd") and not npm_cmd.lower().endswith(".exe"):
        # If it doesn't end with .cmd or .exe, it might be a problem on Windows with shell=False
        # Try to find the .cmd version
        npm_cmd_cmd = shutil.which("npm.cmd")
        if npm_cmd_cmd:
            npm_cmd = npm_cmd_cmd

    try:
        # Use shlex to split args
        cmd_args = shlex.split(clean_args)
    except ValueError:
        return {"status": "error", "message": "Invalid command arguments"}

    command = [npm_cmd] + cmd_args

    # 4. Execute
    try:
        # 5 minute timeout
        result = subprocess.run(
            command,
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=300,
            shell=False # Safer
        )

        # Truncate output
        MAX_OUTPUT = 2000
        stdout = result.stdout[:MAX_OUTPUT] + ("..." if len(result.stdout) > MAX_OUTPUT else "")
        stderr = result.stderr[:MAX_OUTPUT] + ("..." if len(result.stderr) > MAX_OUTPUT else "")

        return {
            "status": "success" if result.returncode == 0 else "error",
            "stdout": stdout,
            "stderr": stderr,
            "returncode": result.returncode
        }

    except subprocess.TimeoutExpired:
        return {"status": "error", "message": "Command timed out (300s)"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
