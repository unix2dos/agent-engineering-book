"""验收代码已提供。--wiring 只查接线；默认检查你实现的 list_files。"""

import argparse
import json
from pathlib import Path
import tempfile
from unittest.mock import patch

import starter

CORE = starter.reading_demo.CORE


def make_workspace(root):
    workspace = root / "workspace"
    workspace.mkdir()
    (workspace / "server.log").write_text("示例日志：订单查询失败", encoding="utf-8")
    (workspace / "order_service.py").write_text("# 教学源码占位\n", encoding="utf-8")
    (workspace / "logs").mkdir()
    (workspace / "logs/worker.log").write_text("示例工作日志", encoding="utf-8")
    (workspace / "empty").mkdir()
    outside = root / "outside"
    outside.mkdir()
    (outside / "private.txt").write_text("仅为临时测试文字", encoding="utf-8")
    (workspace / "escape").symlink_to(outside, target_is_directory=True)
    (workspace / "shortcut.log").symlink_to(workspace / "server.log")
    (workspace / "broken.log").symlink_to(outside / "missing.txt")
    return workspace


def check_listing(workspace):
    with patch.object(Path, "open", side_effect=AssertionError("列文件名不需要读取文件内容")):
        assert starter.list_files(workspace) == {
            "path": ".", "files": ["order_service.py", "server.log"],
        }, "只列本层普通文件，排好序，不包含子目录或软链接"
        assert starter.list_files(workspace, "logs") == {"path": "logs", "files": ["worker.log"]}
        assert starter.list_files(workspace, "empty") == {"path": "empty", "files": []}
        for path in ("../outside", str(workspace), "escape", "server.log", "missing", "", None, []):
            try:
                starter.list_files(workspace, path)
            except ValueError:
                pass
            else:
                raise AssertionError(f"应该拒绝这个目录参数：{path!r}")
    print("目录检查通过：排序、子目录、空目录、软链接与越界拒绝")


def check_loop(workspace):
    client = CORE["FakeClient"]([
        CORE["fake_response"]("tool_calls", tool_calls=[
            CORE["fake_tool_call"]("list_1", "list_files", {"path": "."}),
        ]),
        CORE["fake_response"]("tool_calls", tool_calls=[
            CORE["fake_tool_call"]("read_1", "read_file", {"path": "server.log"}),
        ]),
        CORE["fake_response"]("stop", content="已取得目录清单和日志（预设回复）"),
    ])
    answer = CORE["run_agent_loop"](
        client, "scripted", starter.TOOLS, "先看看有哪些文件，再读取 server.log。",
        lambda call: starter.execute_tool(workspace, call),
    )
    assert len(client.completions.requests) == 3
    listing = client.completions.requests[1]["messages"][-1]
    assert listing["role"] == "tool" and listing["tool_call_id"] == "list_1"
    assert json.loads(listing["content"]) == {"path": ".", "files": ["order_service.py", "server.log"]}
    reading = client.completions.requests[2]["messages"][-1]
    assert reading["tool_call_id"] == "read_1"
    assert json.loads(reading["content"])["content"] == "示例日志：订单查询失败"
    assert "预设回复" in answer

    for name, args in (
        ("write_file", {"path": "server.log", "content": "changed"}),
        ("read_file", {"path": "logs/worker.log"}),
        ("list_files", {"path": ".", "recursive": True}),
        ("list_files", {"path": []}),
        ("list_files", []),
    ):
        call = CORE["fake_tool_call"]("rejected", name, args)
        assert "error" in json.loads(starter.execute_tool(workspace, call))
    call = CORE["fake_tool_call"]("bad_json", "list_files", {})
    call.function.arguments = "{"
    assert "error" in json.loads(starter.execute_tool(workspace, call))
    print("接线检查通过：list_files -> read_file -> Final；调用编号配对，读取权限没有扩大")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wiring", action="store_true")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="agent-list-files-") as folder:
        workspace = make_workspace(Path(folder))
        paths = [workspace / "server.log", workspace / "order_service.py", workspace / "logs/worker.log", workspace.parent / "outside/private.txt"]
        before = {path: path.read_bytes() for path in paths}
        if args.wiring:
            # 仅验证接线；固定目录结果不包含 list_files 的参考实现。
            with patch.object(starter, "list_files", return_value={"path": ".", "files": ["order_service.py", "server.log"]}) as listing:
                check_loop(workspace)
                assert listing.call_count == 1, "不合法请求不得进入目录函数"
        else:
            check_listing(workspace)
            check_loop(workspace)
        assert {path: path.read_bytes() for path in paths} == before, "不得修改任何输入文件"
        print("wiring passed（目录函数由测试替身代替，不代表作业通过）" if args.wiring else "作业通过：受限目录查看已接入现有工具循环")


if __name__ == "__main__":
    try:
        main()
    except NotImplementedError as error:
        raise SystemExit(f"待完成：{error}")
