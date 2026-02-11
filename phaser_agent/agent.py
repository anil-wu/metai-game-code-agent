from typing import Any, Mapping

from google.adk.agents.llm_agent import Agent
from google.adk.models import LiteLlm
from .patches import apply_patches
from .config import LITELLM_MODEL, LITELLM_KWARGS
from .token_usage import track_tokens_after_model

# Apply patches to fix LiteLLM issues with DeepSeek (list-wrapped tool args)
apply_patches()

from .tools import create_project, bootstrap_project, run_npm, read_file, write_file, edit_file, list_files
from .agents.spec_agent import create_spec_agent
from .agents.verifier_agent import create_verifier_agent
from .agents.planner_agent import create_planner_agent
from .agents.coder_agent import create_coder_agent
from .agents.debugger_agent import create_debugger_agent

# Instantiate LiteLlm directly with the provider-prefixed model name
# This follows the ADK documentation for LiteLLM integration: https://adk.wiki/agents/models/litellm/
# And DeepSeek provider docs: https://docs.litellm.ai/docs/providers/deepseek
# Using 'deepseek/' prefix tells LiteLLM to use the native DeepSeek provider and DEEPSEEK_API_KEY

def _litellm_from_agent_config(
    agent_name: str,
    agent_model_configs: Mapping[str, Mapping[str, Any]] | None,
) -> LiteLlm:
    if agent_model_configs and agent_name in agent_model_configs:
        cfg = agent_model_configs[agent_name]
        model = cfg.get("model") or LITELLM_MODEL
        kwargs = cfg.get("kwargs") or {}
        if not isinstance(kwargs, dict):
            kwargs = {}
        safe_kwargs = dict(kwargs)
        if "api_key" in safe_kwargs and safe_kwargs["api_key"]:
            safe_kwargs["api_key"] = "***"
        print(f"Creating LiteLlm for {agent_name} with model={model} and kwargs={kwargs}")
        return LiteLlm(model=str(model), **kwargs)
    return LiteLlm(model=LITELLM_MODEL, **LITELLM_KWARGS)


def create_root_agent(
    agent_model_configs: Mapping[str, Mapping[str, Any]] | None = None,
) -> Agent:
    spec_agent = create_spec_agent(model=_litellm_from_agent_config("spec_agent", agent_model_configs))
    verifier_agent = create_verifier_agent(
        model=_litellm_from_agent_config("verifier_agent", agent_model_configs)
    )
    planner_agent = create_planner_agent(model=_litellm_from_agent_config("planner_agent", agent_model_configs))
    coder_agent = create_coder_agent(model=_litellm_from_agent_config("coder_agent", agent_model_configs))
    debugger_agent = create_debugger_agent(model=_litellm_from_agent_config("debugger_agent", agent_model_configs))

    return Agent(
        model=_litellm_from_agent_config("phaser_agent", agent_model_configs),
        name="phaser_agent",
        description="Orchestrator Agent for Phaser 3 Game Development",
        after_model_callback=track_tokens_after_model,
        instruction="""
        You are the Orchestrator Agent for Phaser 3 game development.

        Always operate within a workspace `project_id`.

        Bootstrap (once per project):
        - create_project(prompt)
        - bootstrap_project(project_id)
        - run_npm(project_id, "install")

        Build a game incrementally:
        - Ask spec_agent to write artifacts/spec.txt.
        - Ask planner_agent to write artifacts/plan.txt.
        - For the next unchecked task in artifacts/plan.txt:
          - Ask coder_agent to implement it.
          - Ask verifier_agent to run npm build and eslint.
          - If verification passes, mark the task done in plan.txt via edit_file.
          - If verification fails, ask coder_agent to fix using the error summary, then verify again.

        Bugs:
        - Delegate investigation and fixes to debugger_agent, then verify build.

        IMPORTANT: Tool arguments must be a JSON object, not wrapped in a list.
        """,
        tools=[create_project, bootstrap_project, run_npm, read_file, write_file, edit_file, list_files],
        sub_agents=[spec_agent, verifier_agent, planner_agent, coder_agent, debugger_agent],
    )


root_agent = create_root_agent()
