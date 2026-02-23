# 检查工作空间状态流程

检查本地工作空间目录是否存在。

## 目录结构规范

基于 `user_id` 和 `project_id` 的层级化目录结构：

| 目录 | 路径 | 说明 |
|------|------|------|
| 项目工作空间根目录 | `workspaces/{user_id}/{project_id}` | 项目隔离根目录 |
| 软件工作目录 | `{workspace_dir}/game_project/{software_name}` | 游戏代码目录 |
| 构件目录 | `{workspace_dir}/artifacts` | 构件存储 |
| 构建输出 | `{workspace_dir}/build_output` | 构建产物 |
| 日志目录 | `{workspace_dir}/logs` | 日志文件 |

## 检查流程

```
获取 user_id 和 project_id → 检查工作空间根目录 → 返回状态
```

## 使用工具

| 工具名称 | 来源文件 | 状态 |
|----------|----------|------|
| `check_workspaces` | `project_manager_tools.py` | 已注册 |

## 详细步骤

### 步骤 1: 获取用户和项目信息

从 tool_context 中获取 `user_id` 和 `project_id`。

**失败处理**:
- 缺少 `user_id`：返回 "请先登录"
- 缺少 `project_id`：返回 "请先选择项目"

---

### 步骤 2: 检查工作空间目录

调用 `check_workspaces` 工具检查工作空间目录完整性：

```
result = check_workspaces(project_id=project_id, tool_context=tool_context)
```

---

### 步骤 3: 返回状态报告

```json
{
  "project_id": 2002,
  "workspace_dir": "workspaces/1001/2002",
  "overall_status": "complete",
  "all_dirs_exist": true,
  "missing_dirs": [],
  "check_results": {
    "workspace_dir": {"path": "workspaces/1001/2002", "exists": true},
    "workspace_game_dir": {"path": "workspaces/1001/2002/game_project", "exists": true},
    "workspace_artifacts_dir": {"path": "workspaces/1001/2002/artifacts", "exists": true},
    "workspace_build_dir": {"path": "workspaces/1001/2002/build_output", "exists": true},
    "workspace_logs_dir": {"path": "workspaces/1001/2002/logs", "exists": true}
  }
}
```

**状态判断**:
| 状态 | 条件 | 说明 |
|------|------|------|
| `complete` | 所有目录存在 | 工作空间完整 |
| `incomplete` | 有目录缺失 | 需要创建工作空间 |

---

## 问题处理

| 问题 | 处理方式 |
|------|----------|
| 工作空间目录不存在 | 提示走 [创建工作空间流程](create-workspace-flow.md) |

---

## 相关流程

- [创建工作空间流程](create-workspace-flow.md)
- [创建软件工程流程](create-software-flow.md)
