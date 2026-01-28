import subprocess
import shutil
import shlex
import sys
import re
from typing import Dict, Any
from phaser_agent.config import DIR_GAME
from .utils import get_target_path

# Security constraints
ALLOWED_NPM_COMMANDS = {
    "install",
    "run build",
    "run lint",
    "run dev",
    "run preview"
}

def _tail_text(text: str, max_chars: int) -> str:
    if max_chars <= 0:
        return ""
    if len(text) <= max_chars:
        return text
    return text[-max_chars:]

def _extract_error_summary(stdout: str, stderr: str, max_lines: int = 30, max_chars: int = 1500) -> str:
    combined = "\n".join([stderr or "", stdout or ""])
    lines = [l.rstrip("\r\n") for l in combined.splitlines() if l.strip()]

    patterns = [
        r"\berror\b",
        r"\bfail(?:ed|ure)?\b",
        r"\bERR!\b",
        r"\bUnhandled\b",
        r"\bCannot find module\b",
        r"\bModule not found\b",
        r"\bTS\d{3,5}\b",
        r"\bSyntaxError\b",
        r"\bReferenceError\b",
        r"\bTypeError\b",
        r"\bVite\b",
        r"\brollup\b",
        r"\bplugin:\b",
    ]
    rx = re.compile("|".join(f"(?:{p})" for p in patterns), re.IGNORECASE)

    picked: list[str] = []
    seen = set()
    for line in lines:
        if rx.search(line):
            key = line.lower()
            if key in seen:
                continue
            seen.add(key)
            picked.append(line)

    if not picked:
        picked = lines[-max_lines:]
    else:
        picked = picked[-max_lines:]

    summary = "\n".join(picked)
    if len(summary) > max_chars:
        summary = summary[:max_chars]
    return summary

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

    try:
        project_dir = get_target_path(DIR_GAME, project_id)
    except ValueError as e:
        return {"status": "error", "message": str(e)}

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
            encoding='utf-8',
            errors='replace',
            timeout=300,
            shell=False # Safer
        )

        MAX_OUTPUT = 2000
        stdout = _tail_text(result.stdout, MAX_OUTPUT)
        stderr = _tail_text(result.stderr, MAX_OUTPUT)
        summary = _extract_error_summary(result.stdout, result.stderr)

        return {
            "status": "success" if result.returncode == 0 else "error",
            "stdout": stdout,
            "stderr": stderr,
            "summary": summary,
            "returncode": result.returncode
        }

    except subprocess.TimeoutExpired:
        return {"status": "error", "message": "Command timed out (300s)"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def run_cmd(project_id: str, args: str) -> Dict[str, Any]:
    return run_npm(project_id, args)
