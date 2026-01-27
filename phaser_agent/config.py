from pathlib import Path

# Configuration
WORKSPACE_ROOT = Path("workspaces")
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
