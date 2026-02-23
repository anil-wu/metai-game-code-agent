---
name: "workspace-manager"
version: "2.0.0"
description: "工作空间管理技能，准备工作环境"
file_patterns: []
triggers:
  - "准备工作环境"
priority: 6
dependencies:
  - user-info-validator
allowed_tools:
  - get_tool_context_info
  - create_project
  - create_software
  - pull_project
  - push_project
---

# 工作空间管理技能

## 概述

工作空间管理技能，准备工作环境，拉取工程，提交工程变更

## 目录结构规范

| 目录 | 路径 | 说明 |
|------|------|------|
| 项目工作空间根目录 | `workspaces/{user_id}/{project_id}` | 项目隔离根目录 |
| 软件工作目录 | `{workspace_dir}/game_project/{software_name}` | 游戏代码目录 |
| 构件目录 | `{workspace_dir}/artifacts` | 构件存储 |
| 构建输出 | `{workspace_dir}/build_output` | 构建产物 |
| 日志目录 | `{workspace_dir}/logs` | 日志文件 |

## 核心功能

### 准备工作环境流程

在开始任何开发工作之前，需要确保有正确的工作环境。

**流程概览**:
```
用户认证 → 创建工作空间 → 获取项目信息 → 分支处理（创建/拉取工程）
```

---
#### Step 1: 检查用户认证信息

**目的**: 确保用户已登录且认证信息完备。

**使用技能**: `user-info-validator`

---

#### Step 2: 创建工作空间

**目的**: 创建本地工作目录结构。

**使用流程**: [创建工作空间流程](assets/create-workspace-flow.md)

#### Step 3: 获取项目信息

**目的**: 获取远程项目信息及软件工程列表，判断后续操作。

**使用流程**: [获取项目信息流程](assets/get-project-info-flow.md)

**使用工具**:
- `get_project_info` - 获取远程项目信息
- `get_local_project_info` - 获取本地工作空间状态


---

