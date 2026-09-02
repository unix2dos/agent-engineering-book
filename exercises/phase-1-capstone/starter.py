"""Phase 1 capstone, checkpoint 1: a bounded Tool Calling Loop."""

import copy
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
from typing import Callable


MAX_MODEL_REQUESTS = 4
MAX_READ_BYTES = 50 * 1024


def append_entry(path: Path, entry: dict) -> None:
    """TODO: 第三关 A 由你亲手实现。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(entry, ensure_ascii=False, separators=(",", ":")) + "\n"
    with path.open("a", encoding="utf-8") as file:
        file.write(line)
        file.flush()
        os.fsync(file.fileno())


def load_entries(path: Path) -> list[dict]:
    """TODO: 第三关 A 由你亲手实现。"""
    if not path.exists():
        return []

    entries = []
    with path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            if not line.strip():
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError as error:
                raise ValueError(f"第 {line_number} 行损坏") from error
    return entries


def persist_message(path: Path, message: dict) -> None:
    append_entry(path, {"type": "message", "message": message})


def append_compaction(
    path: Path,
    summary: str,
    retained_tail: list[dict],
    *,
    is_split_turn: bool = False,
) -> None:
    """TODO: 第三关 D 由你亲手实现。"""
    if not summary.strip():
        raise ValueError("Compaction Summary 不能为空")
    append_entry(
        path,
        {
            "type": "compaction",
            "summary": summary,
            "retained_tail": retained_tail,
            "is_split_turn": is_split_turn,
        },
    )


def build_prompt_view(entries: list[dict]) -> list[dict]:
    """TODO: 第三关 D 增加 Compaction 支持。"""
    latest_compaction = None
    for index in range(len(entries) - 1, -1, -1):
        if entries[index].get("type") == "compaction":
            latest_compaction = index
            break

    if latest_compaction is None:
        messages = []
        for entry in entries:
            if entry.get("type") == "message":
                messages.append(entry["message"])
        return messages

    checkpoint = entries[latest_compaction]
    messages = [
        {
            "role": "assistant",
            "content": "Conversation summary:\n" + checkpoint["summary"],
        }
    ]
    messages.extend(checkpoint["retained_tail"])

    for entry in entries[latest_compaction + 1 :]:
        if entry.get("type") == "message":
            messages.append(entry["message"])
    return messages



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
    session_file: Path | None = None,
) -> str:
    """TODO: 第三关 C 把消息持久化接入现有循环。"""

    def add_message(messages: list[dict], message: dict) -> None:
        messages.append(message)
        if session_file is not None:
            persist_message(session_file, message)

    messages = (
        build_prompt_view(load_entries(session_file))
        if session_file is not None
        else []
    )
    add_message(messages, {"role": "user", "content": user_text})
    for i in range(MAX_MODEL_REQUESTS):
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=tools,
        )
        choice = response.choices[0]
        api_message = choice.message
        history_message = assistant_message_from_api(api_message)
        add_message(messages, history_message)
        if api_message.tool_calls:
            if choice.finish_reason != "tool_calls":
                raise RuntimeError(
                    "响应同时包含 Tool Call 和不一致的 finish_reason"
                )
            for tool_call in api_message.tool_calls:
                result = execute_tool(tool_call)
                add_message(
                    messages,
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
    if offset < 0:
        raise ValueError("offset 不能为负数")

    file_path = resolve_workspace_file(workspace, path)
    if not file_path.is_file():
        raise ValueError("路径必须指向普通文件")

    with open(file_path, "rb") as file:
        file.seek(offset)
        raw = file.read(MAX_READ_BYTES + 1)
        content = raw[:MAX_READ_BYTES]
        truncated = len(raw) > MAX_READ_BYTES
        return {
            "path": path,
            "content": content.decode("utf-8"),
            "truncated": truncated,
            "next_offset": offset + len(content) if truncated else None,
        }


def write_file(workspace: Path, path: str, content: str) -> dict:
    """TODO: 第二关 C 由你亲手实现。"""
    file_path = resolve_workspace_file(workspace, path)
    if not file_path.parent.is_dir():
        raise ValueError("父目录不存在")
    if file_path.exists() and not file_path.is_file():
        raise ValueError("路径必须指向普通文件")

    encoded = content.encode("utf-8")
    overwritten = file_path.exists()
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=file_path.parent,
            delete=False,
        ) as temp_file:
            temp_file.write(encoded)
            temp_path = Path(temp_file.name)
        temp_path.replace(file_path)
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)

    return {
        "status": "succeeded",
        "path": path,
        "bytes_written": len(encoded),
        "overwritten": overwritten,
    }


def run_bash(workspace: Path, command: str) -> dict:
    """TODO: 第二关 E 由你亲手实现。"""
    try:
        completed = subprocess.run(
            ["/bin/zsh", "-lc", command],
            cwd=workspace,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {
            "status": "failed",
            "returncode": None,
            "stdout": "",
            "stderr": "命令执行超时",
        }

    return {
        "status": "succeeded" if completed.returncode == 0 else "failed",
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def execute_workspace_tool(
    workspace: Path,
    tool_call: object,
    approve: Callable[[str, dict], bool],
) -> str:
    """TODO: 第二关 D 由你亲手实现。"""
    tool_name = tool_call.function.name
    tool_arguments = json.loads(tool_call.function.arguments)
    if tool_name == "read_file":
        return json.dumps(
            read_file(
                workspace,
                tool_arguments["path"],
                tool_arguments.get("offset", 0),
            ),
            ensure_ascii=False,
        )
    elif tool_name == "write_file":
        if not approve(tool_name, tool_arguments):
            return json.dumps({"status": "rejected"}, ensure_ascii=False)
        result = write_file(workspace, tool_arguments["path"], tool_arguments["content"])
        return json.dumps(result, ensure_ascii=False)
    elif tool_name == "run_bash":
        if not approve(tool_name, tool_arguments):
            return json.dumps({"status": "rejected"}, ensure_ascii=False)
        result = run_bash(workspace, tool_arguments["command"])
        return json.dumps(result, ensure_ascii=False)
    else:
        return json.dumps(
            {
                "status": "failed",
                "error": "unknown_tool",
                "tool_name": tool_name,
            },
            ensure_ascii=False,
        )


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

        output_dir = workspace / "output"
        output_dir.mkdir()
        created = write_file(workspace, "output/result.txt", "hello 写入")
        assert created == {
            "status": "succeeded",
            "path": "output/result.txt",
            "bytes_written": len("hello 写入".encode("utf-8")),
            "overwritten": False,
        }
        assert (output_dir / "result.txt").read_text() == "hello 写入"

        overwritten = write_file(workspace, "output/result.txt", "short")
        assert overwritten["overwritten"] is True
        assert overwritten["bytes_written"] == 5
        assert (output_dir / "result.txt").read_text() == "short"

        for bad_path in ["../escape.txt", "outside-link/secret.txt", "."]:
            try:
                write_file(workspace, bad_path, "不应写入")
            except ValueError:
                pass
            else:
                raise AssertionError(f"write_file 必须拒绝：{bad_path}")

        try:
            write_file(workspace, "missing/result.txt", "不应写入")
        except ValueError:
            pass
        else:
            raise AssertionError("write_file 不应偷偷创建父目录")

        approval_requests: list[tuple[str, dict]] = []

        def reject(name: str, arguments: dict) -> bool:
            approval_requests.append((name, arguments))
            return False

        denied_call = fake_tool_call(
            "call_denied",
            "write_file",
            {"path": "output/denied.txt", "content": "不应落盘"},
        )
        denied = json.loads(
            execute_workspace_tool(workspace, denied_call, reject)
        )
        assert denied["status"] == "rejected"
        assert not (output_dir / "denied.txt").exists()
        assert approval_requests == [
            (
                "write_file",
                {"path": "output/denied.txt", "content": "不应落盘"},
            )
        ]

        approved_call = fake_tool_call(
            "call_approved",
            "write_file",
            {"path": "output/approved.txt", "content": "approved"},
        )
        approved = json.loads(
            execute_workspace_tool(workspace, approved_call, lambda *_: True)
        )
        assert approved["status"] == "succeeded"
        assert (output_dir / "approved.txt").read_text() == "approved"

        read_approvals: list[str] = []
        read_call = fake_tool_call(
            "call_read",
            "read_file",
            {"path": "output/approved.txt"},
        )
        read_result = json.loads(
            execute_workspace_tool(
                workspace,
                read_call,
                lambda name, _: read_approvals.append(name) or False,
            )
        )
        assert read_result["content"] == "approved"
        assert read_approvals == []

        unknown_call = fake_tool_call("call_unknown", "unknown_tool", {})
        unknown = json.loads(
            execute_workspace_tool(workspace, unknown_call, lambda *_: True)
        )
        assert unknown == {
            "status": "failed",
            "error": "unknown_tool",
            "tool_name": "unknown_tool",
        }

        bash_success = run_bash(workspace, "printf hello")
        assert bash_success == {
            "status": "succeeded",
            "returncode": 0,
            "stdout": "hello",
            "stderr": "",
        }

        bash_failure = run_bash(workspace, "printf boom >&2; exit 7")
        assert bash_failure == {
            "status": "failed",
            "returncode": 7,
            "stdout": "",
            "stderr": "boom",
        }

        denied_bash_call = fake_tool_call(
            "call_bash_denied",
            "run_bash",
            {"command": "printf denied > output/bash-denied.txt"},
        )
        denied_bash = json.loads(
            execute_workspace_tool(workspace, denied_bash_call, lambda *_: False)
        )
        assert denied_bash["status"] == "rejected"
        assert not (output_dir / "bash-denied.txt").exists()

        approved_bash_call = fake_tool_call(
            "call_bash_approved",
            "run_bash",
            {"command": "printf approved > output/bash-approved.txt"},
        )
        approved_bash = json.loads(
            execute_workspace_tool(workspace, approved_bash_call, lambda *_: True)
        )
        assert approved_bash["status"] == "succeeded"
        assert (output_dir / "bash-approved.txt").read_text() == "approved"

    print("checkpoint 2E passed")


def checkpoint_3_check() -> None:
    with tempfile.TemporaryDirectory() as temp:
        session_file = Path(temp) / "state" / "session.jsonl"
        assert load_entries(session_file) == []

        expected = [
            {
                "type": "message",
                "message": {"role": "user", "content": "你好"},
            },
            {
                "type": "message",
                "message": {"role": "assistant", "content": "你好！"},
            },
        ]
        for entry in expected:
            append_entry(session_file, entry)

        assert load_entries(session_file) == expected
        raw = session_file.read_text(encoding="utf-8")
        assert len(raw.splitlines()) == 2
        assert "你好" in raw
        assert "\\u4f60" not in raw

        broken_file = Path(temp) / "broken.jsonl"
        broken_file.write_text(
            '{"type":"message"}\n{"type":',
            encoding="utf-8",
        )
        try:
            load_entries(broken_file)
        except ValueError as error:
            assert "第 2 行" in str(error)
        else:
            raise AssertionError("损坏的 JSONL 必须被发现")

        prompt_file = Path(temp) / "prompt-view.jsonl"
        messages = [
            {"role": "user", "content": "读取 note.txt"},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_read",
                        "type": "function",
                        "function": {
                            "name": "read_file",
                            "arguments": '{"path":"note.txt"}',
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "tool_call_id": "call_read",
                "content": '{"content":"hello"}',
            },
            {"role": "assistant", "content": "文件内容是 hello"},
        ]
        persist_message(prompt_file, messages[0])
        persist_message(prompt_file, messages[1])
        append_entry(
            prompt_file,
            {
                "type": "tool_execution",
                "tool_call_id": "call_read",
                "status": "succeeded",
            },
        )
        persist_message(prompt_file, messages[2])
        persist_message(prompt_file, messages[3])

        prompt_entries = load_entries(prompt_file)
        assert len(prompt_entries) == 5
        prompt_view = build_prompt_view(prompt_entries)
        assert prompt_view == messages
        assert [message["role"] for message in prompt_view] == [
            "user",
            "assistant",
            "tool",
            "assistant",
        ]
        assert prompt_view[1]["tool_calls"][0]["id"] == "call_read"
        assert prompt_view[2]["tool_call_id"] == "call_read"

        workspace = Path(temp) / "workspace"
        workspace.mkdir()
        (workspace / "note.txt").write_text("persistent hello")
        agent_session = Path(temp) / "agent-session.jsonl"
        tool_call = fake_tool_call(
            "call_persistent_read",
            "read_file",
            {"path": "note.txt"},
        )
        first_client = FakeClient(
            [
                fake_response("tool_calls", tool_calls=[tool_call]),
                fake_response("stop", content="文件内容是 persistent hello"),
            ]
        )
        answer = run_agent_loop(
            client=first_client,
            model="test-model",
            tools=[],
            user_text="读取 note.txt",
            execute_tool=lambda call: execute_workspace_tool(
                workspace,
                call,
                lambda *_: False,
            ),
            session_file=agent_session,
        )
        assert answer == "文件内容是 persistent hello"
        first_entries = load_entries(agent_session)
        assert [entry["type"] for entry in first_entries] == [
            "message",
            "message",
            "message",
            "message",
        ]
        assert [message["role"] for message in build_prompt_view(first_entries)] == [
            "user",
            "assistant",
            "tool",
            "assistant",
        ]

        restarted_client = FakeClient(
            [fake_response("stop", content="我还记得上一轮")]
        )
        restarted_answer = run_agent_loop(
            client=restarted_client,
            model="test-model",
            tools=[],
            user_text="你还记得吗？",
            execute_tool=lambda _: "不应执行",
            session_file=agent_session,
        )
        assert restarted_answer == "我还记得上一轮"
        restarted_messages = restarted_client.completions.requests[0]["messages"]
        assert [message["role"] for message in restarted_messages] == [
            "user",
            "assistant",
            "tool",
            "assistant",
            "user",
        ]
        assert restarted_messages[-1]["content"] == "你还记得吗？"
        assert len(load_entries(agent_session)) == 6

        compacted_file = Path(temp) / "compacted-session.jsonl"
        old_messages = [
            {"role": "user", "content": "我叫小明"},
            {"role": "assistant", "content": "记住了"},
            {"role": "user", "content": "请读取项目配置"},
            {"role": "assistant", "content": "配置已经读取"},
        ]
        for message in old_messages:
            persist_message(compacted_file, message)

        append_compaction(
            compacted_file,
            summary="用户叫小明；此前已经读取项目配置。",
            retained_tail=old_messages[2:],
        )
        newest_message = {"role": "user", "content": "继续处理"}
        persist_message(compacted_file, newest_message)

        compacted_entries = load_entries(compacted_file)
        assert len(compacted_entries) == 6
        assert compacted_entries[:4] == [
            {"type": "message", "message": message}
            for message in old_messages
        ]
        assert build_prompt_view(compacted_entries) == [
            {
                "role": "assistant",
                "content": (
                    "Conversation summary:\n"
                    "用户叫小明；此前已经读取项目配置。"
                ),
            },
            *old_messages[2:],
            newest_message,
        ]

        try:
            append_compaction(compacted_file, "   ", [])
        except ValueError:
            pass
        else:
            raise AssertionError("Compaction Summary 不能为空")

    print("checkpoint 3D passed")


def main() -> None:
    if "--checkpoint-3" in sys.argv:
        checkpoint_3_check()
        return
    if "--checkpoint-2" in sys.argv:
        checkpoint_2_check()
        return
    if "--self-check" not in sys.argv:
        print("运行方式：python starter.py --self-check")
        return
    self_check()


if __name__ == "__main__":
    main()
