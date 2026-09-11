"""验证第 6 课正式正文；仅操作临时文件和内存 SQLite，不调用真实模型。"""

import ast
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import re
import runpy
import sqlite3
import tempfile
from unittest.mock import patch

import demo


def self_check():
    chapter = demo.HERE.parents[1] / "chapters/06-工具可靠性.md"
    blocks = re.findall(r"```python\n(.*?)\n```", chapter.read_text(encoding="utf-8"), re.S)
    expected = [
        "{'path': 'diagnosis.txt', 'bytes_written': 4}\n{'status': 'unknown'}\n",
        "1\n0\n",
        "更新失败，事务已回滚\n0\n0\n",
    ]
    assert len(blocks) == len(expected)
    namespace = {}
    for block, output in zip(blocks, expected):
        with redirect_stdout(io.StringIO()) as captured:
            # 只执行本仓库教学代码，不执行模型输出的字符串。
            exec(compile(ast.parse(block), str(chapter), "exec"), namespace)
        assert captured.getvalue() == output, captured.getvalue()
    replay = namespace["replay_result"]
    assert replay({"status": "rejected"}) == {"status": "rejected"}
    assert replay({"status": "failed", "result": {"error": "denied"}}) == {"error": "denied"}
    for state, expected_error in [
        ({"status": "succeeded"}, "终态存在，但结果缺失"),
        ({"status": "failed"}, "终态存在，但结果缺失"),
        ({"status": "running"}, "这个状态还不能生成回执"),
    ]:
        try:
            replay(state)
        except RuntimeError as error:
            assert str(error) == expected_error
        else:
            raise AssertionError("不能把不可重放状态当成结果")

    core = demo.CORE
    arguments = {"path": "diagnosis.txt", "content": "done"}
    assert core["arguments_sha256"](arguments) == core["arguments_sha256"]({"content": "done", "path": "diagnosis.txt"})

    def interrupt_after_effect(result):
        assert result["status"] == "succeeded"
        raise RuntimeError("模拟副作用后中断")

    def forbid_execution(*args, **kwargs):
        raise AssertionError("恢复时不得重新执行写入工具")

    with tempfile.TemporaryDirectory(prefix="agent-lesson06-check-") as temporary:
        for case in ["saved", "same", "changed", "rejected", "conflict"]:
            case_dir = Path(temporary) / case
            workspace = case_dir / "workspace"
            workspace.mkdir(parents=True)
            session_file = case_dir / "session.jsonl"
            target = workspace / "diagnosis.txt"
            call = core["fake_tool_call"]("call_report", "write_file", arguments)
            core["persist_message"](session_file, {"role": "user", "content": "保存诊断报告"})
            core["persist_message"](session_file, core["assistant_message_from_api"](
                core["fake_response"]("tool_calls", tool_calls=[call]).choices[0].message))
            try:
                core["execute_workspace_tool_with_ledger"](
                    workspace, session_file, call,
                    approve=lambda name, args: case != "rejected",
                    after_effect=interrupt_after_effect if case in {"same", "changed"} else None,
                )
            except RuntimeError as error:
                assert case in {"same", "changed"} and str(error) == "模拟副作用后中断"
            else:
                assert case not in {"same", "changed"}
            state = core["latest_execution_by_tool_call"](core["load_entries"](session_file))[call.id]
            execution_id = state["execution_id"]
            if case == "rejected":
                assert state["status"] == "rejected" and not target.exists()
            else:
                assert target.read_bytes() == b"done"
            if case in {"same", "changed"}:
                assert state["status"] == "running" and "result" not in state
            if case == "changed":
                target.write_text("user updated report", encoding="utf-8")
            if case == "conflict":
                details = {key: state[key] for key in ("tool_name", "idempotency_key", "result")}
                details["arguments_sha256"] = "mismatched"
                core["append_execution_state"](session_file, execution_id, call.id, "succeeded", details)

            before = target.read_bytes() if target.exists() else None
            identity = (target.stat().st_ino, target.stat().st_mtime_ns) if target.exists() else None
            with patch.dict(core["repair_missing_tool_results"].__globals__, {"write_file": forbid_execution}):
                marked = core["mark_interrupted_executions_unknown"](session_file)
                assert marked == ([execution_id] if case in {"same", "changed"} else [])
                reconciled = core["reconcile_unknown_write_files"](workspace, session_file)
                assert reconciled == ([call.id] if case == "same" else [])
                if case == "conflict":
                    try:
                        core["repair_missing_tool_results"](session_file)
                    except RuntimeError as error:
                        assert "参数与 Ledger 不一致" in str(error)
                    else:
                        raise AssertionError("参数冲突应停止恢复")
                    assert len(core["pending_tool_calls"](core["load_entries"](session_file))) == 1
                else:
                    assert core["repair_missing_tool_results"](session_file) == [call.id]
                    assert core["repair_missing_tool_results"](session_file) == []
                    entries = core["load_entries"](session_file)
                    assert len(core["latest_execution_states"](entries)) == 1
                    view = core["build_prompt_view"](entries)
                    assert [message["role"] for message in view] == ["user", "assistant", "tool"]
                    assert view[-1]["tool_call_id"] == call.id
                    result = json.loads(view[-1]["content"])
                    assert result["execution_id"] == execution_id
                    expected_status = {"saved": "succeeded", "same": "succeeded", "changed": "unknown", "rejected": "rejected"}[case]
                    assert result["status"] == expected_status
                    if case == "same":
                        assert result["reconciled"] is True
                        statuses = [entry["status"] for entry in entries if entry.get("type") == "tool_execution"]
                        assert statuses == ["approved", "running", "unknown", "succeeded"]
                    client = core["FakeClient"]([core["fake_response"]("stop", content="已读取恢复结果")])
                    assert core["run_agent_loop"](client, "scripted", [], None, forbid_execution, session_file=session_file) == "已读取恢复结果"
                    assert client.completions.requests[0]["messages"] == view
            assert (target.read_bytes() if target.exists() else None) == before
            assert ((target.stat().st_ino, target.stat().st_mtime_ns) if target.exists() else None) == identity

    storage = runpy.run_path(str(demo.HERE.parents[1] / "exercises/session-storage-sqlite/starter.py"))
    db = sqlite3.connect(":memory:")
    try:
        storage["create_schema"](db)
        for execution_id, status in [("exec_1", "running"), ("exec_1", "unknown"), ("exec_2", "unknown"), ("exec_2", "succeeded")]:
            storage["record_execution_state"](db, execution_id, status)
        assert storage["list_unknown_executions"](db) == ["exec_1"]
        key = core["make_idempotency_key"]("write_file", "call_report")
        fingerprint = core["arguments_sha256"](arguments)
        assert storage["claim_operation"](db, key, fingerprint) is True
        assert storage["claim_operation"](db, key, fingerprint) is False
        try:
            storage["claim_operation"](db, key, "different")
        except ValueError as error:
            assert "不能用于不同参数" in str(error)
        else:
            raise AssertionError("同一幂等键参数改变必须报错")
    finally:
        db.close()
    print("lesson 06 passed: replay, interrupted effects, reconciliation, conflict rejection, unique claims, rollback")


if __name__ == "__main__":
    self_check()
