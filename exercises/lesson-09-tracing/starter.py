"""Lesson 09 exercise: represent one Agent run as Trace and Span records."""

import sys


# ponytail: 第一关只处理单进程、父节点先写入；分布式收集时需允许乱序到达。
def append_span(
    trace: dict,
    span_id: str,
    parent_span_id: str | None,
    name: str,
    status: str,
) -> None:
    """TODO: 检查点 A。校验 Span 身份和父节点，再追加到 Trace。"""
    if any(span["span_id"] == span_id for span in trace["spans"]):
        raise ValueError(f"重复 span_id：{span_id}")
    if parent_span_id is not None and not any(
        span["span_id"] == parent_span_id for span in trace["spans"]
    ):
        raise ValueError(f"父 Span 不存在：{parent_span_id}")

    trace["spans"].append({
        "trace_id": trace["trace_id"],
        "span_id": span_id,
        "parent_span_id": parent_span_id,
        "name": name,
        "status": status,
    })


def finish_span(
    span: dict,
    *,
    ended_at_ms: int,
    operation_status: str,
    outcome: str,
) -> None:
    """TODO: 检查点 B。结束 Span，并分开保存调用状态与业务结果。"""
    if span.get("status") != "running":
        raise ValueError("只有 running Span 可以结束")
    if operation_status not in {"ok", "error"}:
        raise ValueError(f"未知调用状态：{operation_status}")
    if ended_at_ms < span["started_at_ms"]:
        raise ValueError("结束时间不能早于开始时间")

    span["status"] = operation_status
    span["outcome"] = outcome
    span["ended_at_ms"] = ended_at_ms
    span["duration_ms"] = ended_at_ms - span["started_at_ms"]


def checkpoint_a() -> None:
    trace = {"trace_id": "trace_demo", "spans": []}

    append_span(trace, "span_root", None, "agent_run", "completed")
    append_span(
        trace,
        "span_model",
        "span_root",
        "model_call",
        "completed",
    )
    append_span(
        trace,
        "span_tool",
        "span_root",
        "read_file",
        "completed",
    )

    assert len(trace["spans"]) == 3
    assert [span["span_id"] for span in trace["spans"]] == [
        "span_root",
        "span_model",
        "span_tool",
    ]
    assert all(
        span["trace_id"] == "trace_demo" for span in trace["spans"]
    )
    assert trace["spans"][0]["parent_span_id"] is None
    assert trace["spans"][1]["parent_span_id"] == "span_root"
    assert trace["spans"][2]["parent_span_id"] == "span_root"

    try:
        append_span(
            trace,
            "span_tool",
            "span_root",
            "duplicate",
            "completed",
        )
    except ValueError:
        pass
    else:
        raise AssertionError("重复 span_id 必须被拒绝")

    try:
        append_span(
            trace,
            "span_orphan",
            "span_missing",
            "orphan",
            "completed",
        )
    except ValueError:
        pass
    else:
        raise AssertionError("不存在的 parent_span_id 必须被拒绝")

    print(f'trace_id={trace["trace_id"]}')
    print(f'span_count={len(trace["spans"])}')
    print("checkpoint A passed")


def checkpoint_b() -> None:
    checkpoint_a()

    span = {
        "trace_id": "trace_demo",
        "span_id": "span_model",
        "parent_span_id": "span_root",
        "name": "model_call",
        "status": "running",
        "started_at_ms": 1000,
    }
    finish_span(
        span,
        ended_at_ms=1125,
        operation_status="ok",
        outcome="failed",
    )

    assert span["status"] == "ok"
    assert span["outcome"] == "failed"
    assert span["ended_at_ms"] == 1125
    assert span["duration_ms"] == 125

    try:
        finish_span(
            {
                "status": "running",
                "started_at_ms": 2000,
            },
            ended_at_ms=1999,
            operation_status="error",
            outcome="failed",
        )
    except ValueError:
        pass
    else:
        raise AssertionError("结束时间早于开始时间时必须被拒绝")

    for invalid_span, invalid_status in [
        ({"status": "ok", "started_at_ms": 1000}, "ok"),
        ({"status": "running", "started_at_ms": 1000}, "completed"),
    ]:
        try:
            finish_span(
                invalid_span,
                ended_at_ms=1001,
                operation_status=invalid_status,
                outcome="failed",
            )
        except ValueError:
            pass
        else:
            raise AssertionError("非 running Span 和未知调用状态必须被拒绝")

    print("operation_status=ok")
    print("business_outcome=failed")
    print("duration_ms=125")
    print("checkpoint B passed")


def main() -> None:
    if "--checkpoint-b" in sys.argv:
        checkpoint_b()
        return
    if "--checkpoint-a" in sys.argv:
        checkpoint_a()
        return
    print(
        "运行：python -B exercises/lesson-09-tracing/starter.py "
        "--checkpoint-a 或 --checkpoint-b"
    )


if __name__ == "__main__":
    main()
