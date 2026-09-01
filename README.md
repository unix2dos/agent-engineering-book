# Agent 工程实践：从工具循环到可靠系统

📖 **在线阅读**：[https://levon.gitbook.io/agent-engineering/](https://levon.gitbook.io/agent-engineering/)

这是一本写给 Agent 工程初学者的开源书。它不从框架 API 开始，而是沿着一个问题往下走：语言模型怎样从“只能生成文本”，逐步变成能够调用工具、保存状态、恢复故障并受到安全边界约束的行动系统？

书中的结论来自三类证据：官方文档与开源源码、可以运行的最小代码、主动回忆中真实暴露的理解缺口。目标不是记住一批术语，而是能预测一次 Agent 运行会发生什么，并在出错时找到责任层。

## 适合谁

你需要会基础 Python、Git 和命令行，但不需要预先理解 Tool Calling、Context、JSONL、数据库、幂等、Trace 或 Sandbox。本书会在这些概念第一次真正有用时再引入它们。

## 怎么学

每一课都区分四类学习任务：

- **必须亲写**：承载本课核心机制的最小代码，需要自己实现一次。
- **允许 AI**：SDK 初始化、类型、配置和重复样板，可以让 AI 生成初稿。
- **必须验证**：涉及副作用、状态恢复、上下文和安全边界时，需要运行或制造故障，不能只读代码。
- **只需读懂**：数据库、容器、microVM 等成熟基础设施，只学习职责与边界，不重复实现。

一篇 Blog 文章只有经过“主动回忆 → 当前源码核验 → 实践证据 → 小白审阅”，才会晋升为这里的正式章节。

## 阅读路线

| 阶段 | 课程 | 状态 |
|---|---|---|
| 地图 | [第 0 课：Agent 工程史](chapters/00-agent-engineering-history.md) | 已晋升 |
| 最小运行时 | 第 1～3 课：Agent、Harness 与 Tool Calling Loop | 待逐章晋升 |
| 上下文与状态 | 第 4～6 课：Context、Memory 与存储 | 待逐章晋升 |
| 可靠与安全 | 第 7～8 课：故障恢复、审批、权限与 Sandbox | 待逐章晋升 |
| 改进闭环 | 第 9～11 课：Trace、Evaluation 与回归门禁 | 计划学习 |

完整目录见 [SUMMARY.md](SUMMARY.md)。

## 核心源码参考

本书不会把所有热门框架都讲一遍。以下八个项目组成长期参考集：

- [Pi](https://github.com/earendil-works/pi)、[OpenClaw](https://github.com/openclaw/openclaw)、[Hermes](https://github.com/NousResearch/hermes-agent) 与 [Codex](https://github.com/openai/codex)：观察 Coding Agent 的 Runtime、Context、Tool 与安全边界；
- [OpenAI Agents SDK](https://github.com/openai/openai-agents-python)：观察通用 Agent Loop、Session、Handoff、Guardrail 与 Trace；
- [LangGraph](https://github.com/langchain-ai/langgraph)：观察状态图、Checkpoint、长任务恢复与 Human-in-the-loop；
- [Phoenix](https://github.com/Arize-ai/phoenix)：观察 Trace、Span、Evaluation 与运行诊断；
- [Inspect AI](https://github.com/UKGovernmentBEIS/inspect_ai)：观察 Dataset、Solver、Scorer 与评估日志。

其他项目只在它们能回答某个章节的独特问题时选读。

## 配套代码

现有教学代码暂时保留原路径，避免已经发布的文章链接失效：

- [`01-agent.py`](01-agent.py)：最小 Tool Calling Loop；
- [`02_rember.py`](02_rember.py)：Session、Checkpoint 与长期记忆；
- [`03_context.py`](03_context.py)：JSONL Transcript、Compaction 与 Prompt View；
- [`04_tool_reliability.py`](04_tool_reliability.py)：Execution Ledger、幂等与故障恢复。

这些文件是教学实现，不宣称覆盖生产系统的并发、分布式事务、租户隔离和高可用要求。

## 内容归属

本仓库保存唯一持续维护的完整章节。已经发布的 Blog 文章作为历史快照和入口保留；GitBook 接入后只负责展示本仓库内容，不成为第二份写作来源。
