import fnmatch
import os
import re
import shutil
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from phaser_agent.config import (
    MAX_READ_CHARS,
    MAX_READ_CHARS_HARD,
    MAX_LIST_FILES,
    MAX_LIST_FILES_HARD,
    MAX_SEARCH_FILES,
    MAX_SEARCH_FILES_HARD,
    MAX_SEARCH_MATCHES,
    MAX_SEARCH_MATCHES_HARD,
    MAX_SEARCH_FILE_CHARS,
    MAX_SEARCH_FILE_CHARS_HARD,
    MAX_SEARCH_TOTAL_CHARS,
    MAX_SEARCH_TOTAL_CHARS_HARD,
    IGNORED_DIR_NAMES,
)
from .utils import get_target_path

_LINE_RANGE_RE = re.compile(r"^\s*(?:L)?(?P<start>\d+)\s*(?:-|:|,|\.\.)\s*(?:L)?(?P<end>\d+)\s*$")
_SINGLE_LINE_RE = re.compile(r"^\s*(?:L)?(?P<line>\d+)\s*$")

def _normalize_line(line: str) -> str:
    return line.rstrip("\r\n").rstrip()

def _split_lines(text: str) -> List[str]:
    return text.splitlines()

def _preserve_trailing_newline(original: str, updated: str) -> str:
    if "\r\n" in original:
        updated = updated.replace("\r\n", "\n").replace("\n", "\r\n")
        if original.endswith("\r\n") and not updated.endswith("\r\n"):
            updated += "\r\n"
        return updated
    if original.endswith("\n") and not updated.endswith("\n"):
        return updated + "\n"
    return updated

def _parse_line_edit_selector(selector: str) -> Optional[Tuple[int, int]]:
    m = _LINE_RANGE_RE.match(selector)
    if m:
        start = int(m.group("start"))
        end = int(m.group("end"))
        if start <= 0 or end <= 0:
            return None
        if start > end:
            start, end = end, start
        return start, end
    m = _SINGLE_LINE_RE.match(selector)
    if m:
        line = int(m.group("line"))
        if line <= 0:
            return None
        return line, line
    return None

def _replace_line_range(content: str, start_line: int, end_line: int, replacement: str) -> str:
    original_lines = _split_lines(content)
    total = len(original_lines)
    start_idx = max(0, min(total, start_line - 1))
    end_idx = max(0, min(total, end_line))
    replacement_lines = _split_lines(replacement)
    updated_lines = original_lines[:start_idx] + replacement_lines + original_lines[end_idx:]
    updated = "\n".join(updated_lines)
    return _preserve_trailing_newline(content, updated)

def _fuzzy_block_replace(content: str, search_block: str, replace_block: str) -> Optional[str]:
    file_lines = _split_lines(content)
    search_lines = _split_lines(search_block)
    if not search_lines:
        return None
    replace_lines = _split_lines(replace_block)

    search_norm = [_normalize_line(l) for l in search_lines]
    file_norm = [_normalize_line(l) for l in file_lines]

    max_start = len(file_lines) - len(search_lines)
    for start in range(max_start + 1):
        window = file_norm[start : start + len(search_norm)]
        if window == search_norm:
            updated_lines = file_lines[:start] + replace_lines + file_lines[start + len(search_lines) :]
            updated = "\n".join(updated_lines)
            return _preserve_trailing_newline(content, updated)
    return None

def _looks_like_unified_diff(text: str) -> bool:
    s = text.lstrip()
    if s.startswith(("diff --git", "--- ", "+++ ", "@@ ")):
        return True
    return "\n@@ " in text or "\n--- " in text or "\ndiff --git" in text

_HUNK_HEADER_RE = re.compile(r"^@@\s+-(?P<o_start>\d+)(?:,(?P<o_count>\d+))?\s+\+(?P<n_start>\d+)(?:,(?P<n_count>\d+))?\s+@@")

def _normalize_diff_path(p: str) -> str:
    p = p.strip()
    if p.startswith(("a/", "b/")):
        p = p[2:]
    return p.replace("\\", "/")

def _path_matches(diff_path: str, target_rel_path: str) -> bool:
    dp = _normalize_diff_path(diff_path)
    tp = _normalize_diff_path(target_rel_path)
    return dp == tp or dp.endswith("/" + tp) or tp.endswith("/" + dp)

def _extract_unified_diff_for_file(patch_text: str, target_rel_path: str) -> Tuple[List[dict], bool]:
    lines = patch_text.splitlines()
    in_target_file = False
    have_headers = False
    current_old: Optional[str] = None
    current_new: Optional[str] = None

    hunks: List[dict] = []
    current_hunk: Optional[dict] = None

    def flush_hunk() -> None:
        nonlocal current_hunk
        if current_hunk is not None:
            hunks.append(current_hunk)
            current_hunk = None

    for line in lines:
        if line.startswith("diff --git "):
            flush_hunk()
            in_target_file = False
            current_old = None
            current_new = None
            have_headers = False
            continue

        if line.startswith("--- "):
            flush_hunk()
            have_headers = True
            current_old = line[4:].strip()
            continue

        if line.startswith("+++ "):
            flush_hunk()
            have_headers = True
            current_new = line[4:].strip()
            candidates = [p for p in (current_old, current_new) if p and p != "/dev/null"]
            in_target_file = any(_path_matches(c, target_rel_path) for c in candidates)
            continue

        m = _HUNK_HEADER_RE.match(line)
        if m:
            if have_headers and not in_target_file:
                flush_hunk()
                current_hunk = None
                continue
            flush_hunk()
            current_hunk = {
                "old_start": int(m.group("o_start")),
                "old_count": int(m.group("o_count") or "1"),
                "new_start": int(m.group("n_start")),
                "new_count": int(m.group("n_count") or "1"),
                "lines": [],
            }
            continue

        if line == r"\ No newline at end of file":
            continue

        if current_hunk is not None and line[:1] in (" ", "+", "-"):
            current_hunk["lines"].append((line[0], line[1:]))
            continue

    flush_hunk()

    if not hunks and not have_headers:
        in_hunk = False
        for line in lines:
            m = _HUNK_HEADER_RE.match(line)
            if m:
                flush_hunk()
                current_hunk = {
                    "old_start": int(m.group("o_start")),
                    "old_count": int(m.group("o_count") or "1"),
                    "new_start": int(m.group("n_start")),
                    "new_count": int(m.group("n_count") or "1"),
                    "lines": [],
                }
                in_hunk = True
                continue
            if line == r"\ No newline at end of file":
                continue
            if in_hunk and current_hunk is not None and line[:1] in (" ", "+", "-"):
                current_hunk["lines"].append((line[0], line[1:]))
                continue
        flush_hunk()

    return hunks, have_headers

def _apply_unified_diff(content: str, patch_text: str, target_rel_path: str) -> Tuple[Optional[str], Optional[str]]:
    hunks, had_headers = _extract_unified_diff_for_file(patch_text, target_rel_path)
    if not hunks:
        if had_headers:
            return None, "No hunks found for target file"
        return None, "No hunks found"

    lines = _split_lines(content)
    line_norm = [_normalize_line(l) for l in lines]

    def hunk_matches_at(start_idx: int, hunk: dict) -> bool:
        idx = start_idx
        for op, text in hunk["lines"]:
            if op == "+":
                continue
            if idx >= len(lines):
                return False
            if line_norm[idx] != _normalize_line(text):
                return False
            idx += 1
        return True

    def apply_hunk_at(start_idx: int, hunk: dict) -> None:
        nonlocal lines, line_norm
        idx = start_idx
        new_segment: List[str] = []
        for op, text in hunk["lines"]:
            if op == " ":
                new_segment.append(lines[idx])
                idx += 1
            elif op == "-":
                idx += 1
            elif op == "+":
                new_segment.append(text)
        end_idx = idx
        lines = lines[:start_idx] + new_segment + lines[end_idx:]
        line_norm = [_normalize_line(l) for l in lines]

    for hunk in hunks:
        expected = max(0, min(len(lines), int(hunk["old_start"]) - 1))
        window = 50
        chosen: Optional[int] = None

        candidates: List[int] = []
        for delta in range(window + 1):
            for idx in (expected - delta, expected + delta):
                if 0 <= idx <= len(lines):
                    candidates.append(idx)

        seen = set()
        candidates = [c for c in candidates if not (c in seen or seen.add(c))]

        for idx in candidates:
            if hunk_matches_at(idx, hunk):
                chosen = idx
                break

        if chosen is None:
            for idx in range(0, len(lines) + 1):
                if hunk_matches_at(idx, hunk):
                    chosen = idx
                    break

        if chosen is None:
            return None, f"Hunk failed to apply near line {hunk['old_start']}"

        apply_hunk_at(chosen, hunk)

    updated = "\n".join(lines)
    return _preserve_trailing_newline(content, updated), None

def _get_context_info(tool_context: Any, project_id: Optional[str] = None) -> Tuple[str, Path]:
    state = getattr(tool_context, "state", {}) if tool_context else {}
    
    # 1. 确定 project_id
    if not project_id:
        project_id = state.get("user:project_id")
    if not project_id:
        raise ValueError("project_id is required (either as argument or in tool_context)")
        
    # 2. 确定根目录
    # work_space_manager 会设置 user:workspace_game_dir，这是代码所在的目录
    # 如果没有设置，回退到默认的 get_target_path 逻辑（基于 WORKSPACE_ROOT/project_id）
    workspace_game_dir = state.get("user:workspace_game_dir")
    
    if workspace_game_dir:
        # 如果存在 workspace_game_dir，我们认为它是绝对路径或相对于项目根的路径
        # 这里假设它是绝对路径，或者我们可以直接用它作为根
        root_path = Path(workspace_game_dir)
    else:
        # Fallback to standard path
        root_path = get_target_path("", str(project_id))
        
    return str(project_id), root_path

def _resolve_path(tool_context: Any, file_path: str, project_id: Optional[str] = None) -> Path:
    _, root_path = _get_context_info(tool_context, project_id)
    
    # 防止路径遍历
    target = (root_path / file_path).resolve()
    
    # 简单检查是否跑出去了
    try:
        root_abs = root_path.resolve()
        if os.path.commonpath([str(target), str(root_abs)]) != str(root_abs):
             raise ValueError(f"Path traversal detected: {file_path}")
    except ValueError:
         raise ValueError(f"Path traversal detected: {file_path}")
         
    return target

def read_file(
    file_path: str,
    project_id: Optional[str] = None,
    tool_context: Any = None,
    start_line: Optional[int] = None,
    end_line: Optional[int] = None,
    max_chars: Optional[int] = None,
) -> Dict[str, Any]:
    """Reads the content of a file in the workspace."""
    print(f"Reading file----------------》: {file_path}")
    try:
        target = _resolve_path(tool_context, file_path, project_id)
        if not target.exists():
            return {"status": "error", "message": "File not found"}

        if max_chars is None or max_chars <= 0:
            max_chars = MAX_READ_CHARS
        max_chars = min(int(max_chars), MAX_READ_CHARS_HARD)

        if start_line is None and end_line is None:
            with open(target, "r", encoding="utf-8", errors="replace") as f:
                content = f.read(max_chars + 1)
            truncated = len(content) > max_chars
            if truncated:
                content = content[:max_chars]
            return {"status": "success", "content": content, "truncated": truncated}

        if start_line is None:
            start_line = 1
        if end_line is None:
            end_line = start_line

        start_line = int(start_line)
        end_line = int(end_line)
        if start_line <= 0 or end_line <= 0:
            return {"status": "error", "message": "Invalid line range"}
        if start_line > end_line:
            start_line, end_line = end_line, start_line

        collected: List[str] = []
        total_chars = 0
        truncated = False

        with open(target, "r", encoding="utf-8", errors="replace") as f:
            for idx, line in enumerate(f, start=1):
                if idx < start_line:
                    continue
                if idx > end_line:
                    break
                collected.append(line)
                total_chars += len(line)
                if total_chars >= max_chars:
                    truncated = True
                    break

        content = "".join(collected)
        if truncated and len(content) > max_chars:
            content = content[:max_chars]
        return {
            "status": "success",
            "content": content,
            "truncated": truncated,
            "start_line": start_line,
            "end_line": end_line,
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

def write_file(file_path: str, content: str, project_id: Optional[str] = None, tool_context: Any = None) -> Dict[str, Any]:
    """Writes content to a file, creating directories if needed."""
    print(f"Writing file----------------》: {file_path}")
    try:
        target = _resolve_path(tool_context, file_path, project_id)
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, 'w', encoding='utf-8') as f:
            f.write(content)
        return {"status": "success", "message": f"Written to {file_path}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def edit_file(file_path: str, patch: str, project_id: Optional[str] = None, tool_context: Any = None) -> Dict[str, Any]:
    """Edits a file by applying a patch (unified diff or line-range)."""
    print(f"Editing file----------------》: {file_path}")
    try:
        target = _resolve_path(tool_context, file_path, project_id)
        if not target.exists():
            return {"status": "error", "message": "File not found"}
        
        with open(target, 'r', encoding='utf-8') as f:
            content = f.read()

        if _looks_like_unified_diff(patch):
            patched, err = _apply_unified_diff(content, patch, file_path)
            if err:
                return {"status": "error", "message": err}
            new_content = patched if patched is not None else content
        else:
            patch_lines = patch.splitlines()
            if patch_lines:
                maybe_selector = patch_lines[0]
                line_sel = _parse_line_edit_selector(maybe_selector)
                if line_sel is not None:
                    start_line, end_line = line_sel
                    replacement = "\n".join(patch_lines[1:])
                    new_content = _replace_line_range(content, start_line, end_line, replacement)
                else:
                    return {
                        "status": "error",
                        "message": "Unsupported patch format. Provide unified diff or 'Lx-Ly' on first line followed by replacement.",
                    }
            else:
                return {"status": "error", "message": "Empty patch"}
        
        with open(target, 'w', encoding='utf-8') as f:
            f.write(new_content)
            
        return {"status": "success", "message": f"Successfully patched {file_path}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def list_files(
    directory: str = "",
    project_id: Optional[str] = None,
    tool_context: Any = None,
    glob: Optional[str] = None,
    contains: Optional[str] = None,
    include_ext: Optional[str] = None,
    max_files: Optional[int] = None,
) -> Dict[str, Any]:
    """Lists files in a directory within the workspace."""
    print(f"Listing files----------------》: {directory}")
    try:
        target = _resolve_path(tool_context, directory, project_id)
        if not target.exists():
            return {"status": "error", "message": "Directory not found"}
        
        files = []
        truncated = False
        normalized_contains = contains.lower() if contains else None

        allowed_exts: Optional[Tuple[str, ...]] = None
        if include_ext:
            exts = []
            for raw in re.split(r"[,\s]+", include_ext.strip()):
                if not raw:
                    continue
                ext = raw if raw.startswith(".") else f".{raw}"
                exts.append(ext.lower())
            if exts:
                allowed_exts = tuple(exts)

        if max_files is None or int(max_files) <= 0:
            max_files = MAX_LIST_FILES
        max_files = min(int(max_files), MAX_LIST_FILES_HARD)
        
        _, root_path = _get_context_info(tool_context, project_id)

        for root, dirnames, filenames in os.walk(target):
            dirnames[:] = [d for d in dirnames if d not in IGNORED_DIR_NAMES]
            for name in filenames:
                full_path = os.path.join(root, name)
                rel_path = os.path.relpath(full_path, root_path)
                rel_posix = rel_path.replace("\\", "/")

                if allowed_exts is not None and not rel_posix.lower().endswith(allowed_exts):
                    continue
                if normalized_contains and normalized_contains not in rel_posix.lower():
                    continue
                if glob and not fnmatch.fnmatch(rel_posix, glob):
                    continue

                files.append(rel_path)
                if len(files) >= max_files:
                    truncated = True
                    break
            if truncated:
                break
        
        return {"status": "success", "files": files, "truncated": truncated}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def search(
    query: str,
    directory: str = "",
    project_id: Optional[str] = None,
    tool_context: Any = None,
    glob: Optional[str] = None,
    include_ext: Optional[str] = None,
    is_regex: bool = False,
    ignore_case: bool = True,
    max_files: Optional[int] = None,
    max_matches: Optional[int] = None,
    max_file_chars: Optional[int] = None,
    max_total_chars: Optional[int] = None,
) -> Dict[str, Any]:
    """Searches for a query in files within a directory."""
    print(f"Searching files----------------》: {directory}")
    try:
        if not query:
            return {"status": "error", "message": "Missing query"}

        target = _resolve_path(tool_context, directory, project_id)
        if not target.exists():
            return {"status": "error", "message": "Directory not found"}

        if max_files is None or int(max_files) <= 0:
            max_files = MAX_SEARCH_FILES
        max_files = min(int(max_files), MAX_SEARCH_FILES_HARD)

        if max_matches is None or int(max_matches) <= 0:
            max_matches = MAX_SEARCH_MATCHES
        max_matches = min(int(max_matches), MAX_SEARCH_MATCHES_HARD)

        if max_file_chars is None or int(max_file_chars) <= 0:
            max_file_chars = MAX_SEARCH_FILE_CHARS
        max_file_chars = min(int(max_file_chars), MAX_SEARCH_FILE_CHARS_HARD)

        if max_total_chars is None or int(max_total_chars) <= 0:
            max_total_chars = MAX_SEARCH_TOTAL_CHARS
        max_total_chars = min(int(max_total_chars), MAX_SEARCH_TOTAL_CHARS_HARD)

        allowed_exts: Optional[Tuple[str, ...]] = None
        if include_ext:
            exts = []
            for raw in re.split(r"[,\s]+", include_ext.strip()):
                if not raw:
                    continue
                ext = raw if raw.startswith(".") else f".{raw}"
                exts.append(ext.lower())
            if exts:
                allowed_exts = tuple(exts)

        flags = re.IGNORECASE if ignore_case else 0
        rx: Optional[re.Pattern[str]] = None
        if is_regex:
            rx = re.compile(query, flags)
        elif ignore_case:
            query_norm = query.lower()
        else:
            query_norm = query

        _, root_path = _get_context_info(tool_context, project_id)

        scanned_files = 0
        matches: List[Dict[str, Any]] = []
        truncated = False
        total_chars_read = 0

        for root, dirnames, filenames in os.walk(target):
            dirnames[:] = [d for d in dirnames if d not in IGNORED_DIR_NAMES]
            for name in filenames:
                full_path = os.path.join(root, name)
                rel_path = os.path.relpath(full_path, root_path).replace("\\", "/")

                if allowed_exts is not None and not rel_path.lower().endswith(allowed_exts):
                    continue
                if glob and not fnmatch.fnmatch(rel_path, glob):
                    continue

                scanned_files += 1
                if scanned_files > max_files:
                    truncated = True
                    break

                try:
                    file_chars_read = 0
                    with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                        for line_no, line in enumerate(f, start=1):
                            if not line:
                                continue

                            file_chars_read += len(line)
                            total_chars_read += len(line)

                            if file_chars_read > max_file_chars or total_chars_read > max_total_chars:
                                truncated = True
                                break

                            hay = line
                            if rx is not None:
                                if rx.search(hay) is None:
                                    continue
                            else:
                                if ignore_case:
                                    if query_norm not in hay.lower():
                                        continue
                                else:
                                    if query_norm not in hay:
                                        continue

                            matches.append(
                                {
                                    "file": rel_path,
                                    "line": line_no,
                                    "text": line.rstrip("\r\n")[:400],
                                }
                            )
                            if len(matches) >= max_matches:
                                truncated = True
                                break
                except Exception:
                    continue

                if truncated:
                    break

            if truncated:
                break

        return {
            "status": "success",
            "matches": matches,
            "match_count": len(matches),
            "scanned_files": min(scanned_files, max_files),
            "truncated": truncated,
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

def ensure_dir(directory: str, project_id: Optional[str] = None, tool_context: Any = None) -> Dict[str, Any]:
    """Ensures that a directory exists, creating it if necessary."""
    print(f"Ensuring directory----------------》: {directory}")
    try:
        target = _resolve_path(tool_context, directory, project_id)
        target.mkdir(parents=True, exist_ok=True)
        return {"status": "success", "message": f"Directory ensured: {directory}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def delete_file(file_path: str, recursive: bool = False, project_id: Optional[str] = None, tool_context: Any = None) -> Dict[str, Any]:
    try:
        target = _resolve_path(tool_context, file_path, project_id)
        if not target.exists():
            return {"status": "error", "message": "Path not found"}

        if target.is_dir():
            if not recursive:
                return {"status": "error", "message": "Refusing to delete directory without recursive=true"}
            shutil.rmtree(target)
            return {"status": "success", "message": f"Deleted directory: {file_path}"}

        target.unlink()
        return {"status": "success", "message": f"Deleted file: {file_path}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def move_file(
    src_path: str,
    dst_path: str,
    project_id: Optional[str] = None,
    tool_context: Any = None,
    overwrite: bool = False,
) -> Dict[str, Any]:
    """Moves a file or directory to a new location, overwriting if specified."""
    print(f"Moving file----------------》: {src_path} -> {dst_path}")
    try:
        src = _resolve_path(tool_context, src_path, project_id)
        if not src.exists():
            return {"status": "error", "message": "Source not found"}

        dst = _resolve_path(tool_context, dst_path, project_id)
        if dst.exists() and not overwrite:
            return {"status": "error", "message": "Destination exists (set overwrite=true to replace)"}

        dst.parent.mkdir(parents=True, exist_ok=True)

        if src.is_dir():
            if dst.exists():
                if overwrite:
                    shutil.rmtree(dst)
                else:
                    return {"status": "error", "message": "Destination directory exists"}
            shutil.move(str(src), str(dst))
            return {"status": "success", "message": f"Moved directory: {src_path} -> {dst_path}"}

        if dst.exists() and overwrite:
            dst.unlink()
        os.replace(str(src), str(dst))
        return {"status": "success", "message": f"Moved file: {src_path} -> {dst_path}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
