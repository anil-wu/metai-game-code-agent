# 拉取软件工程流程

本文档描述从远程拉取软件工程到本地的完整流程。

## 流程概览

```
前置校验 → 获取软件工程列表 → 获取远程 manifest → 对比版本 → 下载变更文件 → 更新本地 manifest → 返回结果
```

## 前置条件

- 用户已登录（`token`、`user_id` 存在）
- `api_base_url` 已配置
- `project_id` 已设置
- 工作空间已创建（`workspace_game_dir` 存在）

## 工具清单

| 步骤 | 工具名称 | 来源文件 | 状态 |
|------|----------|----------|------|
| 1 | `get_tool_context_info` | `work_space_manager.py` | 已注册 |
| 2 | `pull_project` | `project_manager_tools.py` | **需新增** |
| 3 | `get_project_info` | `project_manager_tools.py` | **需新增** |

---

## 详细步骤

### 步骤 1: 前置校验

**目的**: 确保工作空间已创建且具备拉取软件工程的权限。

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
- 缺少 `project_id`：返回 "请先创建或选择项目"
- 缺少 `workspace_game_dir`：返回 "请先创建工作空间"

---

### 步骤 2: 检查版本状态

**目的**: 对比本地与远程版本，判断是否需要拉取。

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
      "name": "My Phaser Game"
    },
    "softwares": [
      {
        "id": 1,
        "projectId": 123,
        "name": "main-game",
        "versionNumber": 7
      }
    ]
  }
}
```

**版本对比逻辑**:
```
local_version = 本地 manifest.version
remote_version = 远程 softwares[0].versionNumber

if local_version >= remote_version:
    无需拉取，已是最新版本
else:
    需要拉取，落后 remote_version - local_version 个版本
```

---

### 步骤 3: 拉取软件工程

**目的**: 从远程拉取指定版本的软件工程文件。

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
| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `software_name` | str | 是 | 软件工程名称 |
| `version_number` | int | 否 | 指定版本号，默认拉取最新版本 |
| `tool_context` | Any | 否 | 工具上下文（自动传入） |

**工具调用**:
```
pull_project(
    software_name="main-game"
)
```

**工具内部流程**:

1. **获取软件工程列表**
   - 调用 `GET /api/v1/projects/{project_id}/softwares`
   - 查找指定名称的软件工程 ID

2. **获取远程 manifest**
   - 调用 `GET /api/v1/projects/{project_id}/software_manifests?software_ids={software_id}`
   - 获取最新版本的 manifest 文件 ID

3. **下载 manifest 内容**
   - 调用 `GET /api/v1/files/{manifest_file_id}/content`
   - 解析 manifest JSON

4. **对比文件差异**
   - 对比远程 manifest 与本地 manifest
   - 识别需要下载的文件

5. **下载变更文件**
   - 遍历远程 manifest.files
   - 下载每个文件到本地

6. **更新本地 manifest**
   - 将远程 manifest 写入本地 manifest.json

**返回数据结构**:

**成功时**:
```json
{
  "status": "success",
  "status_code": 200,
  "message": "拉取成功",
  "data": {
    "software_name": "main-game",
    "pulled_version": 7,
    "previous_version": 5,
    "files_synced": 25,
    "files_added": 3,
    "files_modified": 5,
    "files_deleted": 1,
    "software_dir": "workspaces/1001/123/game_project/main-game"
  }
}
```

**已是最新时**:
```json
{
  "status": "success",
  "status_code": 200,
  "message": "已是最新版本",
  "data": {
    "software_name": "main-game",
    "current_version": 7,
    "is_latest": true
  }
}
```

**失败时**:
```json
{
  "status": "error",
  "status_code": 404,
  "message": "软件工程不存在: main-game",
  "data": null
}
```

---

### 步骤 4: 验证拉取结果

**目的**: 确认文件同步成功。

**验证项**:
- 本地 manifest 版本号已更新
- 文件数量与远程 manifest 一致

**使用工具**: `get_local_project_info`

```
get_local_project_info()
```

---

## 流程状态图

```
┌─────────────────┐
│ 前置校验         │
│ (get_tool_context_info)│
└────────┬────────┘
         │ 校验通过
         ▼
┌─────────────────┐
│ 检查版本状态     │
│ (get_project_info)│
└────────┬────────┘
         │
         ▼
    ┌────────────┐
    │ 是否需要拉取？│
    └────┬───┬───┘
         │   │ 否
         │   └──→ 返回 "已是最新版本"
         │ 是
         ▼
┌─────────────────┐
│ 获取软件工程列表 │ ──→ 不存在 → 返回错误
└────────┬────────┘
         │ 存在
         ▼
┌─────────────────┐
│ 获取远程 manifest│ ──→ 无版本记录 → 返回错误
└────────┬────────┘
         │ 获取成功
         ▼
┌─────────────────┐
│ 对比文件差异     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 下载变更文件     │ ──→ 下载失败 → 返回错误
└────────┬────────┘
         │ 下载成功
         ▼
┌─────────────────┐
│ 更新本地 manifest│
└────────┬────────┘
         │
         ▼
    ✅ 拉取完成
```

---

## 文件同步策略

| 场景 | 处理方式 |
|------|----------|
| 远程新增文件 | 下载到本地 |
| 远程修改文件 | 覆盖本地文件 |
| 远程删除文件 | 删除本地文件 |
| 本地有未提交变更 | 提示用户先提交或放弃变更 |

---

## 错误处理

| 步骤 | 错误场景 | 处理方式 |
|------|----------|----------|
| 1 | 工作空间不存在 | 提示先创建工作空间 |
| 1 | project_id 缺失 | 提示先创建或选择项目 |
| 2 | 软件工程不存在 | 提示先创建软件工程 |
| 3 | 远程无版本记录 | 提示软件工程尚未推送 |
| 4 | 下载失败 | 返回错误，建议检查网络 |
| 5 | 本地有未提交变更 | 提示用户先处理变更 |

---

## 注意事项

1. **版本选择**: 可指定 `version_number` 拉取特定版本
2. **变更保护**: 拉取前检查本地是否有未提交变更
3. **网络依赖**: 拉取过程需要下载文件，确保网络畅通
4. **版本回退**: 指定较低版本号可实现版本回退

---

## 相关流程

- [创建软件工程流程](create-software-flow.md)
- [提交变更流程](commit-changes-flow.md)
- [检查工作空间状态](check-workspace-status.md)
