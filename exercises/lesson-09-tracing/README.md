# 第 9 课实践：把一次 Agent 运行组织成 Trace

Agent 完成一次任务后，你手里有 Model 日志、Tool 日志和执行账本。如果它们没有共同的身份和层级，只能逐行猜测哪些记录属于同一个任务。

仓库保留完成后的参考实现。自己重做时，每次只清空当前检查点指定的函数；下面的 `NotImplementedError` 是该函数尚未实现时的红测试，不是完成版代码的当前输出。

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

函数尚未实现时会看到：

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

## 检查点 B：调用成功，不等于业务成功

一次 Model API 请求正常返回了，但内容表示任务无法完成：

```text
调用过程：ok
业务结果：failed
```

这两个结果可以同时成立。前者说明 Model Call 正常结束；后者说明 Agent 没有完成用户目标。

实现 `finish_span()`，满足下面五条规则：

1. Span 只能从 `status="running"` 结束；
2. `operation_status` 只能是 `ok` 或 `error`；
3. `ended_at_ms` 不能早于 `started_at_ms`；
4. 保存 `ended_at_ms`，并计算 `duration_ms`；
5. 把 `operation_status` 保存到 `status`，把业务结果另存为 `outcome`。

测试特意传入：

```text
operation_status=ok
outcome=failed
```

不要根据 `outcome` 偷偷把 Span 的 `status` 改成 `error`。它们回答的不是同一个问题。

运行：

```bash
python -B exercises/lesson-09-tracing/starter.py --checkpoint-b
```

函数尚未实现时会看到：

```text
NotImplementedError: 请实现 finish_span
```

完成后应看到：

```text
trace_id=trace_demo
span_count=3
checkpoint A passed
operation_status=ok
business_outcome=failed
duration_ms=125
checkpoint B passed
```

## 检查点 C：一次 Tool Call，可以有多次执行尝试

Model 只发出一张写文件申请：

```text
tool_call_id=call_write
```

第一次执行失败，Harness 决定重试：

```text
第一次：execution_id=exec_1  span_id=span_exec_1
第二次：execution_id=exec_2  span_id=span_exec_2
```

它们仍在完成同一张 Tool Call，所以 `tool_call_id` 不变。它们是两次真实尝试，所以 `execution_id` 与 `span_id` 都不同。

实现 `append_tool_attempt()`：

1. 同一个 Trace 中，`execution_id` 不能重复；
2. 使用已有的 `append_span()` 添加名为 `tool_execution` 的 Span；
3. 再给新 Span 保存 `tool_call_id` 和 `execution_id`；
4. 同一个 `tool_call_id` 可以出现多次；
5. 非法输入必须在追加 Span 前拒绝，不能留下半条记录。

运行：

```bash
python -B exercises/lesson-09-tracing/starter.py --checkpoint-c
```

函数尚未实现时会看到：

```text
NotImplementedError: 请实现 append_tool_attempt
```

完成后最后应看到：

```text
tool_call_count=1
execution_count=2
execution_span_count=2
checkpoint C passed
```

## 检查点 D：先筛选，再导出

Trace 里可能同时存在两类字段：

```text
排查需要：provider、model、duration_ms
可能泄密：prompt、authorization、tool_result
```

如果采用“只删除目前知道的敏感字段”，以后新增一个 `api_key` 就可能漏出去。更稳妥的起点是反过来：只允许明确批准的字段离开本机，其余字段默认不导出。

实现 `select_export_attributes()`：

1. 只保留 `allowed_names` 中列出的字段；
2. 被允许但原字典中不存在的字段直接忽略；
3. 返回一个新字典；
4. 不得修改传入的 `attributes`；
5. 不要在函数里写死 `prompt`、`authorization` 等黑名单。

运行：

```bash
python -B exercises/lesson-09-tracing/starter.py --checkpoint-d
```

函数尚未实现时会看到：

```text
NotImplementedError: 请实现 select_export_attributes
```

完成后最后应看到：

```text
local_attribute_count=6
exported_attribute_count=3
sensitive_content_exported=false
checkpoint D passed
```

## 检查点 E：任务没结束，先别决定删不删

假设生产环境只想保留少量成功 Trace，但所有错误和 `unknown` 都必须保留。任务刚开始时，我们还不知道它最后是否失败，因此不能立刻删除没被抽中的 Trace。

```text
Trace 还有 running Span
-> 返回 None，继续临时保留

Trace 已结束，而且出现 error / failed / unknown
-> 返回 True，保留

Trace 已结束，而且全部成功
-> 使用成功样本的抽样结果
```

这就是 Tail Sampling 的核心：等整条 Trace 接近尾部、结果已经出现后，再做保留决定。

实现 `decide_trace_retention()`：

1. 只要还有 `status="running"`，返回 `None`；
2. 任一 Span 的 `status="error"`，返回 `True`；
3. 任一 Span 的 `outcome` 为 `failed` 或 `unknown`，返回 `True`；
4. 其余情况返回 `keep_success_sample`；
5. 不要在函数中调用随机数，测试会传入确定的抽样结果。

运行：

```bash
python -B exercises/lesson-09-tracing/starter.py --checkpoint-e
```

函数尚未实现时会看到：

```text
NotImplementedError: 请实现 decide_trace_retention
```

完成后最后应看到：

```text
running_decision=pending
error_retained=true
unknown_retained=true
successful_sample_retained=false
checkpoint E passed
```
