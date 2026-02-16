import asyncio
import inspect
import json
import logging
import os
import ssl
import time
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
    # Handle Pydantic v2
    model_dump = getattr(event, "model_dump", None)
    if callable(model_dump):
        try:
            return model_dump(mode="json", by_alias=True)
        except Exception:
            # Fallback for some types that might fail with mode="json"
            pass
        try:
            return model_dump(by_alias=True)
        except Exception:
            pass
            
    # Handle Pydantic v1
    dict_method = getattr(event, "dict", None)
    if callable(dict_method):
        return dict_method()
        
    # Handle dataclasses or simple objects
    if hasattr(event, "__dict__"):
        return event.__dict__
        
    return {"repr": repr(event)}


def _safe_error_message(err: BaseException) -> str:
    msg = str(err).replace("\r", " ").replace("\n", " ").strip()
    if len(msg) > 300:
        msg = msg[:300] + "..."
    return msg


def _non_empty_str(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    v = value.strip()
    return v if v else None


def _user_id_value(value: Any) -> str | None:
    if isinstance(value, int):
        return str(value)
    return _non_empty_str(value)


async def _ws_send(ws: WebSocket, payload: Dict[str, Any]) -> bool:
    try:
        await ws.send_text(json.dumps(payload, ensure_ascii=False))
        return True
    except WebSocketDisconnect:
        return False
    except RuntimeError:
        return False
    except Exception:
        return False


async def _ws_error(
    ws: WebSocket,
    error: str,
    request_id: str | None = None,
    **extra: Any,
) -> None:
    payload: Dict[str, Any] = {"type": "error", "error": error}
    if request_id is not None:
        payload["request_id"] = request_id
    payload.update(extra)
    await _ws_send(ws, payload)


async def _ws_close(ws: WebSocket, code: int, reason: str) -> None:
    try:
        await ws.close(code=code, reason=reason)
    except Exception:
        return


def _is_valid_agent_payload(payload: Any) -> bool:
    return (
        isinstance(payload, dict)
        and isinstance(payload.get("models"), list)
        and isinstance(payload.get("agentinfos"), list)
    )


def _get_session_lock(token_key: str, user_id: str, session_id: str) -> asyncio.Lock:
    lock_key = (token_key, user_id, session_id)
    lock = _session_locks.get(lock_key)
    if lock is None:
        lock = asyncio.Lock()
        _session_locks[lock_key] = lock
    return lock


app = FastAPI()
_runner_by_token: Dict[str, InMemoryRunner] = {}
_user_id_by_token: Dict[str, str] = {}
_runner_create_lock = asyncio.Lock()
_session_locks: Dict[Tuple[str, str, str], asyncio.Lock] = {}

_AGENT_CONFIG_API_BASE = (
    (os.getenv("AGENT_CONFIG_API_BASE") or "").strip().rstrip("/")
    or (os.getenv("SPARKX_API_BASE_URL") or "").strip().rstrip("/")
)
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
    base_lower = (_AGENT_CONFIG_API_BASE or "").lower()
    if base_lower.startswith("https://localhost") or base_lower.startswith("https://127.0.0.1"):
        return ssl._create_unverified_context()
    return None


@app.on_event("startup")
async def _startup() -> None:
    global _AGENT_CONFIG_API_BASE
    _AGENT_CONFIG_API_BASE = (
        (os.getenv("AGENT_CONFIG_API_BASE") or "").strip().rstrip("/")
        or (os.getenv("SPARKX_API_BASE_URL") or "").strip().rstrip("/")
    )
    if not _AGENT_CONFIG_API_BASE:
        raise RuntimeError("AGENT_CONFIG_API_BASE is required")


@app.on_event("shutdown")
async def _shutdown() -> None:
    for runner in list(_runner_by_token.values()):
        await runner.close()
    _runner_by_token.clear()
    _user_id_by_token.clear()


def _fetch_json(url: str, token: str | None) -> Dict[str, Any] | None:
    headers = {"Accept": "application/json"}
    auth_token = token or _AGENT_CONFIG_TOKEN
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        ctx = _ssl_context_for_agent_config() if url.lower().startswith("https://") else None
        open_kwargs: Dict[str, Any] = {}
        if ctx is not None:
            open_kwargs["context"] = ctx
        with urllib.request.urlopen(req, timeout=8, **open_kwargs) as resp:
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
    except Exception as e:
        logger.warning("agent_config.fetch.failed url=%s", url, exc_info=_AGENT_CONFIG_DEBUG)
        _emit_terminal_log("WARN", "agent_config.fetch.failed url=%s err=%s", url, _safe_error_message(e))
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


def _load_agent_payload(token: str | None) -> Dict[str, Any] | None:
    if not _AGENT_CONFIG_API_BASE:
        logger.info("agent_config.disabled env AGENT_CONFIG_API_BASE is empty")
        _emit_terminal_log("INFO", "agent_config.disabled env AGENT_CONFIG_API_BASE is empty")
        return None

    logger.info("agent_config.load.start api_base=%s", _AGENT_CONFIG_API_BASE)
    _emit_terminal_log("INFO", "agent_config.load.start api_base=%s", _AGENT_CONFIG_API_BASE)

    url = f"{_AGENT_CONFIG_API_BASE}/api/v1/agents/configs"
    payload = _fetch_json(url, token)
    if not isinstance(payload, dict):
        logger.warning("agent_config.load.failed url=%s", url)
        _emit_terminal_log("WARN", "agent_config.load.failed url=%s", url)
        return None

    logger.info("agent_config.load.done url=%s", url)
    _emit_terminal_log("INFO", "agent_config.load.done url=%s", url)
    return payload


async def _get_runner(
    token: str,
    agent_payload: Dict[str, Any] | None = None,
) -> InMemoryRunner:
    runner = _runner_by_token.get(token)
    if runner is not None:
        return runner

    async with _runner_create_lock:
        runner = _runner_by_token.get(token)
        if runner is not None:
            return runner
        if agent_payload is None:
            agent_payload = _load_agent_payload(token)

        if not isinstance(agent_payload, dict):
            raise RuntimeError("agent_payload is required")
        agent = create_root_agent(agent_payload)
        runner = InMemoryRunner(agent=agent, app_name=f"phaser_agent_ws:{token}")
        runner.auto_create_session = True
        _runner_by_token[token] = runner
        return runner


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket) -> None:
    token = _non_empty_str(ws.query_params.get("token")) if ws.query_params else None
    agent_payload: Dict[str, Any] | None = None
    project_id: str | None = None
    user_id: str | None = None
    await ws.accept()
    try:
        while True:
            raw = await ws.receive_text()
            try:
                req = json.loads(raw)
            except json.JSONDecodeError:
                await _ws_error(ws, "invalid_json")
                continue

            if not isinstance(req, dict):
                await _ws_error(ws, "invalid_request")
                continue

            msg_type = req.get("type") or "message"
            if isinstance(msg_type, str):
                msg_type = msg_type.strip()
            
            print("msg_type:", msg_type)
            # Legacy compatibility
            if msg_type == "user_message":
                msg_type = "message"

            match msg_type:
                case "ping":
                    await _ws_send(ws, {"type": "pong"})
                
                case "auth":
                    token_candidate = _non_empty_str(req.get("token")) or _non_empty_str(token)
                    project_id_candidate = _non_empty_str(req.get("project_id"))
                    user_id_candidate = _user_id_value(req.get("user_id"))
                    if token_candidate:
                        token = token_candidate
                        if project_id_candidate:
                            project_id = project_id_candidate
                        if not user_id_candidate:
                            await _ws_error(ws, "missing_user_id")
                            await _ws_close(ws, code=1008, reason="missing_user_id")
                            return
                        user_id = user_id_candidate
                        _user_id_by_token[token] = user_id
                        loaded_payload = _load_agent_payload(token)
                        if not _is_valid_agent_payload(loaded_payload):
                            agent_payload = None
                            await _ws_error(ws, "agent_config_load_failed")
                            await _ws_close(ws, code=1008, reason="auth_failed")
                            return
                        agent_payload = loaded_payload
                        await _ws_send(ws, {"type": "auth_ok", "project_id": project_id})
                    else:
                        await _ws_error(ws, "missing_token")
                        await _ws_close(ws, code=1008, reason="missing_token")
                        return

                case "message":
                    request_id = str(req.get("request_id") or uuid.uuid4())
                    if not _is_valid_agent_payload(agent_payload):
                        await _ws_error(ws, "not_authenticated", request_id=request_id)
                        continue
                    project_id_candidate = _non_empty_str(req.get("project_id"))
                    if project_id_candidate:
                        project_id = project_id_candidate
                    if not token:
                        await _ws_error(ws, "missing_token", request_id=request_id)
                        continue
                    stored_user_id = _user_id_by_token.get(token)
                    if not stored_user_id:
                        await _ws_error(ws, "missing_user_id", request_id=request_id)
                        continue
                    user_id = stored_user_id
                    session_id = str(req.get("session_id") or uuid.uuid4())
                    text = req.get("text")
                    if not isinstance(text, str) or not text.strip():
                        await _ws_error(ws, "missing_text", request_id=request_id)
                        continue

                    token_key = token or "anon"
                    lock = _get_session_lock(token_key, user_id, session_id)
                    async with lock:
                        start_time = time.time()
                        await _ws_send(
                            ws,
                            {
                                "type": "task_update",
                                "request_id": request_id,
                                "user_id": user_id,
                                "session_id": session_id,
                                "project_id": project_id,
                                "has_token": bool(token),
                                "status": "start",
                                "start_time": start_time * 1000,  # 毫秒
                            },
                        )
                        content = _content_from_text(text)
                        try:
                            runner = await _get_runner(
                                token,
                                agent_payload=agent_payload,
                            )
                            state_seed = {}
                            api_base_url = os.getenv("SPARKX_API_BASE_URL") or ""
                            state_seed["token"] = token
                            state_seed["project_id"] = project_id
                            state_seed["user_id"] = user_id
                            state_seed["api_base_url"] = api_base_url
                            session_service = runner.session_service
                            app_name = runner.app_name
                            try:
                                await session_service.get_session(
                                    app_name=app_name,
                                    user_id=user_id,
                                    session_id=session_id,
                                )
                            except Exception:
                                try:
                                    if state_seed:
                                        await session_service.create_session(
                                            app_name=app_name,
                                            user_id=user_id,
                                            session_id=session_id,
                                            state=state_seed,
                                        )
                                    else:
                                        await session_service.create_session(
                                            app_name=app_name,
                                            user_id=user_id,
                                            session_id=session_id,
                                        )
                                except Exception:
                                    pass
                            state_delta = {}
                            state_delta["token"] = token
                            state_delta["project_id"] = project_id
                            state_delta["user_id"] = user_id
                            state_delta["api_base_url"] = api_base_url
                            if not state_delta:
                                state_delta = None
                            async def _stream_events() -> None:
                                async for event in runner.run_async(
                                    user_id=user_id,
                                    session_id=session_id,
                                    new_message=content,
                                    state_delta=state_delta,
                                ):
                                    payload = _event_payload(event)
                                    current_time = time.time()
                                    elapsed_ms = int((current_time - start_time) * 1000)
                                    # 获取 event 本身的时间戳（如果有）
                                    event_timestamp = getattr(event, 'timestamp', None)
                                    ok = await _ws_send(
                                        ws,
                                        {
                                            "type": "task_update",
                                            "request_id": request_id,
                                            "event": payload,
                                            "event_timestamp": event_timestamp * 1000 if event_timestamp else None,
                                            "server_time": current_time * 1000,
                                            "elapsed_ms": elapsed_ms,
                                        },
                                    )
                                    if not ok:
                                        return
                                    delta = _event_text(event)
                                    if delta:
                                        ok = await _ws_send(
                                            ws,
                                            {
                                                "type": "message",
                                                "request_id": request_id,
                                                "text": delta,
                                            },
                                        )
                                        if not ok:
                                            return
                            try:
                                await _stream_events()
                            except Exception as e:
                                msg = _safe_error_message(e)
                                if "Session not found" in msg or "session not found" in msg:
                                    try:
                                        if state_seed:
                                            await session_service.create_session(
                                                app_name=app_name,
                                                user_id=user_id,
                                                session_id=session_id,
                                                state=state_seed,
                                            )
                                        else:
                                            await session_service.create_session(
                                                app_name=app_name,
                                                user_id=user_id,
                                                session_id=session_id,
                                            )
                                    except Exception:
                                        pass
                                    await _stream_events()
                                else:
                                    raise
                        except Exception as e:
                            await _ws_error(
                                ws,
                                "run_failed",
                                request_id=request_id,
                                exception=type(e).__name__,
                                message=_safe_error_message(e),
                            )
                        finally:
                            await _ws_send(
                                ws,
                                {
                                    "type": "task_update",
                                    "request_id": request_id,
                                    "status": "done",
                                },
                            )

                case _:
                    request_id = str(req.get("request_id") or uuid.uuid4())
                    await _ws_error(
                        ws,
                        "unsupported_type",
                        request_id=request_id,
                        supported=["message", "ping", "auth"],
                    )
    except WebSocketDisconnect:
        return


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("service.service_ws:app", host="0.0.0.0", port=8001)
