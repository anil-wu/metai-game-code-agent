# 项目同步流程

本文档描述项目同步（拉取远程变更）的完整流程。

## 流程概览

```
用户信息校验 → 获取项目信息 → 获取本地工程信息 → 拉取远程变更
```

## 前置条件

- 用户已登录（`token`、`user_id` 存在）
- `api_base_url` 已配置
- `project_id` 已设置
- `workspace_game_dir` 已设置

## 工具清单

| 步骤 | 工具名称 | 来源文件 |
|------|----------|----------|
| 1 | `get_tool_context_info` | 内置工具 |
| 2 | `get_project_info` | `project_manager_tools.py` |
| 3 | `get_local_project_info` | `project_manager_tools.py` |
| 4 | `pull_project` | `project_manager_tools.py` |

## 详细步骤

### 步骤 1: 用户信息校验

**目的**: 确保用户已登录且具备同步项目的权限。

**使用工具**: `get_tool_context_info`

**操作**:
```
get_tool_context_info(key="user_id")
get_tool_context_info(key="token")
get_tool_context_info(key="api_base_url")
get_tool_context_info(key="project_id")
get_tool_context_info(key="workspace_game_dir")
```

**校验项**:
| 字段 | 必需 | 说明 |
|------|------|------|
| `user_id` | 是 | 用户唯一标识 |
| `token` | 是 | JWT 认证令牌 |
| `api_base_url` | 是 | API 基础地址 |
| `project_id` | 是 | 项目 ID |
| `workspace_game_dir` | 是 | 游戏工程目录 |

**失败处理**:
- 缺少 `user_id` 或 `token`：返回 "请先登录后再同步项目"
- 缺少 `api_base_url`：返回 "请先配置 api_base_url"
- 缺少 `project_id`：返回 "请先创建或选择项目"
- 缺少 `workspace_game_dir`：返回 "请先创建工作空间"

---

### 步骤 2: 获取项目信息

**目的**: 获取远程项目信息和软件工程列表。

**使用工具**: `get_project_info`

**工具签名**:
```python
def get_project_info(tool_context: Any = None) -> Dict[str, Any]
```

**工具调用**:
```
get_project_info()
```

**返回数据结构**:
```json
{
  "status": "success",
  "status_code": 200,
  "message": "获取项目信息成功",
  "data": {
    "project": {
      "id": 123,
      "name": "My Phaser Game",
      "description": "A platformer game project",
      "status": "active"
    },
    "softwares": [
      {
        "id": 1,
        "projectId": 123,
        "name": "main-game",
        "description": "主游戏工程",
        "technologyStack": "phaser",
        "status": "active"
      }
    ],
    "software_count": 1
  }
}
```

---

### 步骤 3: 获取本地工程信息

**目的**: 扫描本地工作空间，获取软件工程列表和 manifest 信息。

**使用工具**: `get_local_project_info`

**工具签名**:
```python
def get_local_project_info(tool_context: Any = None) -> Dict[str, Any]
```

**工具调用**:
```
get_local_project_info()
```

**返回数据结构**:
```json
{
  "status": "success",
  "status_code": 200,
  "message": "获取本地工程信息成功",
  "data": {
    "workspace_dir": "workspaces/1001/123",
    "workspace_exists": true,
    "software_projects": [
      {
        "name": "main-game",
        "path": "workspaces/1001/123/game_project/main-game",
        "has_manifest": true,
        "manifest": {
          "engine": {"name": "phaser", "version": "3.60.0"},
          "entry": "src/main.ts",
          "files_count": 25,
          "folders": ["src", "assets"]
        }
      }
    ],
    "software_count": 1
  }
}
```

---

### 步骤 4: 拉取远程变更

**目的**: 从后端拉取最新版本的工程文件。

**使用工具**: `pull_project`

**工具签名**:
```python
def pull_project(
    software_name: str,
    version_number: int | None = None,
    tool_context: Any = None,
) -> Dict[str, Any]
```

**参数说明**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `software_name` | string | 是 | 软件工程名称 |
| `version_number` | int | 否 | 指定版本号（默认最新） |

**执行流程**:
```
1. 获取软件工程列表，找到 software_id
2. 获取最新 manifest 文件版本
3. 下载 manifest 内容
4. 对比本地文件，下载变更/缺失的文件
5. 删除远程已删除的文件
6. 更新本地 manifest.json
```

**工具调用**:
```
pull_project(
    software_name="main-game",
    version_number=None
)
```

**返回数据结构**:
```json
{
  "status": "success",
  "status_code": 200,
  "message": "拉取成功",
  "data": {
    "software_name": "main-game",
    "pulled_version": 5,
    "files_updated": 8,
    "files_added": 2,
    "files_unchanged": 15,
    "files_deleted": 0,
    "manifest_updated": true
  }
}
```

**状态更新**:
- `software_id`: 软件工程 ID
- `software_manifest_id`: Manifest ID
- `software_name`: 软件工程名称

---

## 流程状态图

```
┌─────────────────┐
│ 用户信息校验     │
└────────┬────────┘
         │ 校验通过
         ▼
┌─────────────────┐
│ 获取项目信息     │ ──→ 获得软件工程列表
│ (get_project_info)│
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 获取本地工程信息 │ ──→ 获得本地工程状态
│ (get_local_project_info)│
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 拉取远程变更     │ ──→ 文件同步完成
│ (pull_project)  │
└────────┬────────┘
         │
         ▼
    ✅ 完成
```

## 错误处理

| 步骤 | 错误场景 | 处理方式 |
|------|----------|----------|
| 1 | 用户未登录 | 提示用户登录 |
| 1 | project_id 缺失 | 提示用户创建或选择项目 |
| 1 | workspace_game_dir 缺失 | 提示用户创建工作空间 |
| 2 | 项目不存在 | 提示用户项目已被删除 |
| 4 | 软件工程不存在 | 提示用户创建软件工程 |
| 4 | 远程无版本记录 | 提示用户远程暂无版本 |

## 冲突处理

当本地有未提交的修改时：

1. **本地修改的文件远程也有更新**：
   - 远程版本覆盖本地（建议先提交本地变更）

2. **本地新增的文件远程不存在**：
   - 保留本地文件（不在远程 manifest 中）

3. **远程删除的文件本地存在**：
   - 删除本地文件

## 最佳实践

1. **同步前先检查本地变更**：使用 `get_local_project_info` 查看本地状态
2. **有本地修改时先提交**：避免本地修改被远程覆盖
3. **指定版本号回滚**：使用 `version_number` 参数可回滚到指定版本
4. **同步后验证**：检查文件完整性，确保同步成功
