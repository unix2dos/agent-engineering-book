"""默认完整验收；--demo 展示模型申请与工具回执；--wiring 只查真实工具接线。"""

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
    (workspace / "pages").mkdir()
    for name in ["e.log", "c.log", "a.log", "d.log", "b.log"]:
        (workspace / "pages" / name).write_text("分页测试文字", encoding="utf-8")
    (workspace / "many").mkdir()
    for number in range(101):
        (workspace / "many" / f"file_{number:03}.log").touch()
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
            "path": ".", "files": ["order_service.py", "server.log"], "next_offset": None,
        }, "只列本层普通文件，排好序，不包含子目录或软链接"
        assert starter.list_files(workspace, "logs") == {"path": "logs", "files": ["worker.log"], "next_offset": None}
        assert starter.list_files(workspace, "empty") == {"path": "empty", "files": [], "next_offset": None}
        for offset, names, next_offset in [
            (0, ["a.log", "b.log"], 2), (2, ["c.log", "d.log"], 4),
            (4, ["e.log"], None), (5, [], None), (8, [], None),
        ]:
            assert starter.list_files(workspace, "pages", offset, 2) == {
                "path": "pages", "files": names, "next_offset": next_offset,
            }
        assert starter.list_files(workspace, "pages", 0, 5)["next_offset"] is None
        default_page = starter.list_files(workspace, "many")
        assert len(default_page["files"]) == 20 and default_page["next_offset"] == 20
        largest_page = starter.list_files(workspace, "many", limit=100)
        assert len(largest_page["files"]) == 100 and largest_page["next_offset"] == 100
        assert starter.list_files(workspace, "many", 100, 100) == {
            "path": "many", "files": ["file_100.log"], "next_offset": None,
        }
        for path in ("../outside", str(workspace), "escape", "server.log", "missing", "", None, []):
            try:
                starter.list_files(workspace, path)
            except ValueError:
                pass
            else:
                raise AssertionError(f"应该拒绝这个目录参数：{path!r}")
        for field, bad_values in {
            "offset": [-1, True, 1.5, "0", None],
            "limit": [0, -1, 101, True, 1.5, "2", None],
        }.items():
            for value in bad_values:
                try:
                    starter.list_files(workspace, **{field: value})
                except ValueError:
                    pass
                else:
                    raise AssertionError(f"应该拒绝 {field}={value!r}")
    print("目录检查通过：分页、结束位置、数量上限、参数校验与路径边界")


def check_loop(workspace, show_steps=False):
    client = CORE["FakeClient"]([
        CORE["fake_response"]("tool_calls", tool_calls=[
            CORE["fake_tool_call"]("list_1", "list_files", {"path": ".", "limit": 1}),
        ]),
        CORE["fake_response"]("tool_calls", tool_calls=[
            CORE["fake_tool_call"]("list_2", "list_files", {"path": ".", "offset": 1, "limit": 1}),
        ]),
        CORE["fake_response"]("tool_calls", tool_calls=[
            CORE["fake_tool_call"]("read_1", "read_file", {"path": "server.log"}),
        ]),
        CORE["fake_response"]("stop", content="已取得目录清单和日志（预设回复）"),
    ])

    def execute(call):
        if show_steps:
            print(f"模型申请 {call.id}: {call.function.name} {call.function.arguments}")
        result = starter.execute_tool(workspace, call)
        if show_steps:
            print(f"工具回执 {call.id}: {result}")
        return result

    answer = CORE["run_agent_loop"](
        client, "scripted", starter.TOOLS, "每页查看一个文件名，查完目录后读取 server.log。",
        execute,
    )
    assert len(client.completions.requests) == 4
    schema = client.completions.requests[0]["tools"][-1]["function"]["parameters"]
    assert set(schema["properties"]) == {"path", "offset", "limit"}
    assert schema["properties"]["limit"]["maximum"] == 100
    listing = client.completions.requests[1]["messages"][-1]
    assert listing["role"] == "tool" and listing["tool_call_id"] == "list_1"
    assert json.loads(listing["content"]) == {"path": ".", "files": ["order_service.py"], "next_offset": 1}
    next_page = client.completions.requests[2]["messages"][-1]
    assert next_page["tool_call_id"] == "list_2"
    assert json.loads(next_page["content"]) == {"path": ".", "files": ["server.log"], "next_offset": None}
    reading = client.completions.requests[3]["messages"][-1]
    assert reading["tool_call_id"] == "read_1"
    assert json.loads(reading["content"])["content"] == "示例日志：订单查询失败"
    assert "预设回复" in answer
    if show_steps:
        print("模型最终回答：", answer)
        print("共 4 次模型请求：3 次提出工具调用，1 次最终回答。")

    default_call = CORE["fake_tool_call"]("default", "list_files", {"path": "."})
    assert json.loads(starter.execute_tool(workspace, default_call)) == starter.list_files(workspace)

    for name, args in (
        ("write_file", {"path": "server.log", "content": "changed"}),
        ("read_file", {"path": "logs/worker.log"}),
        ("list_files", {"path": ".", "recursive": True}),
        ("list_files", {"path": []}),
        ("list_files", {"path": ".", "offset": -1}),
        ("list_files", {"path": ".", "offset": True}),
        ("list_files", {"path": ".", "limit": 0}),
        ("list_files", {"path": ".", "limit": 101}),
        ("list_files", {"path": ".", "limit": False}),
        ("list_files", {"path": ".", "limit": "2"}),
        ("list_files", {"path": "escape"}),
        ("list_files", {"path": "../outside"}),
        ("list_files", {"offset": 0}),
        ("list_files", []),
    ):
        call = CORE["fake_tool_call"]("rejected", name, args)
        assert "error" in json.loads(starter.execute_tool(workspace, call))
    call = CORE["fake_tool_call"]("bad_json", "list_files", {})
    call.function.arguments = "{"
    assert "error" in json.loads(starter.execute_tool(workspace, call))

    corrected = CORE["FakeClient"]([
        CORE["fake_response"]("tool_calls", tool_calls=[
            CORE["fake_tool_call"]("bad_limit", "list_files", {"path": ".", "limit": 0}),
        ]),
        CORE["fake_response"]("tool_calls", tool_calls=[
            CORE["fake_tool_call"]("corrected_limit", "list_files", {"path": ".", "limit": 2}),
        ]),
        CORE["fake_response"]("stop", content="参数已修正（预设回复）"),
    ])
    CORE["run_agent_loop"](corrected, "scripted", starter.TOOLS, "查看目录", lambda call: starter.execute_tool(workspace, call))
    rejected = corrected.completions.requests[1]["messages"][-1]
    assert rejected["tool_call_id"] == "bad_limit"
    assert "limit 必须" in json.loads(rejected["content"])["error"]
    repaired = corrected.completions.requests[2]["messages"][-1]
    assert repaired["tool_call_id"] == "corrected_limit"
    assert json.loads(repaired["content"])["files"] == ["order_service.py", "server.log"]
    print("接线检查通过：两页目录 -> 读取日志 -> Final；参数传入、回执配对与原读取权限均正常")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--wiring", action="store_true")
    modes.add_argument("--demo", action="store_true")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="agent-list-files-") as folder:
        workspace = make_workspace(Path(folder))
        paths = [path for path in Path(folder).rglob("*") if not path.is_symlink() and path.is_file()]
        before = {path: path.read_bytes() for path in paths}
        if args.wiring or args.demo:
            if args.demo:
                print("模型回复为预设剧本；目录和文件读取真实发生，无网络调用。")
            check_loop(workspace, show_steps=args.demo)
        else:
            check_listing(workspace)
            check_loop(workspace)
        assert {path: path.read_bytes() for path in paths} == before, "不得修改任何输入文件"
        print("输入文件未改变。" if args.demo else "wiring passed（使用真实工具）" if args.wiring else "全部检查通过：分页目录工具已接入 Agent Loop")


if __name__ == "__main__":
    main()
