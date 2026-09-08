# 第 8 课：Agent Tracing——用 Trace 与 Span 还原一次运行

假设 Agent 读取订单文件、计算总金额，再写入汇总文件。任务超时了，日志却各报各的喜：

```text
第一次模型请求：1.2 秒，HTTP 200
读取文件：0.05 秒，成功
整次任务：等了三分钟，超时
```

模型和工具都拿出了成功回执，用户还没拿到结果。日志像在轮流给自己开无罪证明。

我们要把它们接回同一次运行，找出中间缺了哪一步。下面用一组教学数据还原这个过程；其中的时间与事件用于说明机制，不是线上事故实测。

## 1. 先知道这些记录属于谁

给整次任务一个编号，再给每个步骤自己的编号：

```text
Trace trace_42：汇总订单
|
+-- Span run：整次 Agent 运行
    |
    +-- Span model_1：第一次模型请求
    +-- Span read_1：读取订单文件
    +-- Span model_2：第二次模型请求
```

整条运行记录叫 **Trace**，其中一个有开始、结束和结果的步骤叫 **Span**。[1]

Span 不是一行日志。一次模型请求可以持续两秒，期间写出十条日志，它仍然是同一个步骤。实际发生多少次模型请求、工具执行或重试，就按需要记录多少个 Span，没有固定数量。

一个步骤至少需要能说明身份、归属和时间。以第一次模型请求为例：

```json
{
  "trace_id": "trace_42",
  "span_id": "model_1",
  "parent_span_id": "run",
  "name": "model_call",
  "started_ms": 0,
  "ended_ms": 1200,
  "status": "ok"
}
```

这里用便于阅读的编号和相对时间。所有步骤共享 `trace_id`；`span_id` 区分步骤；`parent_span_id` 指向包含它的父步骤。示例中三段工作都由 Agent 运行包住，所以都指向 `run`。

父子关系说明包含关系，不说明谁先发生。先后和并行要看时间；一次工具调用由哪条模型响应提出，还要结合 Tool Call 和会话记录。

同一 Trace 内不能重复使用步骤编号。分布式收集时，子步骤可能比父步骤先到，不能只因暂时没收到父节点就判断记录错误。

## 2. 为什么前两步成功，任务仍然超时？

把刚才三段工作的开始与结束时间补齐，缺口就出现了。以下代码只取步骤编号、时间和调用状态，时间单位是毫秒：

```python
spans = [
    {"span_id": "model_1", "start": 0, "end": 1200, "status": "ok"},
    {"span_id": "read_1", "start": 1200, "end": 1250, "status": "ok"},
    {"span_id": "model_2", "start": 1250, "end": 180000, "status": "error"},
]

for span in spans:
    duration = span["end"] - span["start"]
    print(span["span_id"], duration, span["status"])
```

输出为：

```text
model_1 1200 ok
read_1 50 ok
model_2 178750 error
```

第一段模型请求完成，文件也读到了；随后第二次模型请求持续等待，直到整次任务的三分钟期限耗尽。写汇总文件和最终回答都还没有发生。

下一步应检查第二次请求的超时记录、网络和服务状态。现在已经找到了调查位置，但仅凭 `error` 还不能断定是网络断开，还是服务迟迟没有响应。

有并行工作时，不要把所有 Span 耗时相加当成任务总耗时；重叠的时间会被重复计算。整个任务持续多久，要看根步骤的起止时间。

反过来，整条路径没有调用错误，也不保证结果正确。HTTP 200 可能带回错误参数，工具也可能正常返回“没有找到订单”。本书的教学记录把两层分开：

```text
status  = ok       调用过程正常结束
outcome = failed   业务目标没有完成
```

这些是教学字段，不要求所有框架使用相同名称。排查时既看调用错误，也看业务结果、实际产物和最终回答。

## 3. 重试了两次，怎样知道它们在做同一件事？

一次工具调用可能尝试多次。假设一项已确认可安全重试的读取请求，第一次超时，第二次成功：

| 记录 | 工具调用编号 | 执行编号 | 步骤编号 |
| --- | --- | --- | --- |
| 第一次尝试 | call_read | exec_1 | span_1 |
| 第二次尝试 | call_read | exec_2 | span_2 |

`tool_call_id` 保持相同，因为它们在处理同一张模型申请；`execution_id` 与 `span_id` 改变，因为实际执行了两次。两次尝试仍属于同一条 Trace。

Trace 只负责把这些尝试关联起来。它不能批准重试，也不能证明邮件、付款等副作用发生了几次。第 6 课的账本、幂等保护和外部回执仍然需要保留。

三种记录各有用途：

- Transcript 保存会话消息，帮助继续对话。
- Ledger 保存工具执行状态，支持核对与恢复。
- Trace 展示步骤关系、耗时和结果，帮助定位故障。

例如写文件后崩溃，会话可能缺少 Tool Result，账本可能停在 `running`，Trace 可能显示写入步骤已经结束。是否需要重做，仍要核对执行记录与实际文件。进程突然退出时，Trace 自身也可能没来得及收齐。

## 4. Trace 保存在哪里，为什么有的 Agent 默认不开？

创建 Span 只完成了记录的第一步。后续还需要缓存、发送和存储：

```text
创建 Span → 缓存与处理 → Exporter 发送 → 存储后端
```

Exporter 是把记录送出去的组件。它可以写本地文件，也可以发到集中保存和查询的服务。因此，项目目录里没有 `trace.jsonl`，不能证明没有 Tracing。

例如，核验版本的 OpenClaw 会通过可选插件导出记录；诊断、插件和导出配置共同决定这条通道是否开启。记录可以发送给收集服务，而不是写进项目文件夹。[2] 其他项目的固定版本与实现对照保留在章末的核验资料中。

Agent 的模型与工具循环可以在没有 Tracing 时运行。默认关闭能避免未经配置就导出内容，也减少运行开销。任务出现多轮调用、重试或并发后，记录完整路径通常会明显降低排查成本。

先确认需要回答什么诊断问题，再决定记录哪些步骤、保存在哪里。完整平台不是理解 Trace 的前提。

## 5. 留下诊断证据，也别顺手留下密钥

工具参数、文件内容、HTTP Header 和异常消息都可能带有秘密。只给 `content` 字段打码不够，凭据可能换个字段名就出门了。

下面用示例数据展示“只允许指定字段导出”的做法：

```python
attributes = {
    "model": "example-model",
    "duration_ms": 1200,
    "authorization": "示例凭据",
}
allowed_names = {"model", "duration_ms"}

exported = {}
for name, value in attributes.items():
    if name in allowed_names:
        exported[name] = value

print(exported)
```

输出为：

```text
{'model': 'example-model', 'duration_ms': 1200}
```

白名单限制了字段，字段值仍要检查。这个例子只放行固定模型名与数值；如果允许任意文本或路径，就还需要截断、遮盖等处理。应在发送前完成这些检查，本地文件也需要合适的访问权限。

记录量大以后，还要决定保留哪些 Trace。常见目标是保留失败，抽样保留成功；失败往往到结束时才知道，因此需要先收集，结束后再决定。这叫 **Tail Sampling（尾部采样）**。任务开始时就决定取舍，则是 Head Sampling；它更早降低采集成本，却不能保证选中后来失败的任务。

下面演示最小保留规则。`finished` 由调用方在确认所有步骤结束后设置，`keep_success` 是对成功记录的抽样决定：

```python
def should_keep(finished, spans, keep_success):
    if not finished:
        return None

    for span in spans:
        if span["status"] == "error":
            return True
        if span["outcome"] in {"failed", "unknown"}:
            return True

    return keep_success

spans = [{"status": "ok", "outcome": "failed"}]
print(should_keep(True, spans, False))
```

输出为 `True`：调用过程正常，但业务失败，仍要保留。返回 `None` 表示等待结束，不能当成“丢弃”。真实系统还要处理缓冲上限、晚到记录和数据丢失，不能靠这段判断保证所有失败都被完整留下。

现在再看开头的三份日志：共同编号把它们归到一个任务，步骤时间把等待定位到第二次模型请求，业务结果说明用户仍未拿到交付。Trace 帮我们缩小了排查范围；下一课的 Evaluation 再判断一组任务是否满足要求，以及改动有没有让旧能力退步。

## 资料与配套实验

1. [OpenTelemetry：Traces](https://opentelemetry.io/docs/concepts/signals/traces/)
2. [OpenClaw：已核验版本的 OpenTelemetry 配置](https://github.com/openclaw/openclaw/blob/64da06a78ffa98c5bb425cc79059d992260a4c76/docs/gateway/opentelemetry.md)
3. [配套实验与完整实现](../exercises/lesson-08-tracing/README.md)
4. [固定源码、导出去向及全部项目对照](../research/08-tracing-source-verification.md)
