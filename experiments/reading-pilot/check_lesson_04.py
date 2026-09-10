"""检查第 4 课正式正文的教学代码和数据，不调用模型或写入用户状态。"""

import ast
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import re


def self_check():
    chapter = Path(__file__).resolve().parents[2] / "chapters/04-会话持久化.md"
    text = chapter.read_text(encoding="utf-8")
    blocks = re.findall(r"```python\n(.*?)\n```", text, re.S)
    expected = [
        "12\n12\n",
        "order-debug-01\n2\n",
        "旧会话： ['默认使用中文', '诊断要注明文件位置', '等待用户提供日志位置']\n"
        "新会话： ['默认使用中文', '诊断要注明文件位置']\n",
    ]
    assert len(blocks) == len(expected), "正文应包含三个教学片段"
    namespace = {}
    for block, output in zip(blocks, expected):
        tree = ast.parse(block)
        with redirect_stdout(io.StringIO()) as captured:
            # 仅执行本仓库的教学代码；不是执行模型输出。
            exec(compile(tree, str(chapter), "exec"), namespace)
        assert captured.getvalue() == output, captured.getvalue()

    checkpoint = namespace["checkpoint"]
    events = namespace["events"]
    assert checkpoint["balance"] + sum(events[checkpoint["processed"]:]) == sum(events)
    restored = namespace["restored"]
    assert restored == namespace["state"]
    assert restored["processed_entries"] == 2 == len(restored["messages"])
    jsonl = re.findall(r"```jsonl\n(.*?)\n```", text, re.S)
    assert len(jsonl) == 1
    entries = [json.loads(line) for line in jsonl[0].splitlines()]
    assert all(entry["type"] == "message" for entry in entries)
    assert [entry["message"] for entry in entries] == restored["messages"]
    assert namespace["context_materials"]("new") == ["默认使用中文", "诊断要注明文件位置"]
    assert not namespace["session_dir"].exists(), "教学临时目录应被清理"
    print("lesson 04 passed: checkpoint replay, JSON round-trip, JSONL messages, session separation")


if __name__ == "__main__":
    self_check()
