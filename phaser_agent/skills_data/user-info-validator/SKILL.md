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

## 工作流程
1. 调用 `get_tool_context_info(key="token")` 检查 token
2. 调用 `get_tool_context_info(key="user_id")` 检查 user_id
3. 调用 `get_tool_context_info(key="project_id")` 检查 project_id
4. 调用 `get_tool_context_info(key="api_base_url")` 检查 api_base_url
5. 如果所有字段都存在，返回校验通过
6. 如果有字段缺失，返回缺失字段列表和建议操作
