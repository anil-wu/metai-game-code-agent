from pathlib import Path

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
