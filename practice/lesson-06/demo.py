"""在文件写入之后中断，核对已有结果再恢复；不调用模型。"""

from pathlib import Path
import runpy
import tempfile

CORE = runpy.run_path(str(Path(__file__).resolve().parents[1] / "workspace-agent/agent.py"))


def run_demo():
    with tempfile.TemporaryDirectory(prefix="agent-reliability-") as folder:
        workspace = Path(folder)
        session = workspace / "session.jsonl"
        call = CORE["fake_tool_call"]("write_report", "write_file", {"path": "diagnosis.txt", "content": "done"})
        CORE["persist_message"](session, CORE["assistant_message_from_api"](
            CORE["fake_response"]("tool_calls", tool_calls=[call]).choices[0].message))

        def interrupt(result):
            assert result["status"] == "succeeded"
            raise RuntimeError("模拟写入后、回执前中断")

        try:
            CORE["execute_workspace_tool_with_ledger"](workspace, session, call, lambda *_: True, interrupt)
        except RuntimeError as error:
            assert str(error) == "模拟写入后、回执前中断"
        else:
            raise AssertionError("故障注入必须发生")
        target = workspace / "diagnosis.txt"
        assert target.read_text() == "done"
        original = target.read_bytes(), target.stat().st_ino, target.stat().st_mtime_ns
        state = CORE["latest_execution_by_tool_call"](CORE["load_entries"](session))[call.id]
        assert state["status"] == "running"
        print("文件已经写入，账本仍为：", state["status"])
        CORE["mark_interrupted_executions_unknown"](session)
        print("恢复时先标记：unknown")
        assert CORE["reconcile_unknown_write_files"](workspace, session) == [call.id]
        assert CORE["repair_missing_tool_results"](session) == [call.id]
        assert CORE["reconcile_unknown_write_files"](workspace, session) == []
        assert CORE["repair_missing_tool_results"](session) == []
        assert (target.read_bytes(), target.stat().st_ino, target.stat().st_mtime_ns) == original
        print("核对文件后补回执：succeeded；重复核对没有重写文件。")
    print("该证据只适用于可核对的文件覆盖写入；不能据此重试任意外部副作用。")


if __name__ == "__main__":
    run_demo()
