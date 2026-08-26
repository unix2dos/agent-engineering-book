"""
1. 最小 ReAct Agent：模型可以调用本地计算器

2. 判断某一轮走了哪条路，看这两个信号：
    2.1 finish_reason == "tool_calls" 且 msg.tool_calls 有值  -> 跑了本地工具
    2.2 finish_reason == "stop" 且 msg.tool_calls 为空        -> 给出最终自然语言回答
"""

import json
import os
from pathlib import Path
from openai import OpenAI


OPENCODE_GO_BASE_URL = "https://opencode.ai/zen/go/v1"
MODEL = os.environ.get("OPENCODE_MODEL", "mimo-v2.5")
def load_api_key() -> str:
    key = os.environ.get("OPENCODE_API_KEY") or os.environ.get("OPENCODE_GO_API_KEY")
    if key:
        return key
    auth_path = Path.home() / ".local/share/opencode/auth.json"
    if auth_path.exists():
        data = json.loads(auth_path.read_text())
        for provider in ("opencode-go", "opencode"):
            stored = data.get(provider) or {}
            if stored.get("key"):
                return stored["key"]
    raise RuntimeError(
        "Missing OpenCode API key. Set OPENCODE_API_KEY, or log in with `opencode`."
    )


client = OpenAI(base_url=OPENCODE_GO_BASE_URL, api_key=load_api_key())


# --- 1. 本地工具：模型只能“点名”，真正执行发生在这里 ---
def calculate(expression: str) -> str:
    try:
        return str(eval(expression))
    except Exception as e:
        return f"Error: {e}"
# 模型返回的是函数名字符串，用这张表在本地找到对应的 Python 函数。
tool_map = {"calculate": calculate}




# --- 2. 发给模型的工具 Schema（它看不到上面的 Python 函数） ---
tools = [{
    "type": "function",
    "function": {
        "name": "calculate",
        "description": "Evaluate a math expression",
        "parameters": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "For example: 123 * 456",
                }
            },
            "required": ["expression"],
        },
    },
}]


# --- 3. ReAct 循环：模型思考 -> 可能调工具 -> 把结果喂回去 ---
messages = [{"role": "user", "content": "帮我算一下 248 乘以 15 等于多少？"}]
round_num = 0
while True:
    round_num += 1
    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        tools=tools,  # 一个 schema
    )
    choice = response.choices[0]
    msg = choice.message
    print(f"\n--- round {round_num} ---")
    print(choice,"liuwei")
    print("finish_reason:", choice.finish_reason)

    # 把这一轮 assistant 消息写入历史；后面要把 tool_call id 对上。
    assistant_msg = {"role": "assistant", "content": msg.content or ""}
    if msg.tool_calls:
        assistant_msg["tool_calls"] = [
            {
                "id": tool_call.id,
                "type": "function",
                "function": {
                    "name": tool_call.function.name,
                    "arguments": tool_call.function.arguments,
                },
            }
            for tool_call in msg.tool_calls
        ]
    messages.append(assistant_msg)

    # 没有 tool_calls 说明模型已经直接给最终答案，结束循环。
    if not msg.tool_calls:
        print("path: model returned the answer directly (no tool_calls)")
        print("Agent final answer:", msg.content)
        break

    print("path: model requested tool_calls")
    for tool_call in msg.tool_calls:
        func_name = tool_call.function.name
        func_args = json.loads(tool_call.function.arguments)
        # 本地执行工具，再把结果追加进 messages，下一轮模型才能看到。
        result = tool_map[func_name](**func_args)
        print(f"  call {func_name}({func_args}) -> {result}")
        messages.append({
            "role": "tool",
            "tool_call_id": tool_call.id,
            "content": result,
        })
