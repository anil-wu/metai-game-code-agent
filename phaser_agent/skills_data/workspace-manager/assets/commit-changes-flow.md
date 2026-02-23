# 提交工程变更流程

本文档描述将本地软件工程变更提交到远程的完整流程。

## 流程概览

```
前置校验 → 检查本地变更 → 用户确认 → 扫描文件变更 → 上传文件 → 创建新版本 manifest → 更新远程记录 → 返回结果
```

## 前置条件

- 用户已登录（`token`、`user_id` 存在）
- `api_base_url` 已配置
- `project_id` 已设置
- 工作空间已创建（`workspace_game_dir` 存在）
- 软件工程已创建

## 工具清单

| 步骤 | 工具名称 | 来源文件 | 状态 |
|------|----------|----------|------|
| 1 | `get_tool_context_info` | `work_space_manager.py` | 已注册 |
| 2 | `get_local_project_info` | `project_manager_tools.py` | **需新增** |
| 3 | `push_project` | `project_manager_tools.py` | **需新增** |

---

## 详细步骤

### 步骤 1: 前置校验

**目的**: 确保工作空间和软件工程已创建。

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

### 步骤 2: 检查本地变更

**目的**: 检测本地是否有未提交的变更。

**使用工具**: `get_local_project_info`

**工具调用**:
```
get_local_project_info()
```

**变更检测逻辑**:

基于本地 manifest 和实际文件对比：

```
manifest_files = 本地 manifest.files 列表
local_files = 扫描本地目录获取的文件列表

added_files = local_files 中存在但 manifest_files 中不存在的文件
deleted_files = manifest_files 中存在但 local_files 中不存在的文件
modified_files = hash 值不一致的文件

has_changes = len(added_files) + len(deleted_files) + len(modified_files) > 0
```

**变更类型说明**:
| 类型 | 说明 | 检测方式 |
|------|------|----------|
| 新增文件 | 本地新增但未记录到 manifest | 本地有，manifest 无 |
| 删除文件 | manifest 记录但本地已删除 | manifest 有，本地无 |
| 修改文件 | 文件内容已变更 | hash 不一致 |

**无变更时**:
```json
{
  "status": "success",
  "message": "没有需要提交的变更",
  "data": {
    "has_changes": false
  }
}
```

---

### 步骤 3: 用户确认

**目的**: 在提交变更前获取用户确认。

**确认内容**:
- 显示变更摘要（新增、修改、删除文件数量）
- 询问用户是否继续提交
- 可选：输入版本描述

**确认提示格式**:
```
检测到以下变更：
- 新增文件: 2 个
- 修改文件: 3 个
- 删除文件: 1 个

是否提交这些变更？(y/n)
请输入版本描述（可选）:
```

**用户选择**:
- 确认：继续提交流程
- 取消：终止流程，返回状态报告

---

### 步骤 4: 提交变更

**目的**: 将本地变更推送到远程服务器。

**使用工具**: `push_project`

**工具签名**:
```python
def push_project(
    software_name: str,
    version_description: str = "",
    tool_context: Any = None,
) -> Dict[str, Any]
```

**参数说明**:
| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `software_name` | str | 是 | 软件工程名称 |
| `version_description` | str | 否 | 版本描述 |
| `tool_context` | Any | 否 | 工具上下文（自动传入） |

**工具调用**:
```
push_project(
    software_name="main-game",
    version_description="添加新功能：角色跳跃动画"
)
```

**工具内部流程**:

1. **获取软件工程列表**
   - 调用 `GET /api/v1/projects/{project_id}/softwares`
   - 查找指定名称的软件工程 ID

2. **获取远程最新版本**
   - 调用 `GET /api/v1/projects/{project_id}/software_manifests?software_ids={software_id}`
   - 获取最新版本号

3. **扫描本地文件**
   - 遍历软件工程目录
   - 计算每个文件的 hash

4. **对比变更**
   - 对比本地文件与远程 manifest
   - 识别新增、修改、删除的文件

5. **上传文件**
   - 调用 `POST /api/v1/files/upload` 上传变更文件
   - 获取文件 ID

6. **创建新版本 manifest**
   - 构建新的 manifest JSON
   - 版本号 +1
   - 上传 manifest 文件

7. **更新远程记录**
   - 调用 `POST /api/v1/projects/{project_id}/software_manifests`
   - 创建新版本记录

**返回数据结构**:

**成功时**:
```json
{
  "status": "success",
  "status_code": 200,
  "message": "提交成功",
  "data": {
    "software_name": "main-game",
    "new_version": 8,
    "previous_version": 7,
    "files_uploaded": 5,
    "added_files": ["src/jump.ts", "assets/jump.png"],
    "modified_files": ["src/player.ts", "src/main.ts"],
    "deleted_files": ["src/old_logic.ts"],
    "version_description": "添加新功能：角色跳跃动画"
  }
}
```

**无变更时**:
```json
{
  "status": "success",
  "status_code": 200,
  "message": "没有需要提交的变更",
  "data": {
    "software_name": "main-game",
    "current_version": 7,
    "has_changes": false
  }
}
```

**失败时**:
```json
{
  "status": "error",
  "status_code": 404,
  "message": "本地工程不存在: main-game",
  "data": null
}
```

---

### 步骤 5: 验证提交结果

**目的**: 确认变更已成功提交。

**验证项**:
- 本地 manifest 版本号已更新
- 远程版本记录已创建

**使用工具**: `get_project_info`

```
get_project_info()
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
│ 检查本地变更     │
│ (get_local_project_info)│
└────────┬────────┘
         │
         ▼
    ┌────────────┐
    │ 是否有变更？ │
    └────┬───┬───┘
         │   │ 否
         │   └──→ 返回 "没有需要提交的变更"
         │ 是
         ▼
┌─────────────────┐
│ 用户确认         │ ──→ 取消 → 终止流程
└────────┬────────┘
         │ 确认
         ▼
┌─────────────────┐
│ 获取软件工程列表 │ ──→ 不存在 → 返回错误
└────────┬────────┘
         │ 存在
         ▼
┌─────────────────┐
│ 扫描本地文件     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 上传变更文件     │ ──→ 上传失败 → 返回错误
└────────┬────────┘
         │ 上传成功
         ▼
┌─────────────────┐
│ 创建新版本 manifest│
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 更新远程记录     │ ──→ API 失败 → 返回错误
└────────┬────────┘
         │
         ▼
    ✅ 提交完成
```

---

## 版本描述建议

| 变更类型 | 描述示例 |
|----------|----------|
| 新功能 | "添加角色跳跃功能" |
| Bug 修复 | "修复碰撞检测问题" |
| 重构 | "重构玩家控制模块" |
| 资源更新 | "更新角色精灵图" |
| 配置变更 | "更新游戏配置参数" |

---

## 错误处理

| 步骤 | 错误场景 | 处理方式 |
|------|----------|----------|
| 1 | 工作空间不存在 | 提示先创建工作空间 |
| 1 | project_id 缺失 | 提示先创建或选择项目 |
| 2 | 软件工程不存在 | 提示先创建软件工程 |
| 2 | manifest 缺失 | 提示先拉取或初始化工程 |
| 4 | 上传失败 | 返回错误，建议检查网络 |
| 5 | API 创建失败 | 返回错误，建议检查权限 |

---

## 注意事项

1. **用户确认**: 提交变更前必须获取用户确认
2. **版本描述**: 建议提供有意义的版本描述，便于后续追溯
3. **网络依赖**: 提交过程需要上传文件，确保网络畅通
4. **版本递增**: 每次提交版本号自动 +1
5. **冲突处理**: 如果远程有新版本，建议先拉取再提交

---

## 相关流程

- [拉取软件工程流程](pull-software-flow.md)
- [检查工作空间状态](check-workspace-status.md)
- [创建软件工程流程](create-software-flow.md)
