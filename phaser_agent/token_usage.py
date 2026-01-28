from __future__ import annotations

from typing import Any, Dict, Optional

from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_response import LlmResponse


def _get_int(obj: Any, attr: str) -> int:
    value = getattr(obj, attr, 0)
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _ensure_bucket(state: Dict[str, Any], key: str) -> Dict[str, int]:
    bucket = state.get(key)
    if not isinstance(bucket, dict):
        bucket = {"prompt": 0, "completion": 0, "total": 0, "cached": 0, "calls": 0}
        state[key] = bucket
        return bucket
    for k in ("prompt", "completion", "total", "cached", "calls"):
        if not isinstance(bucket.get(k), int):
            bucket[k] = 0
    return bucket  # type: ignore[return-value]


def _extract_model_name(
    callback_context: CallbackContext,
    llm_response: LlmResponse,
) -> Optional[str]:
    if llm_response.model_version:
        return str(llm_response.model_version)

    invocation_context = getattr(callback_context, "_invocation_context", None)
    agent = getattr(invocation_context, "agent", None)
    agent_model = getattr(agent, "model", None)
    if agent_model is None:
        return None

    requested = getattr(agent_model, "model", None)
    if requested:
        return str(requested)
    return str(agent_model)


async def track_tokens_after_model(
    callback_context: CallbackContext,
    llm_response: LlmResponse,
) -> Optional[LlmResponse]:
    usage = llm_response.usage_metadata
    if usage is None:
        return None

    prompt = _get_int(usage, "prompt_token_count")
    completion = _get_int(usage, "candidates_token_count")
    total = _get_int(usage, "total_token_count")
    cached = _get_int(usage, "cached_content_token_count")
    model = _extract_model_name(callback_context, llm_response)

    total_bucket = _ensure_bucket(callback_context.state, "token_usage_total")
    total_bucket["prompt"] += prompt
    total_bucket["completion"] += completion
    total_bucket["total"] += total
    total_bucket["cached"] += cached
    total_bucket["calls"] += 1

    per_agent = callback_context.state.get("token_usage_by_agent")
    if not isinstance(per_agent, dict):
        per_agent = {}
        callback_context.state["token_usage_by_agent"] = per_agent

    agent_name = callback_context.agent_name or "unknown"
    agent_bucket = per_agent.get(agent_name)
    if not isinstance(agent_bucket, dict):
        agent_bucket = {"prompt": 0, "completion": 0, "total": 0, "cached": 0, "calls": 0}
        per_agent[agent_name] = agent_bucket
    for k in ("prompt", "completion", "total", "cached", "calls"):
        if not isinstance(agent_bucket.get(k), int):
            agent_bucket[k] = 0

    agent_bucket["prompt"] += prompt
    agent_bucket["completion"] += completion
    agent_bucket["total"] += total
    agent_bucket["cached"] += cached
    agent_bucket["calls"] += 1

    last = {
        "agent": agent_name,
        "model": model,
        "prompt": prompt,
        "completion": completion,
        "total": total,
        "cached": cached,
    }
    callback_context.state["token_usage_last"] = last
    return None
