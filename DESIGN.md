# Phaser 游戏 Agent 系统（ADK 版）

## 概述
本项目基于 **Google Agent Development Kit (ADK)** 框架实现一个自治游戏开发智能体，并配置使用 **DeepSeek** 作为智能后端。

## 架构

### 1. 技术栈
*   **框架**：Google ADK（Python）
*   **大模型**：DeepSeek-V3/R1（通过 OpenAI 兼容 API）
*   **运行时**：Vite + Phaser 3（TypeScript）
*   **交互界面**：ADK CLI（`adk run`）或 Web UI（`adk web`）

### 2. 项目结构
```text
/
├── phaser_agent/            # ADK 智能体包
│   ├── __init__.py
│   ├── agent.py             # 定义 `root_agent` 与模型配置
│   ├── config.py
│   ├── agents/              # Spec/Planner/Coder/Verifier 子智能体
│   ├── tools/               # project/filesystem/commands 工具（project_id 优先）
│   └── .env                 # API Key
├── templates/
│   └── phaser-starter/      # 最小化 Vite+Phaser 模板
├── workspaces/              # 运行时生成的项目（已加入 .gitignore）
└── README.md
```

### 3. 多智能体角色（精简但合理）
为保持职责与权限边界清晰，同时仍适合 MVP，本系统拆分为多个智能体。

*   **Orchestrator Agent（编排智能体）**
    *   负责单次用户请求的端到端流程。
    *   创建 `project_id`，协调其他智能体，并输出最终报告。
*   **Spec Agent（需求智能体）**
    *   将一行需求整理为详细的需求文档（主循环、输入、胜负条件、实体、UI、资源），直接输出文本。
    *   仅写入 `workspaces/<project_id>/agent/`。
*   **Planner Agent（计划智能体）**
    *   将需求文档转换为增量式开发计划（3–8 个可构建的任务），直接输出文本。
    *   仅写入 `workspaces/<project_id>/agent/`。
*   **Coder Agent（编码智能体）**
    *   通过 patch 方式修改 `workspaces/<project_id>/` 下的 TypeScript/Phaser 文件来实现任务。
    *   优先使用 diff 风格的局部编辑，避免整文件重写。
*   **Verifier Agent（验证智能体）**
    *   运行受限的构建命令，并循环修复直至 `npm run build` 通过。
    *   仅拥有验证与修复所必需的最小命令/写入权限。

### 4. 项目隔离模型（project_id）
所有工作都在隔离的项目目录内完成：

*   **项目根目录**：`workspaces/<project_id>/`
*   **智能体产物**：`workspaces/<project_id>/agent/`
    *   `spec.txt`：需求文档
    *   `plan.txt`：任务列表
    *   `changes.txt`：追加式变更日志（触达文件、简要摘要、构建结果）

### 5. 工具契约（project_id 优先）
所有工具必须要求传入 `project_id`，并且只能在 `workspaces/<project_id>/` 内操作。

*   **Project**
    *   `create_project(prompt) -> { project_id, path }`
    *   `bootstrap_project(project_id)`（将模板复制到项目根目录）
*   **Filesystem**
    *   `read_file(project_id, rel_path)`
    *   `write_file(project_id, rel_path, content)`
    *   `edit_file(project_id, rel_path, search_content, replace_content)`
    *   `list_files(project_id, rel_dir="")`
*   **Commands**
    *   `run_npm(project_id, args)`：带严格 allowlist（仅 install/build/dev/preview）
    *   命令执行必须非 shell、带超时，并对输出做截断

### 6. 从一行需求到可运行游戏（流水线）
对于每个“一行需求”，编排智能体遵循固定流水线以保持行为稳定：

1. 创建 `project_id` 与项目目录。
2. 从 `templates/phaser-starter/` 引导生成项目。
3. 安装依赖一次（`npm install`）。
4. 生成需求文档（spec.txt）。
5. 生成开发计划（plan.txt）。
6. 执行任务（patch 代码），并在每个任务后运行 `npm run build`。
7. 输出最终报告（如何运行、实现了什么、已知限制）。

### 7. 建议的代码布局（下一次重构）
为了支持多智能体角色与“project_id 优先”的工具契约，同时避免复杂度膨胀，推荐的包布局如下：

```text
phaser_agent/
  agent.py                   # root_agent：编排（父）智能体
  agents/
    __init__.py
    spec_agent.py            # Spec 智能体（仅 LLM）
    planner_agent.py         # Planner 智能体（仅 LLM）
    coder_agent.py           # Coder 智能体（LLM + 文件系统工具）
    verifier_agent.py        # Verifier 智能体（LLM + 受限运行工具）
  tools/
    __init__.py
    project.py               # create_project, bootstrap_project
    filesystem.py            # read_file, write_file, edit_file, list_files
    commands.py              # run_npm（allowlist，非 shell）
  config.py                  # 工具限制、忽略列表、超时
  .env
```

原则：
*   `agent.py` 保持为唯一的 ADK 入口；其他角色以子智能体方式导入。
*   只有 Coder/Verifier 拥有写入/命令工具；Spec/Planner 仅计算，不接触 I/O。
*   所有工具都要求 `project_id`，并强制路径只能落在 `workspaces/<project_id>/` 下。

### 8. DeepSeek 集成
智能体通过 ADK 的模型接口接入 DeepSeek。

*   **模型**：`deepseek/deepseek-chat`（通过 LiteLLM 路由）
*   **配置**：在 `.env` 中定义 OpenAI 兼容端点与 API Key

### 9. 安全基线（MVP）
*   路径安全：禁止绝对路径与父目录穿越；解析并验证目标路径始终位于 `workspaces/<project_id>/` 下。
*   命令安全：禁止任意 shell；对命令与参数做 allowlist；强制超时。
*   数据安全：绝不记录 API Key；保持 `.env` 不进入 workspaces。

## 使用方法

### 前置条件
```bash
pip install google-adk
```

### 运行（CLI）
```bash
adk run phaser_agent
```

### 运行（Web UI）
```bash
adk web --port 8000
```
