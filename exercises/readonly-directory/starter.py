"""小需求：给已有只读助手增加 list_files；只需实现下面这个函数。"""

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "experiments/reading-pilot"))
import demo as reading_demo

resolve_workspace_file = reading_demo.CORE["resolve_workspace_file"]


def list_files(workspace: Path, path: str = ".", offset: int = 0, limit: int = 20) -> dict:
    """你的部分：列当前目录的普通文件名，排序、跳过软链接、拒绝越界。"""
    if not isinstance(path, str):
        raise ValueError("path 必须是字符串")
    if path == "":
        raise ValueError("path 不能为空")

    directory = resolve_workspace_file(workspace, path)
    if not directory.is_dir():
        raise ValueError("path 必须指向一个存在的目录")

    files = []
    for file in directory.iterdir():
        if not file.is_symlink() and file.is_file():
            files.append(file.name)

    files = sorted(files)[offset:offset+limit]
    return {"path": path, "files": files}


# 下方接线已准备好，第一遍不需要改。
TOOLS = reading_demo.TOOLS + [{
    "type": "function",
    "function": {
        "name": "list_files",
        "description": "列出工作区内指定目录的普通文件名；不递归，不读取内容，跳过软链接。",
        "parameters": {
            "type": "object",
            "properties": {"path": {"type": "string", "minLength": 1}},
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
        if not isinstance(arguments, dict) or set(arguments) != {"path"}:
            raise ValueError("list_files 参数必须只有 path")
        path = arguments["path"]
        if not isinstance(path, str) or not path:
            raise ValueError("path 必须是非空字符串")
        result = list_files(workspace, path)
    except (OSError, ValueError, TypeError):
        return json.dumps({"error": "目录不可用，或请求不符合工具规则"}, ensure_ascii=False)
    return json.dumps(result, ensure_ascii=False)
