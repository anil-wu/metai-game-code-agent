# 项目提交流程

本文档描述项目提交（推送本地变更）的完整流程。

## 流程概览

```
用户信息校验 → 获取本地工程信息 → 扫描变更文件 → 上传变更文件 → 创建版本记录
```

## 前置条件

- 用户已登录（`token`、`user_id` 存在）
- `api_base_url` 已配置
- `project_id` 已设置
- `workspace_game_dir` 已设置
- 本地软件工程存在

## 工具清单

| 步骤 | 工具名称 | 来源文件 |
|------|----------|----------|
| 1 | `get_tool_context_info` | 内置工具 |
| 2 | `get_local_project_info` | `project_manager_tools.py` |
| 3 | `push_project` | `project_manager_tools.py` |

## 详细步骤

### 步骤 1: 用户信息校验

**目的**: 确保用户已登录且具备提交项目的权限。

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
- 缺少 `user_id` 或 `token`：返回 "请先登录后再提交项目"
- 缺少 `api_base_url`：返回 "请先配置 api_base_url"
- 缺少 `project_id`：返回 "请先创建或选择项目"
- 缺少 `workspace_game_dir`：返回 "请先创建工作空间"

---

### 步骤 2: 获取本地工程信息

**目的**: 扫描本地工作空间，确认软件工程存在。

**使用工具**: `get_local_project_info`

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
          "files": [...],
          "folders": ["src", "assets"]
        }
      }
    ],
    "software_count": 1
  }
}
```

**检查项**:
- 确认要提交的软件工程存在
- 如果不存在，提示用户先创建软件工程

---

### 步骤 3: 推送变更

**目的**: 将本地变更推送到后端，创建新版本。

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
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `software_name` | string | 是 | 软件工程名称 |
| `version_description` | string | 否 | 版本描述 |

**执行流程**:
```
1. 获取软件工程列表，找到 software_id
2. 获取远程 manifest，对比检测变更
3. 扫描本地工程目录，计算文件哈希
4. 对变更文件：
   a. 调用 POST /api/v1/files/preupload 获取上传 URL
   b. 上传文件到 OSS
   c. 确认上传完成
5. 更新 manifest.json 并上传
6. 调用 POST /api/v1/software-manifests 创建版本记录
```

**工具调用**:
```
push_project(
    software_name="main-game",
    version_description="添加新游戏场景"
)
```

**返回数据结构**:
```json
{
  "status": "success",
  "status_code": 200,
  "message": "推送成功",
  "data": {
    "software_name": "main-game",
    "new_version": 6,
    "files_uploaded": 3,
    "files_modified": 2,
    "files_added": 1,
    "files_unchanged": 18,
    "manifest_id": 456,
    "version_number": 6
  }
}
```

---

## 流程状态图

```
┌─────────────────┐
│ 用户信息校验     │
└────────┬────────┘
         │ 校验通过
         ▼
┌─────────────────┐
│ 获取本地工程信息 │ ──→ 确认工程存在
│ (get_local_project_info)│
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 推送变更        │ ──→ 版本记录创建
│ (push_project)  │
└────────┬────────┘
         │
         ▼
    ✅ 完成
```

## 变更检测逻辑

### 排除目录
以下目录不会被扫描：
- `node_modules`
- `.git`
- `__pycache__`
- `.cache`
- `dist`
- `build`

### 排除文件
以下文件不会被上传：
- `.DS_Store`
- `Thumbs.db`
- `manifest.json`

### 变更类型

| 类型 | 说明 |
|------|------|
| `added` | 本地新增，远程不存在 |
| `modified` | 本地修改，哈希值不同 |
| `deleted` | 远程存在，本地不存在 |

### 哈希计算
使用 SHA-256 算法计算文件哈希值，用于检测文件变更。

## 错误处理

| 步骤 | 错误场景 | 处理方式 |
|------|----------|----------|
| 1 | 用户未登录 | 提示用户登录 |
| 1 | project_id 缺失 | 提示用户创建或选择项目 |
| 2 | 本地工程不存在 | 提示用户创建软件工程 |
| 3 | 软件工程不存在 | 提示用户先创建软件工程记录 |
| 3 | 无变更需要推送 | 提示用户当前无变更 |
| 3 | 上传失败 | 重试或检查网络 |

## 版本描述建议

良好的版本描述有助于追溯变更历史：

| 场景 | 示例描述 |
|------|----------|
| 初始创建 | "初始版本 - 项目创建" |
| 新增功能 | "添加玩家移动功能" |
| 修复问题 | "修复碰撞检测问题" |
| 优化改进 | "优化渲染性能" |
| 资源更新 | "更新游戏素材资源" |

## 最佳实践

1. **提交前检查变更**：使用 `get_local_project_info` 确认要提交的内容
2. **写清晰的版本描述**：便于后续追溯和回滚
3. **频繁小提交**：避免大量变更一次性提交
4. **提交前测试**：确保代码可运行，避免提交错误版本
5. **同步后再提交**：先拉取远程变更，解决冲突后再提交

## 回滚策略

如果需要回滚到之前的版本：

1. 使用 `pull_project` 指定 `version_number` 参数
2. 拉取指定版本后，重新提交作为新版本

```
pull_project(
    software_name="main-game",
    version_number=5  # 回滚到版本 5
)

push_project(
    software_name="main-game",
    version_description="回滚到版本 5"
)
```
