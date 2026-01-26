# MetAI Game Code Agent (ADK Version)

A Phaser 3 Game Development Agent built with **Google ADK (Python)** and **DeepSeek**.

## Features
- **Stack**: Python 3.10+ / ADK / DeepSeek / Vite / Phaser 3
- **Capabilities**:
    - Auto-initializes game projects
    - Reads/Writes TypeScript code
    - Manages local workspaces

## Quick Start

1. **Install ADK**:
   ```bash
   pip install google-adk
   ```

2. **Configure API Key**:
   Edit `phaser_agent/.env`:
   ```env
   GOOGLE_API_KEY="your-key-here"
   # OR
   DEEPSEEK_API_KEY="your-deepseek-key"
   ```

3. **Run Agent**:
   ```bash
   # CLI Mode
   adk run phaser_agent
   
   # Web UI Mode
   adk web --port 8000
   ```

## Directory Structure
- `phaser_agent/`: The ADK Agent definition and tools.
- `templates/`: Phaser game templates.
- `workspaces/`: Where your games are created.
