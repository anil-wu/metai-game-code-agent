from pathlib import Path

# Configuration
WORKSPACE_ROOT = Path("workspaces")
FIXED_PROJECT_ID = "phaser-game"
TEMPLATE_PATH = Path("templates/phaser-starter")
MAX_LIST_FILES = 2000
MAX_READ_CHARS = 200_000
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
