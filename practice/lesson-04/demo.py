"""保存并读回一个会话，对比历史、快照和跨会话材料；只用临时文件。"""

import json
from pathlib import Path
import tempfile


def run_demo():
    messages = [
        {"role": "user", "content": "排查订单接口的500"},
        {"role": "assistant", "content": "请提供日志位置"},
    ]
    state = {
        "session_id": "order-debug-01", "processed_entries": len(messages),
        "messages": messages, "summary": "等待用户提供日志位置",
    }
    with tempfile.TemporaryDirectory(prefix="agent-session-") as folder:
        session = Path(folder) / state["session_id"]
        session.mkdir()
        transcript = session / "session.jsonl"
        with transcript.open("w", encoding="utf-8") as stream:
            for message in messages:
                stream.write(json.dumps({"type": "message", "message": message}, ensure_ascii=False) + "\n")
        checkpoint = session / "checkpoint.json"
        temporary = checkpoint.with_suffix(".tmp")
        temporary.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
        temporary.replace(checkpoint)
        restored = json.loads(checkpoint.read_text(encoding="utf-8"))
        history = [json.loads(line)["message"] for line in transcript.read_text(encoding="utf-8").splitlines()]
        assert restored == state
        assert history == restored["messages"] and len(history) == restored["processed_entries"]
        print("读回会话：", restored["session_id"])
        print("历史条数：", len(history))
        memories = ["默认使用中文", "诊断要注明文件位置"]
        for session_id in ("order-debug-01", "new"):
            materials = list(memories)
            if session_id == restored["session_id"]:
                materials.append(restored["summary"])
            print(session_id, "本次选择的材料：", materials)
            assert (restored["summary"] in materials) == (session_id == restored["session_id"])
    print("只验证文件存取与会话材料选择；没有调用模型或重放工具。")


if __name__ == "__main__":
    run_demo()
