"""验证第 3 课正式正文中的代码；复用现有工具和模型替身，不调用云端模型。"""

import ast
from contextlib import redirect_stdout
from copy import deepcopy
import io
import json
from pathlib import Path
import re
import shutil
import tempfile
from types import SimpleNamespace

import demo


def recording_client():
    requests = []

    def create(**request):
        requests.append(deepcopy(request))
        return demo.scripted_model(**request)

    client = SimpleNamespace(chat=SimpleNamespace(
        completions=SimpleNamespace(create=create)))
    return client, requests


def self_check():
    chapter = demo.HERE.parents[1] / "chapters/03-工具调用循环.md"
    blocks = re.findall(r"```python\n(.*?)\n```", chapter.read_text(encoding="utf-8"), re.S)
    definitions = []
    namespace = {
        "read_file": demo.CORE["read_file"],
        "assistant_message_from_api": demo.CORE["assistant_message_from_api"],
    }
    for block in blocks:
        tree = ast.parse(block)
        definitions.extend(node.name for node in tree.body if isinstance(node, ast.FunctionDef))
        # 只执行本仓库正式正文的代码块；不是执行模型给出的字符串。
        exec(compile(tree, str(chapter), "exec"), namespace)
    assert definitions == ["execute_read", "run_loop"], definitions
    run_loop = namespace["run_loop"]
    execute_read = namespace["execute_read"]
    with tempfile.TemporaryDirectory(prefix="agent-lesson03-check-") as temporary:
        workspace = Path(temporary)
        shutil.copyfile(demo.HERE / "order_service.py", workspace / "order_service.py")
        for order_id, status, lengths in [("order_404", 500, [1, 3, 5]), ("order_001", 200, [1, 3])]:
            assert demo.reproduce(workspace, order_id)["status"] == status
            snapshots = {path.name: path.read_bytes() for path in workspace.iterdir()}
            question = f"排查 {order_id}"
            client, requests = recording_client()
            answer = run_loop(client, "scripted", demo.TOOLS, workspace, question)
            reference_client, reference_requests = recording_client()
            expected = demo.CORE["run_agent_loop"](
                reference_client, "scripted", demo.TOOLS, question,
                lambda call: demo.execute_read(workspace, call),
            )
            assert answer == expected and requests == reference_requests
            assert [len(request["messages"]) for request in requests] == lengths
            messages = requests[-1]["messages"]
            call_ids = [call["id"] for message in messages for call in message.get("tool_calls", [])]
            result_ids = [message["tool_call_id"] for message in messages if message["role"] == "tool"]
            assert call_ids == result_ids
            assert snapshots == {path.name: path.read_bytes() for path in workspace.iterdir()}

        calls = [demo.CORE["fake_tool_call"](f"read_{number}", "read_file", {"path": path})
                 for number, path in enumerate(["server.log", "order_service.py"], 1)]
        extra = demo.CORE["fake_tool_call"]("bad_args", "read_file", {"path": "server.log", "command": "ignored"})
        denied = demo.CORE["fake_tool_call"]("denied", "write_file", {"path": "server.log", "content": "bad"})
        fake_response = demo.CORE["fake_response"]
        client = demo.CORE["FakeClient"]([
            fake_response("tool_calls", tool_calls=calls + [extra, denied]),
            fake_response("stop", content="batch checked"),
        ])
        assert run_loop(client, "scripted", demo.TOOLS, workspace, "batch") == "batch checked"
        messages = client.completions.requests[1]["messages"]
        assert [message["role"] for message in messages] == ["user", "assistant"] + ["tool"] * 4
        assert [message["tool_call_id"] for message in messages[2:]] == ["read_1", "read_2", "bad_args", "denied"]
        assert json.loads(messages[-2]["content"]) == {"error": "参数必须只包含 path"}
        assert "error" in json.loads(messages[-1]["content"])
        assert snapshots == {path.name: path.read_bytes() for path in workspace.iterdir()}

        executions = []

        def execute_spy(folder, call):
            executions.append(call.id)
            return execute_read(folder, call)

        namespace["execute_read"] = execute_spy
        for response in [fake_response("length", tool_calls=calls), fake_response("length")]:
            client = demo.CORE["FakeClient"]([response])
            try:
                run_loop(client, "scripted", demo.TOOLS, workspace, "truncated")
            except RuntimeError:
                pass
            else:
                raise AssertionError("截断响应必须停止")
            assert not executions, "不能先执行工具再判断截断"

        client = demo.CORE["FakeClient"]([
            fake_response("tool_calls", tool_calls=[calls[0]]),
            fake_response("tool_calls", tool_calls=[calls[1]]),
        ])
        try:
            run_loop(client, "scripted", demo.TOOLS, workspace, "budget", max_requests=2)
        except RuntimeError as error:
            assert str(error) == "超过模型请求次数上限"
        else:
            raise AssertionError("请求次数上限必须生效")
        assert len(client.completions.requests) == 2 and len(executions) == 2
    print("lesson 03 passed: real HTTP 500/200, reference parity, message IDs, batch errors, truncation, budget")


if __name__ == "__main__":
    # 已有读取工具会打印进度；这里只输出验证结果。
    with redirect_stdout(io.StringIO()) as output:
        self_check()
    print(output.getvalue().splitlines()[-1])
