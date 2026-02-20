---
name: "project-manager"
version: "1.0.0"
description: "项目生命周期管理技能，负责项目创建、工作空间初始化、版本同步。当用户需要创建项目、同步项目、提交变更时调用。"
file_patterns: []
triggers:
  - "创建项目"
  - "新建项目"
  - "同步项目"
  - "拉取项目"
  - "推送项目"
  - "提交项目"
  - "工作空间"
priority: 5
dependencies: []
allowed_tools:
  - get_tool_context_info
  - http_get
  - http_post
  - create_workspace
  - create_software
  - get_project_info
  - get_local_project_info
  - pull_project
  - push_project
---

# 项目管理技能

## 概述

此技能帮助你管理项目的完整生命周期，包括项目创建、工作空间初始化、版本同步（拉取/推送）。

## 状态依赖

执行任何操作前，需验证以下状态字段：

| 字段 | 必需 | 说明 |
|------|------|------|
| `token` | 是 | JWT 认证令牌 |
| `user_id` | 是 | 用户 ID |
| `api_base_url` | 是 | API 基础地址 |
| `project_id` | 可选 | 项目 ID（创建后设置） |
| `workspace_dir` | 可选 | 工作空间根目录 |
| `workspace_game_dir` | 可选 | 游戏工程目录 |

## 项目与工作环境准备流程

```
用户信息校验 → 项目判断 → 执行对应流程
```

### 1. 用户信息校验

**前置检查**:
- 没有 `user_id` 或 `token`：提示用户登录
- 没有 `api_base_url`：提示用户配置 `api_base_url`

**使用工具**: `get_tool_context_info`

```
get_tool_context_info(key="user_id")
get_tool_context_info(key="token")
get_tool_context_info(key="api_base_url")
```

### 2. 项目判断

- **没有 `project_id`** → 执行项目新建流程
- **有 `project_id`** → 执行项目同步流程

## 项目新建流程

详情查看 [assets/create-project-workflow.md](assets/create-project-workflow.md)

### 流程概览

```
创建项目信息(API) → 创建项目工作空间 → 下载客户端工程模板 → 提交客户端工程版本
```

### 工具清单

| 步骤 | 工具名称 | 说明 |
|------|----------|------|
| 1 | `http_post` | 创建项目记录 |
| 2 | `create_workspace` | 创建本地工作空间 |
| 3 | `create_software` | 下载模板初始化工程 |
| 4 | `push_project` | 提交初始版本 |

### 详细步骤

#### 步骤 1: 创建项目信息

```
http_post(
    url="/api/v1/projects",
    body={"name": "项目名称", "description": "项目描述"}
)
```

**状态更新**: 将返回的 `id` 存储到 `project_id`

#### 步骤 2: 创建工作空间

```
create_workspace(software_name="main-game")
```

**目录结构**:
```
{workspace_root}/{user_id}/{project_id}/
├── game_project/       # 游戏工程目录
├── artifacts/          # 资产目录
├── build/              # 构建输出目录
└── logs/               # 日志目录
```

#### 步骤 3: 下载工程模板

```
create_software(
    software_name="main-game",
    template_name="phaser-blank"
)
```

#### 步骤 4: 提交初始版本

```
push_project(
    software_name="main-game",
    version_description="初始版本 - 项目创建"
)
```

## 项目拉取流程

详情查看 [assets/sync-project-workflow.md](assets/sync-project-workflow.md)

### 流程概览

```
获取项目信息 → 获取本地工程信息 → 拉取远程变更
```

### 详细步骤

#### 步骤 1: 获取项目信息

```
get_project_info()
```

返回项目详情和软件工程列表。

#### 步骤 2: 获取本地工程信息

```
get_local_project_info()
```

返回本地工作空间状态和软件工程列表。

#### 步骤 3: 拉取远程变更

```
pull_project(
    software_name="main-game",
    version_number=None  # None 表示最新版本
)
```

## 项目提交流程

详情查看 [assets/commit-project-workflow.md](assets/commit-project-workflow.md)

### 流程概览

```
检查本地变更 → 上传变更文件 → 创建版本记录
```

### 详细步骤

#### 步骤 1: 检查本地工程

```
get_local_project_info()
```

#### 步骤 2: 推送变更

```
push_project(
    software_name="main-game",
    version_description="版本描述"
)
```

## 工具参考

| 工具 | 功能 | 必需状态 |
|------|------|----------|
| `get_project_info` | 获取远程项目信息 | `project_id`, `api_base_url` |
| `create_project` | 创建远程项目 + 本地工作空间 | `user_id`, `api_base_url` |
| `get_local_project_info` | 扫描本地工作空间 | `workspace_dir` |
| `create_workspace` | 创建本地工作空间 | `user_id` |
| `create_software` | 从模板初始化工程 | `workspace_game_dir`, `project_id` |
| `pull_project` | 拉取远程版本 | `project_id`, `workspace_game_dir` |
| `push_project` | 推送本地变更 | `project_id`, 本地工程存在 |

## 错误处理

| 场景 | 处理方式 |
|------|----------|
| 用户未登录 | 提示用户登录 |
| `api_base_url` 缺失 | 提示用户配置 API 地址 |
| `workspace_game_dir` 缺失 | 建议先调用 `create_workspace` |
| `project_id` 缺失 | 建议先调用 `create_project` |
| 本地软件工程不存在 | 建议先调用 `create_software` |

## 最佳实践

1. **始终先校验用户信息**：确保 `token`、`user_id`、`api_base_url` 存在
2. **按流程顺序执行**：新建 → 工作空间 → 模板 → 提交
3. **处理错误时提供明确指引**：告诉用户下一步该做什么
4. **版本描述要清晰**：使用有意义的版本描述便于追溯
