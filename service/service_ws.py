import asyncio
import json
import logging
import os
import ssl
import uuid
import urllib.parse
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, Tuple

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from google.adk.runners import InMemoryRunner
from google.genai import types

from phaser_agent.agent import create_root_agent


logger = logging.getLogger(__name__)


def _load_dotenv() -> None:
    def _strip_quotes(value: str) -> str:
        v = value.strip()
        if len(v) >= 2 and ((v[0] == v[-1] == '"') or (v[0] == v[-1] == "'")):
            return v[1:-1]
        return v

    def _apply_file(file_path: Path) -> None:
        if not file_path.is_file():
            return
        try:
            lines = file_path.read_text(encoding="utf-8").splitlines()
        except Exception:
            return
        for line in lines:
            raw = line.strip()
            if not raw or raw.startswith("#"):
                continue
            if raw.startswith("export "):
                raw = raw[len("export ") :].strip()
            if "=" not in raw:
                continue
            key, value = raw.split("=", 1)
            key = key.strip()
            if not key:
                continue
            if key in os.environ:
                continue
            os.environ[key] = _strip_quotes(value)

    base_dir = Path(__file__).resolve().parents[1]
    candidates = [
        Path.cwd() / ".env",
        base_dir / ".env",
        base_dir / "service" / ".env",
        base_dir / "web" / ".env",
        base_dir / "phaser_agent" / ".env",
    ]
    for p in candidates:
        _apply_file(p)


_load_dotenv()


def _content_from_text(text: str) -> types.Content:
    return types.Content(role="user", parts=[types.Part.from_text(text=text)])


def _event_text(event: Any) -> str:
    content = getattr(event, "content", None)
    if not content:
        return ""
    parts = getattr(content, "parts", None)
    if not parts:
        return ""
    chunks = []
    for part in parts:
        t = getattr(part, "text", None)
        if isinstance(t, str) and t:
            chunks.append(t)
    return "".join(chunks)


def _event_payload(event: Any) -> Dict[str, Any]:
    dump = getattr(event, "model_dump", None)
    if callable(dump):
        return dump(by_alias=True)
    as_dict = getattr(event, "dict", None)
    if callable(as_dict):
        return as_dict()
    return {"repr": repr(event)}


def _safe_error_message(err: BaseException) -> str:
    msg = str(err).replace("\r", " ").replace("\n", " ").strip()
    if len(msg) > 300:
        msg = msg[:300] + "..."
    return msg


app = FastAPI()
_runner_by_token: Dict[str, InMemoryRunner] = {}
_runner_create_lock = asyncio.Lock()
_session_locks: Dict[Tuple[str, str, str], asyncio.Lock] = {}

_AGENT_CONFIG_API_BASE = (os.getenv("AGENT_CONFIG_API_BASE") or "").strip().rstrip("/")
_AGENT_CONFIG_DEBUG = (os.getenv("AGENT_CONFIG_DEBUG") or "").strip().lower() in {"1", "true", "yes", "on"}
_AGENT_CONFIG_PRINT = (os.getenv("AGENT_CONFIG_PRINT") or "").strip().lower() in {"1", "true", "yes", "on"}
_AGENT_CONFIG_TOKEN = (os.getenv("AGENT_CONFIG_TOKEN") or "").strip()
_AGENT_CONFIG_FALLBACK_LIST = (os.getenv("AGENT_CONFIG_FALLBACK_LIST") or "").strip().lower() not in {
    "0",
    "false",
    "no",
    "off",
}
_AGENT_CONFIG_INSECURE_SSL = (os.getenv("AGENT_CONFIG_INSECURE_SSL") or "").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
_AGENT_CONFIG_CA_BUNDLE = (os.getenv("AGENT_CONFIG_CA_BUNDLE") or "").strip()
_AGENT_NAMES = [
    "phaser_agent",
    "spec_agent",
    "planner_agent",
    "coder_agent",
    "verifier_agent",
    "debugger_agent",
]


def _emit_terminal_log(level: str, message: str, *args: Any) -> None:
    if not (_AGENT_CONFIG_PRINT or _AGENT_CONFIG_DEBUG):
        return
    try:
        text = message % args if args else message
    except Exception:
        text = message
    print(f"[service_ws][{level}] {text}", flush=True)


def _ssl_context_for_agent_config() -> ssl.SSLContext | None:
    if _AGENT_CONFIG_INSECURE_SSL:
        return ssl._create_unverified_context()
    if _AGENT_CONFIG_CA_BUNDLE:
        ctx = ssl.create_default_context()
        try:
            ctx.load_verify_locations(cafile=_AGENT_CONFIG_CA_BUNDLE)
        except Exception:
            _emit_terminal_log("WARN", "agent_config.ssl.ca_bundle_invalid path=%s", _AGENT_CONFIG_CA_BUNDLE)
        return ctx
    return None


@app.on_event("shutdown")
async def _shutdown() -> None:
    for runner in list(_runner_by_token.values()):
        await runner.close()


def _fetch_json(url: str, token: str | None) -> Dict[str, Any] | None:
    headers = {"Accept": "application/json"}
    auth_token = token or _AGENT_CONFIG_TOKEN
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        ctx = _ssl_context_for_agent_config() if url.lower().startswith("https://") else None
        if ctx is None:
            resp_ctx = urllib.request.urlopen(req, timeout=8)
        else:
            resp_ctx = urllib.request.urlopen(req, timeout=8, context=ctx)
        with resp_ctx as resp:
            if _AGENT_CONFIG_DEBUG:
                logger.info(
                    "agent_config.fetch.ok url=%s status=%s content_type=%s",
                    url,
                    getattr(resp, "status", None),
                    resp.headers.get("content-type"),
                )
                _emit_terminal_log(
                    "INFO",
                    "agent_config.fetch.ok url=%s status=%s content_type=%s",
                    url,
                    getattr(resp, "status", None),
                    resp.headers.get("content-type"),
                )
            raw = resp.read()
    except urllib.error.HTTPError as e:
        body_preview = ""
        try:
            body_preview = e.read(800).decode("utf-8", errors="replace").replace("\r", " ").replace("\n", " ").strip()
        except Exception:
            body_preview = ""
        logger.warning(
            "agent_config.fetch.http_error url=%s status=%s",
            url,
            getattr(e, "code", None),
            exc_info=_AGENT_CONFIG_DEBUG,
        )
        _emit_terminal_log(
            "WARN",
            "agent_config.fetch.http_error url=%s status=%s body=%s",
            url,
            getattr(e, "code", None),
            body_preview[:300],
        )
        return None
    except Exception:
        logger.warning("agent_config.fetch.failed url=%s", url, exc_info=_AGENT_CONFIG_DEBUG)
        _emit_terminal_log("WARN", "agent_config.fetch.failed url=%s", url)
        return None
    try:
        payload = json.loads(raw.decode("utf-8"))
    except Exception:
        logger.warning("agent_config.decode.failed url=%s", url, exc_info=_AGENT_CONFIG_DEBUG)
        _emit_terminal_log("WARN", "agent_config.decode.failed url=%s", url)
        return None
    if isinstance(payload, dict):
        return payload
    return None


def _binding_to_litellm_config(binding: Dict[str, Any]) -> Dict[str, Any] | None:
    if not isinstance(binding, dict):
        return None
    model_name = (binding.get("modelName") or "").strip()
    provider_name = (binding.get("providerName") or "").strip().lower()
    model_type = (binding.get("modelType") or "").strip().lower()
    provider = provider_name or (model_type if model_type and model_type != "llm" else "")
    if not model_name:
        return None

    model_name_lower = model_name.lower()
    if provider == "openrouter":
        litellm_model = model_name if model_name_lower.startswith("openrouter/") else f"openrouter/{model_name}"
    elif provider and model_name_lower.startswith(f"{provider}/"):
        litellm_model = model_name
    elif provider and "/" not in model_name:
        litellm_model = f"{provider}/{model_name}"
    else:
        litellm_model = model_name
    kwargs: Dict[str, Any] = {}
    provider_base_url = (binding.get("providerBaseUrl") or "").strip()
    if provider_base_url:
        kwargs["api_base"] = provider_base_url

    provider_api_key = binding.get("providerApiKey")
    if isinstance(provider_api_key, str) and provider_api_key.strip():
        kwargs["api_key"] = provider_api_key.strip()

    return {"model": litellm_model, "kwargs": kwargs}


def _select_binding(bindings: Any) -> Dict[str, Any] | None:
    if not isinstance(bindings, list):
        return None
    active = [b for b in bindings if isinstance(b, dict) and b.get("isActive") is True]
    candidates = active or [b for b in bindings if isinstance(b, dict)]
    if not candidates:
        return None
    candidates.sort(key=lambda b: (b.get("priority") if isinstance(b.get("priority"), int) else 10**9))
    return candidates[0]


def _normalize_agent_name(name: str) -> str:
    return name.strip().lower().replace("_", "").replace("-", "")


def _get_agent_config_by_name(agent_name: str, token: str | None) -> Dict[str, Any] | None:
    candidates: list[str] = []
    for c in [
        agent_name,
        agent_name.lower(),
        agent_name.replace("_", "-"),
        agent_name.replace("_", "-").lower(),
    ]:
        if c and c not in candidates:
            candidates.append(c)

    for c in candidates:
        url = f"{_AGENT_CONFIG_API_BASE}/api/v1/agents/by-name/{urllib.parse.quote(c)}"
        payload = _fetch_json(url, token)
        if payload:
            return payload
    return None


def _list_available_agents(token: str | None) -> Dict[str, Dict[str, Any]]:
    page = 1
    page_size = 200
    mapping: Dict[str, Dict[str, Any]] = {}

    while True:
        url = f"{_AGENT_CONFIG_API_BASE}/api/v1/agents?page={page}&pageSize={page_size}"
        payload = _fetch_json(url, token)
        if not payload:
            return mapping

        items = payload.get("list")
        if isinstance(items, list):
            for item in items:
                if not isinstance(item, dict):
                    continue
                name = item.get("name")
                agent_id = item.get("id")
                if isinstance(name, str) and isinstance(agent_id, int):
                    mapping[_normalize_agent_name(name)] = {"id": agent_id, "name": name}

        page_obj = payload.get("page")
        if not isinstance(page_obj, dict):
            return mapping
        total = page_obj.get("total")
        if not isinstance(total, int):
            return mapping
        if page * page_size >= total:
            return mapping
        page += 1


def _list_agent_bindings(agent_id: int, token: str | None) -> list[Dict[str, Any]]:
    url = f"{_AGENT_CONFIG_API_BASE}/api/v1/agents/{agent_id}/bindings"
    payload = _fetch_json(url, token)
    if not payload:
        return []
    items = payload.get("list")
    if not isinstance(items, list):
        return []
    return [b for b in items if isinstance(b, dict)]


def _load_agent_model_configs(token: str | None) -> Dict[str, Dict[str, Any]]:
    if not _AGENT_CONFIG_API_BASE:
        logger.info("agent_config.disabled env AGENT_CONFIG_API_BASE is empty")
        _emit_terminal_log("INFO", "agent_config.disabled env AGENT_CONFIG_API_BASE is empty")
        return {}

    configs: Dict[str, Dict[str, Any]] = {}
    logger.info("agent_config.load.start api_base=%s", _AGENT_CONFIG_API_BASE)
    _emit_terminal_log("INFO", "agent_config.load.start api_base=%s", _AGENT_CONFIG_API_BASE)

    agent_index: Dict[str, Dict[str, Any]] | None = None

    for name in _AGENT_NAMES:
        payload = _get_agent_config_by_name(name, token)
        url = f"{_AGENT_CONFIG_API_BASE}/api/v1/agents/by-name/{urllib.parse.quote(name)}"

        agent_id = None
        if payload:
            agent_obj = payload.get("agent")
            if isinstance(agent_obj, dict) and isinstance(agent_obj.get("id"), int):
                agent_id = agent_obj.get("id")

        selected = _select_binding(payload.get("bindings") if payload else None)
        if not selected and _AGENT_CONFIG_FALLBACK_LIST:
            if agent_index is None:
                agent_index = _list_available_agents(token)
            normalized = _normalize_agent_name(name)
            info = agent_index.get(normalized) if agent_index else None
            if isinstance(info, dict) and isinstance(info.get("id"), int):
                agent_id = info["id"]
                bindings = _list_agent_bindings(agent_id, token)
                selected = _select_binding(bindings)
                url = f"{_AGENT_CONFIG_API_BASE}/api/v1/agents/{agent_id}/bindings"

        if not selected:
            logger.warning("agent_config.load.no_binding agent=%s id=%s url=%s", name, agent_id, url)
            _emit_terminal_log("WARN", "agent_config.load.no_binding agent=%s id=%s url=%s", name, agent_id, url)
            continue

        cfg = _binding_to_litellm_config(selected)
        if not cfg:
            logger.warning(
                "agent_config.load.invalid_binding agent=%s id=%s url=%s binding_id=%s",
                name,
                agent_id,
                url,
                selected.get("id") if isinstance(selected, dict) else None,
            )
            _emit_terminal_log(
                "WARN",
                "agent_config.load.invalid_binding agent=%s id=%s url=%s binding_id=%s",
                name,
                agent_id,
                url,
                selected.get("id") if isinstance(selected, dict) else None,
            )
            continue

        configs[name] = cfg
        if _AGENT_CONFIG_DEBUG:
            logger.info(
                "agent_config.load.ok agent=%s id=%s binding_id=%s model=%s api_base=%s url=%s",
                name,
                agent_id,
                selected.get("id"),
                cfg.get("model"),
                (cfg.get("kwargs") or {}).get("api_base"),
                url,
            )
            _emit_terminal_log(
                "INFO",
                "agent_config.load.ok agent=%s id=%s binding_id=%s model=%s api_base=%s url=%s",
                name,
                agent_id,
                selected.get("id"),
                cfg.get("model"),
                (cfg.get("kwargs") or {}).get("api_base"),
                url,
            )

    logger.info(
        "agent_config.load.done count=%s models=%s",
        len(configs),
        {k: (v.get("model") if isinstance(v, dict) else None) for k, v in configs.items()},
    )
    _emit_terminal_log(
        "INFO",
        "agent_config.load.done count=%s models=%s",
        len(configs),
        {k: (v.get("model") if isinstance(v, dict) else None) for k, v in configs.items()},
    )
    return configs


async def _get_runner(
    token: str | None, agent_model_configs: Dict[str, Dict[str, Any]] | None = None
) -> InMemoryRunner:
    token_key = token or "anon"
    runner = _runner_by_token.get(token_key)
    if runner is not None:
        return runner

    async with _runner_create_lock:
        runner = _runner_by_token.get(token_key)
        if runner is not None:
            return runner
        configs = agent_model_configs if agent_model_configs is not None else _load_agent_model_configs(token)
        # logger.info("runner.create token_present=%s agent_model_configs=%s", bool(token), bool(configs))
        # _emit_terminal_log(
        #     "INFO",
        #     "runner.create token_present=%s agent_model_configs=%s",
        #     bool(token),
        #     bool(configs),
        # )
        agent = create_root_agent(configs or None)
        runner = InMemoryRunner(agent=agent, app_name=f"phaser_agent_ws:{token_key}")
        runner.auto_create_session = True
        _runner_by_token[token_key] = runner
        return runner


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket) -> None:
    token = ws.query_params.get("token") if ws.query_params else None
    await ws.accept()
    agent_model_configs = _load_agent_model_configs(token)
    await _get_runner(token, agent_model_configs=agent_model_configs)
    try:
        while True:
            raw = await ws.receive_text()
            try:
                req = json.loads(raw)
            except json.JSONDecodeError:
                await ws.send_text(
                    json.dumps(
                        {"type": "error", "error": "invalid_json"},
                        ensure_ascii=False,
                    )
                )
                continue

            msg_type = req.get("type") or "user_message"
            if msg_type == "ping":
                await ws.send_text(json.dumps({"type": "pong"}, ensure_ascii=False))
                continue
            if msg_type == "auth":
                raw_token = req.get("token")
                if isinstance(raw_token, str) and raw_token:
                    token = raw_token
                    await ws.send_text(
                        json.dumps(
                            {"type": "auth_ok"},
                            ensure_ascii=False,
                        )
                    )
                else:
                    await ws.send_text(
                        json.dumps(
                            {"type": "error", "error": "missing_token"},
                            ensure_ascii=False,
                        )
                    )
                continue
            if msg_type != "user_message":
                await ws.send_text(
                    json.dumps(
                        {
                            "type": "error",
                            "error": "unsupported_type",
                            "supported": ["user_message", "ping", "auth"],
                        },
                        ensure_ascii=False,
                    )
                )
                continue

            user_id = str(req.get("user_id") or "default")
            session_id = str(req.get("session_id") or "default")
            text = req.get("text")
            if not isinstance(text, str) or not text.strip():
                await ws.send_text(
                    json.dumps(
                        {"type": "error", "error": "missing_text"},
                        ensure_ascii=False,
                    )
                )
                continue

            request_id = str(req.get("request_id") or uuid.uuid4())
            token_key = token or "anon"
            lock_key = (token_key, user_id, session_id)
            lock = _session_locks.get(lock_key)
            if lock is None:
                lock = asyncio.Lock()
                _session_locks[lock_key] = lock

            async with lock:
                await ws.send_text(
                    json.dumps(
                        {
                            "type": "start",
                            "request_id": request_id,
                            "user_id": user_id,
                            "session_id": session_id,
                            "has_token": bool(token),
                        },
                        ensure_ascii=False,
                    )
                )

                content = _content_from_text(text)
                try:
                    runner = await _get_runner(token)
                    state_delta = {"auth": {"token": token}} if token else None
                    async for event in runner.run_async(
                        user_id=user_id,
                        session_id=session_id,
                        new_message=content,
                        state_delta=state_delta,
                    ):
                        payload = _event_payload(event)
                        await ws.send_text(
                            json.dumps(
                                {
                                    "type": "event",
                                    "request_id": request_id,
                                    "event": payload,
                                },
                                ensure_ascii=False,
                            )
                        )

                        delta = _event_text(event)
                        if delta:
                            await ws.send_text(
                                json.dumps(
                                    {
                                        "type": "delta",
                                        "request_id": request_id,
                                        "text": delta,
                                    },
                                    ensure_ascii=False,
                                )
                            )
                except Exception as e:
                    await ws.send_text(
                        json.dumps(
                            {
                                "type": "error",
                                "request_id": request_id,
                                "error": "run_failed",
                                "exception": type(e).__name__,
                                "message": _safe_error_message(e),
                            },
                            ensure_ascii=False,
                        )
                    )

                await ws.send_text(
                    json.dumps(
                        {"type": "done", "request_id": request_id},
                        ensure_ascii=False,
                    )
                )
    except WebSocketDisconnect:
        return


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("service.service_ws:app", host="0.0.0.0", port=8001)
