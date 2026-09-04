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
    """检查点 A：校验 Span 身份和父节点，再追加到 Trace。"""
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
    """检查点 B：结束 Span，并分开保存调用状态与业务结果。"""
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


def append_tool_attempt(
    trace: dict,
    *,
    span_id: str,
    parent_span_id: str,
    tool_call_id: str,
    execution_id: str,
    status: str,
) -> None:
    """检查点 C：记录同一个 Tool Call 的一次执行尝试。"""
    if any(
        span.get("execution_id") == execution_id
        for span in trace["spans"]
    ):
        raise ValueError(f"重复 execution_id：{execution_id}")

    append_span(
        trace,
        span_id,
        parent_span_id,
        "tool_execution",
        status,
    )
    trace["spans"][-1].update({
        "tool_call_id": tool_call_id,
        "execution_id": execution_id,
    })


def select_export_attributes(
    attributes: dict,
    allowed_names: set[str],
) -> dict:
    """检查点 D：只复制允许离开本机的 Trace 字段。"""
    return {
        name: value
        for name, value in attributes.items()
        if name in allowed_names
    }


def decide_trace_retention(
    trace: dict,
    *,
    keep_success_sample: bool,
) -> bool | None:
    """检查点 E：Trace 结束后，根据结果决定是否保留。"""
    spans = trace["spans"]
    if any(span.get("status") == "running" for span in spans):
        return None
    if any(span.get("status") == "error" for span in spans):
        return True
    if any(
        span.get("outcome") in {"failed", "unknown"}
        for span in spans
    ):
        return True
    return keep_success_sample


def checkpoint_a() -> None:
    trace = {"trace_id": "trace_demo", "spans": []}

    append_span(trace, "span_root", None, "agent_run", "ok")
    append_span(
        trace,
        "span_model",
        "span_root",
        "model_call",
        "ok",
    )
    append_span(
        trace,
        "span_tool",
        "span_root",
        "read_file",
        "ok",
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
            "ok",
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
            "ok",
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


def checkpoint_c() -> None:
    checkpoint_b()

    trace = {"trace_id": "trace_retry", "spans": []}
    append_span(trace, "span_root", None, "agent_run", "ok")

    append_tool_attempt(
        trace,
        span_id="span_exec_1",
        parent_span_id="span_root",
        tool_call_id="call_write",
        execution_id="exec_1",
        status="error",
    )
    append_tool_attempt(
        trace,
        span_id="span_exec_2",
        parent_span_id="span_root",
        tool_call_id="call_write",
        execution_id="exec_2",
        status="ok",
    )

    attempts = trace["spans"][1:]
    assert [span["tool_call_id"] for span in attempts] == [
        "call_write",
        "call_write",
    ]
    assert [span["execution_id"] for span in attempts] == [
        "exec_1",
        "exec_2",
    ]
    assert [span["span_id"] for span in attempts] == [
        "span_exec_1",
        "span_exec_2",
    ]
    assert [span["name"] for span in attempts] == [
        "tool_execution",
        "tool_execution",
    ]

    before = [dict(span) for span in trace["spans"]]
    try:
        append_tool_attempt(
            trace,
            span_id="span_exec_3",
            parent_span_id="span_root",
            tool_call_id="call_write",
            execution_id="exec_2",
            status="ok",
        )
    except ValueError:
        pass
    else:
        raise AssertionError("重复 execution_id 必须被拒绝")
    assert trace["spans"] == before

    print("tool_call_count=1")
    print("execution_count=2")
    print("execution_span_count=2")
    print("checkpoint C passed")


def checkpoint_d() -> None:
    checkpoint_c()

    attributes = {
        "provider": "openai",
        "model": "demo-model",
        "duration_ms": 125,
        "prompt": "private user message",
        "authorization": "Bearer private-token",
        "tool_result": {"content": "private file content"},
    }
    original = dict(attributes)

    exported = select_export_attributes(
        attributes,
        allowed_names={"provider", "model", "duration_ms"},
    )

    assert exported == {
        "provider": "openai",
        "model": "demo-model",
        "duration_ms": 125,
    }
    assert attributes == original
    assert exported is not attributes
    assert "prompt" not in exported
    assert "authorization" not in exported
    assert "tool_result" not in exported

    print("local_attribute_count=6")
    print("exported_attribute_count=3")
    print("sensitive_content_exported=false")
    print("checkpoint D passed")


def checkpoint_e() -> None:
    checkpoint_d()

    running = {
        "spans": [
            {"name": "agent_run", "status": "running"},
            {"name": "model_call", "status": "ok"},
        ]
    }
    assert decide_trace_retention(
        running,
        keep_success_sample=True,
    ) is None

    operation_error = {
        "spans": [
            {"name": "agent_run", "status": "ok"},
            {"name": "tool_execution", "status": "error"},
        ]
    }
    assert decide_trace_retention(
        operation_error,
        keep_success_sample=False,
    ) is True

    business_failure = {
        "spans": [
            {"name": "agent_run", "status": "ok", "outcome": "failed"},
            {"name": "model_call", "status": "ok"},
        ]
    }
    assert decide_trace_retention(
        business_failure,
        keep_success_sample=False,
    ) is True

    unknown = {
        "spans": [
            {"name": "agent_run", "status": "ok"},
            {"name": "tool_execution", "status": "ok", "outcome": "unknown"},
        ]
    }
    assert decide_trace_retention(
        unknown,
        keep_success_sample=False,
    ) is True

    succeeded = {
        "spans": [
            {"name": "agent_run", "status": "ok", "outcome": "succeeded"},
            {"name": "model_call", "status": "ok"},
        ]
    }
    assert decide_trace_retention(
        succeeded,
        keep_success_sample=False,
    ) is False
    assert decide_trace_retention(
        succeeded,
        keep_success_sample=True,
    ) is True

    print("running_decision=pending")
    print("error_retained=true")
    print("unknown_retained=true")
    print("successful_sample_retained=false")
    print("checkpoint E passed")


def main() -> None:
    if "--checkpoint-e" in sys.argv:
        checkpoint_e()
        return
    if "--checkpoint-d" in sys.argv:
        checkpoint_d()
        return
    if "--checkpoint-c" in sys.argv:
        checkpoint_c()
        return
    if "--checkpoint-b" in sys.argv:
        checkpoint_b()
        return
    if "--checkpoint-a" in sys.argv:
        checkpoint_a()
        return
    print(
        "运行：python -B exercises/lesson-08-tracing/starter.py "
        "--checkpoint-a、--checkpoint-b、--checkpoint-c、--checkpoint-d "
        "或 --checkpoint-e"
    )


if __name__ == "__main__":
    main()
