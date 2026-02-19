---
name: user-info-validator
description: 用户信息校验技能，检查当前用户认证信息和项目上下文是否完备。当需要验证用户登录状态、检查项目权限或确认用户信息完整性时触发。
license: MIT
metadata:
  triggers:
    - "用户信息校验"
    - "检查用户认证信息"
    - "检查用户 id"
    - "检查项目 id"
    - "检查 base url"
  priority: 15
---

# 用户信息校验技能

此技能帮助你校验当前用户的信息是否完备，确保后续操作能够正常执行。

## 适用范围

- 验证 user_id 是否有效
- 验证 project_id 是否有效
- 验证 token 是否有效
- 验证 api_base_url 是否有效

## 使用工具

使用 `get_tool_context_info` 工具查询 tool_context 中的信息。

### 工具参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `key` | string | 是 | 要查询的字段名称 |

### 查询示例

**查询单个字段：**
```
get_tool_context_info(key="project_id")
```

返回示例：
```json
{
  "status": "success",
  "message": "字段 'project_id' 查询成功",
  "data": {
    "key": "project_id",
    "value": 123
  }
}
```

**字段不存在时：**
```
get_tool_context_info(key="project_id")
```

返回示例：
```json
{
  "status": "success",
  "message": "字段 'project_id' 不存在或为空",
  "data": null
}
```

**未提供 key 参数时：**
```
get_tool_context_info()
```

返回示例：
```json
{
  "status": "error",
  "status_code": 400,
  "message": "请提供要查询的字段名称 (key 参数)",
  "data": null
}
```

## 用户信息字段说明

### 必需字段

| 字段 | 类型 | 说明 | 来源 |
|------|------|------|------|
| `token` | string | JWT 认证令牌 | WebSocket 认证时获取 |
| `user_id` | int | 用户 ID | WebSocket 认证时获取 |
| `project_id` | int | 项目 ID | 用户选择项目时设置 |
| `api_base_url` | string | API 服务基础地址 | 环境变量 `SPARKX_API_BASE_URL` |

## 校验流程

### 1. 查询单个字段

调用 `get_tool_context_info(key="字段名")` 查询特定字段。

### 2. 检查必需字段

依次检查以下字段：
- `token` - 存在则为 `"***"`
- `user_id` - 存在则为整数值
- `project_id` - 存在则为整数值
- `api_base_url` - 存在则为 `"***"`

### 3. 处理缺失字段

| 缺失字段 | 影响 | 建议操作 |
|----------|------|----------|
| `token` | 无法调用需要认证的 API | 提示用户重新登录 |
| `user_id` | 无法关联用户操作 | 提示用户重新登录 |
| `project_id` | 无法执行项目相关操作 | 提示用户创建或选择项目 |
| `api_base_url` | 无法连接后端服务 | 检查服务配置 |

## 工作流程

### 校验用户信息完备性

1. 调用 `get_tool_context_info(key="token")` 检查 token
2. 调用 `get_tool_context_info(key="user_id")` 检查 user_id
3. 调用 `get_tool_context_info(key="project_id")` 检查 project_id
4. 调用 `get_tool_context_info(key="api_base_url")` 检查 api_base_url
5. 如果所有字段都存在，返回校验通过
6. 如果有字段缺失，返回缺失字段列表和建议操作

### 查询单个字段

1. 调用 `get_tool_context_info(key="字段名")` 查询特定字段
2. 如果 data 为 null，表示字段不存在或为空
3. 如果 data 有值，表示字段存在

## 注意事项

1. `token` 和 `api_base_url` 字段返回值为 `"***"`，不暴露实际值
2. `user_id` 和 `project_id` 返回实际整数值
3. 敏感信息不应记录到日志
4. 校验失败时应提供清晰的错误提示和恢复建议
