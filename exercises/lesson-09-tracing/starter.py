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


def main() -> None:
    if "--checkpoint-a" in sys.argv:
        checkpoint_a()
        return
    print("运行：python -B exercises/lesson-09-tracing/starter.py --checkpoint-a")


if __name__ == "__main__":
    main()
