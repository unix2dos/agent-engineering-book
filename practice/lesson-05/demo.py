"""观察完整历史与压缩后输入的差别；复用综合项目，只操作临时文件。"""

import json
from pathlib import Path
import runpy
import tempfile

KEEP_RECENT_TURNS = 1
CORE = runpy.run_path(str(Path(__file__).resolve().parents[1] / "workspace-agent/agent.py"))


def run_demo(keep_recent_turns=KEEP_RECENT_TURNS):
    messages = [
        {"role": "user", "content": "只读排查订单500。" + "重复日志。" * 100},
        {"role": "assistant", "content": "已确认只读范围。"},
        {"role": "user", "content": "接下来读取源码。"},
        {"role": "assistant", "content": "需要核对 order_service.py。"},
        {"role": "user", "content": "给出建议，不修改文件。"},
    ]
    with tempfile.TemporaryDirectory(prefix="agent-context-") as folder:
        session = Path(folder) / "session.jsonl"
        for message in messages:
            CORE["persist_message"](session, message)
        original = session.read_bytes()
        cut = CORE["find_compaction_cut"](messages, keep_recent_turns=keep_recent_turns)
        changed = CORE["maybe_compact"](
            session, 1, keep_recent_turns, lambda _: "只读排查订单500，日志已查看；尚未核对源码。",
        )
        view = CORE["build_prompt_view"](CORE["load_entries"](session))
        assert changed == (cut is not None)
        assert (view[1:] == messages[cut:]) if changed else (view == messages)
        assert session.read_bytes().startswith(original)
        print("发生压缩：", changed)
        print("旧历史仍在：", session.read_bytes().startswith(original))
        print("会话输入字符数：", len(json.dumps(messages, ensure_ascii=False)), "->", len(json.dumps(view, ensure_ascii=False)))
        for message in view:
            print(message["role"], message["content"])
        before_failure = session.read_bytes()
        try:
            CORE["maybe_compact"](session, 1, 0, lambda _: "无效长摘要" * 1000)
        except RuntimeError as error:
            assert str(error) == "Compaction 没有减少 Context，拒绝写入"
            print("失败分支：", error)
        else:
            raise AssertionError("变长的摘要必须被拒绝")
        assert session.read_bytes() == before_failure
    print("摘要为预设文字；字符数不等于 Token 数，也不证明摘要语义完整。")


if __name__ == "__main__":
    run_demo()
