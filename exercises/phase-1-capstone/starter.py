"""Phase 1 capstone, checkpoint 1: a bounded Tool Calling Loop."""

import copy
import json
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
from typing import Callable


MAX_MODEL_REQUESTS = 4
MAX_READ_BYTES = 50 * 1024


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


def resolve_workspace_file(workspace: Path, path: str) -> Path:
    """Resolve a relative path and require it to stay inside Workspace."""
    workspace_root = workspace.resolve()
    requested = Path(path)
    if requested.is_absolute():
        raise ValueError("路径必须是相对路径")

    target = (workspace_root / requested).resolve()
    try:
        target.relative_to(workspace_root)
    except ValueError as error:
        raise ValueError("路径必须位于 Workspace 内") from error
    return target


def read_file(workspace: Path, path: str, offset: int = 0) -> dict:
    """TODO: 第二关 B 由你亲手实现。"""
    raise NotImplementedError("请实现分段 read_file")


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


def checkpoint_2_check() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        workspace = root / "workspace"
        outside = root / "outside"
        workspace.mkdir()
        outside.mkdir()

        expected = (workspace / "notes" / "result.txt").resolve()
        assert resolve_workspace_file(
            workspace,
            "notes/result.txt",
        ) == expected

        def assert_rejected(path: str) -> None:
            try:
                resolve_workspace_file(workspace, path)
            except ValueError:
                return
            raise AssertionError(f"路径必须被拒绝：{path}")

        assert_rejected("../escape.txt")
        assert_rejected((outside / "absolute.txt").as_posix())

        link = workspace / "outside-link"
        link.symlink_to(outside, target_is_directory=True)
        assert_rejected("outside-link/secret.txt")

        source = workspace / "notes.txt"
        source.write_bytes(b"a" * MAX_READ_BYTES + b"tail")
        first = read_file(workspace, "notes.txt")
        assert first == {
            "path": "notes.txt",
            "content": "a" * MAX_READ_BYTES,
            "truncated": True,
            "next_offset": MAX_READ_BYTES,
        }
        second = read_file(
            workspace,
            "notes.txt",
            offset=first["next_offset"],
        )
        assert second == {
            "path": "notes.txt",
            "content": "tail",
            "truncated": False,
            "next_offset": None,
        }

        for bad_path, bad_offset in [
            ("missing.txt", 0),
            (".", 0),
            ("notes.txt", -1),
            ("../escape.txt", 0),
        ]:
            try:
                read_file(workspace, bad_path, offset=bad_offset)
            except ValueError:
                pass
            else:
                raise AssertionError(
                    f"read_file 必须拒绝：{bad_path}, offset={bad_offset}"
                )

    print("checkpoint 2B passed")


def main() -> None:
    if "--checkpoint-2" in sys.argv:
        checkpoint_2_check()
        return
    if "--self-check" not in sys.argv:
        print("运行方式：python starter.py --self-check")
        return
    self_check()


if __name__ == "__main__":
    main()
