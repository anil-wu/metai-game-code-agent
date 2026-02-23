# 创建工作空间流程

本文档描述创建本地工作空间的完整流程。

## 流程概览

```
前置校验 → 检查项目状态 → 创建本地目录结构 → 更新 State 字段 → 返回结果
```

## 工具清单

| 步骤 | 工具名称 | 来源文件 | 状态 |
|------|----------|----------|------|
| 1 | `get_tool_context_info` | `work_space_manager.py` | 已注册 |
| 2 | `create_project_workspace` | `work_space_manager.py` | 已注册 |

---

## 详细步骤

### 步骤 1: 创建本地目录结构

**目的**: 创建完整的工作空间目录结构。

**使用工具**: `create_workspaces`, `check_workspaces`

**工具 1: create_workspaces**

**工具签名**:
```python
def create_workspaces(
    project_id: int,
    tool_context: Any = None,
) -> Dict[str, Any]
```

**工具调用**:
```
create_workspaces(project_id)
```

**工具 2: check_workspaces**

**工具签名**:
```python
def check_workspaces(
    project_id: int,
    tool_context: Any = None,
) -> Dict[str, Any]
```

**工具调用**:
```
check_workspaces(project_id)
```
**用途**: 检查工作空间目录是否存在，用于确认创建结果或诊断问题。

