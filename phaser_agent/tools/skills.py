"""
Skills 原子工具模块

提供两类核心原子工具：
1. API Service 请求封装 - 与后端 API 服务交互
2. 工作空间文件操作封装 - 文件查询、创建、修改
"""

import json
import os
from typing import Any, Dict, List, Optional, Union

from .http_client import (
    http_request as _http_request,
    http_get as _http_get,
    http_post as _http_post,
    http_put as _http_put,
    http_delete as _http_delete,
    http_patch as _http_patch,
)
from .filesystem import (
    read_file as _read_file,
    write_file as _write_file,
    edit_file as _edit_file,
    list_files as _list_files,
    search as _search,
    ensure_dir as _ensure_dir,
    delete_file as _delete_file,
    move_file as _move_file,
    scan_files as _scan_files,
)


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


def _resp(status: str, status_code: int, message: str, data: Any = None) -> Dict[str, Any]:
    return {"status": status, "status_code": status_code, "message": message, "data": data}


# ============================================================
# API Service 请求封装
# ============================================================

def api_get(
    path: str,
    query: Optional[Dict[str, Any]] = None,
    tool_context: Any = None,
) -> Dict[str, Any]:
    """
    发送 GET 请求到 API Service。

    Args:
        path: API 路径，如 "/api/v1/projects" 或 "api/v1/projects"
              会自动拼接 api_base_url
        query: 可选的查询参数
        tool_context: ADK tool context，用于获取 token 和 api_base_url

    Returns:
        {
            "status": "success" | "error",
            "status_code": HTTP 状态码,
            "message": 错误信息或成功消息,
            "data": 响应数据（JSON 解析后）
        }
    """
    print(f"api_get----------------》: {path}")
    result = _http_get(
        url=path,
        query=query,
        auth=True,
        tool_context=tool_context,
    )
    return result


def api_post(
    path: str,
    body: Optional[Union[Dict[str, Any], str]] = None,
    tool_context: Any = None,
) -> Dict[str, Any]:
    """
    发送 POST 请求到 API Service。

    Args:
        path: API 路径
        body: 请求体，dict 会被自动 JSON 序列化
        tool_context: ADK tool context

    Returns:
        响应字典，包含 status, status_code, message, data
    """
    print(f"api_post----------------》: {path}")
    result = _http_post(
        url=path,
        body=body,
        auth=True,
        tool_context=tool_context,
    )
    return result


def api_put(
    path: str,
    body: Optional[Union[Dict[str, Any], str]] = None,
    tool_context: Any = None,
) -> Dict[str, Any]:
    """
    发送 PUT 请求到 API Service。

    Args:
        path: API 路径
        body: 请求体
        tool_context: ADK tool context

    Returns:
        响应字典
    """
    print(f"api_put----------------》: {path}")
    result = _http_put(
        url=path,
        body=body,
        auth=True,
        tool_context=tool_context,
    )
    return result


def api_delete(
    path: str,
    tool_context: Any = None,
) -> Dict[str, Any]:
    """
    发送 DELETE 请求到 API Service。

    Args:
        path: API 路径
        tool_context: ADK tool context

    Returns:
        响应字典
    """
    print(f"api_delete----------------》: {path}")
    result = _http_delete(
        url=path,
        auth=True,
        tool_context=tool_context,
    )
    return result


def api_patch(
    path: str,
    body: Optional[Union[Dict[str, Any], str]] = None,
    tool_context: Any = None,
) -> Dict[str, Any]:
    """
    发送 PATCH 请求到 API Service。

    Args:
        path: API 路径
        body: 请求体
        tool_context: ADK tool context

    Returns:
        响应字典
    """
    print(f"api_patch----------------》: {path}")
    result = _http_patch(
        url=path,
        body=body,
        auth=True,
        tool_context=tool_context,
    )
    return result


def api_request(
    path: str,
    method: str = "GET",
    query: Optional[Dict[str, Any]] = None,
    body: Optional[Union[Dict[str, Any], str]] = None,
    tool_context: Any = None,
) -> Dict[str, Any]:
    """
    通用 API 请求方法。

    Args:
        path: API 路径
        method: HTTP 方法 (GET/POST/PUT/DELETE/PATCH)
        query: 查询参数
        body: 请求体
        tool_context: ADK tool context

    Returns:
        响应字典
    """
    print(f"api_request----------------》: {method} {path}")
    result = _http_request(
        url=path,
        method=method.upper(),
        query=query,
        body=body,
        auth=True,
        tool_context=tool_context,
    )
    return result


# ============================================================
# 工作空间文件操作封装
# ============================================================

def workspace_read(
    file_path: str,
    tool_context: Any = None,
    start_line: Optional[int] = None,
    end_line: Optional[int] = None,
) -> Dict[str, Any]:
    """
    读取工作空间中的文件内容。

    Args:
        file_path: 相对于工作空间的文件路径
        tool_context: ADK tool context
        start_line: 起始行号（可选）
        end_line: 结束行号（可选）

    Returns:
        {
            "status": "success" | "error",
            "content": 文件内容,
            "truncated": 是否被截断,
            "start_line": 起始行号,
            "end_line": 结束行号
        }
    """
    print(f"workspace_read----------------》: {file_path}")
    return _read_file(
        file_path=file_path,
        tool_context=tool_context,
        start_line=start_line,
        end_line=end_line,
    )


def workspace_write(
    file_path: str,
    content: str,
    tool_context: Any = None,
) -> Dict[str, Any]:
    """
    写入文件到工作空间，自动创建所需目录。

    Args:
        file_path: 相对于工作空间的文件路径
        content: 文件内容
        tool_context: ADK tool context

    Returns:
        {"status": "success" | "error", "message": "..."}
    """
    print(f"workspace_write----------------》: {file_path}")
    return _write_file(
        file_path=file_path,
        content=content,
        tool_context=tool_context,
    )


def workspace_edit(
    file_path: str,
    patch: str,
    tool_context: Any = None,
) -> Dict[str, Any]:
    """
    编辑工作空间中的文件，支持 unified diff 或行范围替换。

    Args:
        file_path: 相对于工作空间的文件路径
        patch: 补丁内容，支持两种格式：
               1. unified diff 格式
               2. "Lx-Ly" 格式（第一行为行范围，后续为替换内容）
        tool_context: ADK tool context

    Returns:
        {"status": "success" | "error", "message": "..."}
    """
    print(f"workspace_edit----------------》: {file_path}")
    return _edit_file(
        file_path=file_path,
        patch=patch,
        tool_context=tool_context,
    )


def workspace_list(
    directory: str = "",
    tool_context: Any = None,
    glob: Optional[str] = None,
    contains: Optional[str] = None,
    include_ext: Optional[str] = None,
) -> Dict[str, Any]:
    """
    列出工作空间目录中的文件。

    Args:
        directory: 目录路径，空字符串表示根目录
        tool_context: ADK tool context
        glob: glob 模式过滤（如 "*.ts"）
        contains: 文件名包含的字符串
        include_ext: 包含的扩展名（如 ".ts,.js"）

    Returns:
        {
            "status": "success" | "error",
            "files": ["相对路径列表"],
            "truncated": 是否被截断
        }
    """
    print(f"workspace_list----------------》: {directory}")
    return _list_files(
        directory=directory,
        tool_context=tool_context,
        glob=glob,
        contains=contains,
        include_ext=include_ext,
    )


def workspace_search(
    query: str,
    directory: str = "",
    tool_context: Any = None,
    glob: Optional[str] = None,
    include_ext: Optional[str] = None,
    is_regex: bool = False,
    ignore_case: bool = True,
) -> Dict[str, Any]:
    """
    在工作空间文件中搜索内容。

    Args:
        query: 搜索查询（字符串或正则表达式）
        directory: 搜索目录
        tool_context: ADK tool context
        glob: glob 模式过滤
        include_ext: 包含的扩展名
        is_regex: 是否为正则表达式
        ignore_case: 是否忽略大小写

    Returns:
        {
            "status": "success" | "error",
            "matches": [
                {
                    "file": "文件路径",
                    "line": 行号,
                    "content": "匹配行内容"
                }
            ],
            "truncated": 是否被截断
        }
    """
    print(f"workspace_search----------------》: {query} in {directory}")
    return _search(
        query=query,
        directory=directory,
        tool_context=tool_context,
        glob=glob,
        include_ext=include_ext,
        is_regex=is_regex,
        ignore_case=ignore_case,
    )


def workspace_mkdir(
    directory: str,
    tool_context: Any = None,
) -> Dict[str, Any]:
    """
    在工作空间中创建目录（包括父目录）。

    Args:
        directory: 目录路径
        tool_context: ADK tool context

    Returns:
        {"status": "success" | "error", "message": "..."}
    """
    print(f"workspace_mkdir----------------》: {directory}")
    return _ensure_dir(
        directory=directory,
        tool_context=tool_context,
    )


def workspace_delete(
    file_path: str,
    recursive: bool = False,
    tool_context: Any = None,
) -> Dict[str, Any]:
    """
    删除工作空间中的文件或目录。

    Args:
        file_path: 文件或目录路径
        recursive: 是否递归删除目录
        tool_context: ADK tool context

    Returns:
        {"status": "success" | "error", "message": "..."}
    """
    print(f"workspace_delete----------------》: {file_path}")
    return _delete_file(
        file_path=file_path,
        recursive=recursive,
        tool_context=tool_context,
    )


def workspace_move(
    src_path: str,
    dst_path: str,
    tool_context: Any = None,
    overwrite: bool = False,
) -> Dict[str, Any]:
    """
    移动工作空间中的文件或目录。

    Args:
        src_path: 源路径
        dst_path: 目标路径
        tool_context: ADK tool context
        overwrite: 是否覆盖已存在的目标

    Returns:
        {"status": "success" | "error", "message": "..."}
    """
    print(f"workspace_move----------------》: {src_path} -> {dst_path}")
    return _move_file(
        src_path=src_path,
        dst_path=dst_path,
        tool_context=tool_context,
        overwrite=overwrite,
    )


def workspace_scan(
    directory: str = "",
    tool_context: Any = None,
    exclude_dirs: Optional[str] = None,
    include_ext: Optional[str] = None,
    calculate_hash: bool = True,
) -> Dict[str, Any]:
    """
    扫描工作空间目录，返回文件详细信息（包括类型、大小、hash）。

    Args:
        directory: 目录路径
        tool_context: ADK tool context
        exclude_dirs: 排除的目录名（逗号分隔，如 "node_modules,.git"）
        include_ext: 只包含的扩展名（逗号分隔）
        calculate_hash: 是否计算文件 hash

    Returns:
        {
            "status": "success" | "error",
            "files": [
                {
                    "path": "相对路径",
                    "name": "文件名",
                    "category": "text|image|audio|video|archive|binary",
                    "format": "具体格式",
                    "ext": "扩展名",
                    "size": 文件大小,
                    "hash": "sha256 hash"
                }
            ]
        }
    """
    print(f"workspace_scan----------------》: {directory}")
    return _scan_files(
        directory=directory,
        tool_context=tool_context,
        exclude_dirs=exclude_dirs,
        include_ext=include_ext,
        calculate_hash=calculate_hash,
    )


# ============================================================
# 便捷组合工具
# ============================================================

def workspace_create_file(
    file_path: str,
    content: str,
    tool_context: Any = None,
) -> Dict[str, Any]:
    """
    创建新文件（如果文件已存在则返回错误）。

    先检查文件是否存在，不存在则创建。

    Args:
        file_path: 文件路径
        content: 文件内容
        tool_context: ADK tool context

    Returns:
        {"status": "success" | "error", "message": "..."}
    """
    print(f"workspace_create_file----------------》: {file_path}")
    read_result = _read_file(file_path=file_path, tool_context=tool_context)
    if read_result.get("status") == "success":
        return _resp("error", 409, f"文件已存在: {file_path}")
    return _write_file(
        file_path=file_path,
        content=content,
        tool_context=tool_context,
    )


def workspace_create_directory(
    directory: str,
    tool_context: Any = None,
) -> Dict[str, Any]:
    """
    创建目录的别名，语义更清晰。

    Args:
        directory: 目录路径
        tool_context: ADK tool context

    Returns:
        {"status": "success" | "error", "message": "..."}
    """
    return workspace_mkdir(directory=directory, tool_context=tool_context)


def workspace_exists(
    file_path: str,
    tool_context: Any = None,
) -> Dict[str, Any]:
    """
    检查文件或目录是否存在。

    Args:
        file_path: 文件或目录路径
        tool_context: ADK tool context

    Returns:
        {"status": "success", "exists": True/False}
    """
    print(f"workspace_exists----------------》: {file_path}")
    read_result = _read_file(file_path=file_path, tool_context=tool_context)
    exists = read_result.get("status") == "success"
    return {"status": "success", "exists": exists}


def workspace_get_info(
    tool_context: Any = None,
) -> Dict[str, Any]:
    """
    获取当前工作空间信息。

    Args:
        tool_context: ADK tool context

    Returns:
        {
            "status": "success",
            "workspace_dir": 工作空间根目录,
            "workspace_game_dir": 游戏目录,
            "software_name": 当前软件名称
        }
    """
    print("workspace_get_info----------------》")
    state = getattr(tool_context, "state", None) if tool_context else None
    
    info = {
        "workspace_dir": _state_get(state, "workspace_dir"),
        "workspace_game_dir": _state_get(state, "workspace_game_dir"),
        "workspace_artifacts_dir": _state_get(state, "workspace_artifacts_dir"),
        "workspace_build_dir": _state_get(state, "workspace_build_dir"),
        "software_name": _state_get(state, "software_name"),
        "project_id": _state_get(state, "project_id"),
        "user_id": _state_get(state, "user_id"),
    }
    
    return {"status": "success", "data": info}
