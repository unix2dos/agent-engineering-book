# 第 0 课：Agent 工程史——从工具循环到可靠系统

> 本章不是产品年表，而是后续课程的地图。资料最后核验于 2026-09-01；会变化的项目状态和固定版本链接收录在[研究记录](../research/00-agent-engineering-history-sources.md)。

LLM Agent 的历史可以从一个很小的问题开始：你让模型“读取 `report.txt` 并总结”，模型本身碰不到这份文件。它只能生成文字，真正打开文件的是模型外面的宿主程序，也就是后文反复出现的 **Harness**。

最小循环只有几步：

```python
while True:
    reply = model(context)
    if not reply.tool_calls:
        return reply.final
    results = [host_execute(call) for call in reply.tool_calls]
    context.extend([reply, *results])  # 每个结果保留原来的 tool_call_id
```

这段伪代码能跑一次工具，却回答不了很多问题：参数错了怎么办？循环停不下来怎么办？历史放不下怎么办？程序崩溃后能否继续？工具是否重复执行？谁允许它删除文件？Agent 工程的各层，正是沿着这些缺口长出来的。

```text
生成文本
→ 调用工具
→ 连续行动
→ 结构化协议
→ 真实任务评测
→ 管理 Context 与执行状态
→ 跨实现互操作
→ 处理权限、副作用与恢复
```

## 本章怎样学

| 类型 | 本章要求 |
|---|---|
| 必须亲写 | 不看答案，亲手写出上面的最小循环，并标出 Model 与 Harness 的责任分界 |
| 允许 AI | 帮你整理时间线、检查引用格式，但不能替你解释“下一层为什么出现” |
| 必须验证 | 查询会变化的项目、协议和 Release；不能拿旧教程描述当前实现 |
| 只需读懂 | 经典 BDI 的形式逻辑和哲学来源，本章只理解它提出了哪些问题 |

## 1. Agent 问题早于大模型

早期 Agent 与 BDI 研究已经在讨论状态、目标、意图、计划和环境反馈。1990 年代的 Agent-Oriented Programming 与 BDI Agent 还尝试把这些概念放进可执行系统。[Intelligent Agents: Theory and Practice](https://doi.org/10.1017/S0269888900008122)

这些研究为今天提供了问题语言，却不是 LLM Agent 的直接代码祖先。经典系统主要依赖形式逻辑、手工知识和计划；LLM Agent 主要依赖生成模型、Context 与工具协议。两条路线关心相似的问题，技术基础并不相同。

## 2. 2022～2023：模型开始边行动边观察

ReAct 让模型交错产生 reasoning trace 和 action，环境返回 Observation，模型再决定下一步。说白了，就是“先做一步，看见结果，再调整”。[ReAct v3](https://arxiv.org/abs/2210.03629v3)

这里要守住一个边界：**Agent Loop 不一定使用 ReAct，也不要求把模型内部思考暴露给用户。** ReAct 是一种经典的推理—行动组织方式；现代模型也可以直接返回结构化 Tool Call，由 Harness 驱动同样的循环。

Toolformer 研究的是另一个问题：能否通过训练，让模型学会何时选择 API、填写什么参数，并利用 API 结果继续生成。它是工具使用的训练方法，不是能够无限交互的 Agent Runtime。[Toolformer v1](https://arxiv.org/abs/2302.04761v1)

两者可以这样记：

```text
ReAct      研究运行时怎样边做边看
Toolformer 研究训练时怎样学会使用工具
```

Auto-GPT 在 2023 年 3 月从一份长期目标与工具设想的 Prompt，很快演变成公开可运行的连续命令循环。到 3 月 28 日，源码已经能让模型反复选择搜索、网页摘要和内存操作，并在每一步等待人工授权；当时浏览器操作与子实例仍是 TODO。这个原型展示了“让模型持续决定下一步”怎样落到代码里，也让循环失控、费用、权限与故障恢复成为必须面对的工程问题。[最早 Prompt](https://github.com/Significant-Gravitas/AutoGPT/commit/b099adcb0830ab00c003749c2ae2cf0f5ec5524a)、[早期循环](https://github.com/Significant-Gravitas/AutoGPT/commit/68640a58640156398aea344da21683a5f7f27487)

同年 6 月，OpenAI Function Calling 用 JSON Schema 描述函数，让模型返回结构化的工具名和参数。它减少了从自然语言里猜命令的歧义，但没有替应用执行工具。[OpenAI Function Calling 公告](https://openai.com/index/function-calling-and-other-api-updates/)

因此，最小循环要补上第一条责任边界：

```text
Model   提出调用什么工具、传什么参数
Harness 校验、授权、执行，再把结果交还模型
```

Tool Call 是一张调用申请单，不是工具已经执行的证明。

## 3. 2023～2024：Coding Agent 变成可测系统

SWE-bench 把真实 GitHub Issue 与对应修复整理成可重复评测。它不再问“模型能否写一段代码”，而是问 Agent 能否理解仓库、修改文件并让测试通过。[SWE-bench v3](https://arxiv.org/abs/2310.06770v3)

SWE-agent 则研究参加这场考试的系统。它提出 Agent-Computer Interface：仓库导航、编辑命令、反馈格式和测试接口都会改变 Agent 的表现。[SWE-agent v3](https://arxiv.org/abs/2405.15793v3)

最短区别是：

```text
SWE-bench 是试卷
SWE-agent 是参加考试的 Agent 系统
```

这也说明 Harness 不是模型旁边无关紧要的胶水。工具只返回 `failed`，和返回错误行、堆栈、退出码，会让同一个模型走出完全不同的下一步。工具接口会改变模型能做什么，也会改变它能看见什么。

## 4. 长任务迫使系统管理 Context 与状态

循环变长以后，所有历史不可能永远塞进模型窗口。MemGPT 用分层内存与外部存储模拟 Virtual Context Management；后来的 Context Engineering 把问题说得更直接：每次推理究竟应该选择哪些高信号信息？[MemGPT v2](https://arxiv.org/abs/2310.08560v2)、[Anthropic Context Engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)

这时三个经常混淆的对象开始分开：

```text
Context    模型这一次真正看见的内容
Session    一段连续交互的持久记录
Checkpoint 工作流运行到某一步时的可恢复状态
```

LangGraph 把 State、Node 和 Edge 组成可循环的状态图，并通过 Checkpointer 保存步骤状态，使中断后继续、等待人工确认和回看旧状态成为可能。[LangGraph v0.2](https://blog.langchain.com/langgraph-v0-2/)

但 Checkpoint 仍不能证明外部动作只发生了一次。邮件可能已经发出，程序却在写入 `succeeded` 前崩溃。Checkpoint 能告诉你 Runtime 保存到了哪里，不能单独证明外部世界发生了几次。

## 5. 2024～2025：连接工具与连接 Agent 分成两层

MCP 在 2024 年试图减少重复集成：不再要求每个 Agent 应用分别适配每个工具和数据源，而是建立 Agent 应用（Host）、协议连接器（Client）和外部能力提供方（Server）之间的共同边界，让 Tool、Resource 和 Prompt 能被发现和调用。[MCP 发布公告](https://www.anthropic.com/news/model-context-protocol)

最短记忆是：**MCP 连接 Agent 应用与外部能力。** 它不负责替应用运行 Agent Loop，也不证明某次工具调用应该被允许。

MCP 的当前规范已经不同于 2024 年首发版本。截至 `2026-07-28`，每个请求自带协议版本与 Client Capabilities，不再依赖协议级 Session 或初始化握手。Server 仍可以保存业务数据，但跨请求状态要靠显式标识关联；长任务可以选择官方 Tasks 扩展。历史文章可以解释当年的发布动机，真正实现时必须重新查看当前规范。[MCP Changelog](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/2026-07-28/docs/specification/2026-07-28/changelog.mdx#L10-L28)

A2A 面向另一层：让不同服务器、厂商或框架里的远程 Agent 发现能力、交换消息并协作处理长任务。[A2A 发布公告](https://developers.googleblog.com/en/a2a-a-new-era-of-agent-interoperability/)

```text
Agent 调文件、数据库或搜索工具   看 MCP
Agent 把任务交给另一个远程 Agent 看 A2A
```

两者都不能代替 Harness。连接成功只证明“能够调用”，不证明“本次应该调用”，也不负责本地循环、Context 和执行恢复。

## 6. 今天：可靠性成为独立工程层

现代 Agent SDK 和 Coding Runtime 开始封装 Loop、任务转交（Handoff）、输入输出检查（Guardrail）、运行轨迹（Trace）与会话记录（Session），但一个能持续调用工具的系统仍要回答：谁批准动作？进程最多能访问什么？崩溃以后怎样恢复？相同请求会不会产生第二次副作用？[OpenAI Agents SDK](https://github.com/openai/openai-agents-python)

把前面的缺口叠起来，可以得到后续课程的责任地图：

| 层 | 主要回答的问题 |
|---|---|
| Tool Calling | 模型想调用什么？参数是什么？ |
| Agent Loop | 谁执行工具、回传结果并决定是否继续？ |
| Context / Memory | 这一次给模型看什么？哪些信息跨轮次或跨 Session 保留？ |
| Session / Checkpoint | 重启以后怎样恢复对话或工作流状态？ |
| MCP / A2A | 外部能力和远程 Agent 怎样跨实现连接？ |
| Approval / Sandbox | 谁同意这次动作？操作系统最多允许进程做什么？ |
| Idempotency / Ledger（执行账本） | 外部动作是否发生过？能否安全重试？怎样查账？ |
| Trace / Evaluation | 一次任务为什么失败？系统修改后是否整体变好？ |

这些层不是某个框架一次发明的标准答案。Agent Runtime 只是不断吸收 API、数据库、分布式系统、安全工程和评测方法，补上最小工具循环暴露出来的缺口。

一个系统可以同时拥有 Function Calling、MCP 和 Checkpoint：它能申请工具、连接工具，也能保存进度。但没有 Approval、Sandbox、幂等和 Ledger，它仍可能越权修改文件，或在崩溃后重复发送邮件。

所以，本章真正要记住的不是年份，而是一条判断：

> Agent 每向现实世界多走一步，Harness 就必须多承担一层可验证的责任。

## 主动回忆

先合上正文，口头回答：

1. 为什么 Agent 工程史不适合写成产品发布时间表？
2. 最小 Tool Calling Loop 中，Model 与 Harness 分别负责什么？
3. Agent Loop 是否必须使用 ReAct？
4. ReAct 与 Toolformer 分别解决什么问题？
5. SWE-bench 与 SWE-agent 有什么区别？
6. 为什么工具接口会改变同一个模型的表现？
7. Context、Session 与 Checkpoint 分别是什么？
8. MCP 与 A2A 分别连接谁？它们为什么不能代替 Harness？
9. 为什么 Checkpoint 不能证明邮件只发送了一次？
10. Function Calling、Checkpoint、Sandbox、Ledger 与 Evaluation 分别补哪个缺口？

<details>
<summary>检查简答</summary>

1. 稳定主线是“新能力暴露新缺口，下一层工程再补上”，不是项目热度。
2. Model 提出工具名和参数；Harness 校验、授权、执行、回传，并控制循环。
3. 不必须。ReAct 是经典的推理—行动组织方式，现代 Tool Calling Loop 可以直接处理结构化调用。
4. ReAct 研究运行时怎样边做边看；Toolformer 研究训练时怎样学会选择工具。
5. SWE-bench 是真实仓库任务的评测试卷；SWE-agent 是参加评测的 Agent 系统。
6. 工具决定模型能采取哪些动作，也决定它能得到哪些环境证据。
7. Context 是本次模型可见内容；Session 是连续交互记录；Checkpoint 是可恢复的工作流状态。
8. MCP 连接外部能力；A2A 连接远程 Agent；Harness 负责本地 Loop、策略、Context 和执行控制。
9. 外部动作可能成功，但进程在成功状态写盘前崩溃；恢复点只记录本地已知状态。
10. 它们依次处理结构化调用、状态恢复、强制边界、执行事实与系统质量判断。

</details>

## 参考资料

- [本章一手资料核验记录](../research/00-agent-engineering-history-sources.md)
- [ReAct v3](https://arxiv.org/abs/2210.03629v3)
- [Toolformer v1](https://arxiv.org/abs/2302.04761v1)
- [SWE-bench v3](https://arxiv.org/abs/2310.06770v3)
- [SWE-agent v3](https://arxiv.org/abs/2405.15793v3)
- [MCP 2026-07-28](https://github.com/modelcontextprotocol/modelcontextprotocol/releases/tag/2026-07-28)
- [A2A v1.0.1](https://github.com/a2aproject/A2A/releases/tag/v1.0.1)
