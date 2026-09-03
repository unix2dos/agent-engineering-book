"""Phase 1 capstone, checkpoint 1: a bounded Tool Calling Loop."""

import copy
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import uuid
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


VALID_EXECUTION_STATUSES = {
    "approved",
    "rejected",
    "running",
    "succeeded",
    "failed",
    "unknown",
}


def arguments_sha256(arguments: dict) -> str:
    """TODO: 第四关 B。为工具参数生成稳定 Hash。"""
    canonical = json.dumps(
        arguments,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def make_idempotency_key(tool_name: str, tool_call_id: str) -> str:
    """TODO: 第四关 B。为同一个 Tool Call 生成稳定幂等 Key。"""
    if not tool_name or not tool_call_id:
        raise ValueError("工具名和 tool_call_id 不能为空")
    return f"{tool_name}:{tool_call_id}"


def append_execution_state(
    path: Path,
    execution_id: str,
    tool_call_id: str,
    status: str,
    details: dict | None = None,
) -> dict:
    """TODO: 第四关 A。追加一条 Tool Execution Ledger Entry。"""
    if status not in VALID_EXECUTION_STATUSES:
        raise ValueError(f"未知执行状态：{status}")

    entry = {
        "type": "tool_execution",
        "execution_id": execution_id,
        "tool_call_id": tool_call_id,
        "status": status,
    }
    if details:
        entry.update(details)
    append_entry(path, entry)
    return entry


def latest_execution_states(entries: list[dict]) -> dict[str, dict]:
    """TODO: 第四关 A。恢复每个 execution_id 的最后状态。"""
    execution_states = {}
    for entry in entries:
        if entry.get("type") == "tool_execution":
            execution_id = entry["execution_id"]
            execution_states[execution_id] = entry
    return execution_states


def mark_interrupted_executions_unknown(session_file: Path) -> list[str]:
    """TODO: 第五关 B。把重启时遗留的 running 追加为 unknown。"""
    entries = load_entries(session_file)
    execution_states = latest_execution_states(entries)
    marked = []
    for execution_id, execution_state in execution_states.items():
        if execution_state.get("status") != "running":
            continue

        details = {}
        for key in ("tool_name", "idempotency_key", "arguments_sha256"):
            if key in execution_state:
                details[key] = execution_state[key]
        details["message"] = "进程在 running 状态中断，副作用无法确认"

        append_execution_state(
            session_file,
            execution_id,
            execution_state["tool_call_id"],
            "unknown",
            details,
        )
        marked.append(execution_id)
    return marked


def pending_tool_calls(entries: list[dict]) -> list[dict]:
    pending = {}
    for entry in entries:
        if entry.get("type") != "message":
            continue
        message = entry["message"]
        if message.get("role") == "assistant":
            for call in message.get("tool_calls", []):
                pending[call["id"]] = call
        elif message.get("role") == "tool":
            pending.pop(message.get("tool_call_id"), None)
    return list(pending.values())


def latest_execution_by_tool_call(entries: list[dict]) -> dict[str, dict]:
    states = {}
    for entry in entries:
        if entry.get("type") == "tool_execution":
            states[entry["tool_call_id"]] = entry
    return states


def repair_missing_tool_results(session_file: Path) -> list[str]:
    """TODO: 第五关 C。根据 Ledger 补写缺失的 Tool Result。"""
    mark_interrupted_executions_unknown(session_file)
    entries = load_entries(session_file)
    calls = pending_tool_calls(entries)
    states = latest_execution_by_tool_call(entries)
    repaired = []

    for call in calls:
        call_id = call["id"]
        state = states.get(call_id)
        if state is None:
            raise RuntimeError(f"Tool Call 没有 Ledger：{call_id}")

        arguments = json.loads(call["function"]["arguments"])
        if not isinstance(arguments, dict):
            raise RuntimeError(f"Tool Call 参数不是 JSON 对象：{call_id}")
        if state.get("arguments_sha256") != arguments_sha256(arguments):
            raise RuntimeError(f"Tool Call 参数与 Ledger 不一致：{call_id}")

        if state["status"] == "unknown":
            result = {
                "status": "unknown",
                "execution_id": state["execution_id"],
                "message": state["message"],
            }
        elif state["status"] == "rejected":
            result = {
                "status": "rejected",
                "execution_id": state["execution_id"],
            }
        elif state["status"] in {"succeeded", "failed"}:
            if "result" not in state:
                raise RuntimeError(f"Ledger 缺少可重放 Result：{call_id}")
            result = state["result"]
        else:
            raise RuntimeError(
                f"Ledger 状态尚不能生成 Tool Result：{state['status']}"
            )

        persist_message(
            session_file,
            {
                "role": "tool",
                "tool_call_id": call_id,
                "content": json.dumps(result, ensure_ascii=False),
            },
        )
        repaired.append(call_id)
    return repaired


def reconcile_unknown_write_files(
    workspace: Path,
    session_file: Path,
) -> list[str]:
    """TODO: 第五关 E。核对 unknown write_file 的目标状态。"""
    entries = load_entries(session_file)
    calls = pending_tool_calls(entries)
    states = latest_execution_by_tool_call(entries)
    reconciled = []

    for call in calls:
        call_id = call["id"]
        tool_name = call["function"]["name"]
        if tool_name != "write_file":
            continue

        state = states.get(call_id)
        if state is None or state.get("status") != "unknown":
            continue
        if state.get("tool_name") != tool_name:
            raise RuntimeError(f"Tool Call 与 Ledger 工具名不一致：{call_id}")

        arguments = json.loads(call["function"]["arguments"])
        if not isinstance(arguments, dict):
            raise RuntimeError(f"Tool Call 参数不是 JSON 对象：{call_id}")
        if set(arguments) != {"path", "content"}:
            raise RuntimeError(f"write_file 参数不完整：{call_id}")
        if not isinstance(arguments["path"], str) or not isinstance(
            arguments["content"], str
        ):
            raise RuntimeError(f"write_file 参数类型错误：{call_id}")
        if state.get("arguments_sha256") != arguments_sha256(arguments):
            raise RuntimeError(f"Tool Call 参数与 Ledger 不一致：{call_id}")

        target = resolve_workspace_file(workspace, arguments["path"])
        expected = arguments["content"].encode("utf-8")
        if not target.is_file() or target.read_bytes() != expected:
            continue

        result = {
            "status": "succeeded",
            "execution_id": state["execution_id"],
            "path": arguments["path"],
            "bytes_written": len(expected),
            "reconciled": True,
        }
        details = {
            key: state[key]
            for key in ("tool_name", "idempotency_key", "arguments_sha256")
        }
        details["result"] = result
        append_execution_state(
            session_file,
            state["execution_id"],
            call_id,
            "succeeded",
            details,
        )
        reconciled.append(call_id)

    return reconciled


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


def find_compaction_cut(
    messages: list[dict],
    keep_recent_turns: int = 1,
) -> int | None:
    """TODO: 第三关 E 由你亲手实现。"""

    if keep_recent_turns < 0:
        raise ValueError("keep_recent_turns 不能为负数")

    if not messages:
        return None

    completed_turn_ends = []
    inside_turn = False

    for position, message in enumerate(messages, start=1):
        role = message.get("role")

        if role == "user":
            inside_turn = True

        elif (
            inside_turn
            and role == "assistant"
            and not message.get("tool_calls")
        ):
            completed_turn_ends.append(position)
            inside_turn = False

    compact_turn_count = len(completed_turn_ends) - keep_recent_turns
    if compact_turn_count <= 0:
        return None
    return completed_turn_ends[compact_turn_count - 1]


def maybe_compact(
    session_file: Path,
    max_prompt_chars: int,
    keep_recent_turns: int,
    summarize: Callable[[list[dict]], str],
) -> bool:
    """TODO: 第三关 F 由你亲手实现。"""
    if keep_recent_turns < 0:
        raise ValueError("keep_recent_turns 不能为负数")

    if max_prompt_chars <= 0:
        raise ValueError("max_prompt_chars 不能为零或负数")

    if not session_file.exists():
        return False

    entries = load_entries(session_file)
    if not entries:
        return False

    prompt_view = build_prompt_view(entries)
    prompt_chars = len(json.dumps(prompt_view, ensure_ascii=False))
    if prompt_chars <= max_prompt_chars:
        return False

    cut_position = find_compaction_cut(prompt_view, keep_recent_turns)
    if cut_position is None:
        return False

    prefix = prompt_view[:cut_position]
    retained_tail = prompt_view[cut_position:]
    summary = summarize(prefix)
    append_compaction(session_file, summary, retained_tail)
    return True




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
    user_text: str | None,
    execute_tool: Callable[[object], str],
    session_file: Path | None = None,
    compact_before_request: Callable[[], bool] | None = None,
) -> str:
    """TODO: 第三关 G 在模型请求前接入 Compaction。"""

    def add_message(messages: list[dict], message: dict) -> None:
        messages.append(message)
        if session_file is not None:
            persist_message(session_file, message)

    messages = (
        build_prompt_view(load_entries(session_file))
        if session_file is not None
        else []
    )
    # TODO: 第五关 D。user_text=None 时继续以 Tool Result 结尾的旧 Turn。
    if user_text is None:
        if session_file is None:
            raise ValueError("session_file 不能为 None")
        if not messages:
            raise ValueError("没有可以继续的旧 Turn")
        if messages[-1].get("role") != "tool":
            raise ValueError("恢复旧 Turn 时，最后一条必须是 Tool Result")
    else:
        add_message(messages, {"role": "user", "content": user_text})
    for i in range(MAX_MODEL_REQUESTS):
        # TODO: 第三关 G 在这里执行压缩，并在成功后刷新 messages。
        if compact_before_request is not None:
            if session_file is None:
                raise ValueError("session_file 不能为 None")
            if compact_before_request():
                messages = build_prompt_view(load_entries(session_file))

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


def execute_workspace_tool_with_ledger(
    workspace: Path,
    session_file: Path,
    tool_call: object,
    approve: Callable[[str, dict], bool],
    after_effect: Callable[[dict], None] | None = None,
) -> str:
    """TODO: 第四关 C。执行副作用工具并记录 Ledger 状态。"""
    tool_name = tool_call.function.name
    tool_arguments = json.loads(tool_call.function.arguments)
    if not isinstance(tool_arguments, dict):
        raise ValueError("工具参数必须是 JSON 对象")

    if tool_name not in {"write_file", "run_bash"}:
        return execute_workspace_tool(workspace, tool_call, approve)

    execution_id = f"exec_{uuid.uuid4().hex}"
    details = {
        "tool_name": tool_name,
        "idempotency_key": make_idempotency_key(tool_name, tool_call.id),
        "arguments_sha256": arguments_sha256(tool_arguments),
    }

    if not approve(tool_name, tool_arguments):
        append_execution_state(
            session_file,
            execution_id,
            tool_call.id,
            "rejected",
            details,
        )
        return json.dumps(
            {
                "status": "rejected",
                "execution_id": execution_id,
            },
            ensure_ascii=False,
        )

    append_execution_state(
        session_file,
        execution_id,
        tool_call.id,
        "approved",
        details,
    )
    append_execution_state(
        session_file,
        execution_id,
        tool_call.id,
        "running",
        details,
    )

    result = json.loads(
        execute_workspace_tool(
            workspace,
            tool_call,
            lambda *_: True,
        )
    )
    result["execution_id"] = execution_id
    # TODO: 第五关 A。在副作用完成、Ledger 终态写入前调用 after_effect。
    if after_effect is not None:
        after_effect(result)

    append_execution_state(
        session_file,
        execution_id,
        tool_call.id,
        result["status"],
        {**details, "result": result},
    )
    return json.dumps(result, ensure_ascii=False)


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

        turn_messages = [
            {"role": "user", "content": "T1 用户"},
            {"role": "assistant", "content": "T1 Final"},
            {"role": "user", "content": "T2 用户"},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [{"id": "call_t2"}],
            },
            {
                "role": "tool",
                "tool_call_id": "call_t2",
                "content": "T2 Tool Result",
            },
            {"role": "assistant", "content": "T2 Final"},
            {"role": "user", "content": "T3 当前用户"},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [{"id": "call_t3"}],
            },
        ]
        cut = find_compaction_cut(turn_messages, keep_recent_turns=1)
        assert cut == 2
        assert turn_messages[:cut] == turn_messages[:2]
        assert turn_messages[cut:] == turn_messages[2:]

        cut_all_completed = find_compaction_cut(
            turn_messages,
            keep_recent_turns=0,
        )
        assert cut_all_completed == 6
        assert turn_messages[cut_all_completed]["role"] == "user"

        only_recent = turn_messages[2:]
        assert find_compaction_cut(only_recent, keep_recent_turns=1) is None

        summary_view = [
            {
                "role": "assistant",
                "content": "Conversation summary:\n更早的历史",
            },
            *only_recent,
        ]
        assert find_compaction_cut(summary_view, keep_recent_turns=0) == 5

        try:
            find_compaction_cut(turn_messages, keep_recent_turns=-1)
        except ValueError:
            pass
        else:
            raise AssertionError("keep_recent_turns 不能为负数")

        small_file = Path(temp) / "small-session.jsonl"
        persist_message(small_file, {"role": "user", "content": "短问题"})
        persist_message(
            small_file,
            {"role": "assistant", "content": "短回答"},
        )

        def unexpected_summary(_: list[dict]) -> str:
            raise AssertionError("此时不应生成摘要")

        assert maybe_compact(
            small_file,
            max_prompt_chars=10_000,
            keep_recent_turns=0,
            summarize=unexpected_summary,
        ) is False
        assert len(load_entries(small_file)) == 2

        large_file = Path(temp) / "large-session.jsonl"
        for message in turn_messages:
            persist_message(large_file, message)

        summarized_prefix: list[dict] = []

        def summarize_prefix(prefix: list[dict]) -> str:
            summarized_prefix.extend(prefix)
            return "T1 已完成。"

        assert maybe_compact(
            large_file,
            max_prompt_chars=1,
            keep_recent_turns=1,
            summarize=summarize_prefix,
        ) is True
        assert summarized_prefix == turn_messages[:2]

        large_entries = load_entries(large_file)
        assert len(large_entries) == len(turn_messages) + 1
        assert large_entries[-1]["type"] == "compaction"
        assert large_entries[-1]["retained_tail"] == turn_messages[2:]
        assert build_prompt_view(large_entries) == [
            {
                "role": "assistant",
                "content": "Conversation summary:\nT1 已完成。",
            },
            *turn_messages[2:],
        ]

        recent_file = Path(temp) / "recent-session.jsonl"
        for message in only_recent:
            persist_message(recent_file, message)
        assert maybe_compact(
            recent_file,
            max_prompt_chars=1,
            keep_recent_turns=1,
            summarize=unexpected_summary,
        ) is False
        assert len(load_entries(recent_file)) == len(only_recent)

        loop_session = Path(temp) / "compacting-loop.jsonl"
        previous_turns = [
            {"role": "user", "content": "较早问题"},
            {"role": "assistant", "content": "较早回答"},
            {"role": "user", "content": "最近问题"},
            {"role": "assistant", "content": "最近回答"},
        ]
        for message in previous_turns:
            persist_message(loop_session, message)

        compaction_calls: list[bool] = []

        def compact_before_request() -> bool:
            compaction_calls.append(True)
            return maybe_compact(
                loop_session,
                max_prompt_chars=1,
                keep_recent_turns=1,
                summarize=lambda _: "较早问题已经回答。",
            )

        compacting_client = FakeClient(
            [fake_response("stop", content="继续完成")]
        )
        compacting_answer = run_agent_loop(
            client=compacting_client,
            model="test-model",
            tools=[],
            user_text="当前问题",
            execute_tool=lambda _: "不应执行",
            session_file=loop_session,
            compact_before_request=compact_before_request,
        )
        assert compacting_answer == "继续完成"
        assert compaction_calls == [True]
        request_messages = compacting_client.completions.requests[0]["messages"]
        assert request_messages == [
            {
                "role": "assistant",
                "content": "Conversation summary:\n较早问题已经回答。",
            },
            *previous_turns[2:],
            {"role": "user", "content": "当前问题"},
        ]
        loop_entries = load_entries(loop_session)
        assert len(loop_entries) == 7
        assert loop_entries[-2]["type"] == "compaction"
        assert loop_entries[-1]["message"] == {
            "role": "assistant",
            "content": "继续完成",
        }

    print("checkpoint 3G passed")


def checkpoint_4_check() -> None:
    with tempfile.TemporaryDirectory() as temp:
        ledger_file = Path(temp) / "session.jsonl"

        append_execution_state(
            ledger_file,
            "exec_1",
            "call_1",
            "approved",
            {"tool_name": "write_file"},
        )
        append_execution_state(
            ledger_file,
            "exec_1",
            "call_1",
            "running",
        )
        append_execution_state(
            ledger_file,
            "exec_1",
            "call_1",
            "unknown",
            {"message": "执行结果无法确认"},
        )
        append_execution_state(
            ledger_file,
            "exec_2",
            "call_2",
            "approved",
        )
        append_execution_state(
            ledger_file,
            "exec_2",
            "call_2",
            "running",
        )
        append_execution_state(
            ledger_file,
            "exec_2",
            "call_2",
            "succeeded",
            {"result": {"bytes_written": 5}},
        )

        entries = load_entries(ledger_file)
        assert len(entries) == 6
        assert all(entry["type"] == "tool_execution" for entry in entries)
        assert entries[0] == {
            "type": "tool_execution",
            "execution_id": "exec_1",
            "tool_call_id": "call_1",
            "status": "approved",
            "tool_name": "write_file",
        }

        states = latest_execution_states(entries)
        assert set(states) == {"exec_1", "exec_2"}
        assert states["exec_1"]["status"] == "unknown"
        assert states["exec_1"]["message"] == "执行结果无法确认"
        assert states["exec_2"]["status"] == "succeeded"
        assert states["exec_2"]["result"] == {"bytes_written": 5}

        before_invalid = ledger_file.read_text(encoding="utf-8")
        try:
            append_execution_state(
                ledger_file,
                "exec_bad",
                "call_bad",
                "finished",
            )
        except ValueError:
            pass
        else:
            raise AssertionError("未知 Ledger 状态必须被拒绝")
        assert ledger_file.read_text(encoding="utf-8") == before_invalid

    print("checkpoint 4A passed")


def checkpoint_4b_check() -> None:
    first = {"path": "demo.txt", "content": "你好"}
    reordered = {"content": "你好", "path": "demo.txt"}
    changed = {"path": "demo.txt", "content": "再见"}

    first_hash = arguments_sha256(first)
    assert len(first_hash) == 64
    assert first_hash == arguments_sha256(reordered)
    assert first_hash != arguments_sha256(changed)

    key = make_idempotency_key("write_file", "call_1")
    assert key == "write_file:call_1"
    assert make_idempotency_key("write_file", "call_1") == key
    assert make_idempotency_key("write_file", "call_2") != key

    for tool_name, tool_call_id in [("", "call_1"), ("write_file", "")]:
        try:
            make_idempotency_key(tool_name, tool_call_id)
        except ValueError:
            pass
        else:
            raise AssertionError("工具名和 tool_call_id 不能为空")

    print("checkpoint 4B passed")


def checkpoint_4c_check() -> None:
    with tempfile.TemporaryDirectory() as temp:
        workspace = Path(temp) / "workspace"
        workspace.mkdir()
        ledger_file = Path(temp) / "session.jsonl"

        denied_call = fake_tool_call(
            "call_denied",
            "write_file",
            {"path": "denied.txt", "content": "no"},
        )
        denied = json.loads(
            execute_workspace_tool_with_ledger(
                workspace,
                ledger_file,
                denied_call,
                lambda *_: False,
            )
        )
        assert denied["status"] == "rejected"
        assert denied["execution_id"].startswith("exec_")
        assert not (workspace / "denied.txt").exists()

        denied_entries = load_entries(ledger_file)
        assert [entry["status"] for entry in denied_entries] == ["rejected"]
        assert denied_entries[0]["execution_id"] == denied["execution_id"]
        assert denied_entries[0]["tool_call_id"] == "call_denied"
        assert denied_entries[0]["idempotency_key"] == (
            "write_file:call_denied"
        )

        write_call = fake_tool_call(
            "call_write",
            "write_file",
            {"path": "result.txt", "content": "hello"},
        )
        first = json.loads(
            execute_workspace_tool_with_ledger(
                workspace,
                ledger_file,
                write_call,
                lambda *_: True,
            )
        )
        assert first["status"] == "succeeded"
        assert first["execution_id"].startswith("exec_")
        assert (workspace / "result.txt").read_text(encoding="utf-8") == "hello"

        second = json.loads(
            execute_workspace_tool_with_ledger(
                workspace,
                ledger_file,
                write_call,
                lambda *_: True,
            )
        )
        assert second["status"] == "succeeded"
        assert second["execution_id"] != first["execution_id"]

        entries = load_entries(ledger_file)
        attempts = {}
        for entry in entries:
            attempts.setdefault(entry["execution_id"], []).append(entry)

        assert [entry["status"] for entry in attempts[first["execution_id"]]] == [
            "approved",
            "running",
            "succeeded",
        ]
        assert [entry["status"] for entry in attempts[second["execution_id"]]] == [
            "approved",
            "running",
            "succeeded",
        ]

        completed = [
            entry
            for entry in entries
            if entry["status"] == "succeeded"
        ]
        assert {entry["tool_call_id"] for entry in completed} == {"call_write"}
        assert {entry["idempotency_key"] for entry in completed} == {
            "write_file:call_write"
        }
        assert len({entry["arguments_sha256"] for entry in completed}) == 1
        assert completed[0]["result"]["execution_id"] == first["execution_id"]

    print("checkpoint 4C passed")


def checkpoint_4d_check() -> None:
    with tempfile.TemporaryDirectory() as temp:
        workspace = Path(temp) / "workspace"
        workspace.mkdir()
        session_file = Path(temp) / "session.jsonl"
        tool_call = fake_tool_call(
            "call_full_turn",
            "write_file",
            {"path": "answer.txt", "content": "done"},
        )
        client = FakeClient(
            [
                fake_response("tool_calls", tool_calls=[tool_call]),
                fake_response("stop", content="文件已经写好"),
            ]
        )

        answer = run_agent_loop(
            client=client,
            model="test-model",
            tools=[],
            user_text="写入 answer.txt",
            execute_tool=lambda call: execute_workspace_tool_with_ledger(
                workspace,
                session_file,
                call,
                lambda *_: True,
            ),
            session_file=session_file,
        )
        assert answer == "文件已经写好"
        assert (workspace / "answer.txt").read_text(encoding="utf-8") == "done"

        entries = load_entries(session_file)
        assert [entry["type"] for entry in entries] == [
            "message",
            "message",
            "tool_execution",
            "tool_execution",
            "tool_execution",
            "message",
            "message",
        ]
        assert [entries[index]["status"] for index in (2, 3, 4)] == [
            "approved",
            "running",
            "succeeded",
        ]

        prompt = build_prompt_view(entries)
        assert [message["role"] for message in prompt] == [
            "user",
            "assistant",
            "tool",
            "assistant",
        ]
        assert prompt[1]["tool_calls"][0]["id"] == "call_full_turn"
        assert prompt[2]["tool_call_id"] == "call_full_turn"
        tool_result = json.loads(prompt[2]["content"])
        assert tool_result["status"] == "succeeded"
        assert tool_result["execution_id"] == entries[4]["execution_id"]

    print("checkpoint 4D passed")


def checkpoint_5a_check() -> None:
    with tempfile.TemporaryDirectory() as temp:
        workspace = Path(temp) / "workspace"
        workspace.mkdir()
        session_file = Path(temp) / "interrupted.jsonl"
        tool_call = fake_tool_call(
            "call_interrupted",
            "write_file",
            {"path": "answer.txt", "content": "done"},
        )
        client = FakeClient(
            [
                fake_response("tool_calls", tool_calls=[tool_call]),
                fake_response("stop", content="不应到达这里"),
            ]
        )

        def simulate_crash(_: dict) -> None:
            raise RuntimeError("模拟副作用后的进程崩溃")

        try:
            run_agent_loop(
                client=client,
                model="test-model",
                tools=[],
                user_text="写入 answer.txt",
                execute_tool=lambda call: execute_workspace_tool_with_ledger(
                    workspace,
                    session_file,
                    call,
                    lambda *_: True,
                    after_effect=simulate_crash,
                ),
                session_file=session_file,
            )
        except RuntimeError as error:
            assert "模拟副作用后的进程崩溃" in str(error)
        else:
            raise AssertionError("故障注入回调必须被执行")

        assert (workspace / "answer.txt").read_text(encoding="utf-8") == "done"
        entries = load_entries(session_file)
        assert [entry["type"] for entry in entries] == [
            "message",
            "message",
            "tool_execution",
            "tool_execution",
        ]
        assert [entries[index]["status"] for index in (2, 3)] == [
            "approved",
            "running",
        ]
        assert latest_execution_states(entries)[entries[3]["execution_id"]][
            "status"
        ] == "running"
        assert [message["role"] for message in build_prompt_view(entries)] == [
            "user",
            "assistant",
        ]

    print("checkpoint 5A passed")


def checkpoint_5b_check() -> None:
    with tempfile.TemporaryDirectory() as temp:
        session_file = Path(temp) / "recovery.jsonl"
        shared = {
            "tool_name": "write_file",
            "idempotency_key": "write_file:call_running",
            "arguments_sha256": "hash_running",
        }
        append_execution_state(
            session_file,
            "exec_running",
            "call_running",
            "approved",
            shared,
        )
        append_execution_state(
            session_file,
            "exec_running",
            "call_running",
            "running",
            shared,
        )
        append_execution_state(
            session_file,
            "exec_done",
            "call_done",
            "running",
        )
        append_execution_state(
            session_file,
            "exec_done",
            "call_done",
            "succeeded",
        )
        append_execution_state(
            session_file,
            "exec_rejected",
            "call_rejected",
            "rejected",
        )

        before = load_entries(session_file)
        assert mark_interrupted_executions_unknown(session_file) == [
            "exec_running"
        ]
        after = load_entries(session_file)
        assert len(after) == len(before) + 1
        assert after[-1] == {
            "type": "tool_execution",
            "execution_id": "exec_running",
            "tool_call_id": "call_running",
            "status": "unknown",
            **shared,
            "message": "进程在 running 状态中断，副作用无法确认",
        }
        assert latest_execution_states(after)["exec_running"]["status"] == (
            "unknown"
        )
        assert latest_execution_states(after)["exec_done"]["status"] == (
            "succeeded"
        )

        assert mark_interrupted_executions_unknown(session_file) == []
        assert load_entries(session_file) == after

    print("checkpoint 5B passed")


def checkpoint_5c_check() -> None:
    with tempfile.TemporaryDirectory() as temp:
        session_file = Path(temp) / "orphaned-calls.jsonl"
        unknown_call = fake_tool_call(
            "call_unknown",
            "write_file",
            {"path": "unknown.txt", "content": "maybe"},
        )
        succeeded_call = fake_tool_call(
            "call_succeeded",
            "write_file",
            {"path": "done.txt", "content": "done"},
        )
        persisted_calls = assistant_message_from_api(
            SimpleNamespace(
                content="",
                tool_calls=[unknown_call, succeeded_call],
            )
        )
        persist_message(
            session_file,
            {"role": "user", "content": "写入两个文件"},
        )
        persist_message(session_file, persisted_calls)

        unknown_arguments = {"path": "unknown.txt", "content": "maybe"}
        unknown_details = {
            "tool_name": "write_file",
            "idempotency_key": "write_file:call_unknown",
            "arguments_sha256": arguments_sha256(unknown_arguments),
        }
        append_execution_state(
            session_file,
            "exec_unknown",
            "call_unknown",
            "approved",
            unknown_details,
        )
        append_execution_state(
            session_file,
            "exec_unknown",
            "call_unknown",
            "running",
            unknown_details,
        )

        succeeded_result = {
            "status": "succeeded",
            "execution_id": "exec_succeeded",
            "path": "done.txt",
            "bytes_written": 4,
        }
        append_execution_state(
            session_file,
            "exec_succeeded",
            "call_succeeded",
            "succeeded",
            {
                "tool_name": "write_file",
                "idempotency_key": "write_file:call_succeeded",
                "arguments_sha256": arguments_sha256(
                    {"path": "done.txt", "content": "done"}
                ),
                "result": succeeded_result,
            },
        )

        assert [call["id"] for call in pending_tool_calls(load_entries(session_file))] == [
            "call_unknown",
            "call_succeeded",
        ]
        assert repair_missing_tool_results(session_file) == [
            "call_unknown",
            "call_succeeded",
        ]

        entries = load_entries(session_file)
        states = latest_execution_by_tool_call(entries)
        assert states["call_unknown"]["status"] == "unknown"
        prompt = build_prompt_view(entries)
        assert [message["role"] for message in prompt] == [
            "user",
            "assistant",
            "tool",
            "tool",
        ]
        assert [message["tool_call_id"] for message in prompt[-2:]] == [
            "call_unknown",
            "call_succeeded",
        ]

        unknown_result = json.loads(prompt[-2]["content"])
        assert unknown_result == {
            "status": "unknown",
            "execution_id": "exec_unknown",
            "message": "进程在 running 状态中断，副作用无法确认",
        }
        assert json.loads(prompt[-1]["content"]) == succeeded_result

        before_second_repair = load_entries(session_file)
        assert repair_missing_tool_results(session_file) == []
        assert load_entries(session_file) == before_second_repair

    print("checkpoint 5C passed")


def checkpoint_5d_check() -> None:
    with tempfile.TemporaryDirectory() as temp:
        session_file = Path(temp) / "resume-turn.jsonl"
        tool_call = fake_tool_call(
            "call_resume",
            "write_file",
            {"path": "answer.txt", "content": "maybe"},
        )
        persist_message(
            session_file,
            {"role": "user", "content": "写入 answer.txt"},
        )
        persist_message(
            session_file,
            assistant_message_from_api(
                SimpleNamespace(content="", tool_calls=[tool_call])
            ),
        )
        append_execution_state(
            session_file,
            "exec_resume",
            "call_resume",
            "unknown",
            {
                "tool_name": "write_file",
                "idempotency_key": "write_file:call_resume",
                "arguments_sha256": arguments_sha256(
                    {"path": "answer.txt", "content": "maybe"}
                ),
                "message": "副作用无法确认",
            },
        )
        assert repair_missing_tool_results(session_file) == ["call_resume"]

        client = FakeClient(
            [fake_response("stop", content="写入状态不确定，请先检查文件")]
        )
        answer = run_agent_loop(
            client=client,
            model="test-model",
            tools=[],
            user_text=None,
            execute_tool=lambda _: "不应执行",
            session_file=session_file,
        )
        assert answer == "写入状态不确定，请先检查文件"
        assert [
            message["role"]
            for message in client.completions.requests[0]["messages"]
        ] == ["user", "assistant", "tool"]

        prompt = build_prompt_view(load_entries(session_file))
        assert [message["role"] for message in prompt] == [
            "user",
            "assistant",
            "tool",
            "assistant",
        ]
        assert prompt[-1]["content"] == "写入状态不确定，请先检查文件"

        try:
            run_agent_loop(
                client=FakeClient([]),
                model="test-model",
                tools=[],
                user_text=None,
                execute_tool=lambda _: "不应执行",
                session_file=None,
            )
        except ValueError:
            pass
        else:
            raise AssertionError("恢复旧 Turn 时必须提供 session_file")

        empty_session = Path(temp) / "empty.jsonl"
        try:
            run_agent_loop(
                client=FakeClient([]),
                model="test-model",
                tools=[],
                user_text=None,
                execute_tool=lambda _: "不应执行",
                session_file=empty_session,
            )
        except ValueError:
            pass
        else:
            raise AssertionError("空 Session 没有可以继续的旧 Turn")

        completed_session = Path(temp) / "completed.jsonl"
        persist_message(
            completed_session,
            {"role": "user", "content": "已经完成的问题"},
        )
        persist_message(
            completed_session,
            {"role": "assistant", "content": "已经完成的 Final"},
        )
        try:
            run_agent_loop(
                client=FakeClient([]),
                model="test-model",
                tools=[],
                user_text=None,
                execute_tool=lambda _: "不应执行",
                session_file=completed_session,
            )
        except ValueError:
            pass
        else:
            raise AssertionError("已完成的 Turn 不能进入恢复模式")

    print("checkpoint 5D passed")


def checkpoint_5e_check() -> None:
    with tempfile.TemporaryDirectory() as temp:
        workspace = Path(temp) / "workspace"
        workspace.mkdir()

        matched_session = Path(temp) / "matched.jsonl"
        matched_arguments = {"path": "answer.txt", "content": "done"}
        matched_call = fake_tool_call(
            "call_matched",
            "write_file",
            matched_arguments,
        )
        persist_message(
            matched_session,
            {"role": "user", "content": "写入 answer.txt"},
        )
        persist_message(
            matched_session,
            assistant_message_from_api(
                SimpleNamespace(content="", tool_calls=[matched_call])
            ),
        )
        matched_details = {
            "tool_name": "write_file",
            "idempotency_key": "write_file:call_matched",
            "arguments_sha256": arguments_sha256(matched_arguments),
            "message": "副作用无法确认",
        }
        append_execution_state(
            matched_session,
            "exec_matched",
            "call_matched",
            "unknown",
            matched_details,
        )
        (workspace / "answer.txt").write_text("done", encoding="utf-8")

        assert reconcile_unknown_write_files(workspace, matched_session) == [
            "call_matched"
        ]
        matched_entries = load_entries(matched_session)
        matched_state = latest_execution_by_tool_call(matched_entries)[
            "call_matched"
        ]
        assert matched_state["status"] == "succeeded"
        assert matched_state["execution_id"] == "exec_matched"
        assert matched_state["idempotency_key"] == (
            "write_file:call_matched"
        )
        assert matched_state["result"] == {
            "status": "succeeded",
            "execution_id": "exec_matched",
            "path": "answer.txt",
            "bytes_written": 4,
            "reconciled": True,
        }
        assert reconcile_unknown_write_files(workspace, matched_session) == []
        assert repair_missing_tool_results(matched_session) == ["call_matched"]
        matched_result = json.loads(
            build_prompt_view(load_entries(matched_session))[-1]["content"]
        )
        assert matched_result["reconciled"] is True

        changed_session = Path(temp) / "changed.jsonl"
        changed_arguments = {"path": "changed.txt", "content": "expected"}
        changed_call = fake_tool_call(
            "call_changed",
            "write_file",
            changed_arguments,
        )
        persist_message(
            changed_session,
            assistant_message_from_api(
                SimpleNamespace(content="", tool_calls=[changed_call])
            ),
        )
        append_execution_state(
            changed_session,
            "exec_changed",
            "call_changed",
            "unknown",
            {
                "tool_name": "write_file",
                "idempotency_key": "write_file:call_changed",
                "arguments_sha256": arguments_sha256(changed_arguments),
                "message": "副作用无法确认",
            },
        )
        (workspace / "changed.txt").write_text("someone else", encoding="utf-8")
        changed_before = load_entries(changed_session)
        assert reconcile_unknown_write_files(workspace, changed_session) == []
        assert load_entries(changed_session) == changed_before

        bash_session = Path(temp) / "bash.jsonl"
        bash_arguments = {"command": "echo charged"}
        bash_call = fake_tool_call("call_bash_unknown", "run_bash", bash_arguments)
        persist_message(
            bash_session,
            assistant_message_from_api(
                SimpleNamespace(content="", tool_calls=[bash_call])
            ),
        )
        append_execution_state(
            bash_session,
            "exec_bash_unknown",
            "call_bash_unknown",
            "unknown",
            {
                "tool_name": "run_bash",
                "idempotency_key": "run_bash:call_bash_unknown",
                "arguments_sha256": arguments_sha256(bash_arguments),
                "message": "副作用无法确认",
            },
        )
        bash_before = load_entries(bash_session)
        assert reconcile_unknown_write_files(workspace, bash_session) == []
        assert load_entries(bash_session) == bash_before

    print("checkpoint 5E passed")


def main() -> None:
    if "--checkpoint-5" in sys.argv:
        checkpoint_3_check()
        checkpoint_4_check()
        checkpoint_4b_check()
        checkpoint_4c_check()
        checkpoint_4d_check()
        checkpoint_5a_check()
        checkpoint_5b_check()
        checkpoint_5c_check()
        checkpoint_5d_check()
        checkpoint_5e_check()
        return
    if "--checkpoint-4" in sys.argv:
        checkpoint_3_check()
        checkpoint_4_check()
        checkpoint_4b_check()
        checkpoint_4c_check()
        checkpoint_4d_check()
        return
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
