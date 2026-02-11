import json
from pathlib import Path
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


def _load_local_agent_prompt_configs() -> dict[str, dict[str, str]]:
    path = Path(__file__).resolve().parent / "agents_prompts.json"
    try:
        raw = path.read_text(encoding="utf-8")
    except Exception:
        return {}
    try:
        payload = json.loads(raw)
    except Exception:
        return {}
    if not isinstance(payload, list):
        return {}
    out: dict[str, dict[str, str]] = {}
    for item in payload:
        if not isinstance(item, dict):
            continue
        name = item.get("name") or item.get("名称")
        if not isinstance(name, str) or not name.strip():
            continue
        description = item.get("description") or item.get("描述")
        instruction = item.get("instruction") or item.get("指令")
        cfg: dict[str, str] = {}
        if isinstance(description, str) and description.strip():
            cfg["description"] = description
        if isinstance(instruction, str) and instruction.strip():
            cfg["instruction"] = instruction
        if cfg:
            out[name.strip()] = cfg
    return out


def _merged_agent_prompt_configs(
    agent_prompt_configs: Mapping[str, Mapping[str, Any]] | None,
) -> dict[str, dict[str, str]]:
    local = _load_local_agent_prompt_configs()
    if not agent_prompt_configs:
        return local
    merged: dict[str, dict[str, str]] = dict(local)
    for name, cfg in agent_prompt_configs.items():
        if not isinstance(name, str) or not name.strip() or not isinstance(cfg, Mapping):
            continue
        cur = dict(merged.get(name, {}))
        desc = cfg.get("description")
        instr = cfg.get("instruction")
        if isinstance(desc, str) and desc.strip():
            cur["description"] = desc
        if isinstance(instr, str) and instr.strip():
            cur["instruction"] = instr
        if cur:
            merged[name] = cur
    return merged


def _prompt_value(
    agent_name: str,
    agent_prompt_configs: Mapping[str, Mapping[str, Any]] | None,
    key: str,
) -> str | None:
    if not agent_prompt_configs:
        return None
    cfg = agent_prompt_configs.get(agent_name)
    if not isinstance(cfg, Mapping):
        return None
    value = cfg.get(key)
    if isinstance(value, str) and value.strip():
        return value
    return None


def create_root_agent(
    agent_model_configs: Mapping[str, Mapping[str, Any]] | None = None,
    agent_prompt_configs: Mapping[str, Mapping[str, Any]] | None = None,
) -> Agent:
    merged_prompts = _merged_agent_prompt_configs(agent_prompt_configs)

    spec_agent = create_spec_agent(
        model=_litellm_from_agent_config("spec_agent", agent_model_configs),
        description=_prompt_value("spec_agent", merged_prompts, "description"),
        instruction=_prompt_value("spec_agent", merged_prompts, "instruction"),
    )
    verifier_agent = create_verifier_agent(
        model=_litellm_from_agent_config("verifier_agent", agent_model_configs),
        description=_prompt_value("verifier_agent", merged_prompts, "description"),
        instruction=_prompt_value("verifier_agent", merged_prompts, "instruction"),
    )
    planner_agent = create_planner_agent(
        model=_litellm_from_agent_config("planner_agent", agent_model_configs),
        description=_prompt_value("planner_agent", merged_prompts, "description"),
        instruction=_prompt_value("planner_agent", merged_prompts, "instruction"),
    )
    coder_agent = create_coder_agent(
        model=_litellm_from_agent_config("coder_agent", agent_model_configs),
        description=_prompt_value("coder_agent", merged_prompts, "description"),
        instruction=_prompt_value("coder_agent", merged_prompts, "instruction"),
    )
    debugger_agent = create_debugger_agent(
        model=_litellm_from_agent_config("debugger_agent", agent_model_configs),
        description=_prompt_value("debugger_agent", merged_prompts, "description"),
        instruction=_prompt_value("debugger_agent", merged_prompts, "instruction"),
    )

    return Agent(
        model=_litellm_from_agent_config("phaser_agent", agent_model_configs),
        name="phaser_agent",
        description=_prompt_value("phaser_agent", merged_prompts, "description"),
        after_model_callback=track_tokens_after_model,
        instruction=_prompt_value("phaser_agent", merged_prompts, "instruction"),
        tools=[create_project, bootstrap_project, run_npm, read_file, write_file, edit_file, list_files],
        sub_agents=[spec_agent, verifier_agent, planner_agent, coder_agent, debugger_agent],
    )


root_agent = create_root_agent()
