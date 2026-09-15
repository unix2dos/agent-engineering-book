"""跨进程验证写入后丢失回执的恢复；复用 Workspace Agent，不调用模型。"""

import json
import os
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile


SCRIPT = Path(__file__).resolve()
core_path = SCRIPT.parents[1] / "workspace-agent/agent.py"
CORE = runpy.run_path(str(core_path))
EXPECTED = '{"theme":"dark","port":3000}'
CHANGED = '{"theme":"dark","port":8081}'
CALL_ID = "change_theme"


def crash_after_write(workspace):
    session = workspace / "session.jsonl"
    call = CORE["fake_tool_call"](
        CALL_ID, "write_file", {"path": "config.json", "content": EXPECTED}
    )
    response = CORE["fake_response"]("tool_calls", tool_calls=[call])
    CORE["persist_message"](
        session, CORE["assistant_message_from_api"](response.choices[0].message)
    )

    def interrupt(result):
        assert result["status"] == "succeeded"
        os._exit(23)

    CORE["execute_workspace_tool_with_ledger"](
        workspace, session, call, lambda *_: True, interrupt
    )
    raise AssertionError("故障注入未发生")


def recover(workspace):
    session = workspace / "session.jsonl"
    target = workspace / "config.json"
    before = target.read_bytes(), target.stat().st_ino, target.stat().st_mtime_ns
    CORE["mark_interrupted_executions_unknown"](session)
    reconciled = CORE["reconcile_unknown_write_files"](workspace, session)
    CORE["repair_missing_tool_results"](session)
    assert (target.read_bytes(), target.stat().st_ino, target.stat().st_mtime_ns) == before
    entries = CORE["load_entries"](session)
    state = CORE["latest_execution_by_tool_call"](entries)[CALL_ID]
    assert len(CORE["latest_execution_states"](entries)) == 1
    assert not CORE["pending_tool_calls"](entries)
    print(json.dumps({"status": state["status"], "reconciled": bool(reconciled)}))


def run_demo():
    # ponytail: 串行且确认旧进程已退出；并发接管需额外的执行资格与协调机制。
    with tempfile.TemporaryDirectory(prefix="agent-progress-") as folder:
        for changed in (False, True):
            workspace = Path(folder) / ("changed" if changed else "matched")
            workspace.mkdir()
            target = workspace / "config.json"
            target.write_text('{"theme":"light","port":3000}', encoding="utf-8")
            command = [sys.executable, "-B", str(SCRIPT)]
            crashed = subprocess.run(command + ["--crash", str(workspace)], timeout=10)
            assert crashed.returncode == 23
            assert target.read_text(encoding="utf-8") == EXPECTED
            session = workspace / "session.jsonl"
            state = CORE["latest_execution_by_tool_call"](CORE["load_entries"](session))
            assert state[CALL_ID]["status"] == "running"
            if changed:
                target.write_text(CHANGED, encoding="utf-8")
            resumed = subprocess.run(
                command + ["--recover", str(workspace)],
                capture_output=True, text=True, check=True, timeout=10,
            )
            expected_status = "unknown" if changed else "succeeded"
            assert json.loads(resumed.stdout) == {
                "status": expected_status, "reconciled": not changed,
            }
            assert target.read_text(encoding="utf-8") == (CHANGED if changed else EXPECTED)
            entries = CORE["load_entries"](session)
            receipts = [entry["message"] for entry in entries if entry.get("type") == "message"
                        and entry["message"].get("role") == "tool"]
            assert len(receipts) == 1 and receipts[0]["tool_call_id"] == CALL_ID
            before_repeat = {
                path: (path.read_bytes(), path.stat().st_ino, path.stat().st_mtime_ns)
                for path in (target, session)
            }
            repeated = subprocess.run(
                command + ["--recover", str(workspace)],
                capture_output=True, text=True, check=True, timeout=10,
            )
            assert json.loads(repeated.stdout) == {
                "status": expected_status, "reconciled": False,
            }
            for path, original in before_repeat.items():
                assert (path.read_bytes(), path.stat().st_ino, path.stat().st_mtime_ns) == original
            label = "文件被人修改" if changed else "文件符合原请求"
            print(f"{label}：进程退出码 23；running -> unknown -> {expected_status}；恢复未改写文件")
            print(f"再次启动恢复进程：{expected_status}；文件和账本均未变化，未重复补回执。")
    print("PASS：两个场景各启动两次独立恢复进程；未调用模型、未验证断电或容器丢失。")


if __name__ == "__main__":
    if len(sys.argv) == 1:
        run_demo()
    elif len(sys.argv) == 3 and sys.argv[1] in {"--crash", "--recover"}:
        workspace = Path(sys.argv[2]).resolve(strict=True)
        if not workspace.is_dir():
            raise ValueError("实验工作区必须是目录")
        (crash_after_write if sys.argv[1] == "--crash" else recover)(workspace)
    else:
        raise SystemExit("运行方式：python -B practice/lesson-06/recovery_process_demo.py")
