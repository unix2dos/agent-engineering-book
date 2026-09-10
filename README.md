# Agent 工程实践：从工具循环到可靠系统

假设 Agent 已经发出一封“系统维护完毕”的通知，却在保存成功记录前崩溃。重启后，程序把没有回执当成没有执行，又发了一遍。同一项任务，客户收到了双份报喜。

这本书从最小工具调用循环出发，逐步搭起一个能读写工作区文件的 Agent。你会学习怎样保存任务进度、控制执行权限、处理崩溃，以及用实际结果判断一次改动有没有让系统变好。

## 适合谁，怎样学

适合会一点 Python、Git 和命令行，想理解 Agent 原理并亲手搭建系统的开发者。重点是 Agent Runtime / AI Systems：模型之外的程序怎样组织和控制一次运行，不以模型训练为主线。

先看具体问题、短代码和输出，再理解术语。想练手时，运行配套实验，故意制造截断、重启或越界访问；最后合上代码，试着解释为什么会出现这个结果。各课的机制会接进同一个工作区 Agent。

## 源码依据

本书结合以下项目的源码与官方资料，核对教学实现中的关键选择：

- **运行时**：[Pi](https://github.com/earendil-works/pi)、[OpenClaw](https://github.com/openclaw/openclaw)、[Hermes](https://github.com/NousResearch/hermes-agent)、[Codex](https://github.com/openai/codex)、[OpenCode](https://github.com/anomalyco/opencode)、[DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness)——看真实 Agent 怎样组织运行、管理状态和限制工具。
- **框架与接口**：[OpenAI Agents SDK](https://github.com/openai/openai-agents-python)、[Claude Agent SDK Python](https://github.com/anthropics/claude-agent-sdk-python)、[LangGraph](https://github.com/langchain-ai/langgraph)——看任务怎样编排、转交和恢复。
- **观测与评估**：[Phoenix](https://github.com/Arize-ai/phoenix)、[Inspect AI](https://github.com/UKGovernmentBEIS/inspect_ai)——看怎样记录运行过程、检验任务结果。

实现结论以各章核验的版本为准。对 [Claude Code](https://github.com/anthropics/claude-code)，本书讨论官方文档和可观察的产品行为，不把这些材料或 SDK 源码当成核心运行时的实现。链接供追溯，理解正文不要求同时打开仓库。

## 你会逐步做出什么

| 课程 | 要解决的问题 |
|---|---|
| 第 1～3 课：判断与行动 | 什么时候需要 Agent？怎样把模型申请、工具执行和最终回答接成一个循环？ |
| 第 4～7 课：状态与控制 | 重启后怎样继续？历史太长给模型看什么？执行结果不明时怎么办？工具能碰哪些文件？ |
| 第 8～9 课：观测与评估 | 运行卡在哪一步？换了模型或代码，怎样判断变好还是变坏？ |
| [第 10 课：编排与长任务](chapters/10-Agent编排.md) | 哪些步骤应由程序固定？怎样交接任务、保留进度并控制总预算？ |

后续计划在同一项目上继续处理并发、限流与生产运行。

## 从哪里开始

- 第一次系统学习，从[第 1 课：Agent 基础](chapters/01-Agent基础.md)开始。
- 已理解基本概念，想先看代码，从[第 3 课：工具调用循环](chapters/03-工具调用循环.md)开始。
- 想了解这些工程问题怎样出现，选读[第 0 课：Agent 工程史](chapters/00-Agent工程史.md)。

[在线阅读](https://levon.gitbook.io/agent-engineering/) · [完整目录](SUMMARY.md)

## 配套实践

- [最小工具循环](examples/lesson_03_tool_calling_loop.py)：运行一个完整的调用与回传过程。
- [综合实践](exercises/phase-1-capstone/README.md)：把文件工具、会话记录和故障恢复接成一个小系统。
- [工作流实践](exercises/lesson-10-orchestration/README.md)：复用现有 Agent，接上程序验收、有限次修复和共享预算。
- 按需练习：[SQLite 存储](exercises/session-storage-sqlite/README.md)、[安全边界](exercises/lesson-07-safety/README.md)、[运行追踪](exercises/lesson-08-tracing/README.md)、[任务评估](exercises/lesson-09-evaluation/README.md)。

配套说明包含配置、完整代码和验收步骤。这些是教学实现；通过练习不等于已经满足生产系统的并发、隔离和高可用要求。
