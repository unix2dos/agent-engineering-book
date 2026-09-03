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
| 地图 | [第 0 课：Agent 工程史](chapters/00-Agent工程史.md) | 已晋升 |
| 最小运行时 | 第 1～3 课：Agent、Harness 与 Tool Calling Loop | 已晋升 |
| 上下文与状态 | 第 4～5 课：Context、Memory 与 Compaction | 已晋升 |
| 存储选择 | 第 6 课：JSONL、SQLite 与数据库 | 待完成实践后晋升 |
| 可靠与安全 | 第 7～8 课：故障恢复、审批、权限与 Sandbox | 待逐章晋升 |
| 改进闭环 | 第 9～11 课：Trace、Evaluation 与回归门禁 | 计划学习 |

完整目录见 [SUMMARY.md](SUMMARY.md)。

## 核心源码参考

本书不会把所有热门框架都讲一遍。以下十一个开源项目组成长期源码参考集，并按它们最适合回答的问题分为三组：

- **Coding Agent Runtime**：[Pi](https://github.com/earendil-works/pi)、[OpenClaw](https://github.com/openclaw/openclaw)、[Hermes](https://github.com/NousResearch/hermes-agent)、[Codex](https://github.com/openai/codex)、[OpenCode](https://github.com/anomalyco/opencode) 与 [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness)。它们用于观察 Agent Loop、Session、Context、Tool、权限和安全边界。OpenCode 还适合研究多模型适配、工具注册与输出截断；DeepSeek Harness 适合研究插件化 Runtime、Session Controller 与上下文来源追踪，但它仍处于 Developer Preview，书中只针对固定版本学习，不把当前接口写成稳定规范；
- **Agent 框架与接口**：[OpenAI Agents SDK](https://github.com/openai/openai-agents-python)、[Claude Agent SDK Python](https://github.com/anthropics/claude-agent-sdk-python) 与 [LangGraph](https://github.com/langchain-ai/langgraph)。它们用于观察通用 Agent Loop、Session、Handoff、Guardrail、状态图与长任务恢复。Claude Agent SDK Python 通过子进程调用捆绑的 Claude Code CLI，开放了消息解析、CLI Transport、MCP Bridge 与 Session Store，但不包含 Claude Code 核心 Runtime；
- **可观测性与评估**：[Phoenix](https://github.com/Arize-ai/phoenix) 与 [Inspect AI](https://github.com/UKGovernmentBEIS/inspect_ai)。它们用于观察 Trace、Span、Dataset、Solver、Scorer、Evaluation 与评估日志。

其他项目只在它们能回答某个章节的独特问题时选读。

## 产品行为参考

[Claude Code](https://github.com/anthropics/claude-code) 是重要的 Coding Agent 参考，但其核心 Runtime 没有开源；官方仓库使用 [商业条款许可证](https://github.com/anthropics/claude-code/blob/main/LICENSE.md)。本书通过官方文档、设置、插件与示例研究它的权限、Hooks、Sandbox、Memory、Subagent 和 Workflow，不把这些外部行为描述成已经读过的核心源码。

## 运行配置

在线示例只读取通用的 OpenAI-compatible 环境变量：

```bash
export OPENAI_API_KEY="your-api-key"
export OPENAI_MODEL="your-model"

# 使用第三方兼容端点时再设置；OpenAI 官方端点可以省略。
export OPENAI_BASE_URL="https://provider.example/v1"
```

仓库不会读取 OpenCode、Claude Code 或其他 Provider 的本地登录文件。你可以在 Shell、密码管理器、CI 或部署平台中把自己的凭据映射到这三个变量。

## 配套代码

教学代码按对应课程放在 `examples/`：

- [`lesson_03_tool_calling_loop.py`](examples/lesson_03_tool_calling_loop.py)：最小 Tool Calling Loop；
- [`lesson_04_session_memory.py`](examples/lesson_04_session_memory.py)：Session、Checkpoint 与长期记忆；
- [`lesson_05_context_compaction.py`](examples/lesson_05_context_compaction.py)：JSONL Transcript、Compaction 与 Prompt View；
- [`lesson_07_tool_reliability.py`](examples/lesson_07_tool_reliability.py)：Execution Ledger、幂等与故障恢复。

这些文件是教学实现，不宣称覆盖生产系统的并发、分布式事务、租户隔离和高可用要求。

## 内容归属

本仓库保存唯一持续维护的完整章节。已经发布的 Blog 文章作为历史快照和入口保留；GitBook 接入后只负责展示本仓库内容，不成为第二份写作来源。
