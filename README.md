# Agent 工程实践：从工具循环到可靠系统

假设 Agent 已经把一封邮件发出去了，却在写下“发送成功”之前崩溃。

程序重启后，只看见一项没有结果的任务。重试，用户可能收到两封邮件；不重试，这封邮件也可能根本没有发出去。

能调用工具只是开始。真正困难的是：历史越来越长时给 Model 看什么，程序中断后怎样继续，副作用不明时能不能重试，用户批准后命令又能碰到什么。这本书从一个最小 Tool Calling Loop 出发，一层层补上持久化、Context、故障恢复、Sandbox 和 Tracing，直到一次 Agent 运行可以被解释、限制和验证。

## 适合谁，怎样学

你只需要会一点 Python、Git 和命令行。Tool Calling、Context、JSONL、幂等、Trace、Sandbox 等术语，不要求提前懂；本书会等它们真正派上用场时再解释。

本书以 Agent Runtime / AI Systems 为主要技术深度，同时保留真实应用落地。本书不把框架名称或一次成功演示当作证据，每个关键结论都要经过实际材料检查：

- 用官方文档和固定版本的源码确认真实实现；
- 用最小代码跑通关键路径；
- 主动制造截断、崩溃、重复执行和越界访问；
- 通过主动回忆检查能否独立解释和迁移。

📖 **在线阅读**：[https://levon.gitbook.io/agent-engineering/](https://levon.gitbook.io/agent-engineering/)

## 源码依据

源码参考不追求把热门框架全部讲一遍，而是分成三组，让每组项目回答自己最擅长的问题：

- **Coding Agent Runtime**：[Pi](https://github.com/earendil-works/pi)、[OpenClaw](https://github.com/openclaw/openclaw)、[Hermes](https://github.com/NousResearch/hermes-agent)、[Codex](https://github.com/openai/codex)、[OpenCode](https://github.com/anomalyco/opencode) 与 [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness)，主要用于观察 Agent Loop、Session、Context、Tool、权限和安全边界。DeepSeek Harness 仍处于 Developer Preview，本书只针对核验过的固定版本讨论；
- **Agent 框架与接口**：[OpenAI Agents SDK](https://github.com/openai/openai-agents-python)、[Claude Agent SDK Python](https://github.com/anthropics/claude-agent-sdk-python) 与 [LangGraph](https://github.com/langchain-ai/langgraph)，主要用于观察通用 Agent Loop、Session、Handoff、Guardrail、状态图和长任务恢复；
- **可观测性与评估**：[Phoenix](https://github.com/Arize-ai/phoenix) 与 [Inspect AI](https://github.com/UKGovernmentBEIS/inspect_ai)，主要用于观察 Trace、Span、Dataset、Solver、Scorer 和 Evaluation。

[Claude Code](https://github.com/anthropics/claude-code) 也会作为重要的产品行为参考，但其核心 Runtime 没有开源。书中只根据官方文档、设置、插件和示例研究它的权限、Hooks、Sandbox、Memory、Subagent 与 Workflow，不把这些外部行为说成已经核验过的内部实现。

## 阅读路线

| 阶段 | 课程 | 状态 |
|---|---|---|
| 一：判断与行动 | 第 1～3 课：是否需要 Agent、Runtime 与 Tool Calling Loop；第 0 课选读 | 已完成 |
| 二：状态、可靠性与控制 | 第 4～7 课：持久化、Context、故障恢复与 Sandbox | 已完成 |
| 三：看见与验证 | 第 8～9 课：Trace，以及合并回归检查的 Agent Evaluation | 第 8 课已完成 |
| 四：编排与长任务 | 第 10 课：Workflow、Routing、Handoff、少量 Subagent、后台任务与恢复 | 待第 9 课验证后开始 |
| 五：生产运行 | 第 11 课：并发、队列、限流、成本、部署、监控与回滚 | 待第 10 课验证后开始 |
| 可选分支 | RAG、MCP/A2A、Browser、Voice、多模态与专用 Sandbox | 按实际问题选择 |

第 9～11 课是当前唯一详细规划的未来主线，不提前创建空章节。Recorded-session Replay、完整 OpenTelemetry 平台和大规模 Multi-Agent 都在真实问题出现后再补。

## 从哪里开始

- 第一次系统学习 Agent：从[第 1 课：Agent 基础——从语言模型到行动系统](chapters/01-Agent基础.md)开始；
- 已经理解基本概念，想先看代码：从[第 3 课：Tool Calling Loop——从调用请求到最终回答](chapters/03-工具调用循环.md)开始；
- 想把前两个阶段真正串起来：直接做[阶段一～二综合实践](exercises/phase-1-capstone/README.md)；
- 只想先了解工程演进：选读[第 0 课：Agent 工程史](chapters/00-Agent工程史.md)。

完整目录见 [SUMMARY.md](SUMMARY.md)。

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
- [`lesson_06_tool_reliability.py`](examples/lesson_06_tool_reliability.py)：Execution Ledger、幂等与故障恢复。

[阶段一～二综合实践](exercises/phase-1-capstone/README.md)会把有停止条件的 Agent Loop、受限工作区工具、Transcript、Prompt View、Ledger 和故障恢复串成一个可以运行的小系统。

[SQLite 专项练习](exercises/session-storage-sqlite/README.md)连接第 4 课的存储选择与第 6 课的可靠执行，从状态查询开始，验证索引、事务和唯一约束什么时候比继续扩写 JSONL 代码更省事。

[第 7 课安全边界练习](exercises/lesson-07-safety/README.md)先证明 `cwd=workspace` 不是 Sandbox，再逐层加入 Tool Policy、Approval、执行 Backend 与 Elevated。

[第 8 课 Trace 练习](exercises/lesson-08-tracing/README.md)先把一次 Agent Run 组织成具有共同 `trace_id` 和父子关系的 Span。

后续课程继续扩展同一个综合 Agent：第 9 课加入固定任务与回归检查，第 10 课加入编排和长任务，第 11 课再处理生产运行。RAG 与 MCP 只在这个项目确实需要知识检索或外部能力时加入。

这些代码是教学实现，不宣称覆盖生产系统的并发、分布式事务、租户隔离和高可用要求。

## 单一真实源（SSOT）与发布规范

本仓库是唯一持续维护的权威源（Single Source of Truth）。历史发布的 Blog 文章仅作为外部快照和引流入口保留，除修正失效链接和关键事实错误外，不再全量同步正文；新 Blog 仅在阶段收官或特定话题独立成篇时发布。GitBook 镜像仅用于排版展示，不作为并行写作来源。
