---
name: project-manager
description: 项目管理技能，用于创建项目，获取项目信息和工程信息。
license: MIT
metadata:
  triggers:
    - "新建项目"
    - "获取项目信息"
    - "获取项目工程信息"
  priority: 10
---

# 项目管理技能

此技能帮助你管理 SparkPlay 平台上的项目。

## 适用范围

- 创建新项目
- 获取项目信息
- 获取项目下的软件工程列表

## 流程
1. 先获得项目 ID 使用 `get_tool_context_info(key="project_id")` 查询
2. 如果没有项目 ID，提示用户创建项目或选择项目
3. 根据项目 ID 调用 API 获取项目信息或工程列表


## 项目 API

### 创建项目

**POST** `/api/v1/projects`

请求体：
```json
{
  "userId": 1,
  "name": "项目名称",
  "description": "项目描述"
}
```

响应：
```json
{
  "id": 1,
  "name": "项目名称",
  "description": "项目描述",
  "coverFileId": 0,
  "ownerId": 1,
  "status": "active",
  "createdAt": "2024-01-01T00:00:00Z",
  "updatedAt": "2024-01-01T00:00:00Z"
}
```

### 获取项目信息

**GET** `/api/v1/projects/:id`

### 获取项目列表

**GET** `/api/v1/projects?page=1&pageSize=20`

## 软件工程 API

### 获取项目下的软件工程列表

**GET** `/api/v1/projects/:projectId/softwares?page=1&pageSize=20`

响应：
```json
{
  "list": [
    {
      "id": 1,
      "projectId": 1,
      "name": "游戏工程名称",
      "description": "工程描述",
      "templateId": 0,
      "technologyStack": "Phaser3",
      "status": "active",
      "createdBy": 1,
      "createdAt": "2024-01-01T00:00:00Z",
      "updatedAt": "2024-01-01T00:00:00Z"
    }
  ],
  "page": {
    "page": 1,
    "pageSize": 20,
    "total": 1
  }
}
```

### 创建软件工程

**POST** `/api/v1/projects/:projectId/softwares`

请求体：
```json
{
  "name": "游戏工程名称",
  "description": "工程描述",
  "templateId": 0,
  "technologyStack": "Phaser3",
  "status": "active"
}
```

### 获取软件工程最新版本清单

**GET** `/api/v1/projects/:projectId/software_manifests?software_ids=1,2,3`

## 工作流程

### 创建新项目

1. 确认用户已登录并获取 userId
2. 收集项目名称和描述
3. 调用创建项目 API
4. 返回项目 ID 和基本信息

### 获取项目信息

1. 确认项目 ID
2. 调用获取项目 API
3. 返回项目详细信息

### 获取项目工程信息

1. 确认项目 ID (projectId)
2. 调用获取软件工程列表 API
3. 返回项目下所有软件工程信息

## 状态说明

| 状态 | 说明 |
|------|------|
| `active` | 活跃状态 |
| `archived` | 已归档 |

## 工具使用说明

使用 `http_get` 和 `http_post` 工具调用 API：

### GET 请求

使用 `http_get` 工具获取数据：

```
http_get(url="/api/v1/projects/1")
http_get(url="/api/v1/projects", query={"page": 1, "pageSize": 20})
http_get(url="/api/v1/projects/1/softwares")
```

### POST 请求

使用 `http_post` 工具创建资源：

```
http_post(
    url="/api/v1/projects",
    body={"name": "项目名称", "description": "项目描述"}
)
```

### 注意事项

1. URL 使用相对路径（如 `/api/v1/projects`），系统会自动拼接 `api_base_url`
2. `token` 和 `api_base_url` 从 `tool_context` 自动获取，无需手动传递
3. 请求体 `body` 传入字典，会自动序列化为 JSON
4. 响应格式：`{"status": "success/error", "status_code": 200, "data": {...}, "body": "..."}`

## 注意事项

1. 所有 API 请求需要 JWT 认证，在 Header 中携带 `Authorization: Bearer <token>`
2. 项目名称不能为空
3. 每个项目可以包含多个软件工程（如多个游戏项目）
