# Agent 工程实践：从工具循环到可靠系统

你让 Model “读取 `report.txt`，再告诉我里面写了什么”。它可以回复“好的”，但它自己并不能打开文件。真正找到文件、检查路径、读取内容并把结果送回 Model 的，是外面的 Agent 程序。

事情一旦变长，更多问题就会冒出来：该把哪些历史消息发给 Model？程序重启后从哪里继续？工具执行到一半崩溃了，能不能直接重试？用户点了允许，命令就一定安全吗？

这本书从这些具体问题出发，一步步拆开 Agent 的工具循环、上下文、存储、故障恢复和安全边界。目标不是背术语，而是看懂一次 Agent 运行到底发生了什么，出错时知道该查哪一层。

## 从哪里开始

- 第一次系统学习 Agent：从[第 1 课：Agent 基础——从语言模型到行动系统](chapters/01-Agent基础.md)开始；
- 已经理解基本概念，想先看代码：[第 3 课：Tool Calling Loop——从调用请求到最终回答](chapters/03-工具调用循环.md)；
- 想把前两个阶段真正串起来：直接做[阶段一～二综合实践](exercises/phase-1-capstone/README.md)；
- 想先知道整个领域是怎么走到今天的：阅读[第 0 课：Agent 工程史](chapters/00-Agent工程史.md)。

完整目录见 [SUMMARY.md](SUMMARY.md)。

📖 **在线阅读**：[https://levon.gitbook.io/agent-engineering/](https://levon.gitbook.io/agent-engineering/)

## 适合谁

你只需要会一点 Python、Git 和命令行。Tool Calling、Context、JSONL、幂等、Trace、Sandbox 等术语，不要求提前懂；本书会等它们真正派上用场时再解释。

本书以 Agent Runtime / AI Systems 为主要技术深度，同时保留真实应用落地。它适合希望从后端工程进入 Agent 应用或 Runtime 岗位的人，不以模型训练和纯算法研究为主线。

## 怎么学

学习投入大致按 70% 系统原理、30% 应用落地分配。承载核心机制的代码，至少亲手写一次；SDK 初始化、类型声明和重复配置，可以让 AI 帮忙。凡是涉及文件写入、故障恢复、上下文裁剪和安全边界，都要实际运行，最好亲手制造一次失败。数据库、容器和 microVM 等成熟设施，不重复造轮子，重点看懂它们解决什么问题、不能替 Agent 负责什么。

应用部分不会为每个概念新建一个 Demo。现有 Workspace/Coding Agent 会持续加入 Evaluation、Workflow、长任务和生产运行能力，最终形成一份可以演示、解释和写进简历的完整项目。每个阶段结束后，再集中整理口述题、系统设计题和项目证据。

所有正式章节均遵循“主动回忆设计 → 当前源码核验 → 实践证据校验 → 初学者盲测”的准入标准，拒绝未经运行验证的二手解读。

## 阅读路线

| 阶段 | 课程 | 状态 |
|---|---|---|
| 一：判断与行动 | 第 0～3 课：Agent 工程史、Harness 与 Tool Calling Loop | 已完成 |
| 二：状态、可靠性与控制 | 第 4～8 课：Context、存储、故障恢复与 Sandbox | 已完成 |
| 三：看见与验证 | 第 9～10 课：Trace，以及合并回归检查的 Agent Evaluation | 第 9 课已完成 |
| 四：编排与长任务 | 第 11 课：Workflow、Routing、Handoff、少量 Subagent、后台任务与恢复 | 待第 10 课验证后开始 |
| 五：生产运行 | 第 12 课：并发、队列、限流、成本、部署、监控与回滚 | 待第 11 课验证后开始 |
| 可选分支 | RAG、MCP/A2A、Browser、Voice、多模态与专用 Sandbox | 按实际问题选择 |

第 10～12 课是当前唯一详细规划的未来主线，不提前创建空章节。Recorded-session Replay、完整 OpenTelemetry 平台和大规模 Multi-Agent 都在真实问题出现后再补。

## 源码依据

书中的关键结论均与官方文档、开源源码和可运行代码互相核对。我们不逐个堆砌框架，而是让不同领域的代表性实现回答其最擅长的问题：

- **Coding Agent Runtime**：[Pi](https://github.com/earendil-works/pi)、[OpenClaw](https://github.com/openclaw/openclaw)、[Hermes](https://github.com/NousResearch/hermes-agent)、[Codex](https://github.com/openai/codex)、[OpenCode](https://github.com/anomalyco/opencode) 与 [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness)，主要用于观察 Agent Loop、Session、Context、Tool、权限和安全边界。DeepSeek Harness 仍处于 Developer Preview，本书只针对核验过的固定版本讨论；
- **Agent 框架与接口**：[OpenAI Agents SDK](https://github.com/openai/openai-agents-python)、[Claude Agent SDK Python](https://github.com/anthropics/claude-agent-sdk-python) 与 [LangGraph](https://github.com/langchain-ai/langgraph)，主要用于观察通用 Agent Loop、Session、Handoff、Guardrail、状态图和长任务恢复；
- **可观测性与评估**：[Phoenix](https://github.com/Arize-ai/phoenix) 与 [Inspect AI](https://github.com/UKGovernmentBEIS/inspect_ai)，主要用于观察 Trace、Span、Dataset、Solver、Scorer 和 Evaluation。

[Claude Code](https://github.com/anthropics/claude-code) 也会作为重要的产品行为参考，但其核心 Runtime 没有开源。书中只根据官方文档、设置、插件和示例研究它的权限、Hooks、Sandbox、Memory、Subagent 与 Workflow，不把这些外部行为说成已经核验过的内部实现。

## 运行配置

配套代码示例只读取通用的 OpenAI-compatible 环境变量：

```bash
export OPENAI_API_KEY="your-api-key"
export OPENAI_MODEL="your-model"

# 使用第三方兼容端点时再设置；OpenAI 官方端点可以省略。
export OPENAI_BASE_URL="https://provider.example/v1"
```

仓库不会读取 OpenCode、Claude Code 或其他 Provider 的本地登录文件。你可以在 Shell、密码管理器、CI 或部署平台中把自己的凭据映射到这三个变量。

## 代码与综合实践

教学代码按对应课程放在 `examples/`：

- [`lesson_03_tool_calling_loop.py`](examples/lesson_03_tool_calling_loop.py)：最小 Tool Calling Loop；
- [`lesson_04_session_memory.py`](examples/lesson_04_session_memory.py)：Session、Checkpoint 与长期记忆；
- [`lesson_05_context_compaction.py`](examples/lesson_05_context_compaction.py)：JSONL Transcript、Compaction 与 Prompt View；
- [`lesson_07_tool_reliability.py`](examples/lesson_07_tool_reliability.py)：Execution Ledger、幂等与故障恢复。

[阶段一～二综合实践](exercises/phase-1-capstone/README.md)会把有停止条件的 Agent Loop、受限工作区工具、Transcript、Prompt View、Ledger 和故障恢复串成一个可以运行的小系统。

[第 6 课 SQLite 练习](exercises/lesson-06-sqlite/README.md)从状态查询开始，验证索引、事务和唯一约束什么时候比继续扩写 JSONL 代码更省事。

[第 8 课安全边界练习](exercises/lesson-08-safety/README.md)先证明 `cwd=workspace` 不是 Sandbox，再逐层加入 Tool Policy、Approval、执行 Backend 与 Elevated。

[第 9 课 Trace 练习](exercises/lesson-09-tracing/README.md)先把一次 Agent Run 组织成具有共同 `trace_id` 和父子关系的 Span。

后续课程继续扩展同一个综合 Agent：第 10 课加入固定任务与回归检查，第 11 课加入编排和长任务，第 12 课再处理生产运行。RAG 与 MCP 只在这个项目确实需要知识检索或外部能力时加入。

这些代码是教学实现，不宣称覆盖生产系统的并发、分布式事务、租户隔离和高可用要求。

## 单一真实源（SSOT）与发布规范

本仓库是唯一持续维护的权威源（Single Source of Truth）。历史发布的 Blog 文章仅作为外部快照和引流入口保留，除修正失效链接和关键事实错误外，不再全量同步正文；新 Blog 仅在阶段收官或特定话题独立成篇时发布。GitBook 镜像仅用于排版展示，不作为并行写作来源。
