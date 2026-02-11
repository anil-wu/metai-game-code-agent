import asyncio
import json
import logging
import os
import ssl
import uuid
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
    env_file = Path(__file__).resolve().parent / ".env"
    if not env_file.is_file():
        return
    try:
        lines = env_file.read_text(encoding="utf-8").splitlines()
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
        if not key or key in os.environ:
            continue
        v = value.strip()
        if len(v) >= 2 and ((v[0] == v[-1] == '"') or (v[0] == v[-1] == "'")):
            v = v[1:-1]
        os.environ[key] = v


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
_AGENT_CONFIG_INSECURE_SSL = (os.getenv("AGENT_CONFIG_INSECURE_SSL") or "").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
_AGENT_CONFIG_CA_BUNDLE = (os.getenv("AGENT_CONFIG_CA_BUNDLE") or "").strip()


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


@app.on_event("startup")
async def _startup() -> None:
    global _AGENT_CONFIG_API_BASE
    _AGENT_CONFIG_API_BASE = (os.getenv("AGENT_CONFIG_API_BASE") or "").strip().rstrip("/")
    if not _AGENT_CONFIG_API_BASE:
        raise RuntimeError("AGENT_CONFIG_API_BASE is required")


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


def _load_agent_configs(
    token: str | None,
) -> Dict[str, Any]:
    if not _AGENT_CONFIG_API_BASE:
        logger.info("agent_config.disabled env AGENT_CONFIG_API_BASE is empty")
        _emit_terminal_log("INFO", "agent_config.disabled env AGENT_CONFIG_API_BASE is empty")
        return {"agent_payload": {}}

    logger.info("agent_config.load.start api_base=%s", _AGENT_CONFIG_API_BASE)
    _emit_terminal_log("INFO", "agent_config.load.start api_base=%s", _AGENT_CONFIG_API_BASE)

    url = f"{_AGENT_CONFIG_API_BASE}/api/v1/agents/configs"
    payload = _fetch_json(url, token)
    if not isinstance(payload, dict):
        logger.warning("agent_config.load.failed url=%s", url)
        _emit_terminal_log("WARN", "agent_config.load.failed url=%s", url)
        return {"agent_payload": {}}

    logger.info("agent_config.load.done url=%s", url)
    _emit_terminal_log("INFO", "agent_config.load.done url=%s", url)
    return {"agent_payload": payload}


async def _get_runner(
    token: str | None,
    agent_configs: Dict[str, Any] | None = None,
) -> InMemoryRunner:
    token_key = token or "anon"
    runner = _runner_by_token.get(token_key)
    if runner is not None:
        return runner

    async with _runner_create_lock:
        runner = _runner_by_token.get(token_key)
        if runner is not None:
            return runner
        agent_payload: Dict[str, Any] | None = None
        if agent_configs is None:
            loaded = _load_agent_configs(token)
            agent_payload = loaded.get("agent_payload") if isinstance(loaded, dict) else None
        elif isinstance(agent_configs, dict):
            agent_payload = agent_configs

        if not isinstance(agent_payload, dict):
            raise RuntimeError("agent_configs is required")
        agent = create_root_agent(agent_payload)
        runner = InMemoryRunner(agent=agent, app_name=f"phaser_agent_ws:{token_key}")
        runner.auto_create_session = True
        _runner_by_token[token_key] = runner
        return runner


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket) -> None:
    token = ws.query_params.get("token") if ws.query_params else None
    agent_configs: Dict[str, Any] | None = None
    await ws.accept()
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
                token_candidate = raw_token if isinstance(raw_token, str) and raw_token else token
                if isinstance(token_candidate, str) and token_candidate:
                    token = token_candidate
                    loaded = _load_agent_configs(token)
                    agent_configs = loaded.get("agent_payload") if isinstance(loaded, dict) else None
                    if not isinstance(agent_configs, dict) or not isinstance(agent_configs.get("models"), list) or not isinstance(agent_configs.get("agentinfos"), list):
                        agent_configs = None
                        await ws.send_text(json.dumps({"type": "error", "error": "agent_config_load_failed"}, ensure_ascii=False))
                        continue
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
            if not isinstance(agent_configs, dict) or not isinstance(agent_configs.get("models"), list) or not isinstance(agent_configs.get("agentinfos"), list):
                await ws.send_text(json.dumps({"type": "error", "error": "not_authenticated"}, ensure_ascii=False))
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
                    runner = await _get_runner(
                        token,
                        agent_configs=agent_configs,
                    )
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
