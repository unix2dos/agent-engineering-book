# Agent 工程实践：从工具循环到可靠系统

订单接口返回 500。你希望助手自己查日志、读源码，指出哪一行出了问题，以及判断依据是什么。它说“正在检查”还不够，程序得真的把材料取回来。

本书从这个 Python 排查助手出发，逐步解释一次 Agent 运行：模型怎样申请工具，程序怎样保存进度、限制操作，又怎样判断结果是否合格。后面再加入受限写入与修复——文件改错了要返工，回执丢了不能盲目重做，预算用完就停止。

## 适合谁，怎样学

适合会一点 Python、Git 和命令行，初学 Agent、想理解原理并动手搭建系统的开发者。重点是 **Agent Runtime / AI Systems**：模型之外的程序怎样组织和控制一次运行，不以模型训练为主线。

先看具体问题、关键代码和输出，再理解术语。运行实验时，每次只改一个条件：换一个订单号、缩小请求预算，或模拟一次中断。先猜结果，再运行核对，最后合上代码复述“谁做了什么、为什么这样继续或停止”。这些解释也能成为技术讨论和面试中的具体例子。

正文保留理解机制所需的过程与结果；完整脚手架和配置放在配套材料中，不要求一边读书、一边打开所有仓库。

## 源码与验证依据

本书结合以下项目的源码与官方资料，核对关键设计：

- **运行时**：[Pi](https://github.com/earendil-works/pi)、[OpenClaw](https://github.com/openclaw/openclaw)、[Hermes](https://github.com/NousResearch/hermes-agent)、[Codex](https://github.com/openai/codex)、[OpenCode](https://github.com/anomalyco/opencode)、[DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness)——看运行组织、状态管理和工具边界。
- **框架与接口**：[OpenAI Agents SDK](https://github.com/openai/openai-agents-python)、[Claude Agent SDK Python](https://github.com/anthropics/claude-agent-sdk-python)、[LangChain](https://docs.langchain.com/oss/python/langchain/overview)、[LangGraph](https://github.com/langchain-ai/langgraph)——看现成循环、编排、交接与恢复。
- **观测与评估**：[Phoenix](https://github.com/Arize-ai/phoenix)、[Inspect AI](https://github.com/UKGovernmentBEIS/inspect_ai)——看怎样记录运行、检验任务结果。

实现结论以各章核验的版本为准。对 [Claude Code](https://github.com/anthropics/claude-code)，本书讨论官方资料和可观察行为，不把产品表现或公开 SDK 当作核心运行时的源码证据。

配套实验也区分证据：预设模型回复用于反复检查程序分支；真实模型实验用于观察实际表现。文件修改成功、完整任务结束、长期稳定可靠，是不同层次的结论。

## 你会逐步掌握什么

| 课程 | 可以看见并解释的过程 |
| --- | --- |
| 第 1～3 课：判断与行动 | 助手申请读日志、读源码，程序回传证据，最后给出诊断。 |
| 第 4～5 课：状态与上下文 | 保存会话记录，恢复已知状态，按本轮需要组装模型输入。 |
| 第 6～7 课：恢复与权限 | 写入后丢失回执时先核对证据；允许的访问能成功，禁止的访问被拒绝。 |
| 第 8～9 课：观测与评估 | 定位等待发生在哪一步，再用任务产物和运行记录比较不同版本。 |
| 第 10 课：编排与长任务 | 修改后由程序验收，失败反馈进入下一轮，达到上限时停止。 |

综合实践将文件工具、会话和故障恢复接成一个 Workspace Agent，工作流再复用它。Tracing、交接与子任务恢复等部分保留为独立实验，帮助看清机制；它们尚未全部集成为一个后台系统。

## 从哪里开始

- 第一次系统学习，从[第 1 课：Agent 基础](../../chapters/01-Agent基础.md)开始。
- 已理解基本概念，想先看运行过程，从[第 3 课：工具调用循环](../../chapters/03-工具调用循环.md)开始。
- 想了解这些工程问题怎样出现，选读[第 0 课：Agent 工程史](../../chapters/00-Agent工程史.md)。

[在线阅读](https://levon.gitbook.io/agent-engineering/) · [完整目录](../../SUMMARY.md)

## 配套实践

- [只读排查实验](../../chapters/03-工具调用循环.md)：复现订单接口 500，观察日志与源码怎样进入工具循环；该模式不需要模型 Key。
- [综合实践](../../exercises/phase-1-capstone/README.md)：连接文件工具、会话记录、执行账本与故障恢复。
- [工作流实践](../../exercises/lesson-10-orchestration/README.md)：接上程序验收、有限次修复和共享预算。
- 按需练习：[独立的最小工具循环](../../examples/lesson_03_tool_calling_loop.py)、[SQLite 存储](../../exercises/session-storage-sqlite/README.md)、[安全边界](../../exercises/lesson-07-safety/README.md)、[运行追踪](../../exercises/lesson-08-tracing/README.md)、[任务评估](../../exercises/lesson-09-evaluation/README.md)。

配套说明列出运行配置和验证步骤。真实模型调用可能产生费用，按实验说明显式开启。教学检查通过，不等于已经满足生产系统的并发、隔离和高可用要求。
