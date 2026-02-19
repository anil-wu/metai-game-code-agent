import json
import os
import ssl
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional, Union


def _state_get(state: Any, key: str, default: Any = None) -> Any:
    getter = getattr(state, "get", None)
    if callable(getter):
        try:
            return getter(key, default)
        except TypeError:
            try:
                return getter(key)
            except Exception:
                return default
        except Exception:
            return default
    if isinstance(state, dict):
        return state.get(key, default)
    return default


def _get_token_from_context(tool_context: Any) -> Optional[str]:
    if tool_context is None:
        return None
    state = getattr(tool_context, "state", None)
    if state is None:
        return None
    token = _state_get(state, "token")
    if token and str(token).strip():
        return str(token).strip()
    return None


def _get_api_base_url_from_context(tool_context: Any) -> Optional[str]:
    if tool_context is None:
        return None
    state = getattr(tool_context, "state", None)
    if state is None:
        return None
    api_base_url = _state_get(state, "api_base_url")
    if api_base_url and str(api_base_url).strip():
        return str(api_base_url).strip().rstrip("/")
    return None


def _is_absolute_url(url: str) -> bool:
    if not url:
        return False
    stripped = url.strip().lower()
    return stripped.startswith("http://") or stripped.startswith("https://")


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    text = str(value).strip().lower()
    return text in {"1", "true", "yes", "y", "on"}


def _ssl_context(verify: bool = True, cert_path: Optional[str] = None) -> ssl.SSLContext:
    if not verify:
        return ssl._create_unverified_context()
    if cert_path and str(cert_path).strip():
        return ssl.create_default_context(cafile=str(cert_path).strip())
    ca_bundle = (os.getenv("SPARKPLAY_CA_BUNDLE") or os.getenv("REQUESTS_CA_BUNDLE") or "").strip()
    if ca_bundle:
        try:
            return ssl.create_default_context(cafile=ca_bundle)
        except Exception:
            pass
    return ssl.create_default_context()


def _build_url(base_url: str, path: str, query: Optional[Dict[str, Any]] = None) -> str:
    url = base_url.rstrip("/") + "/" + path.lstrip("/") if path else base_url
    if query:
        filtered = {k: v for k, v in query.items() if v is not None}
        if filtered:
            url = f"{url}?{urllib.parse.urlencode(filtered)}"
    return url


def _encode_body(
    body: Optional[Union[str, bytes, Dict[str, Any]]],
    content_type: Optional[str],
) -> tuple[Optional[bytes], Optional[str]]:
    if body is None:
        return None, content_type
    if isinstance(body, bytes):
        return body, content_type
    if isinstance(body, str):
        return body.encode("utf-8"), content_type
    if isinstance(body, dict):
        resolved_ct = content_type or "application/json"
        if "json" in resolved_ct.lower():
            return json.dumps(body).encode("utf-8"), resolved_ct
        if "form" in resolved_ct.lower() or "urlencoded" in resolved_ct.lower():
            return urllib.parse.urlencode(body).encode("utf-8"), resolved_ct
        return json.dumps(body).encode("utf-8"), resolved_ct
    return str(body).encode("utf-8"), content_type


def http_request(
    url: str,
    method: str = "GET",
    headers: Optional[Dict[str, str]] = None,
    query: Optional[Dict[str, Any]] = None,
    body: Optional[Union[str, bytes, Dict[str, Any]]] = None,
    content_type: Optional[str] = None,
    timeout: int = 30,
    verify_ssl: bool = True,
    cert_path: Optional[str] = None,
    follow_redirects: bool = True,
    auth: bool = True,
    tool_context: Any = None,
) -> Dict[str, Any]:
    """Performs an HTTP/HTTPS request and returns the response.

    Args:
        url: The URL to request. Can be absolute (https://api.example.com/data) or relative (/api/v1/data).
             Relative URLs are automatically prefixed with api_base_url from tool_context.state.
        method: HTTP method (GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS). Default: GET.
        headers: Optional dict of request headers.
        query: Optional dict of query parameters to append to URL.
        body: Request body. Can be string, bytes, or dict. Dicts are JSON-encoded by default.
        content_type: Content-Type header value. Auto-set for dict body (application/json).
        timeout: Request timeout in seconds. Default: 30.
        verify_ssl: Whether to verify SSL certificates. Default: True.
        cert_path: Path to custom CA certificate bundle for SSL verification.
        follow_redirects: Whether to follow HTTP redirects. Default: True.
        auth: Whether to auto-inject Authorization header from tool_context.token. Default: True.
        tool_context: ADK tool context for accessing token, api_base_url and state.

    Returns:
        Dict with keys:
        - status: "success" or "error"
        - status_code: HTTP status code (int)
        - headers: Response headers (dict)
        - body: Response body as string (for text) or base64 (for binary)
        - data: Parsed JSON if response is JSON, otherwise None
        - message: Error message if status is "error"
    """
    print(f"HTTP Request------》》: {method} {url}")

    try:
        if not url or not str(url).strip():
            return {"status": "error", "message": "url is required"}

        resolved_method = str(method).strip().upper()
        allowed_methods = {"GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"}
        if resolved_method not in allowed_methods:
            return {"status": "error", "message": f"Unsupported HTTP method: {resolved_method}"}

        url_str = str(url).strip()
        if not _is_absolute_url(url_str):
            api_base_url = _get_api_base_url_from_context(tool_context)
            if api_base_url:
                url_str = api_base_url + "/" + url_str.lstrip("/")
            else:
                return {"status": "error", "message": "Relative URL requires api_base_url in tool_context.state"}

        final_url = _build_url(url_str, "", query)

        req_headers: Dict[str, str] = dict(headers) if headers else {}

        if auth:
            token = _get_token_from_context(tool_context)
            if token and "Authorization" not in {k.title() for k in req_headers}:
                req_headers["Authorization"] = f"Bearer {token}"

        encoded_body, resolved_ct = _encode_body(body, content_type)
        if resolved_ct and "Content-Type" not in {k.title() for k in req_headers}:
            req_headers["Content-Type"] = resolved_ct

        parsed = urllib.parse.urlparse(final_url)
        is_https = parsed.scheme.lower() == "https"
        ssl_ctx = _ssl_context(verify_ssl, cert_path) if is_https else None

        print(f"HTTP Request------》》: {final_url}")
        req = urllib.request.Request(final_url, headers=req_headers, data=encoded_body, method=resolved_method)

        handlers = []
        if ssl_ctx:
            https_handler = urllib.request.HTTPSHandler(context=ssl_ctx)
            handlers.append(https_handler)
        if not follow_redirects:
            class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
                def redirect_request(self, *args, **kwargs):
                    return None
            handlers.append(NoRedirectHandler)

        if handlers:
            opener = urllib.request.build_opener(*handlers)
        else:
            opener = urllib.request.build_opener()

        with opener.open(req, timeout=timeout) as resp:
            status_code = getattr(resp, "status", None) or 200
            resp_headers = {k: v for k, v in resp.getheaders()} if hasattr(resp, "getheaders") else dict(resp.headers)
            raw_body = resp.read()

        return _build_response(status_code, resp_headers, raw_body)

    except urllib.error.HTTPError as e:
        status_code = getattr(e, "code", None) or 500
        resp_headers = {k: v for k, v in e.headers.items()} if hasattr(e, "headers") else {}
        raw_body = e.read()
        return _build_response(status_code, resp_headers, raw_body, is_error=True)

    except urllib.error.URLError as e:
        return {"status": "error", "message": f"URL error: {e.reason}"}

    except Exception as e:
        return {"status": "error", "message": str(e)}


def _build_response(
    status_code: int,
    headers: Dict[str, str],
    raw_body: bytes,
    is_error: bool = False,
) -> Dict[str, Any]:
    content_type = headers.get("Content-Type", "") or ""
    is_json = "application/json" in content_type.lower()
    is_text = is_json or any(t in content_type.lower() for t in ["text/", "application/xml", "application/javascript"])

    body_str = None
    data = None

    if raw_body:
        if is_text or is_json:
            try:
                body_str = raw_body.decode("utf-8")
            except Exception:
                try:
                    body_str = raw_body.decode("latin-1")
                except Exception:
                    body_str = raw_body.hex()
        else:
            import base64
            body_str = base64.b64encode(raw_body).decode("ascii")

        if is_json and body_str:
            try:
                data = json.loads(body_str)
            except Exception:
                pass

    success = 200 <= status_code < 300
    result: Dict[str, Any] = {
        "status": "success" if success and not is_error else "error",
        "status_code": status_code,
        "headers": headers,
        "body": body_str,
        "data": data,
    }

    if not success or is_error:
        result["message"] = body_str or f"HTTP {status_code}"

    return result


def http_get(
    url: str,
    headers: Optional[Dict[str, str]] = None,
    query: Optional[Dict[str, Any]] = None,
    timeout: int = 30,
    verify_ssl: bool = True,
    auth: bool = True,
    tool_context: Any = None,
) -> Dict[str, Any]:
    """Performs an HTTP GET request.

    Args:
        url: The URL to request. Can be absolute or relative (uses api_base_url from tool_context).
        headers: Optional request headers.
        query: Optional query parameters.
        timeout: Request timeout in seconds.
        verify_ssl: Whether to verify SSL certificates.
        auth: Whether to auto-inject Authorization header from tool_context.token. Default: True.
        tool_context: ADK tool context for accessing token and api_base_url.

    Returns:
        Response dict with status, status_code, headers, body, data.
    """
    return http_request(
        url=url,
        method="GET",
        headers=headers,
        query=query,
        timeout=timeout,
        verify_ssl=verify_ssl,
        auth=auth,
        tool_context=tool_context,
    )


def http_post(
    url: str,
    body: Optional[Union[str, bytes, Dict[str, Any]]] = None,
    headers: Optional[Dict[str, str]] = None,
    query: Optional[Dict[str, Any]] = None,
    content_type: Optional[str] = None,
    timeout: int = 30,
    verify_ssl: bool = True,
    auth: bool = True,
    tool_context: Any = None,
) -> Dict[str, Any]:
    """Performs an HTTP POST request.

    Args:
        url: The URL to request. Can be absolute or relative (uses api_base_url from tool_context).
        body: Request body (string, bytes, or dict for JSON).
        headers: Optional request headers.
        query: Optional query parameters.
        content_type: Content-Type header. Default: application/json for dict body.
        timeout: Request timeout in seconds.
        verify_ssl: Whether to verify SSL certificates.
        auth: Whether to auto-inject Authorization header from tool_context.token. Default: True.
        tool_context: ADK tool context for accessing token and api_base_url.

    Returns:
        Response dict with status, status_code, headers, body, data.
    """
    return http_request(
        url=url,
        method="POST",
        headers=headers,
        query=query,
        body=body,
        content_type=content_type,
        timeout=timeout,
        verify_ssl=verify_ssl,
        auth=auth,
        tool_context=tool_context,
    )


def http_put(
    url: str,
    body: Optional[Union[str, bytes, Dict[str, Any]]] = None,
    headers: Optional[Dict[str, str]] = None,
    query: Optional[Dict[str, Any]] = None,
    content_type: Optional[str] = None,
    timeout: int = 30,
    verify_ssl: bool = True,
    auth: bool = True,
    tool_context: Any = None,
) -> Dict[str, Any]:
    """Performs an HTTP PUT request.

    Args:
        url: The URL to request. Can be absolute or relative (uses api_base_url from tool_context).
        body: Request body (string, bytes, or dict for JSON).
        headers: Optional request headers.
        query: Optional query parameters.
        content_type: Content-Type header. Default: application/json for dict body.
        timeout: Request timeout in seconds.
        verify_ssl: Whether to verify SSL certificates.
        auth: Whether to auto-inject Authorization header from tool_context.token. Default: True.
        tool_context: ADK tool context for accessing token and api_base_url.

    Returns:
        Response dict with status, status_code, headers, body, data.
    """
    return http_request(
        url=url,
        method="PUT",
        headers=headers,
        query=query,
        body=body,
        content_type=content_type,
        timeout=timeout,
        verify_ssl=verify_ssl,
        auth=auth,
        tool_context=tool_context,
    )


def http_delete(
    url: str,
    headers: Optional[Dict[str, str]] = None,
    query: Optional[Dict[str, Any]] = None,
    timeout: int = 30,
    verify_ssl: bool = True,
    auth: bool = True,
    tool_context: Any = None,
) -> Dict[str, Any]:
    """Performs an HTTP DELETE request.

    Args:
        url: The URL to request. Can be absolute or relative (uses api_base_url from tool_context).
        headers: Optional request headers.
        query: Optional query parameters.
        timeout: Request timeout in seconds.
        verify_ssl: Whether to verify SSL certificates.
        auth: Whether to auto-inject Authorization header from tool_context.token. Default: True.
        tool_context: ADK tool context for accessing token and api_base_url.

    Returns:
        Response dict with status, status_code, headers, body, data.
    """
    return http_request(
        url=url,
        method="DELETE",
        headers=headers,
        query=query,
        timeout=timeout,
        verify_ssl=verify_ssl,
        auth=auth,
        tool_context=tool_context,
    )


def http_patch(
    url: str,
    body: Optional[Union[str, bytes, Dict[str, Any]]] = None,
    headers: Optional[Dict[str, str]] = None,
    query: Optional[Dict[str, Any]] = None,
    content_type: Optional[str] = None,
    timeout: int = 30,
    verify_ssl: bool = True,
    auth: bool = True,
    tool_context: Any = None,
) -> Dict[str, Any]:
    """Performs an HTTP PATCH request.

    Args:
        url: The URL to request. Can be absolute or relative (uses api_base_url from tool_context).
        body: Request body (string, bytes, or dict for JSON).
        headers: Optional request headers.
        query: Optional query parameters.
        content_type: Content-Type header. Default: application/json for dict body.
        timeout: Request timeout in seconds.
        verify_ssl: Whether to verify SSL certificates.
        auth: Whether to auto-inject Authorization header from tool_context.token. Default: True.
        tool_context: ADK tool context for accessing token and api_base_url.

    Returns:
        Response dict with status, status_code, headers, body, data.
    """
    return http_request(
        url=url,
        method="PATCH",
        headers=headers,
        query=query,
        body=body,
        content_type=content_type,
        timeout=timeout,
        verify_ssl=verify_ssl,
        auth=auth,
        tool_context=tool_context,
    )
