"""A minimal, bounded OpenAI-compatible tool-calling agent."""

import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace


BASE_URL = os.getenv("OPENAI_BASE_URL", "https://opencode.ai/zen/go/v1")
MODEL = os.getenv("OPENAI_MODEL", os.getenv("OPENCODE_MODEL", "mimo-v2.5"))
MAX_STEPS = 8
MAX_ABS_VALUE = 1_000_000

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "multiply",
            "description": "Multiply two integers",
            "parameters": {
                "type": "object",
                "properties": {
                    "a": {"type": "integer"},
                    "b": {"type": "integer"},
                },
                "required": ["a", "b"],
                "additionalProperties": False,
            },
        },
    }
]


def multiply(a: int, b: int) -> int:
    if (
        isinstance(a, bool)
        or isinstance(b, bool)
        or not isinstance(a, int)
        or not isinstance(b, int)
    ):
        raise ValueError("a 和 b 必须是整数")
    if abs(a) > MAX_ABS_VALUE or abs(b) > MAX_ABS_VALUE:
        raise ValueError(f"a 和 b 的绝对值不能超过 {MAX_ABS_VALUE}")
    return a * b


def execute_tool(tool_call: object) -> str:
    try:
        if tool_call.function.name != "multiply":
            raise ValueError(f"未知工具：{tool_call.function.name}")
        arguments = json.loads(tool_call.function.arguments)
        if not isinstance(arguments, dict):
            raise ValueError("工具参数必须是 JSON 对象")
        if set(arguments) != {"a", "b"}:
            raise ValueError("multiply 只接受 a 和 b")
        result = multiply(arguments["a"], arguments["b"])
        payload = {"status": "completed", "result": result}
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
        payload = {"status": "error", "message": str(error)}
    return json.dumps(payload, ensure_ascii=False)


def assistant_message_from_api(message: object) -> dict:
    result = {"role": "assistant", "content": message.content or ""}
    if message.tool_calls:
        result["tool_calls"] = [
            {
                "id": call.id,
                "type": "function",
                "function": {
                    "name": call.function.name,
                    "arguments": call.function.arguments,
                },
            }
            for call in message.tool_calls
        ]
    return result


def run_agent(client: object, model: str, user_text: str) -> str:
    messages = [{"role": "user", "content": user_text}]

    for step in range(1, MAX_STEPS + 1):
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=TOOLS,
        )
        choice = response.choices[0]
        message = choice.message
        messages.append(assistant_message_from_api(message))

        print(f"step {step}: finish_reason={choice.finish_reason}")

        if message.tool_calls:
            if choice.finish_reason != "tool_calls":
                raise RuntimeError(
                    "响应同时包含 Tool Call 和不一致的 finish_reason"
                )
            for tool_call in message.tool_calls:
                result = execute_tool(tool_call)
                print(
                    f"step {step}: {tool_call.function.name}"
                    f" call_id={tool_call.id} result={result}"
                )
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result,
                    }
                )
            continue

        if choice.finish_reason == "stop":
            return message.content or ""

        raise RuntimeError(f"模型没有正常结束：{choice.finish_reason}")

    raise RuntimeError(f"超过最大步骤数：{MAX_STEPS}")


def load_api_key() -> str:
    key = os.getenv("OPENCODE_GO_API_KEY") or os.getenv("OPENCODE_API_KEY")
    if key:
        return key

    auth_path = Path.home() / ".local/share/opencode/auth.json"
    if auth_path.exists():
        data = json.loads(auth_path.read_text(encoding="utf-8"))
        for provider in ("opencode-go", "opencode"):
            stored = data.get(provider) or {}
            if stored.get("key"):
                return stored["key"]

    raise RuntimeError(
        "没有找到 OpenCode API Key；请设置 OPENCODE_GO_API_KEY，"
        "或运行 opencode auth login"
    )


def make_client() -> tuple[object, str]:
    try:
        from openai import OpenAI
    except ImportError as error:
        raise RuntimeError("缺少 openai 包，请运行：python -m pip install openai") from error
    return OpenAI(base_url=BASE_URL, api_key=load_api_key()), MODEL


def fake_response(*, finish_reason: str, content: str = "", tool_calls=None):
    message = SimpleNamespace(content=content, tool_calls=tool_calls or [])
    return SimpleNamespace(
        choices=[SimpleNamespace(finish_reason=finish_reason, message=message)]
    )


def self_check() -> None:
    multiply_call = SimpleNamespace(
        id="call_1",
        function=SimpleNamespace(
            name="multiply",
            arguments='{"a":248,"b":15}',
        ),
    )
    assert json.loads(execute_tool(multiply_call)) == {
        "status": "completed",
        "result": 3720,
    }

    invalid_call = SimpleNamespace(
        id="call_2",
        function=SimpleNamespace(
            name="multiply",
            arguments='{"a":2,"b":3,"command":"whoami"}',
        ),
    )
    assert json.loads(execute_tool(invalid_call))["status"] == "error"

    class FakeCompletions:
        def __init__(self):
            self.requests = []

        def create(self, **kwargs):
            self.requests.append(kwargs)
            if len(self.requests) == 1:
                return fake_response(
                    finish_reason="tool_calls",
                    tool_calls=[multiply_call],
                )
            tool_message = kwargs["messages"][-1]
            assert tool_message["role"] == "tool"
            assert tool_message["tool_call_id"] == "call_1"
            assert json.loads(tool_message["content"])["result"] == 3720
            return fake_response(finish_reason="stop", content="结果是 3720")

    completions = FakeCompletions()
    client = SimpleNamespace(
        chat=SimpleNamespace(completions=completions)
    )
    assert run_agent(client, "test-model", "248 乘以 15") == "结果是 3720"
    assert len(completions.requests) == 2

    class IncompleteCompletions:
        def create(self, **_):
            return fake_response(finish_reason="length", content="未完成")

    incomplete_client = SimpleNamespace(
        chat=SimpleNamespace(completions=IncompleteCompletions())
    )
    try:
        run_agent(incomplete_client, "test-model", "test")
    except RuntimeError as error:
        assert "没有正常结束" in str(error)
    else:
        raise AssertionError("length 不应被当作正常 Final")

    print("self-check passed")


def main() -> None:
    if "--self-check" in sys.argv:
        self_check()
        return
    client, model = make_client()
    answer = run_agent(client, model, "帮我算一下 248 乘以 15 等于多少？")
    print("Agent>", answer)


if __name__ == "__main__":
    main()
