from typing import Any, Mapping

from google.adk.agents.llm_agent import Agent
from google.adk.models import LiteLlm
from .patches import apply_patches
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
    agent_model_configs: Mapping[str, Any] | None,
) -> LiteLlm:
    if not agent_model_configs or agent_name not in agent_model_configs:
        raise RuntimeError(f"missing model config for {agent_name}")
    cfg = agent_model_configs[agent_name]
    if not isinstance(cfg, Mapping):
        raise RuntimeError(f"invalid model config for {agent_name}")
    model = cfg.get("model")
    if not model:
        raise RuntimeError(f"missing model name for {agent_name}")
    kwargs = cfg.get("kwargs") or {}
    if not isinstance(kwargs, dict):
        raise RuntimeError(f"invalid model kwargs for {agent_name}")
    safe_kwargs = dict(kwargs)
    if "api_key" in safe_kwargs and safe_kwargs["api_key"]:
        safe_kwargs["api_key"] = "***"
    return LiteLlm(model=str(model), **kwargs)


def _prompt_value(
    agent_name: str,
    agent_prompt_configs: Mapping[str, Mapping[str, Any]] | None,
    key: str,
) -> str:
    if not agent_prompt_configs:
        raise RuntimeError(f"missing prompt configs for {agent_name}")
    cfg = agent_prompt_configs.get(agent_name)
    if not isinstance(cfg, Mapping):
        raise RuntimeError(f"missing prompt config for {agent_name}")
    value = cfg.get(key)
    if isinstance(value, str) and value.strip():
        return value
    raise RuntimeError(f"missing prompt {key} for {agent_name}")


def _strip_wrapping_chars(text: str, chars: str) -> str:
    out = text.strip()
    while len(out) >= 2 and out[0] in chars and out[-1] == out[0]:
        out = out[1:-1].strip()
    return out


def _clean_provider_base_url(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    out = value.strip()
    out = _strip_wrapping_chars(out, "`\"'")
    return out.strip()


def _select_binding(bindings: Any) -> dict[str, Any] | None:
    if not isinstance(bindings, list):
        return None
    active = [b for b in bindings if isinstance(b, dict) and b.get("isActive") is True]
    candidates = active or [b for b in bindings if isinstance(b, dict)]
    if not candidates:
        return None
    candidates.sort(key=lambda b: (b.get("priority") if isinstance(b.get("priority"), int) else 10**9))
    return candidates[0]


def _model_to_litellm_config(model_info: Mapping[str, Any]) -> dict[str, Any]:
    model_name = str(model_info.get("modelName") or "").strip()
    provider_name = str(model_info.get("providerName") or "").strip().lower()
    model_type = str(model_info.get("modelType") or "").strip().lower()
    provider = provider_name or (model_type if model_type and model_type != "llm" else "")
    if not model_name:
        raise RuntimeError("modelName is required")

    model_name_lower = model_name.lower()
    if provider == "openrouter":
        litellm_model = model_name if model_name_lower.startswith("openrouter/") else f"openrouter/{model_name}"
    elif provider and model_name_lower.startswith(f"{provider}/"):
        litellm_model = model_name
    elif provider and "/" not in model_name:
        litellm_model = f"{provider}/{model_name}"
    else:
        litellm_model = model_name

    kwargs: dict[str, Any] = {}
    provider_base_url = _clean_provider_base_url(model_info.get("providerBaseUrl"))
    if provider_base_url:
        kwargs["api_base"] = provider_base_url

    provider_api_key = model_info.get("providerApiKey")
    if isinstance(provider_api_key, str) and provider_api_key.strip():
        kwargs["api_key"] = provider_api_key.strip()

    return {"model": litellm_model, "kwargs": kwargs}


def _extract_configs_from_agent_payload(
    payload: Mapping[str, Any],
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, str]]]:
    model_configs: dict[str, dict[str, Any]] = {}
    prompt_configs: dict[str, dict[str, str]] = {}

    models = payload.get("models")
    agentinfos = payload.get("agentinfos")
    if isinstance(models, list) and isinstance(agentinfos, list):
        for item in agentinfos:
            if not isinstance(item, dict):
                continue
            agent_obj = item.get("agent")
            if not isinstance(agent_obj, dict):
                continue
            agent_name = agent_obj.get("name")
            if not isinstance(agent_name, str) or not agent_name.strip():
                continue
            agent_name = agent_name.strip()

            desc = agent_obj.get("description")
            instr = agent_obj.get("instruction")
            prompt: dict[str, str] = {}
            if isinstance(desc, str) and desc.strip():
                prompt["description"] = desc.strip()
            if isinstance(instr, str) and instr.strip():
                prompt["instruction"] = instr.strip()
            if prompt:
                prompt_configs[agent_name] = prompt

            selected = _select_binding(item.get("bindings"))
            if not selected:
                raise RuntimeError(f"missing bindings for {agent_name}")
            model_index = selected.get("modelIndex")
            if not isinstance(model_index, int) or model_index < 0 or model_index >= len(models):
                raise RuntimeError(f"invalid modelIndex for {agent_name}")
            model_info = models[model_index]
            if not isinstance(model_info, Mapping):
                raise RuntimeError(f"invalid modelInfo for {agent_name}")
            cfg = _model_to_litellm_config(model_info)
            model_configs[agent_name] = cfg
        if not model_configs or not prompt_configs:
            raise RuntimeError("agent payload missing model or prompt configs")
        return model_configs, prompt_configs

    items = payload.get("list")
    if isinstance(items, list):
        for item in items:
            if not isinstance(item, dict):
                continue
            agent_obj = item.get("agent")
            if not isinstance(agent_obj, dict):
                continue
            agent_name = agent_obj.get("name")
            if not isinstance(agent_name, str) or not agent_name.strip():
                continue
            agent_name = agent_name.strip()

            desc = agent_obj.get("description")
            instr = agent_obj.get("instruction")
            prompt: dict[str, str] = {}
            if isinstance(desc, str) and desc.strip():
                prompt["description"] = desc.strip()
            if isinstance(instr, str) and instr.strip():
                prompt["instruction"] = instr.strip()
            if prompt:
                prompt_configs[agent_name] = prompt

            selected = _select_binding(item.get("bindings"))
            if not isinstance(selected, Mapping):
                raise RuntimeError(f"missing bindings for {agent_name}")
            cfg = _model_to_litellm_config(selected)
            model_configs[agent_name] = cfg

        if not model_configs or not prompt_configs:
            raise RuntimeError("agent payload missing model or prompt configs")
        return model_configs, prompt_configs

    raise RuntimeError("invalid agent payload")


def create_root_agent(
    agent_model_configs: Mapping[str, Any],
) -> Agent:
    if not isinstance(agent_model_configs, Mapping):
        raise RuntimeError("agent_model_configs is required")
    agent_prompt_configs: Mapping[str, Mapping[str, Any]] = {}
    if "models" in agent_model_configs or "agentinfos" in agent_model_configs or "list" in agent_model_configs:
        parsed_models, parsed_prompts = _extract_configs_from_agent_payload(agent_model_configs)
        agent_model_configs = parsed_models
        agent_prompt_configs = parsed_prompts

    spec_agent = create_spec_agent(
        model=_litellm_from_agent_config("spec_agent", agent_model_configs),
        description=_prompt_value("spec_agent", agent_prompt_configs, "description"),
        instruction=_prompt_value("spec_agent", agent_prompt_configs, "instruction"),
    )
    verifier_agent = create_verifier_agent(
        model=_litellm_from_agent_config("verifier_agent", agent_model_configs),
        description=_prompt_value("verifier_agent", agent_prompt_configs, "description"),
        instruction=_prompt_value("verifier_agent", agent_prompt_configs, "instruction"),
    )
    planner_agent = create_planner_agent(
        model=_litellm_from_agent_config("planner_agent", agent_model_configs),
        description=_prompt_value("planner_agent", agent_prompt_configs, "description"),
        instruction=_prompt_value("planner_agent", agent_prompt_configs, "instruction"),
    )
    coder_agent = create_coder_agent(
        model=_litellm_from_agent_config("coder_agent", agent_model_configs),
        description=_prompt_value("coder_agent", agent_prompt_configs, "description"),
        instruction=_prompt_value("coder_agent", agent_prompt_configs, "instruction"),
    )
    debugger_agent = create_debugger_agent(
        model=_litellm_from_agent_config("debugger_agent", agent_model_configs),
        description=_prompt_value("debugger_agent", agent_prompt_configs, "description"),
        instruction=_prompt_value("debugger_agent", agent_prompt_configs, "instruction"),
    )

    return Agent(
        model=_litellm_from_agent_config("phaser_agent", agent_model_configs),
        name="phaser_agent",
        description=_prompt_value("phaser_agent", agent_prompt_configs, "description"),
        after_model_callback=track_tokens_after_model,
        instruction=_prompt_value("phaser_agent", agent_prompt_configs, "instruction"),
        tools=[create_project, bootstrap_project, run_npm, read_file, write_file, edit_file, list_files],
        sub_agents=[spec_agent, verifier_agent, planner_agent, coder_agent, debugger_agent],
    )
