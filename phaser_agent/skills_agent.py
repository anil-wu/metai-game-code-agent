"""
Skills Agent - 提供原子工具能力的 Agent

只包含 skills 相关的工具，没有子 agent。
工具包括：
- SkillToolset: ADK 技能系统（通过 SKILL.md 定义）
- API Service 请求封装
- 工作空间文件操作封装
"""

from pathlib import Path
from typing import Any, Mapping

import litellm
from google.adk.agents.llm_agent import LlmAgent
from google.adk.tools.skill_toolset import SkillToolset
from .skills import SkillRegistry

from .tools.skills import (
    api_get,
    api_post,
    api_put,
    api_delete,
    api_patch,
    api_request,
    workspace_read,
    workspace_write,
    workspace_edit,
    workspace_list,
    workspace_search,
    workspace_mkdir,
    workspace_delete,
    workspace_move,
    workspace_scan,
    workspace_create_file,
    workspace_create_directory,
    workspace_exists,
    workspace_get_info,
    get_tool_context_info,
)
from .tools.project_manager_tools import (
    create_workspaces,
    check_workspaces,
    get_project_info,
    get_local_project_info,
    create_software,
    pull_project,
)
from .token_usage import track_tokens_after_model
from .agent_config import (
    litellm_from_agent_config,
    prompt_value,
    parse_agent_configs,
)

SKILLS_ROOT = Path(__file__).parent / "skills_data"

SKILLS_AGENT_TOOLS = [
    api_get,
    api_post,
    api_put,
    api_delete,
    api_patch,
    api_request,
    workspace_read,
    workspace_write,
    workspace_edit,
    workspace_list,
    workspace_search,
    workspace_mkdir,
    workspace_delete,
    workspace_move,
    workspace_scan,
    workspace_create_file,
    workspace_create_directory,
    workspace_exists,
    workspace_get_info,
    create_workspaces,
    check_workspaces,
    get_project_info,
    get_local_project_info,
    create_software,
    pull_project,
    get_tool_context_info,
]

# litellm._turn_on_debug()

def create_skills_agent(
    agent_model_configs: Mapping[str, Any],
) -> LlmAgent:
    """
    创建 Skills Agent。

    Args:
        agent_model_configs: Agent 配置，支持两种格式：
            1. 原始 payload（包含 models、agentinfos 或 list）
            2. 解析后的 model_configs 和 prompt_configs

    Returns:
        配置好的 LlmAgent 实例
    """
    agent_model_configs, agent_prompt_configs = parse_agent_configs(agent_model_configs)

    skill_registry = SkillRegistry(SKILLS_ROOT)
    skill_toolset = SkillToolset(skills=skill_registry.list_all_skills())

    return LlmAgent(
        model=litellm_from_agent_config("skills_agent", agent_model_configs),
        name="skills_agent",
        description=prompt_value("skills_agent", agent_prompt_configs, "description"),
        after_model_callback=track_tokens_after_model,
        instruction=prompt_value("skills_agent", agent_prompt_configs, "instruction"),
        tools=[
            skill_toolset,
            *SKILLS_AGENT_TOOLS,
        ],
    )
