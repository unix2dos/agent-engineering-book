"""验证第 5 课正式正文与既有压缩函数；不调用真实模型。"""

import ast
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import re
import runpy
import tempfile

import demo


def pending_calls(messages):
    pending = set()
    for message in messages:
        if message.get("tool_calls"):
            assert not pending, "上批工具结果未齐，不能继续添加模型调用"
            pending = {call["id"] for call in message["tool_calls"]}
        elif message["role"] == "tool":
            assert message["tool_call_id"] in pending, "结果缺少对应申请"
            pending.remove(message["tool_call_id"])
        else:
            assert not pending, "工具调用与结果之间不能插入新轮次"
    return pending


def tool_message(call_id, path):
    call = demo.CORE["fake_tool_call"](call_id, "read_file", {"path": path})
    return demo.CORE["assistant_message_from_api"](
        demo.CORE["fake_response"]("tool_calls", tool_calls=[call]).choices[0].message
    )


def self_check():
    chapter = demo.HERE.parents[1] / "chapters/05-上下文工程.md"
    text = chapter.read_text(encoding="utf-8")
    blocks = re.findall(r"```python\n(.*?)\n```", text, re.S)
    expected = [
        "TypeError: 'NoneType' object is not subscriptable\n返回 HTTP 500\n完整输出仍有 4 行\n",
        "35000\nTrue\n",
        "assistant 历史摘要：只读排查订单接口的500，日志为 server.log，诊断要引用证据。\n"
        "user 日志里有什么异常？\nassistant 发现 TypeError，尚未核对源码。\n"
        "user 读取 order_service.py 核对原因\n",
    ]
    assert len(blocks) == len(expected)
    namespace = {}
    for block, output in zip(blocks, expected):
        tree = ast.parse(block)
        with redirect_stdout(io.StringIO()) as captured:
            # 仅执行仓库内的教学代码，不执行模型输出。
            exec(compile(tree, str(chapter), "exec"), namespace)
        assert captured.getvalue() == output, captured.getvalue()
    assert namespace["full_output"].startswith("服务启动\n收到 order_404 请求\n")
    assert namespace["required"] - namespace["window"] == 3000
    assert namespace["messages"][1:3] == namespace["checkpoint"]["retained_tail"]
    assert namespace["messages"][3:] == namespace["new_messages"]

    core = demo.CORE
    messages = [
        {"role": "user", "content": "只读排查订单500。" + "旧材料。" * 100},
        {"role": "assistant", "content": "已确认范围。"},
        {"role": "user", "content": "读取 server.log"},
        tool_message("log_call", "server.log"),
        {"role": "tool", "tool_call_id": "log_call", "content": "TypeError"},
        {"role": "assistant", "content": "还需核对源码。"},
        {"role": "user", "content": "读取 order_service.py"},
        tool_message("source_call", "order_service.py"),
    ]
    cut = core["find_compaction_cut"](messages, keep_recent_turns=1)
    assert cut == 2
    assert core["find_compaction_cut"](messages[2:], keep_recent_turns=1) is None
    assert pending_calls(messages[cut:]) == {"source_call"}

    with tempfile.TemporaryDirectory(prefix="agent-lesson05-check-") as folder:
        session_file = Path(folder) / "session.jsonl"
        for message in messages:
            core["persist_message"](session_file, message)
        original = session_file.read_bytes()
        core["append_compaction"](session_file, "只读排查订单500，日志在 server.log。", messages[cut:])
        view = core["build_prompt_view"](core["load_entries"](session_file))
        assert view[1:] == messages[cut:]
        assert pending_calls(view) == {"source_call"}, "保留状态尚不等于可提交请求"
        assert session_file.read_bytes().startswith(original)

        for message in [
            {"role": "tool", "tool_call_id": "source_call", "content": "源码已经返回"},
            {"role": "assistant", "content": "诊断完成，未修改文件。"},
        ]:
            core["persist_message"](session_file, message)
        view = core["build_prompt_view"](core["load_entries"](session_file))
        assert not pending_calls(view)
        second_cut = core["find_compaction_cut"](view, keep_recent_turns=1)
        captured_prefixes = []

        def summarize(prefix):
            captured_prefixes.append(prefix)
            return "只读排查订单500；日志出现 TypeError。"

        before_second = session_file.read_bytes()
        assert core["maybe_compact"](session_file, 1, 1, summarize)
        assert captured_prefixes == [view[:second_cut]]
        assert captured_prefixes[0][0] == view[0], "再次压缩必须带上旧摘要"
        entries = core["load_entries"](session_file)
        assert entries[-1]["type"] == "compaction"
        assert entries[-1]["retained_tail"] == view[second_cut:]
        latest_view = core["build_prompt_view"](entries)
        assert latest_view[1:] == view[second_cut:]
        assert not pending_calls(latest_view)
        assert session_file.read_bytes().startswith(before_second)
        new_message = {"role": "user", "content": "只给出修复建议。"}
        core["persist_message"](session_file, new_message)
        assert core["build_prompt_view"](core["load_entries"](session_file)) == latest_view + [new_message]

        def fail_summary(prefix):
            raise RuntimeError("模拟摘要服务失败")

        before_failure = session_file.read_bytes()
        for callback, expected_error in [
            (fail_summary, "模拟摘要服务失败"),
            (lambda prefix: "", "Compaction Summary 不能为空"),
        ]:
            try:
                core["maybe_compact"](session_file, 1, 0, callback)
            except (ValueError, RuntimeError) as error:
                assert str(error) == expected_error
            else:
                raise AssertionError("失败摘要不得追加为成功记录")
            assert session_file.read_bytes() == before_failure

        reference = runpy.run_path(str(demo.HERE.parents[1] / "examples/lesson_05_context_compaction.py"))
        # 这里只检查字节表示是否变长，不把它当成 Token 测量。
        def measure(value):
            return len(json.dumps(value, ensure_ascii=False).encode("utf-8"))

        try:
            reference["maybe_compact"](
                session_file, [], 1, 10**9, measure,
                lambda prefix: "x" * (len(before_failure) * 2),
            )
        except RuntimeError as error:
            assert str(error) == "Compaction 没有减少 Context，拒绝写入"
        else:
            raise AssertionError("参考实现应拒绝更长的新视图")
        assert session_file.read_bytes() == before_failure

    print("lesson 05 passed: previews, budget, view assembly, turn boundaries, repeated compaction, failure preservation")


if __name__ == "__main__":
    self_check()
