import os
from pathlib import Path

OPENROUTER_API_KEY = (os.getenv("OPENROUTER_API_KEY") or "").strip()
OPENROUTER_API_BASE = (os.getenv("OPENROUTER_API_BASE") or "").strip()

_raw_litellm_model = (os.getenv("LITELLM_MODEL") or "openrouter/openai/gpt-4o-mini").strip()
if _raw_litellm_model.startswith("openrouter/"):
    LITELLM_MODEL = _raw_litellm_model
else:
    LITELLM_MODEL = f"openrouter/{_raw_litellm_model}"

LITELLM_KWARGS = {}
if OPENROUTER_API_BASE:
    LITELLM_KWARGS["api_base"] = OPENROUTER_API_BASE
elif OPENROUTER_API_KEY:
    LITELLM_KWARGS["api_base"] = "https://openrouter.ai/api/v1"
if OPENROUTER_API_KEY:
    LITELLM_KWARGS["api_key"] = OPENROUTER_API_KEY

# Configuration
WORKSPACE_ROOT = Path("workspaces")
FIXED_PROJECT_ID = "phaser-game"
TEMPLATE_PATH = Path("templates/phaser-starter")
MAX_LIST_FILES_HARD = 2000
MAX_LIST_FILES_DEFAULT = 500
MAX_LIST_FILES = MAX_LIST_FILES_DEFAULT

MAX_READ_CHARS_HARD = 200_000
MAX_READ_CHARS_DEFAULT = 50_000
MAX_READ_CHARS = MAX_READ_CHARS_DEFAULT
MAX_SEARCH_FILES_HARD = 2000
MAX_SEARCH_FILES_DEFAULT = 500
MAX_SEARCH_FILES = MAX_SEARCH_FILES_DEFAULT
MAX_SEARCH_MATCHES_HARD = 5000
MAX_SEARCH_MATCHES_DEFAULT = 500
MAX_SEARCH_MATCHES = MAX_SEARCH_MATCHES_DEFAULT
MAX_SEARCH_FILE_CHARS_HARD = 200_000
MAX_SEARCH_FILE_CHARS_DEFAULT = 50_000
MAX_SEARCH_FILE_CHARS = MAX_SEARCH_FILE_CHARS_DEFAULT
MAX_SEARCH_TOTAL_CHARS_HARD = 5_000_000
MAX_SEARCH_TOTAL_CHARS_DEFAULT = 1_000_000
MAX_SEARCH_TOTAL_CHARS = MAX_SEARCH_TOTAL_CHARS_DEFAULT
IGNORED_DIR_NAMES = {
    ".git",
    ".adk",
    ".vite",
    "node_modules",
    "dist",
    "build",
    "coverage",
}

# Subdirectory structure
DIR_GAME = "game_project"
DIR_ARTIFACTS = "artifacts"
DIR_BUILD = "build_output"
DIR_LOGS = "logs"
