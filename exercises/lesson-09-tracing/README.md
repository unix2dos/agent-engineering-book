# 第 9 课实践：把一次 Agent 运行组织成 Trace

Agent 完成一次任务后，你手里有 Model 日志、Tool 日志和执行账本。如果它们没有共同的身份和层级，只能逐行猜测哪些记录属于同一个任务。

第一关只建立最小结构：一个 Trace 包含一个根 Span、一次 Model Call 和一次 Tool Call。

```text
trace_demo
|
+-- span_root  agent_run
    |
    +-- span_model  model_call
    +-- span_tool   read_file
```

## 检查点 A：同一个 Trace，不同的 Span

打开 [`starter.py`](starter.py)，只实现 `append_span()`。

函数接收：

```text
trace           整次任务的记录
span_id         当前步骤的身份
parent_span_id  当前步骤属于哪个父步骤；根步骤为 None
name            当前步骤做了什么
status          当前步骤是否正常结束
```

你需要满足五条规则：

1. 新 Span 要复制 `trace["trace_id"]`；
2. 把 `span_id`、`parent_span_id`、`name` 和 `status` 保存进新字典；
3. 把新字典追加到 `trace["spans"]`；
4. `span_id` 已存在时抛出 `ValueError`；
5. `parent_span_id` 不是 `None`、但父 Span 尚不存在时抛出 `ValueError`。

这里不自动生成 UUID，也不记录时间。固定 ID 能让你先看清结构，下一关再加入开始时间、结束时间和失败状态。

这也是一个单进程教学实现，假设父 Span 先写入、子 Span 后写入。真实分布式系统可能先收到子 Span，再收到父 Span；那时收集器必须允许乱序到达，稍后根据 ID 接回树形关系。

运行：

```bash
python -B exercises/lesson-09-tracing/starter.py --checkpoint-a
```

当前会看到：

```text
NotImplementedError: 请实现 append_span
```

完成后应看到：

```text
trace_id=trace_demo
span_count=3
checkpoint A passed
```

这份 Trace 单独用于排查运行过程，不进入 Prompt，也不替代 Transcript 和 Ledger。
