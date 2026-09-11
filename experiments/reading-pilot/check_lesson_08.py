"""验证第 8 课正式正文：真实临时文件、受控计时与既有 Trace 练习，不调用模型。"""

from contextlib import redirect_stdout
import io
from pathlib import Path
import re
import runpy
import tempfile
from unittest.mock import patch


def self_check():
    here = Path(__file__).resolve().parent
    chapter = here.parents[1] / "chapters/08-Agent可观测性.md"
    blocks = re.findall(r"```python\n(.*?)\n```", chapter.read_text(encoding="utf-8"), re.S)
    expected = [
        "order lookup failed\nok True\n",
        "{'model': 'example-model', 'duration_ms': 1200}\n",
        "True\n",
    ]
    assert len(blocks) == len(expected)
    namespace = {}
    for block, output in zip(blocks, expected):
        with redirect_stdout(io.StringIO()) as captured:
            # 只执行仓库中的教学代码，不执行模型输出。
            exec(compile(block, str(chapter), "exec"), namespace)
        assert captured.getvalue() == output, captured.getvalue()

    read_observed = namespace["read_observed"]
    with tempfile.TemporaryDirectory(prefix="agent-lesson08-check-") as folder:
        path = Path(folder) / "service.log"
        path.write_text("order lookup failed", encoding="utf-8")
        invalid = Path(folder) / "invalid.log"
        invalid.write_bytes(b"\xff")
        for target, error_type in [(path, None), (Path(folder) / "missing.log", FileNotFoundError), (invalid, UnicodeDecodeError)]:
            span = {"trace_id": "trace_check", "span_id": "read_1", "parent_span_id": "run"}
            # 固定时钟只验证计算，不把 125 ms 声称为磁盘或模型实测耗时。
            ticks = iter([10.0, 10.125])
            with patch.dict(read_observed.__globals__, {"perf_counter": lambda: next(ticks)}):
                try:
                    result = read_observed(target, span)
                except Exception as error:
                    assert error_type is not None and type(error) is error_type
                    assert span["status"] == "error"
                    assert span["error_type"] == error_type.__name__
                else:
                    assert error_type is None, "观测代码不能吞掉原来的读取错误"
                    assert result == "order lookup failed" and span["status"] == "ok"
                    assert "error_type" not in span
            assert span["started_at_ms"] == 10000
            assert span["ended_at_ms"] == 10125 and span["duration_ms"] == 125
            assert span["trace_id"] == "trace_check" and span["parent_span_id"] == "run"
        assert path.read_text() == "order lookup failed"
        assert invalid.read_bytes() == b"\xff"

    assert namespace["attributes"]["authorization"] == "示例凭据"
    assert namespace["exported"] == {"model": "example-model", "duration_ms": 1200}
    assert namespace["exported"] is not namespace["attributes"]

    keep = namespace["should_keep"]
    for sample in (False, True):
        assert keep(False, [{"status": "error", "outcome": "failed"}], sample) is None
        assert keep(True, [{"status": "error"}], sample) is True
        for outcome in ("failed", "unknown"):
            assert keep(True, [{"status": "ok", "outcome": outcome}], sample) is True
        assert keep(True, [{"status": "ok", "outcome": "succeeded"}, {"status": "ok"}], sample) is sample

    tracing = runpy.run_path(str(here.parents[1] / "exercises/lesson-08-tracing/starter.py"))
    tracing["checkpoint_e"]()  # 已包含 A～D 的身份、状态与导出检查。
    print("lesson 08 passed: measured read, propagated errors, timing, identities, export filtering, retention")


if __name__ == "__main__":
    self_check()
