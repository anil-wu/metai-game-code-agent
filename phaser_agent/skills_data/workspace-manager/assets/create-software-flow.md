# 创建软件工程流程

本文档描述在本地工作空间中创建软件工程的完整流程。

## 流程概览

```
前置校验 → 获取模板信息 → 下载模板归档 → 解压模板 → 创建远程软件记录 → 生成 manifest → 返回结果
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
| 2 | `create_software` | `project_manager_tools.py` | **需新增** |

---

## 详细步骤



### 步骤 1: 创建软件工程

**目的**: 从模板创建软件工程，包括下载模板、解压、创建远程记录。

**使用工具**: `create_software`

**工具签名**:
```python
def create_software(
    software_name: str,
    template_name: str = "phaser-blank",
    tool_context: Any = None,
) -> Dict[str, Any]
```

**参数说明**:
| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `software_name` | str | 是 | 软件工程名称 |
| `template_name` | str | 否 | 模板名称，默认 `2d_game_client_phaser` |
| `tool_context` | Any | 否 | 工具上下文（自动传入） |

**工具调用**:
```
create_software(
    software_name="game_client",
    template_name="2d_game_client_phaser"
)
```
**返回数据结构**:

**成功时**:
```json
{
  "status": "success",
  "status_code": 200,
  "message": "软件工程创建成功",
  "data": {
    "software_name": "main-game",
    "software_dir": "workspaces/1001/123/game_project/main-game",
    "template_name": "phaser-blank",
    "manifest": {
      "engine": {"name": "phaser", "version": "3.60.0"},
      "entry": "src/main.ts",
      "files": [
        {"path": "src/main.ts", "hash": "abc123", "size": 1024}
      ],
      "folders": ["src", "assets"],
      "version": 1
    },
    "software_record": {
      "id": 1,
      "projectId": 123,
      "name": "main-game",
      "technologyStack": "phaser",
      "status": "active"
    }
  }
}
```
---

### 步骤 2: 验证创建结果

**目的**: 确认软件工程创建成功。

**验证项**:
- 软件工程目录存在
- manifest.json 文件存在
- 远程软件记录已创建

**使用工具**: `get_local_project_info`

```
get_local_project_info()
```

**验证逻辑**:
```
if result.data.software_count > 0:
    for project in result.data.software_projects:
        if project.name == software_name and project.has_manifest:
            软件工程创建成功
```

---

