# 创建新项目流程

本文档描述创建新项目的完整流程。

## 流程概览

```
用户信息校验 → 创建项目信息(API) → 创建项目工作空间 → 下载客户端工程模板 → 提交客户端工程版本
```

## 工具清单

| 步骤 | 工具名称 | 来源文件 |
|------|----------|----------|
| 1 | `get_tool_context_info` | 内置工具 |
| 2 | `http_post` | 内置工具 |
| 3 | `create_workspace` | `project_manager_tools.py` |
| 4 | `create_software` | `project_manager_tools.py` |
| 5 | `push_project` | `project_manager_tools.py` |

## 详细步骤

### 步骤 1: 用户信息校验

**目的**: 确保用户已登录且具备创建项目的权限。

**使用工具**: `get_tool_context_info`

**操作**:
1. 使用 `get_tool_context_info(key="user_id")` 获取用户 ID
2. 使用 `get_tool_context_info(key="token")` 获取认证令牌
3. 如果 user_id 或 token 不存在，提示用户先登录

**校验项**:
| 字段 | 必需 | 说明 |
|------|------|------|
| `user_id` | 是 | 用户唯一标识 |
| `token` | 是 | JWT 认证令牌 |
| `api_base_url` | 是 | API 基础地址 |

**失败处理**: 返回错误提示 "请先登录后再创建项目"

---

### 步骤 2: 通过 API 创建项目信息

**目的**: 在后端创建项目记录，获取 project_id。

**使用工具**: `http_post`

**API 调用**:
```
POST /api/v1/projects
```

**请求体**:
```json
{
  "name": "项目名称",
  "description": "项目描述"
}
```

**响应**:
```json
{
  "id": 123,
  "name": "项目名称",
  "description": "项目描述",
  "ownerId": 1001,
  "status": "active"
}
```

**工具调用示例**:
```
http_post(
    url="/api/v1/projects",
    body={"name": "我的游戏项目", "description": "一个 Phaser 游戏"}
)
```

**状态更新**: 将返回的 `id` 存储到 state 中的 `project_id`

---

### 步骤 3: 创建项目工作空间

**目的**: 在本地创建工作空间目录结构。

**使用工具**: `create_workspace` (定义于 `project_manager_tools.py`)

**工具签名**:
```python
def create_workspace(
    software_name: str,
    tool_context: Any = None,
) -> Dict[str, Any]
```

**目录结构**:
```
{workspace_root}/{user_id}/{project_id}/
├── game_project/       # 游戏工程目录
├── artifacts/          # 资产目录
├── build/              # 构建输出目录
└── logs/               # 日志目录
```

**工具调用**:
```
create_workspace(software_name="main-game")
```

**状态更新**:
- `workspace_dir`: 工作空间根目录
- `workspace_game_dir`: 游戏工程目录
- `workspace_artifacts_dir`: 资产目录
- `workspace_build_dir`: 构建输出目录
- `workspace_logs_dir`: 日志目录

---

### 步骤 4: 下载客户端工程模板

**目的**: 从远程下载模板并初始化本地工程。

**使用工具**: `create_software` (定义于 `project_manager_tools.py`)

**工具签名**:
```python
def create_software(
    software_name: str,
    template_name: str = "phaser-blank",
    tool_context: Any = None,
) -> Dict[str, Any]
```

**操作**:
1. 根据模板名称获取模板信息
2. 下载模板归档文件
3. 解压到 `{workspace_game_dir}/{software_name}` 目录
4. 生成初始 `manifest.json`
5. 自动创建软件工程记录（如不存在）

**工具调用**:
```
create_software(
    software_name="main-game",
    template_name="phaser-blank"
)
```

**结果**: 本地工程目录初始化完成，包含基础项目结构

---

### 步骤 5: 提交客户端工程版本

**目的**: 将初始化的工程提交为第一个版本。

**使用工具**: `push_project` (定义于 `project_manager_tools.py`)

**工具签名**:
```python
def push_project(
    software_name: str,
    version_description: str = "",
    tool_context: Any = None,
) -> Dict[str, Any]
```

**操作**:
1. 扫描本地工程文件，计算文件哈希
2. 获取远程 manifest，对比检测变更
3. 上传变更文件到对象存储
4. 创建 manifest 版本记录

**工具调用**:
```
push_project(
    software_name="main-game",
    version_description="初始版本 - 项目创建"
)
```

**结果**: 工程版本记录创建成功，项目创建流程完成

---

## 流程状态图

```
┌─────────────────┐
│ 用户信息校验     │
└────────┬────────┘
         │ 校验通过
         ▼
┌─────────────────┐
│ 创建项目信息     │ ──→ 获得 project_id
│ (http_post)     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 创建工作空间     │ ──→ 获得本地目录路径
│ (create_workspace)│
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 下载工程模板     │ ──→ 本地工程初始化
│ (create_software)│
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 提交工程版本     │ ──→ 版本记录创建
│ (push_project)  │
└────────┬────────┘
         │
         ▼
    ✅ 完成
```

## 错误处理

| 步骤 | 错误场景 | 处理方式 |
|------|----------|----------|
| 1 | 用户未登录 | 提示用户登录 |
| 2 | 项目名称重复 | 提示用户更换名称 |
| 3 | 目录权限不足 | 检查文件系统权限 |
| 4 | 模板不存在 | 提示选择其他模板 |
| 5 | 上传失败 | 重试或检查网络 |

## 回滚策略

如果流程中途失败，需要根据失败步骤进行回滚：

1. **步骤 2 失败**: 无需回滚，项目未创建
2. **步骤 3-4 失败**: 清理已创建的本地目录
3. **步骤 5 失败**: 本地工程已就绪，可稍后重试提交
