from pathlib import Path
from typing import Any, Mapping

from google.adk.agents.llm_agent import Agent
from google.adk.tools.skill_toolset import SkillToolset
from .patches import apply_patches
from .token_usage import track_tokens_after_model
from .skills import SkillRegistry
from .agent_config import (
    litellm_from_agent_config,
    prompt_value,
    has_agent_configs,
    parse_agent_configs,
)

apply_patches()

from .tools import (
    create_project,
    bootstrap_project,
    run_npm,
    read_file,
    write_file,
    edit_file,
    list_files,
    scan_files,
    http_get,
    http_post,
)
from .tools.project_manager_tools import (
    get_project_info,
    get_local_project_info,
    create_software,
    pull_project,
    push_project,
)

from .tools.work_space_manager import get_tool_context_info, scan_user_workspace, create_project_workspace

SKILLS_ROOT = Path(__file__).parent / "skills_data"
from .agents.spec_agent import create_spec_agent
from .agents.verifier_agent import create_verifier_agent
from .agents.planner_agent import create_planner_agent
from .agents.coder_agent import create_coder_agent
from .agents.debugger_agent import create_debugger_agent
from .agents.work_space_manager_agent import create_work_space_manager_agent
from .agents.build_agent import create_build_agent
from .agents.project_manager_agent import create_project_manager_agent


def create_root_agent(
    agent_model_configs: Mapping[str, Any],
) -> Agent:
    agent_model_configs, agent_prompt_configs = parse_agent_configs(agent_model_configs)

    spec_agent = create_spec_agent(
        model=litellm_from_agent_config("spec_agent", agent_model_configs),
        description=prompt_value("spec_agent", agent_prompt_configs, "description"),
        instruction=prompt_value("spec_agent", agent_prompt_configs, "instruction"),
    )
    verifier_agent = create_verifier_agent(
        model=litellm_from_agent_config("verifier_agent", agent_model_configs),
        description=prompt_value("verifier_agent", agent_prompt_configs, "description"),
        instruction=prompt_value("verifier_agent", agent_prompt_configs, "instruction"),
    )
    planner_agent = create_planner_agent(
        model=litellm_from_agent_config("planner_agent", agent_model_configs),
        description=prompt_value("planner_agent", agent_prompt_configs, "description"),
        instruction=prompt_value("planner_agent", agent_prompt_configs, "instruction"),
    )
    coder_agent = create_coder_agent(
        model=litellm_from_agent_config("coder_agent", agent_model_configs),
        description=prompt_value("coder_agent", agent_prompt_configs, "description"),
        instruction=prompt_value("coder_agent", agent_prompt_configs, "instruction"),
    )
    debugger_agent = create_debugger_agent(
        model=litellm_from_agent_config("debugger_agent", agent_model_configs),
        description=prompt_value("debugger_agent", agent_prompt_configs, "description"),
        instruction=prompt_value("debugger_agent", agent_prompt_configs, "instruction"),
    )
    work_space_manager_agent = None
    if has_agent_configs("work_space_manager_agent", agent_model_configs, agent_prompt_configs):
        work_space_manager_agent = create_work_space_manager_agent(
            model=litellm_from_agent_config("work_space_manager_agent", agent_model_configs),
            description=prompt_value("work_space_manager_agent", agent_prompt_configs, "description"),
            instruction=prompt_value("work_space_manager_agent", agent_prompt_configs, "instruction"),
        )
    build_agent = create_build_agent(
        model=litellm_from_agent_config("build_agent", agent_model_configs),
        description=prompt_value("build_agent", agent_prompt_configs, "description"),
        instruction=prompt_value("build_agent", agent_prompt_configs, "instruction"),
    )
    project_manager_agent = None
    if has_agent_configs("project_manager_agent", agent_model_configs, agent_prompt_configs):
        project_manager_agent = create_project_manager_agent(
            model=litellm_from_agent_config("project_manager_agent", agent_model_configs),
            description=prompt_value("project_manager_agent", agent_prompt_configs, "description"),
            instruction=prompt_value("project_manager_agent", agent_prompt_configs, "instruction"),
        )
    sub_agents = [
        # work_space_manager_agent,
        # project_manager_agent,
        # spec_agent, 
        # planner_agent, 
        # coder_agent, 
        # verifier_agent, 
        # build_agent
        ]
    # if work_space_manager_agent is not None:
    #     sub_agents.append(work_space_manager_agent)

    skill_registry = SkillRegistry(SKILLS_ROOT)
    skill_toolset = SkillToolset(skills=skill_registry.list_all_skills())

    return Agent(
        model=litellm_from_agent_config("phaser_agent", agent_model_configs),
        name="phaser_agent",
        description=prompt_value("phaser_agent", agent_prompt_configs, "description"),
        after_model_callback=track_tokens_after_model,
        instruction=prompt_value("phaser_agent", agent_prompt_configs, "instruction"),
        sub_agents=sub_agents,
        tools=[
            skill_toolset,
            get_tool_context_info,
            scan_user_workspace,
            create_project_workspace,
            scan_files,
            get_project_info,
            get_local_project_info,
            create_software,
            pull_project,
            push_project,
            http_get,
            http_post,
        ],
    )
