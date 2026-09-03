# 第 7 课一手资料复核：工具执行、幂等与故障恢复

> 核验时间：2026-09-03（Asia/Shanghai）。
>
> 规则：变化中的实现固定到本次核验 Commit。工具状态、消息配对和外部副作用证据分开判断，不把 UI 状态机写成 Exactly Once 保证。

## 本次结论

第 7 课的主线成立：Assistant Tool Call、真实执行尝试和模型可见 Tool Result 是三件事。程序在副作用完成后、Tool Result 持久化前崩溃时，恢复系统必须依靠执行记录和外部证据，不能仅凭 Session 猜测或直接重跑。

旧 Blog 有两处需要在正式章节中收紧：

1. `idempotency_key` 不再直接使用参数 Hash。本书综合实践使用 `工具名:tool_call_id` 标识同一逻辑调用，再用独立的 `arguments_sha256` 防止同一个 Key 被不同参数复用。
2. `write_file` 不再把“相同参数可重复覆盖”写成无条件自动重试。目标文件可能在崩溃后被别人修改。综合实践只在当前 Byte 已等于请求内容时确认“目标状态已满足”；内容不同则保持 `unknown`。

## 当前源码快照

| 项目 | 固定 Commit | 与本章有关的当前实现 |
| --- | --- | --- |
| DeepSeek Harness | [`76fda72`](https://github.com/deepseek-ai/deepseek-harness/commit/76fda729799fe9b3848dbe2c211d4b231032b81e) | 在执行前记录 `tool/call`，经过策略、审批、Guard、执行和结果归一化后，提交单一 `tool/result`；并列调用可以并发执行，但模型历史按原调用顺序看到完整结果。 |
| OpenClaw | [`1fb3e0c`](https://github.com/openclaw/openclaw/commit/1fb3e0ca33847b5827a21cf5cb132d3f90ff49ad) | Incomplete Turn Recovery 会先证明本批 Tool Call 都有匹配 Result，并检查潜在副作用；已经完成的调用不能因缺少可见 Final 而重复执行。 |
| Hermes Agent | [`6327930`](https://github.com/NousResearch/hermes-agent/commit/63279301bcbdc185c1b07b98a9312eb0c862f26d) | 明确维护无副作用工具白名单；未知、插件和 MCP 工具默认视为可能有副作用。文件写入结果只有带可解析成功字段时才被认作已经落地。 |
| OpenCode | [`d2efd81`](https://github.com/anomalyco/opencode/commit/d2efd81fb3e153a51165b8589c4658107002817e) | Session Message 为 Tool 保存 `pending/running/completed/error` 状态和时间。它能展示 Runtime 生命周期，但仅凭这些字段不能证明外部动作恰好发生一次。 |
| Codex | [`6d7f6dc`](https://github.com/openai/codex/commit/6d7f6dcd2285de70a3892d4f05b2a8ff44aa3350) | App Server 的命令执行状态包含 `inProgress/completed/failed/declined`；这是执行协议状态，不应被扩写成通用外部幂等保证。 |
| LangGraph | [`11738d8`](https://github.com/langchain-ai/langgraph/commit/11738d83db4320bb191804342b5c76ae7eca54a0) | Checkpointer 保存 Graph State 与 Pending Writes，恢复失败 Superstep 时可以避免重跑已经完成的节点；外部副作用是否可安全重试仍取决于 Tool 或下游系统。 |

## 固定源码

- [DeepSeek Harness Tool Execution Pipeline](https://github.com/deepseek-ai/deepseek-harness/blob/76fda729799fe9b3848dbe2c211d4b231032b81e/docs/tool-execution-pipeline.zh.md)
- [DeepSeek Harness Parallel Tool Execution](https://github.com/deepseek-ai/deepseek-harness/blob/76fda729799fe9b3848dbe2c211d4b231032b81e/.agents/notes/implemented/feature/2026-07-10-parallel-tool-call-execution.zh.md)
- [OpenClaw Incomplete Turn Recovery](https://github.com/openclaw/openclaw/blob/1fb3e0ca33847b5827a21cf5cb132d3f90ff49ad/src/agents/embedded-agent-runner/run/incomplete-turn-recovery.ts)
- [Hermes Tool Result Classification](https://github.com/NousResearch/hermes-agent/blob/63279301bcbdc185c1b07b98a9312eb0c862f26d/agent/tool_result_classification.py)
- [OpenCode Session Tool State](https://github.com/anomalyco/opencode/blob/d2efd81fb3e153a51165b8589c4658107002817e/packages/schema/src/session-message.ts)
- [Codex Command Execution Status](https://github.com/openai/codex/blob/6d7f6dcd2285de70a3892d4f05b2a8ff44aa3350/codex-rs/app-server-protocol/schema/typescript/v2/CommandExecutionStatus.ts)
- [LangGraph Checkpoint and Pending Writes](https://github.com/langchain-ai/langgraph/blob/11738d83db4320bb191804342b5c76ae7eca54a0/libs/checkpoint/README.md)

## 不能从这些源码推出什么

- Tool 状态变成 `completed`，不自动证明支付、邮件或 Shell 副作用只发生一次。
- Checkpoint 能恢复工作流状态，不自动提供外部系统的幂等键或权威回执。
- 参数 Hash 能发现内容变化，不会主动阻止重复执行。
- 本地 `write_file` 当前内容符合预期，只证明目标状态已满足，不能证明某个旧进程实际写了几次。
