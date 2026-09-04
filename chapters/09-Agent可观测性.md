# 第 9 课：Agent Tracing——用 Trace 与 Span 还原一次运行

一次 Agent 任务结束后，屏幕只显示“执行失败”。你打开三份记录，看到的却是：

```text
Model 日志：请求成功，HTTP 200
Tool 日志：命令成功，exit code 0
应用日志：最终回答发送失败
```

这些记录都没有说谎，但它们各自只拍到了一小段。Model 的请求属于哪次任务？Tool 是由哪次 Model 请求发起的？失败发生在 Tool 前面，还是最终回答后面？如果只能按时间逐行猜，日志越多，真相反而越难拼出来。

这一课要给散落的记录加上一条共同的运行路径。工程上通常把整条路径叫 **Trace**，把路径中的一个具体步骤叫 **Span**。

Tracing 不是 Agent 能运行的必要条件。没有它，Model、Harness 和 Tool 仍然可以完成任务。但当一次任务包含多轮 Model、多个 Tool、重试或并发时，Tracing 会从“方便调试”变成“出了问题还能解释”的基础能力。

## 1. Trace 与 Span 分别指什么？

假设 Agent 收到任务：读取 `orders.csv`，计算总金额，再把结果写进 `summary.txt`。它的运行过程可以组织成：

```text
Trace trace_42: 完成用户的整次任务
|
+-- Span span_root: Agent Run
    |
    +-- Span span_model_1: 第一次 Model Call
    +-- Span span_read: read_file
    +-- Span span_model_2: 第二次 Model Call
    +-- Span span_write: write_file
```

`trace_42` 把这些步骤归到同一次任务里。每个 Span 再记录自己的名称、开始时间、结束时间和结果。

最短的区别是：

```text
Trace：这次任务从开始到结束走过哪条路？
Span：这条路上的某一步做了什么？
```

一个 Trace 有多少个 Span，没有固定答案。一次只回答文字的任务可能只有一个 Model Span；一次读取 30 个文件的任务，可能出现几十个 Tool Span。Span 也不等于一行日志。一个 Span 持续 2 秒，其间可以产生多条日志或事件。

## 2. 为什么还需要 parent_span_id？

只有共同的 `trace_id`，我们能知道记录属于同一次任务，却还不知道谁调用了谁。

给 Span 加上 `parent_span_id` 后，平铺记录才能接成树：

```json
{"trace_id":"trace_42","span_id":"span_root","parent_span_id":null,"name":"agent_run"}
{"trace_id":"trace_42","span_id":"span_model","parent_span_id":"span_root","name":"model_call"}
{"trace_id":"trace_42","span_id":"span_tool","parent_span_id":"span_root","name":"read_file"}
```

这里必须守住两个关系：

- 同一个 Trace 中，`span_id` 不能重复，否则两步会共享同一身份；
- `parent_span_id` 必须指向真实父 Span，否则会出现找不到上级的孤儿节点。

第 9 课练习采用单进程教学模型，要求先写父 Span，再写子 Span。真实的分布式收集器可能先收到子节点，稍后才收到父节点，所以会先接收乱序数据，再按 ID 还原关系。

## 3. Trace ID 为什么不能代替 Tool Call ID？

同一次任务里可能有多次工具调用，一次工具调用又可能尝试多次。这几种 ID 回答的问题不同：

| ID | 回答的问题 |
| --- | --- |
| `trace_id` | 这些步骤属于哪次端到端任务？ |
| `span_id` | 这是运行路径中的哪一个步骤？ |
| `parent_span_id` | 这个步骤是谁的子步骤？ |
| `tool_call_id` | Tool Result 回答 Model 发出的哪张调用申请？ |
| `execution_id` | 这是该 Tool Call 的哪一次真实执行尝试？ |

例如，同一个 `write_file` 因网络超时尝试了两次：

```text
同一个 trace_id       trace_42
同一个 tool_call_id   call_write

第一次尝试            execution_id=exec_1  span_id=span_exec_1
第二次尝试            execution_id=exec_2  span_id=span_exec_2
```

两次尝试都在完成同一张 Model 申请，所以 `tool_call_id` 不变。它们确实运行了两次，所以 `execution_id` 和 `span_id` 都要变化。

Tracing 负责把这些动作接成路径；Ledger 仍负责保存执行状态和恢复依据。不能因为 Trace 里出现了两个执行 Span，就推断外部副作用究竟发生了几次。付款平台的回执、数据库约束或执行器记录才是这件事的证据。

## 4. Span 成功，为什么任务仍可能失败？

一次 HTTP 请求成功返回，只说明传输和调用正常结束，不保证返回内容完成了业务目标。

```text
Model Span：ok
返回内容：参数不合法，无法执行
Agent 任务：failed
```

反过来也一样：Tool 可能返回业务上的 `failed`，但负责调用 Tool 的程序正常收到了这个结果。此时“调用过程正常结束”和“Tool 完成目标”是两个判断。

本书练习暂时用 `completed`、`failed` 表示简化结果。生产系统通常会把两层拆开：

```text
Span status     这一步是否正常完成观测范围内的工作
业务结果         Tool 或 Agent 最终完成了什么
```

因此排查失败不能只搜红色 Span。还要看返回字段、Tool Result、Ledger 终态和最终回答是否已经产生。

## 5. Trace、Transcript 与 Ledger 不要合并

三种记录有时都使用 JSONL 或 SQLite，文件格式相同不代表职责相同：

```text
Transcript：Model 看过哪些消息，下一轮对话怎样继续
Ledger：Tool 获批、开始、成功、失败或状态未知
Trace：这些 Model、Tool 与运行时步骤怎样组成一条路径
```

假设程序在 `write_file` 完成后崩溃：

- Transcript 可能只留下 Assistant Tool Call，缺少 Tool Result；
- Ledger 可能停在 `running`，需要恢复程序判断副作用；
- Trace 可以指出崩溃前走到了哪个 Span、耗时多久、由谁触发。

Trace 帮助定位问题，却不自动修复它。它是诊断证据，不是业务事实来源，也不能代替幂等保护。

## 6. 为什么项目目录里经常看不到 Trace 文件？

Tracing 通常不是“调用一次就写一个文件”，而是一条数据管道：

```text
业务代码创建 Span
        |
        v
Processor 缓冲和批处理
        |
        v
Exporter 发送
        |
        v
Collector / Tracing Backend 保存和查询
```

最后一站可以是 Phoenix、Langfuse、Tempo、Jaeger 或商业平台。只有项目明确选择本地文件 Exporter，Trace 才会出现在磁盘上。

这也是多数 Coding Agent 默认关闭 Tracing 的原因：Prompt、Tool 参数和终端输出可能含有秘密；完整保存还会增加网络、存储和性能成本。默认关闭不代表项目认为它没用，而是把“是否记录、记录多少、发到哪里”留给运行者决定。

## 7. 五个开源 Coding Agent 怎样实现？

这些项目都提供了某种 Tracing 能力，但边界并不相同。

### Codex：远程遥测与本地 Rollout Trace 分开

Codex 的 `codex-otel` 可以把日志、Trace 和指标发送到配置的 OTLP Backend。另一条 Rollout Trace 路径只在设置 `CODEX_ROLLOUT_TRACE_ROOT` 后启用，把 `trace.jsonl`、`payloads/*.json` 和可选的 `state.json` 写到本地。

Codex 源码特意强调：Rollout Trace 是本地诊断记录，不是上传遥测。它可能包含 Prompt、Tool 输入输出和终端内容，需要当作敏感文件处理。

### OpenClaw：插件把运行事件送进 OTLP

OpenClaw 通过可选的 `diagnostics-otel` 插件导出 Trace。只有 Diagnostics、插件和 OTLP 配置同时启用，Exporter 才会工作。Model Call、Harness 生命周期、Tool、Exec 和 Context Assembly 都可以成为 Span。

数据通常发送到 OTLP Collector。它能把日志镜像为 stdout JSONL，但那是日志输出，不是默认的本地 Span 仓库。

### OpenCode：标准 OTLP 加一条开发调试记录

OpenCode `v1.18.27` 已提供 OTLP Trace Exporter。设置 `OTEL_EXPORTER_OTLP_ENDPOINT` 后，它会把 Span 发到该地址的 `/v1/traces`；AI SDK 的 Model Span 还由 `experimental.openTelemetry` 开关控制。

OpenCode 另有一条仅供 Direct Interactive Mode 调试的 JSONL：设置 `OPENCODE_DIRECT_TRACE=1` 后，运行事件写入 `~/.local/share/opencode/log/direct/`。这条记录用于检查流式事件、权限与界面状态，不应和标准 OpenTelemetry Span 混为一谈。

### Pi：先定义接口，不替宿主选择 Backend

Pi 当前提供 `TelemetryContext`、`TelemetrySpan`、父子关系和一套 Agent Telemetry Schema。默认 Context 是 No-op，也就是调用照常执行，但不记录任何 Span。

Pi 还提供只活在当前进程中的 `InMemoryTelemetryContext`，主要用于测试。它没有内置 Exporter，也不决定是否使用 OpenTelemetry、Sentry、日志或其他 Backend。因此 Pi 具备 Tracing 契约和部分 Harness 埋点，不等于 Pi CLI 默认会生成 Trace 文件；其跨进程传播等能力仍有一部分处于设计或实现阶段。

### Hermes：用可选插件把 Turn、LLM 与 Tool 送到 Langfuse

Hermes 内置但默认不启用 `observability/langfuse` 插件。启用并配置凭据后，它为每个 Turn 建立根观察记录，为每次 LLM Call 和 Tool Call 建立子记录，再发送到 Langfuse Cloud 或自建 Langfuse。

Hermes 还有面向 Gateway Health 和 Diagnostic Event 的 OTLP Exporter。它们观察的是网关运行状况，不应被直接当成完整的 Agent 任务 Trace。

五个项目放在一起，能看到一个共同选择：

```text
Agent 核心逻辑可以在没有 Trace 的情况下运行
Tracing 接口尽量不影响业务结果
是否启用、采样和保存，由宿主或部署环境决定
```

## 8. 生产环境为什么还要采样和脱敏？

开发时记录全部 Trace 最容易排错。生产流量变大后，全部保留可能太贵，也可能收进不该保存的内容。

最简单的策略是：错误任务全部保留，成功任务随机保留一小部分。但“是否失败”往往要到任务结束才知道，所以系统需要先临时收集，等 Trace 完成后再决定是否保留。这类做法通常叫 Tail Sampling。

如果任务一开始就决定要不要记录，也就是 Head Sampling，就能更早减少成本，却无法保证未来出错的 Trace 一定被选中。

脱敏也不能只盯着名为 `content` 的字段。下面这些位置都可能出现秘密：

- Model Prompt 和 Response；
- Tool Arguments 和 Tool Result；
- HTTP Header、URL Query 和环境变量；
- 文件内容、终端输出和异常堆栈。

安全顺序应该是先筛选、截断和遮盖，再把数据交给 Exporter。已经发送到远端后再修改本地日志，无法收回泄露的数据。

## 9. 哪些代码值得亲手写？

本课的[最小 Trace 练习](../exercises/lesson-09-tracing/README.md)只要求亲手实现 `append_span()`，因为重复 ID、父子关系和追加记录正是这一课的承重部分。

```bash
python -B exercises/lesson-09-tracing/starter.py --checkpoint-a
```

通过后会看到：

```text
trace_id=trace_demo
span_count=3
checkpoint A passed
```

值得亲手验证的是两个失败用例：重复 `span_id` 必须被拒绝，不存在的 `parent_span_id` 也必须被拒绝。

OpenTelemetry Collector、批量发送、重试队列和 Trace UI 不值得在这本书里重新手写。生产项目应使用成熟 SDK 和 Backend。本课自己写一个小字典，只是为了看懂它们在保护什么关系。

下一课会使用这些 Trace 判断 Agent 是否真的变好了。一次运行路径能够被看见之后，Evaluation 才能把相同任务重复执行、比较结果，并阻止旧能力悄悄退化。

## 主动回忆

1. Trace 和 Span 分别回答什么问题？
2. 一个 Trace 为什么没有固定的 Span 数量？
3. `parent_span_id` 解决了什么问题？
4. 同一个 Tool Call 重试时，哪些 ID 保持不变，哪些应该变化？
5. 为什么 HTTP 请求成功不等于 Agent 任务成功？
6. Trace 为什么不能替代 Transcript 和 Ledger？
7. 已经实现 Tracing 的项目为什么仍可能没有本地 Trace 文件？
8. Pi 的 No-op Context 与 OpenClaw 的 OTLP Exporter 体现了哪两种选择？
9. 为什么“错误全留、成功抽样”通常需要等任务结束后再决定？
10. 哪些字段在导出前可能需要脱敏？

<details>
<summary>检查简答</summary>

1. Trace 描述一次端到端任务，Span 描述其中一个步骤。
2. 步骤数量由本次运行实际发生的 Model、Tool、重试和子任务决定。
3. 它把平铺的 Span 接成调用树，说明当前步骤由谁触发或包含。
4. `trace_id` 和 `tool_call_id` 不变；不同尝试使用新的 `execution_id` 和 `span_id`。
5. 请求正常返回只证明调用过程完成，返回内容和业务目标仍可能失败。
6. Transcript 负责模型上下文，Ledger 负责执行与恢复，Trace 负责诊断路径；Trace 不是外部副作用的权威回执。
7. Span 通常经 Exporter 发往 Collector 或远端 Backend，而且许多项目默认关闭这条管道。
8. Pi 让宿主自行选择是否记录和保存；OpenClaw提供配置好即可发送的标准 Exporter。
9. 任务开始时还不知道最终会不会失败；完成后采样才能按结果决定保留。
10. Prompt、Response、Tool 参数与结果、Header、环境变量、文件和终端输出都可能含有秘密。

</details>

## 参考资料

> 开源实现最后核验于 2026-09-04，完整记录见[第 9 课一手资料复核](../research/09-tracing-source-verification.md)。

- [第 9 课最小 Trace 练习](../exercises/lesson-09-tracing/README.md)
- [OpenTelemetry Traces](https://opentelemetry.io/docs/concepts/signals/traces/)
- [Codex OpenTelemetry](https://github.com/openai/codex/blob/8e6a44b428e31f91b21edc97904fcdf4f0931ade/codex-rs/otel/README.md)
- [Codex Rollout Trace](https://github.com/openai/codex/blob/8e6a44b428e31f91b21edc97904fcdf4f0931ade/codex-rs/rollout-trace/README.md)
- [OpenClaw OpenTelemetry](https://github.com/openclaw/openclaw/blob/64da06a78ffa98c5bb425cc79059d992260a4c76/docs/gateway/opentelemetry.md)
- [OpenCode OTLP Exporter](https://github.com/anomalyco/opencode/blob/4b7e19e315cca414121ba1d61523fef74bb3ae8b/packages/core/src/observability/otlp.ts)
- [OpenCode Direct Trace](https://github.com/anomalyco/opencode/blob/4b7e19e315cca414121ba1d61523fef74bb3ae8b/packages/opencode/src/cli/cmd/run/trace.ts)
- [Pi Telemetry](https://github.com/earendil-works/pi/blob/2d41163332c1a6d11c45911a92100fd2a55e4d1a/packages/telemetry/README.md)
- [Pi Agent Telemetry Schema](https://github.com/earendil-works/pi/blob/2d41163332c1a6d11c45911a92100fd2a55e4d1a/packages/agent/docs/telemetry-schema.md)
- [Hermes Langfuse Observability](https://github.com/NousResearch/hermes-agent/blob/63279301bcbdc185c1b07b98a9312eb0c862f26d/website/docs/user-guide/features/built-in-plugins.md#observabilitylangfuse)
