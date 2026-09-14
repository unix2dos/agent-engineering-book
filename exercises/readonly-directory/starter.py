"""受限目录工具已实现；重点观察 TOOLS、execute_tool 和既有 Agent Loop。"""

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "experiments/reading-pilot"))
import demo as reading_demo

resolve_workspace_file = reading_demo.CORE["resolve_workspace_file"]


def list_files(workspace: Path, path: str = ".", offset: int = 0, limit: int = 20) -> dict:
    """分页列出当前目录的普通文件名，跳过软链接并拒绝越界。"""
    if not isinstance(path, str):
        raise ValueError("path 必须是字符串")
    if path == "":
        raise ValueError("path 不能为空")
    if type(offset) is not int or offset < 0:
        raise ValueError("offset 必须是非负整数")
    if type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError("limit 必须是 1～100 的整数")

    directory = resolve_workspace_file(workspace, path)
    if not directory.is_dir():
        raise ValueError("path 必须指向一个存在的目录")

    files = []
    for file in directory.iterdir():
        if not file.is_symlink() and file.is_file():
            files.append(file.name)

    # ponytail: 每次仍扫描并排序整个目录；这里只限制返回量，不提供跨页快照。
    files = sorted(files)
    page = files[offset : offset + limit]
    next_offset = offset + len(page)
    if next_offset >= len(files):
        next_offset = None
    return {"path": path, "files": page, "next_offset": next_offset}


# 模型看到的工具说明；真正收到的参数仍需在执行时检查。
TOOLS = reading_demo.TOOLS + [{
    "type": "function",
    "function": {
        "name": "list_files",
        "description": "分页列出工作区内目录的普通文件名。next_offset 非 null 时可用它请求下一页。默认每页 20 个，最多 100 个；不递归、不读取内容、跳过软链接。",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "minLength": 1},
                "offset": {"type": "integer", "minimum": 0, "default": 0, "description": "排序后的文件名列表起始位置，从 0 开始，按条目计数。"},
                "limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 20},
            },
            "required": ["path"],
            "additionalProperties": False,
        },
    },
}]


def execute_tool(workspace: Path, call: object) -> str:
    if call.function.name != "list_files":
        # 原读取入口仍只接受 server.log 和 order_service.py。
        return reading_demo.execute_read(workspace, call)
    try:
        arguments = json.loads(call.function.arguments)
        if not isinstance(arguments, dict) or "path" not in arguments:
            raise ValueError("list_files 必须提供 path")
        if set(arguments) - {"path", "offset", "limit"}:
            raise ValueError("list_files 只接受 path、offset 和 limit")
        result = list_files(
            workspace, arguments["path"],
            offset=arguments.get("offset", 0), limit=arguments.get("limit", 20),
        )
    except ValueError as error:
        # 给模型可用于修正参数的具体原因；不把文件系统异常的绝对路径带出去。
        return json.dumps({"error": str(error)}, ensure_ascii=False)
    except (OSError, TypeError):
        return json.dumps({"error": "目录不可用，或请求不符合工具规则"}, ensure_ascii=False)
    return json.dumps(result, ensure_ascii=False)
