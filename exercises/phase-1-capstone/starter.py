"""Phase 1 capstone, checkpoint 1: a bounded Tool Calling Loop."""

import copy
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

    messages = [
        {"role": "user", "content": user_text},
    ]
    for i in range(MAX_MODEL_REQUESTS):
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=tools,
        )
        choice = response.choices[0]
        api_message = choice.message
        history_message = assistant_message_from_api(api_message)
        messages.append(history_message)
        if api_message.tool_calls:
            if choice.finish_reason != "tool_calls":
                raise RuntimeError(
                    "响应同时包含 Tool Call 和不一致的 finish_reason"
                )
            for tool_call in api_message.tool_calls:
                result = execute_tool(tool_call)
                messages.append(
                    {"role": "tool", "content": result, "tool_call_id": tool_call.id}
                )
            continue

        if choice.finish_reason == "stop":
            return api_message.content or ""

        raise RuntimeError("模型没有正常结束")

    raise RuntimeError("模型请求次数超过最大次数")


class FakeCompletions:
    def __init__(self, responses: list[object]):
        self.responses = list(responses)
        self.requests: list[dict] = []

    def create(self, **request: object) -> object:
        self.requests.append(copy.deepcopy(request))
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

    call_a = fake_tool_call("call_a", "first", {})
    call_b = fake_tool_call("call_b", "second", {})
    multi_client = FakeClient(
        [
            fake_response("tool_calls", tool_calls=[call_a, call_b]),
            fake_response("stop", content="两个工具都已完成"),
        ]
    )
    multi_executions: list[str] = []
    assert run_agent_loop(
        client=multi_client,
        model="test-model",
        tools=[],
        user_text="执行两个工具",
        execute_tool=lambda tool_call: multi_executions.append(
            tool_call.id
        )
        or "{}",
    ) == "两个工具都已完成"
    assert multi_executions == ["call_a", "call_b"]
    assert [
        message["role"]
        for message in multi_client.completions.requests[1]["messages"]
    ] == ["user", "assistant", "tool", "tool"]

    incomplete_client = FakeClient(
        [fake_response("length", content="半截回答")]
    )
    try:
        run_agent_loop(
            client=incomplete_client,
            model="test-model",
            tools=[],
            user_text="测试截断",
            execute_tool=lambda _: "不应执行",
        )
    except RuntimeError as error:
        assert "没有正常结束" in str(error)
    else:
        raise AssertionError("非 stop 响应必须报错")

    max_client = FakeClient(
        [
            fake_response(
                "tool_calls",
                tool_calls=[fake_tool_call(f"call_{index}", "repeat", {})],
            )
            for index in range(MAX_MODEL_REQUESTS)
        ]
    )
    try:
        run_agent_loop(
            client=max_client,
            model="test-model",
            tools=[],
            user_text="测试请求上限",
            execute_tool=lambda _: "{}",
        )
    except RuntimeError as error:
        assert "超过最大次数" in str(error)
    else:
        raise AssertionError("达到请求上限后必须报错")

    print("checkpoint 1 passed")


def main() -> None:
    if "--self-check" not in sys.argv:
        print("运行方式：python starter.py --self-check")
        return
    self_check()


if __name__ == "__main__":
    main()
