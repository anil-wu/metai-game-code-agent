# Phaser Game Agent System (ADK Edition)

## Overview
This project implements an autonomous game development agent using the **Google Agent Development Kit (ADK)** framework, configured to use **DeepSeek** as the intelligence backend.

## Architecture

### 1. Stack
*   **Framework**: Google ADK (Python)
*   **LLM**: DeepSeek-V3/R1 (via OpenAI-compatible API)
*   **Runtime**: Vite + Phaser 3 (TypeScript)
*   **Interface**: ADK CLI (`adk run`) or Web UI (`adk web`)

### 2. Project Structure
```text
/
├── phaser_agent/            # ADK Agent Package
│   ├── __init__.py
│   ├── agent.py             # Defines `root_agent` and model config
│   ├── tools.py             # Filesystem & Workspace tools
│   └── .env                 # API Keys
├── templates/
│   └── phaser-starter/      # Minimal Vite+Phaser boilerplate
├── workspaces/              # Runtime generated games (GitIgnored)
└── README.md
```

### 3. Agent Capabilities (Tools)
The agent is equipped with the following ADK tools:
*   `init_game_project(name)`: Bootstraps a new game from `templates/`.
*   `read_file(path)`: Context retrieval.
*   `write_file(path, content)`: Code generation & injection.
*   `list_files(path)`: Structural awareness.

### 4. DeepSeek Integration
The agent uses DeepSeek via the ADK's model interface.
*   **Model**: `deepseek-chat`
*   **Config**: Defined in `.env` (requires compatible ADK provider or custom adapter).

## Usage

### Prerequisite
```bash
pip install google-adk
```

### Run (CLI)
```bash
adk run phaser_agent
```

### Run (Web UI)
```bash
adk web --port 8000
```
