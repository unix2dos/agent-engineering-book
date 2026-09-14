"""综合项目的工具说明与模型连接；导入本模块不会创建客户端或读取文件。"""

import os


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "分段读取 Workspace 内的 UTF-8 文本文件",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "offset": {"type": "integer", "minimum": 0},
                },
                "required": ["path"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_bash",
            "description": "在 Workspace 内执行 Bash 命令",
            "parameters": {
                "type": "object",
                "properties": {"command": {"type": "string"}},
                "required": ["command"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "原子写入 Workspace 内的 UTF-8 文本文件",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["path", "content"],
                "additionalProperties": False,
            },
        },
    },
]


def make_client() -> tuple[object, str]:
    try:
        from openai import OpenAI
    except ImportError as error:
        raise RuntimeError(
            "缺少 openai 包，请运行：python -m pip install openai"
        ) from error

    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("OPENAI_MODEL")
    if not api_key or not model:
        raise RuntimeError("请设置 OPENAI_API_KEY 和 OPENAI_MODEL")
    return OpenAI(
        api_key=api_key,
        base_url=os.getenv("OPENAI_BASE_URL") or None,
    ), model
