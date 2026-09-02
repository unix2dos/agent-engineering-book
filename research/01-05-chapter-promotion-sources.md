# 第 1～5 课一手资料复核

> 用途：在 Blog 第 1～5 课晋升为书籍章节前，核验会变化的协议、SDK 与开源实现。
>
> 核验快照：2026-09-03（Asia/Shanghai）。
>
> 证据规则：协议与产品行为优先采用官方文档；实现细节采用官方 GitHub 仓库的固定 Tag 或 Commit；论文使用固定版本。

## 1. 审计结论

五篇文章的主线可以保留：Agent 与 Workflow 的区别在于谁决定下一步；Harness 负责把 Model、Tool 和 Environment 接成受控循环；Tool Call 是请求而非执行证明；持久化数据只有经过 Harness 选择才会进入 Context；长 Session 需要把完整 Transcript 与受预算控制的 Prompt View 分开。

晋升时修正四处：

1. 第 3 课的 `openai-python v3.5.0` 更新为当前 Release `v3.7.0`。教学代码继续使用 OpenAI-compatible Chat Completions，以便直接观察 `assistant.tool_calls → role=tool`；同时说明 OpenAI 当前官方指南主要使用 Responses API 的 `function_call → function_call_output`。
2. 第 2 课不再罗列一长串可能变化的 Anthropic Stop Reason，只保留稳定判断：只有接受的正常结束状态才能成为 Final；工具调用、截断、暂停与拒绝需要分别处理。
3. 第 5 课使用最新固定源码再次确认：OpenClaw 当前普通 Session 与 Transcript 热路径是 SQLite；旧 JSONL 是迁移或归档材料，Incognito Session 才只在内存里。
4. Blog 中指向旧 `unix2dos/lai` 的代码链接全部改为公开的 `unix2dos/agent-engineering-book`，书籍内部同时链接对应综合实践。

没有发现需要合并章节的理由。第 1 课回答“什么任务值得用 Agent”，第 2 课回答“一次调用中四个部分怎样分工”，第 3 课让最小循环运行；第 4 课区分 Context、Session、Checkpoint 与 Memory，第 5 课再进入 Transcript、Compaction 与 Prompt Cache。每篇可以独立成立，也能按顺序递进。

## 2. 第 1～3 课：Agent Runtime 与 Tool Calling

| 来源 | 固定状态 | 支撑的正文判断 |
| --- | --- | --- |
| [Anthropic：Building Effective AI Agents](https://www.anthropic.com/research/building-effective-agents) | 2024-12 历史文章；页面已提示工具生态后来发生变化 | Workflow 由预设代码路径编排；Agent 让模型动态决定过程和工具使用。这个架构区分仍可引用，但不把文章里的产品列表写成当前状态。 |
| [Anthropic：How tool use works](https://platform.claude.com/docs/en/agents-and-tools/tool-use/how-tool-use-works) | 2026-09-02 页面快照 | Model 产生结构化请求；客户端工具由应用执行并回传 `tool_result`；服务端工具由 Anthropic 执行。客户端工具需要应用驱动循环。 |
| [Anthropic Go SDK v1.69.0 工具示例](https://github.com/anthropics/anthropic-sdk-go/blob/v1.69.0/examples/tools/main.go) | Release `v1.69.0`，2026-09-01 | 可运行的手写工具调用示例。 |
| [Anthropic Go SDK v1.69.0 Tool Runner](https://github.com/anthropics/anthropic-sdk-go/blob/v1.69.0/examples/tool-runner/main.go) | Release `v1.69.0` | SDK 可以封装循环，但不改变 Model 与执行器的责任边界。 |
| [OpenAI：Function calling](https://developers.openai.com/api/docs/guides/function-calling) | 2026-09-02 页面快照 | 当前官方五步流仍是：声明工具、收到 Tool Call、应用执行、回传输出、得到 Final 或更多调用。Responses 使用 `function_call_output`。 |
| [openai-python v3.7.0](https://github.com/openai/openai-python/releases/tag/v3.7.0) | Release `v3.7.0`，2026-09-02 | 本书示例使用的官方 Python SDK 当前版本锚点。 |
| [Chat Completions Tool Call 类型](https://github.com/openai/openai-python/blob/v3.7.0/src/openai/types/chat/chat_completion_message_tool_call.py) | Tag `v3.7.0` | OpenAI-compatible Chat Completions 中 Assistant Tool Call 的 SDK 类型仍存在。 |
| [Chat Completions Tool Message 类型](https://github.com/openai/openai-python/blob/v3.7.0/src/openai/types/chat/chat_completion_tool_message_param.py) | Tag `v3.7.0` | `role=tool` Message 使用 `tool_call_id` 回答对应调用。 |
| [OpenAI Agents SDK v0.22.0 Runner](https://github.com/openai/openai-agents-python/blob/v0.22.0/docs/running_agents.md) | Release `v0.22.0`，2026-08-19 | Agent SDK 可以封装 Loop、Tool、Guardrail、Handoff 和 Session；直接使用模型 API 时这些控制仍由应用负责。 |
| [OpenCode Session Processor](https://github.com/anomalyco/opencode/blob/50efc055de282e0e54a87ccebb8e2054cc45efd2/packages/opencode/src/session/processor.ts) | Commit `50efc05`，2026-09-02 | Coding Agent Runtime 会把模型输出、工具调用与工具结果组织成持续 Session。 |
| [OpenCode Tool Registry](https://github.com/anomalyco/opencode/blob/50efc055de282e0e54a87ccebb8e2054cc45efd2/packages/opencode/src/tool/registry.ts) | Commit `50efc05` | Tool 的注册、发现和执行属于 Runtime，不是 Model 自己获得本地函数。 |
| [OpenCode Permission Evaluation](https://github.com/anomalyco/opencode/blob/50efc055de282e0e54a87ccebb8e2054cc45efd2/packages/opencode/src/permission/evaluate.ts) | Commit `50efc05` | 能生成 Tool Call 不等于本次调用已被策略允许。 |

固定论文仍使用：[ReAct v3](https://arxiv.org/abs/2210.03629v3)、[Self-Refine v2](https://arxiv.org/abs/2303.17651v2)、[Reflexion v4](https://arxiv.org/abs/2303.11366v4)。

## 3. 第 4～5 课：Context、Session 与 Compaction

| 项目 | 固定状态 | 当前实现结论 |
| --- | --- | --- |
| [Pi](https://github.com/earendil-works/pi/commit/e266507b606b9552fa277252644054afd4384b11) | HEAD `e266507`，2026-09-02；Release `v0.84.4` | Coding Agent Session 默认使用 JSONL；Entry 通过 `id/parentId` 组成树；Compaction 保存 Summary 与保留边界，新版 Harness Entry 也可直接保存 `retainedTail`；Core 提供可选 SQLite Backend。 |
| [Pi Session Format](https://github.com/earendil-works/pi/blob/e266507b606b9552fa277252644054afd4384b11/packages/coding-agent/docs/session-format.md) | 固定 Commit | Session Header 与 Message、Compaction 等 Entry 的实际字段。 |
| [Pi Compaction](https://github.com/earendil-works/pi/blob/e266507b606b9552fa277252644054afd4384b11/packages/coding-agent/docs/compaction.md) | 固定 Commit | 在达到 `contextWindow - reserveTokens` 前触发；保留最近内容；重复压缩继承旧 Summary；Split Turn 不在 Tool Result 上切。 |
| [OpenClaw](https://github.com/openclaw/openclaw/commit/ad3268ecccbc7758878662b31adcd72475343d3e) | HEAD `ad3268e`，2026-09-02；Release `v2026.8.2` | 普通 Session 行和 Transcript 默认保存在每 Agent 一个 SQLite；旧 `sessions.json` 与 JSONL 只作迁移输入或归档；Incognito Session 在内存中。 |
| [OpenClaw Session](https://github.com/openclaw/openclaw/blob/ad3268ecccbc7758878662b31adcd72475343d3e/docs/concepts/session.md) | 固定 Commit | SQLite 路径、Incognito 边界与旧数据迁移。 |
| [OpenClaw Pruning](https://github.com/openclaw/openclaw/blob/ad3268ecccbc7758878662b31adcd72475343d3e/docs/concepts/session-pruning.md) | 固定 Commit | Pruning 只改请求前的旧 Tool Result 视图，不改磁盘 Transcript；Compaction 才保存 Summary。 |
| [OpenClaw Compaction](https://github.com/openclaw/openclaw/blob/ad3268ecccbc7758878662b31adcd72475343d3e/docs/concepts/compaction.md) | 固定 Commit | Compaction 保留 Tool Call/Result 配对，失败时不写恢复点；普通历史仍留在磁盘。 |
| [OpenClaw Memory](https://github.com/openclaw/openclaw/blob/ad3268ecccbc7758878662b31adcd72475343d3e/docs/concepts/memory.md) | 固定 Commit | Compaction 前的 Memory Flush 默认开启；长期 Memory 是筛选后的稳定事实，不是原始 Transcript。 |
| [Hermes](https://github.com/NousResearch/hermes-agent/commit/afc3d9d34c9c3b01fa2e1332d2c66a5b5fabae3f) | HEAD `afc3d9d`，2026-09-02；Release `v2026.8.31` | 主状态库是 `~/.hermes/state.db` SQLite；会话与消息支持查询和全文检索。 |
| [Hermes Session Storage](https://github.com/NousResearch/hermes-agent/blob/afc3d9d34c9c3b01fa2e1332d2c66a5b5fabae3f/website/docs/developer-guide/session-storage.md) | 固定 Commit | Session、Message、FTS 与归档状态的当前结构。 |
| [Hermes Micro-compaction](https://github.com/NousResearch/hermes-agent/blob/afc3d9d34c9c3b01fa2e1332d2c66a5b5fabae3f/docs/micro-compaction.md) | 固定 Commit | Micro-compaction 默认关闭；逐轮滚动摘要会更早丢失细节并反复破坏 Prompt Cache 前缀，是否开启取决于占用、延迟和缓存折扣。 |
| [OpenAI Conversation state](https://developers.openai.com/api/docs/guides/conversation-state) | 2026-09-02 页面快照 | Provider 可以通过 Response 或 Conversation 标识承载服务端状态，但应用仍需决定自己的持久化、检索和业务恢复边界。 |
| [OpenAI Compaction](https://developers.openai.com/api/docs/guides/compaction) | 2026-09-02 页面快照 | OpenAI 提供服务端 Compaction；本书的 JSONL 示例仍用于学习客户端 Transcript 与 Prompt View 的职责。 |
| [Anthropic Compaction](https://platform.claude.com/docs/en/build-with-claude/compaction) | 2026-09-02 页面快照 | Anthropic 也提供服务端 Compaction Block；后续请求必须带回该 Block，API 才会从摘要继续。它不等同于本地完整 Transcript。 |

## 4. 书籍正文的边界

- 第 1～5 课解释可迁移机制，不把任何一个 Provider 的当前字段写成 Agent 的统一标准。
- 第 2 课并排展示 Anthropic 与 OpenAI-compatible 两种 Tool Result 形状，但每个示例内部只使用一套协议。
- 第 3 课保留 Chat Completions 教学实现，因为它能直接显示四条 Message；同时链接当前 Responses 官方五步流，不宣称 Chat Completions 是唯一或最新的原生接口。
- 第 4 课的本地 JSON/JSONL 只是教学存储，不把文件扩展名当成 Session、Checkpoint 或 Memory 的定义。
- 第 5 课把 Pi、OpenClaw、Hermes 作为不同实现对照；正文只保留对当前最小 Agent 有迁移价值的差异，不逐项复制项目功能。
