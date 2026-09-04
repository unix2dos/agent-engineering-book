# 第 0 课：Agent 工程史——从工具循环到可靠运行时

2023 年 3 月，早期 Auto-GPT 已经能让 Model 连续选择搜索、网页摘要和记忆操作。每走一步，程序都会停下来等人批准。[最早 Prompt](https://github.com/Significant-Gravitas/AutoGPT/commit/b099adcb0830ab00c003749c2ae2cf0f5ec5524a)、[早期循环](https://github.com/Significant-Gravitas/AutoGPT/commit/68640a58640156398aea344da21683a5f7f27487)

这套原型今天看起来很简单，却一下暴露了后续几年一直在解决的问题：循环可能失控，历史会越来越长，工具可能越权，程序崩溃后还可能重复执行动作。

Agent 工程并不是某个框架一次设计出来的。每当 Agent 多获得一种能力，系统就会遇到一种新的失败；下一层工程，往往就是为了补住这个失败。

## 1. Agent 问题早于大模型

在大语言模型出现以前，人们已经在研究能自己选择动作的软件：它认为外部世界现在是什么状态，想完成什么目标，又准备执行什么计划。

研究者把这三个部分叫作 Belief、Desire 和 Intention，合起来简称 BDI。1990 年代的 Agent-Oriented Programming 与 BDI Agent 已经尝试把它们放进可执行系统。[Intelligent Agents: Theory and Practice](https://doi.org/10.1017/S0269888900008122)

这些研究提出了今天仍会遇到的问题，却不是 LLM Agent 的直接代码祖先。经典系统主要依赖手工规则和计划，今天的 LLM Agent 主要依赖生成模型、Context 和工具调用。

## 2. 2022～2023：模型开始边做边看

ReAct 把一次任务组织成推理、行动和观察交替出现的轨迹：先做一步，看见外部结果，再调整下一步。[ReAct v3](https://arxiv.org/abs/2210.03629v3)

Toolformer 研究的是另一个问题：能不能在训练时让 Model 学会何时调用 API、参数怎样填、结果怎样继续使用。它不是一个可以持续执行任务的 Agent Runtime。[Toolformer v1](https://arxiv.org/abs/2302.04761v1)

```text
ReAct      研究运行时怎样边做边看
Toolformer 研究训练时怎样学会使用工具
```

Auto-GPT 把“让 Model 持续决定下一步”真正放进公开可运行的代码。循环失控、费用、权限和崩溃恢复也因此从边缘问题变成了工程问题。

同年 6 月，OpenAI Function Calling 让开发者先给 Model 一份函数说明。Model 可以返回结构化的工具名和参数，应用不必再从普通文字里猜它想调用什么。[OpenAI Function Calling 公告](https://openai.com/index/function-calling-and-other-api-updates/)

结构化调用解决了“怎样表达申请”，没有解决“谁执行、能否执行、执行后怎样恢复”。这条边界会在第 1～3 课逐步展开。

## 3. 2023～2024：Coding Agent 需要真实试卷

Agent 能修改代码以后，只看一段回答已经不够了。SWE-bench 把真实 GitHub Issue 与对应修复整理成评测任务，检查 Agent 能否理解仓库、修改文件并让测试通过。[SWE-bench v3](https://arxiv.org/abs/2310.06770v3)

SWE-agent 研究的是参加这场考试的系统。Agent 使用什么仓库导航、编辑命令、错误反馈和测试接口，会直接改变表现。这套 Agent 与计算机打交道的界面叫 Agent-Computer Interface。[SWE-agent v3](https://arxiv.org/abs/2405.15793v3)

于是，人们开始认真对待 Model 外面的程序。工具只返回 `failed`，和返回错误行、堆栈、退出码，会让同一个 Model 走出完全不同的下一步。

## 4. 长任务逼出了状态和 Context 管理

循环变长以后，所有历史不可能永远塞进 Model 的窗口。程序必须决定哪些内容现在给 Model 看，哪些只留在外部存储。MemGPT 把这种做法类比成计算机管理内存；后来人们更常把“这一轮到底该给 Model 看什么”叫作 Context Engineering。[MemGPT v2](https://arxiv.org/abs/2310.08560v2)、[Anthropic Context Engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)

任务还可能跨进程、跨时间继续。LangGraph 把任务拆成可以循环连接的步骤，并用 Checkpointer 保存步骤状态，程序因此可以中断后继续，也可以停下来等待人工确认。[LangGraph v0.2](https://blog.langchain.com/langgraph-v0-2/)

但保存进度不等于记录外部动作。邮件可能已经发出，程序却在写下“成功”前崩溃。恢复点只能说明本地最后保存到了哪里，不能证明邮件究竟发了几次。

## 5. 连接工具与连接 Agent 分成两层

同一个天气工具如果要分别适配五种 Agent 应用，就会出现五套连接代码。MCP 在 2024 年提出一套共同的连接方式，让 Agent 应用可以发现和调用外部 Tool、Resource 与 Prompt。[MCP 发布公告](https://www.anthropic.com/news/model-context-protocol)

如果不是调用工具，而是把子任务派发给另一个远程系统，就进入另一层连接。A2A 让不同服务器、厂商或框架里的 Agent 互相发现能力、交换消息并协同作业。[A2A 发布公告](https://developers.googleblog.com/en/a2a-a-new-era-of-agent-interoperability/)

```text
Agent 连接文件、数据库或搜索工具   看 MCP
Agent 把任务派发给另一个远程系统   看 A2A
```

连接成功只代表通道存在。它没有决定本次是否应该调用，也没有自动解决权限、状态和故障恢复。

## 6. 今天：能行动以后，还要能够负责

把这些变化放在一起，会看到一条比产品发布时间更稳定的路线：

右栏里的术语现在不用记。先看清每种新能力暴露了什么问题，后面的课程会在真正用到时再解释名字。

| 新能力 | 随之出现的问题 | 后续工程 |
| --- | --- | --- |
| Model 能申请工具 | 申请怎样变成真实执行？ | Tool Calling Loop 与 Runtime |
| Agent 能连续行动 | 历史放不下，重启后进度丢失 | Session、Context 与 Checkpoint |
| Tool 能修改真实世界 | 崩溃后不知道动作是否完成 | Idempotency 与 Ledger |
| Agent 能运行命令 | 用户批准后仍可能越界 | Permission 与 Sandbox |
| 系统可以长时间运行 | 失败发生在哪一步？改动是否真的变好？ | Trace 与 Evaluation |

这些做法大多不是 Agent 领域凭空发明的。人们把 API、数据库、安全和测试中的成熟办法接到工具循环上，一层层补住新失败。

所以，这段历史真正要留下的不是年份，而是一条判断：

> Agent 每向现实世界多走一步，运行它的程序就必须多承担一层可验证的责任。

## 7. 怎样使用这张地图？

以后看到一个新框架或协议，先问它补的是哪种缺口：让 Model 表达调用、保存任务状态、限制执行边界，还是判断系统有没有变好。

如果一个项目只展示“可以调用很多工具”，却没有说明停止、恢复、权限和验证，不要把缺少的部分自动脑补出来。后面的课程会按照上表的顺序，把这些责任逐层放回一个可以运行的 Agent。

想沿主线学习，可以从[第 1 课：Agent 基础](01-Agent基础.md)开始。

## 主动回忆

先合上正文，口头回答：

1. 为什么 Agent 工程史不适合只写成产品发布时间表？
2. ReAct 与 Toolformer 分别研究什么？
3. SWE-bench 与 SWE-agent 有什么区别？
4. 为什么工具接口会改变同一个 Model 的表现？
5. MCP 与 A2A 分别连接什么？
6. 为什么 Checkpoint 不能证明邮件只发送了一次？
7. Agent 获得行动能力后，为什么还需要可靠性、安全和评测？

<details>
<summary>检查简答</summary>

1. 更稳定的主线是“新能力暴露新失败，下一层工程再补住它”，不是项目热度。
2. ReAct 研究运行时怎样边做边看；Toolformer 研究训练时怎样学会选择工具。
3. SWE-bench 是真实仓库任务的评测试卷；SWE-agent 是参加评测的 Agent 系统。
4. 工具决定 Model 能采取哪些动作，也决定它能得到哪些环境证据。
5. MCP 连接 Agent 应用与外部能力；A2A 连接不同系统中的远程 Agent。
6. 外部动作可能已经成功，但进程在成功状态写盘前崩溃。
7. 能行动只说明系统具备能力；可靠性、安全和评测分别约束动作怎样恢复、最多能做什么，以及改动是否有效。

</details>

## 参考资料

> 资料最后核验于 2026-09-01；会变化的项目状态和固定版本收录在下面的研究记录中。

- [本章一手资料核验记录](../research/00-agent-engineering-history-sources.md)
- [ReAct v3](https://arxiv.org/abs/2210.03629v3)
- [Toolformer v1](https://arxiv.org/abs/2302.04761v1)
- [SWE-bench v3](https://arxiv.org/abs/2310.06770v3)
- [SWE-agent v3](https://arxiv.org/abs/2405.15793v3)
- [MCP 2026-07-28](https://github.com/modelcontextprotocol/modelcontextprotocol/releases/tag/2026-07-28)
- [A2A v1.0.1](https://github.com/a2aproject/A2A/releases/tag/v1.0.1)
