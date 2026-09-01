"""Phase 1 capstone, checkpoint 1: a bounded Tool Calling Loop."""

import json
import sys
from types import SimpleNamespace
from typing import Callable


MAX_MODEL_REQUESTS = 4


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


def run_agent_loop(
    client: object,
    model: str,
    tools: list[dict],
    user_text: str,
    execute_tool: Callable[[object], str],
) -> str:
    """TODO: 这一关由你亲手实现。"""
    raise NotImplementedError("请实现第一关的有界 Tool Calling Loop")


class FakeCompletions:
    def __init__(self, responses: list[object]):
        self.responses = list(responses)
        self.requests: list[dict] = []

    def create(self, **request: object) -> object:
        self.requests.append(request)
        if not self.responses:
            raise AssertionError("模型请求次数超过测试准备的响应数量")
        return self.responses.pop(0)


class FakeClient:
    def __init__(self, responses: list[object]):
        self.completions = FakeCompletions(responses)
        self.chat = SimpleNamespace(completions=self.completions)


def fake_tool_call(call_id: str, name: str, arguments: dict) -> object:
    return SimpleNamespace(
        id=call_id,
        function=SimpleNamespace(
            name=name,
            arguments=json.dumps(arguments, ensure_ascii=False),
        ),
    )


def fake_response(
    finish_reason: str,
    *,
    content: str = "",
    tool_calls: list[object] | None = None,
) -> object:
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                finish_reason=finish_reason,
                message=SimpleNamespace(
                    content=content,
                    tool_calls=tool_calls or [],
                ),
            )
        ]
    )


def self_check() -> None:
    call = fake_tool_call("call_1", "multiply", {"a": 248, "b": 15})
    client = FakeClient(
        [
            fake_response("tool_calls", tool_calls=[call]),
            fake_response("stop", content="结果是 3720"),
        ]
    )
    executed: list[str] = []

    def execute(tool_call: object) -> str:
        executed.append(tool_call.id)
        return json.dumps(
            {"status": "completed", "result": 3720},
            ensure_ascii=False,
        )

    answer = run_agent_loop(
        client=client,
        model="test-model",
        tools=[{"type": "function"}],
        user_text="248 乘以 15",
        execute_tool=execute,
    )
    assert answer == "结果是 3720"
    assert executed == ["call_1"]
    assert len(client.completions.requests) == 2

    second_messages = client.completions.requests[1]["messages"]
    assert [message["role"] for message in second_messages] == [
        "user",
        "assistant",
        "tool",
    ]
    assert second_messages[-1]["tool_call_id"] == "call_1"

    contradictory_call = fake_tool_call(
        "call_bad",
        "multiply",
        {"a": 1, "b": 2},
    )
    contradictory_client = FakeClient(
        [fake_response("length", tool_calls=[contradictory_call])]
    )
    unsafe_executions: list[str] = []

    try:
        run_agent_loop(
            client=contradictory_client,
            model="test-model",
            tools=[],
            user_text="测试矛盾响应",
            execute_tool=lambda tool_call: unsafe_executions.append(
                tool_call.id
            )
            or "不应执行",
        )
    except RuntimeError:
        pass
    else:
        raise AssertionError("矛盾响应必须报错")
    assert unsafe_executions == []

    print("checkpoint 1 passed")


def main() -> None:
    if "--self-check" not in sys.argv:
        print("运行方式：python starter.py --self-check")
        return
    self_check()


if __name__ == "__main__":
    main()
