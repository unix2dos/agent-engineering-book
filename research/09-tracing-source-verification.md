# 第 9 课一手资料复核：Trace、Span 与 Agent 可观测性

> 核验时间：2026-09-04（Asia/Shanghai）。
>
> 核验方式：使用 GitHub CLI 读取官方仓库当前 HEAD、最新正式版本及源码文档；正文链接固定到本次 Commit。`Session`、普通日志、遥测事件和 Span 分开判断，不因文件名含有 `trace` 就认定它实现了完整 OpenTelemetry。

## 本次结论

Tracing 不是 Agent 能运行的必要组成。它观察 Model、Harness、Tool 和运行环境已经发生的工作，不参与 Agent Loop 的最低成立条件。

当任务包含多轮调用、重试、并发、远程执行或生产故障时，Tracing 又会成为可诊断和可运营的重要能力。当前核验的几个项目普遍让 Tracing 默认关闭或使用 No-op；这能避免在用户尚未选择采集范围和存储位置时就发送运行内容，也把成本决定留给部署方。

上一轮“Pi 与 Hermes 没有 Tracing”的判断不成立。重新检查当前源码后：Pi 已提供 Vendor-neutral Telemetry Contract、Agent Span Schema 和部分 Harness 埋点，但默认没有 Exporter；Hermes 已提供可选的 Langfuse 插件，能够记录 Turn、LLM Call 和 Tool Call。

## 当前源码快照

| 项目 | 固定 Commit / Version | 本章核验到的实现 |
| --- | --- | --- |
| Codex | [`8e6a44b`](https://github.com/openai/codex/commit/8e6a44b428e31f91b21edc97904fcdf4f0931ade) | `codex-otel` 支持日志、Trace、指标和 W3C Trace Context；独立的 Rollout Trace 仅在 `CODEX_ROLLOUT_TRACE_ROOT` 设置后写本地 Bundle，并明确声明它不是上传遥测。 |
| OpenClaw | [`64da06a`](https://github.com/openclaw/openclaw/commit/64da06a78ffa98c5bb425cc79059d992260a4c76) | 可选 `diagnostics-otel` 插件通过 OTLP/HTTP 导出 Model、Harness、Skill、Tool、Exec、Context 和 Tool Loop Span；Diagnostics、插件与 OTel 配置必须同时开启。 |
| OpenCode | [`v1.18.27`](https://github.com/anomalyco/opencode/releases/tag/v1.18.27)，源码 Commit [`4b7e19e`](https://github.com/anomalyco/opencode/commit/4b7e19e315cca414121ba1d61523fef74bb3ae8b) | `OTEL_EXPORTER_OTLP_ENDPOINT` 激活 OTLP Trace Exporter；`experimental.openTelemetry` 控制 AI SDK Model Span。另有 `OPENCODE_DIRECT_TRACE=1` 开启的开发用本地 JSONL。 |
| Pi | [`2d41163`](https://github.com/earendil-works/pi/commit/2d41163332c1a6d11c45911a92100fd2a55e4d1a) | `pi-telemetry` 定义 Span、事件、属性、状态、No-op 和 In-memory Adapter；Agent 定义 `pi.ai.request`、`pi.harness.run/turn/step/tool` 等 Schema。包本身没有 Exporter，部分 Runtime Span 与跨进程传播仍在实现中。 |
| Hermes Agent | [`6327930`](https://github.com/NousResearch/hermes-agent/commit/63279301bcbdc185c1b07b98a9312eb0c862f26d) | 默认关闭的 `observability/langfuse` 插件记录 Turn、LLM 与 Tool，并发送到 Langfuse。另一套 OTLP Exporter 主要观察 Gateway Health、Diagnostic 与 Cron Event，不等于完整 Agent Trace。 |

## 为什么通常找不到本地文件

| 实现 | 默认去向 |
| --- | --- |
| Codex OTLP | 配置的 OTLP Backend |
| Codex Rollout Trace | `CODEX_ROLLOUT_TRACE_ROOT` 指定的本地目录 |
| OpenClaw | 配置的 OTLP Collector；stdout JSONL 只用于日志分支 |
| OpenCode OTLP | `${OTEL_EXPORTER_OTLP_ENDPOINT}/v1/traces` |
| OpenCode Direct Trace | `~/.local/share/opencode/log/direct/*.jsonl` |
| Pi | 默认 No-op；In-memory Adapter 不落盘；宿主 Adapter 决定最终位置 |
| Hermes | Langfuse Cloud 或 Self-hosted Langfuse |

文件不存在不能单独证明项目没有 Tracing。先找埋点接口，再找 Processor、Exporter 和 Backend；四者中只有最后一个决定实际存储位置。

## 需要保持的边界

1. Span 成功表示观测范围内的操作正常结束，不自动表示业务目标成功。
2. Trace 能关联 `tool_call_id` 与 `execution_id`，但不能证明外部副作用只发生一次。
3. Session JSONL 保存了运行事件，不自动等于标准 Trace；必须检查是否存在共同身份、父子关系、生命周期和 Exporter。
4. 本地调试 Trace 与远程 OpenTelemetry 可以同时存在，但用途、Schema 和隐私边界不同。
5. 默认关闭或 No-op 是部署选择，不是 Tracing 毫无价值的证据。

## 固定源码

- [Codex OpenTelemetry README](https://github.com/openai/codex/blob/8e6a44b428e31f91b21edc97904fcdf4f0931ade/codex-rs/otel/README.md)
- [Codex Rollout Trace README](https://github.com/openai/codex/blob/8e6a44b428e31f91b21edc97904fcdf4f0931ade/codex-rs/rollout-trace/README.md)
- [OpenClaw OpenTelemetry](https://github.com/openclaw/openclaw/blob/64da06a78ffa98c5bb425cc79059d992260a4c76/docs/gateway/opentelemetry.md)
- [OpenCode OTLP Exporter](https://github.com/anomalyco/opencode/blob/4b7e19e315cca414121ba1d61523fef74bb3ae8b/packages/core/src/observability/otlp.ts)
- [OpenCode Model Telemetry](https://github.com/anomalyco/opencode/blob/4b7e19e315cca414121ba1d61523fef74bb3ae8b/packages/opencode/src/session/llm.ts)
- [OpenCode Direct Trace](https://github.com/anomalyco/opencode/blob/4b7e19e315cca414121ba1d61523fef74bb3ae8b/packages/opencode/src/cli/cmd/run/trace.ts)
- [Pi Telemetry Package](https://github.com/earendil-works/pi/blob/2d41163332c1a6d11c45911a92100fd2a55e4d1a/packages/telemetry/README.md)
- [Pi Agent Telemetry Schema](https://github.com/earendil-works/pi/blob/2d41163332c1a6d11c45911a92100fd2a55e4d1a/packages/agent/docs/telemetry-schema.md)
- [Pi Telemetry Design Notes](https://github.com/earendil-works/pi/blob/2d41163332c1a6d11c45911a92100fd2a55e4d1a/packages/agent/docs/telemetry.md)
- [Hermes Langfuse Observability](https://github.com/NousResearch/hermes-agent/blob/63279301bcbdc185c1b07b98a9312eb0c862f26d/website/docs/user-guide/features/built-in-plugins.md#observabilitylangfuse)
- [Hermes Gateway OTLP Exporter](https://github.com/NousResearch/hermes-agent/blob/63279301bcbdc185c1b07b98a9312eb0c862f26d/agent/monitoring/otlp_exporter.py)
