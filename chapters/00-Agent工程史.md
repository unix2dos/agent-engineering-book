# 第 0 课：Agent 工程史——从工具循环到可靠系统

你让 Model“读取 `report.txt` 并总结”。它能理解要求，却碰不到这份文件。真正打开文件的，是 Model 外面那段负责执行和回传结果的程序，也就是 Harness。

最小循环只有几步：

```python
history = [user_message]

while True:
    reply = model(history)
    history.append(reply)

    if not reply.tool_calls:
        return reply.final

    for call in reply.tool_calls:
        result = host_execute(call)
        history.append(result)
```

这段伪代码能跑一次工具，却回答不了很多问题：参数错了怎么办？循环停不下来怎么办？历史放不下怎么办？程序崩溃后能否继续？工具是否重复执行？谁允许它删除文件？Agent 工程的各层，正是沿着这些缺口长出来的。

```text
生成文本
→ 调用工具
→ 连续行动
→ 结构化协议
→ 真实任务评测
→ 管理 Model 本轮能看的内容（Context）与执行状态
→ 跨实现互操作
→ 处理权限、副作用与恢复
```

## 1. Agent 问题早于大模型

在大语言模型出现以前，人们已经在研究能自己选择动作的软件：它认为外部世界现在是什么状态，想完成什么目标，又准备执行什么计划。

研究者把这三个部分叫作 Belief、Desire 和 Intention，合起来简称 BDI。1990 年代的 Agent-Oriented Programming 与 BDI Agent 已经尝试把它们放进可执行系统。[Intelligent Agents: Theory and Practice](https://doi.org/10.1017/S0269888900008122)

这些研究提出了今天仍会遇到的问题，却不是 LLM Agent 的直接代码祖先。经典系统主要依赖手工规则和计划，今天的 LLM Agent 主要依赖生成模型、Context 和工具调用。它们关心的问题相似，底层做法不同。

## 2. 2022～2023：模型开始边行动边观察

模型先做一步，看见外部结果，再调整下一步。ReAct 把这个过程组织成推理、行动和观察交替出现的轨迹。[ReAct v3](https://arxiv.org/abs/2210.03629v3)

Agent Loop 不一定使用 ReAct，也不要求把 Model 的内部思考公开给用户。现代 Model 可以直接返回结构化 Tool Call，由 Harness 驱动同样的循环。

另一个问题是：Model 能不能在训练时学会什么时候调用 API、参数怎样填、结果怎样继续使用？研究这种训练方法的工作叫 Toolformer。它不是一个可以持续执行任务的 Agent Runtime。[Toolformer v1](https://arxiv.org/abs/2302.04761v1)

两者可以这样记：

```text
ReAct      研究运行时怎样边做边看
Toolformer 研究训练时怎样学会使用工具
```

Auto-GPT 在 2023 年 3 月从一份“长期目标加工具”的 Prompt，很快变成可以公开运行的连续命令循环。到 3 月 28 日，源码已经能让 Model 反复选择搜索、网页摘要和内存操作，并在每一步等待人工授权。浏览器操作和子实例当时还没有完成。[最早 Prompt](https://github.com/Significant-Gravitas/AutoGPT/commit/b099adcb0830ab00c003749c2ae2cf0f5ec5524a)、[早期循环](https://github.com/Significant-Gravitas/AutoGPT/commit/68640a58640156398aea344da21683a5f7f27487)

这个原型把“让 Model 持续决定下一步”真正放进了代码。循环失控、费用、权限和崩溃恢复也因此从边缘问题变成工程主线。

同年 6 月，OpenAI Function Calling 让开发者先给 Model 一张函数说明书。Model 不再用普通文字说“请查天气”，而是返回结构化的工具名和参数。这减少了程序猜测命令的麻烦，但真正执行工具的仍是应用。[OpenAI Function Calling 公告](https://openai.com/index/function-calling-and-other-api-updates/)

因此，最小循环要补上第一条责任边界：

```text
Model   提出调用什么工具、传什么参数
Harness 校验、授权、执行，再把结果交还模型
```

Tool Call 是一张调用申请单，不是工具已经执行的证明。

## 3. 2023～2024：Coding Agent 变成可测系统

Agent 能修改代码以后，人们需要一张可以重复使用的试卷。SWE-bench 把真实 GitHub Issue 与对应修复整理成评测任务。它不再问“Model 能否写一段代码”，而是问 Agent 能否理解仓库、修改文件并让测试通过。[SWE-bench v3](https://arxiv.org/abs/2310.06770v3)

SWE-agent 则研究参加这场考试的系统。Agent 使用什么仓库导航、编辑命令、错误反馈和测试接口，会直接改变它的表现。这套 Agent 与计算机打交道的界面叫 Agent-Computer Interface。[SWE-agent v3](https://arxiv.org/abs/2405.15793v3)

最短区别是：

```text
SWE-bench 是试卷
SWE-agent 是参加考试的 Agent 系统
```

这也说明 Harness 不是模型旁边无关紧要的胶水。工具只返回 `failed`，和返回错误行、堆栈、退出码，会让同一个模型走出完全不同的下一步。工具接口会改变模型能做什么，也会改变它能看见什么。

## 4. 长任务迫使系统管理 Context 与状态

循环变长以后，所有历史不可能永远塞进 Model 的窗口。程序必须决定哪些内容现在放到 Model 面前，哪些留在外部存储。MemGPT 把这种做法类比成计算机管理内存；后来人们更常把“这一轮到底该给 Model 看什么”叫作 Context Engineering。[MemGPT v2](https://arxiv.org/abs/2310.08560v2)、[Anthropic Context Engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)

这时三个经常混淆的对象开始分开：

```text
Context    模型这一次真正看见的内容
Session    以 session_id 标识的一段会话
Checkpoint 程序走到某处时留下的状态存档
```

LangGraph 把任务拆成可以循环连接的步骤，并用 Checkpointer 保存步骤状态。程序因此可以中断后继续，也可以停下来等待人工确认。[LangGraph v0.2](https://blog.langchain.com/langgraph-v0-2/)

但 Checkpoint 仍不能证明外部动作只发生了一次。邮件可能已经发出，程序却在保存“成功”之前崩溃。Checkpoint 只能告诉你程序最后存到哪里，不能证明外面的邮件到底发了几次。

## 5. 2024～2025：连接工具与连接 Agent 分成两层

同一个天气工具如果要分别适配五种 Agent 应用，就会出现五套连接代码。MCP 在 2024 年提出一套共同的连接方式，让 Agent 应用可以发现和调用外部 Tool、Resource 与 Prompt。[MCP 发布公告](https://www.anthropic.com/news/model-context-protocol)

最短记忆是：**MCP 连接 Agent 应用与外部能力。** 它不负责替应用运行 Agent Loop，也不证明某次工具调用应该被允许。

MCP 后来的规范已经和 2024 年首发版本不同。历史课只需要记住它解决了哪层连接问题；真正写代码时，再查看当前稳定规范，不要照抄旧教程。[MCP Changelog](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/2026-07-28/docs/specification/2026-07-28/changelog.mdx#L10-L28)

如果不是调用天气工具，而是把调查任务交给另一个远程 Agent，就进入了另一层连接。A2A 让不同服务器、厂商或框架里的 Agent 发现能力、交换消息并合作处理任务。[A2A 发布公告](https://developers.googleblog.com/en/a2a-a-new-era-of-agent-interoperability/)

```text
Agent 调文件、数据库或搜索工具   看 MCP
Agent 把任务交给另一个远程 Agent 看 A2A
```

两者都不能代替 Harness。连接成功只证明“能够调用”，不证明“本次应该调用”，也不负责本地循环、Context 和执行恢复。

## 6. 今天：可靠性成为独立工程层

现代 Agent SDK 开始把循环、任务转交、输入输出检查、运行记录和会话管理打包起来。但一个能持续调用工具的系统仍要回答：谁批准动作？进程最多能访问什么？崩溃以后怎样恢复？同一个请求会不会执行两次？[OpenAI Agents SDK](https://github.com/openai/openai-agents-python)

把前面的缺口叠起来，可以得到后续课程的责任地图：

| 层 | 主要回答的问题 |
|---|---|
| Tool Calling | 模型想调用什么？参数是什么？ |
| Agent Loop | 谁执行工具、回传结果并决定是否继续？ |
| Context / Memory | 这一次给模型看什么？哪些信息跨轮次或跨 Session 保留？ |
| Session / Checkpoint | 重启以后怎样恢复对话或工作流状态？ |
| MCP / A2A | 外部能力和远程 Agent 怎样跨实现连接？ |
| Approval / Sandbox | 谁同意这次动作？操作系统强制限制它最多能做什么？ |
| Idempotency / Ledger（执行账本） | 怎样证明动作发生过几次？状态不明时能否安全重试？ |
| Trace / Evaluation | 怎样回看一次运行？怎样比较一批任务是否变好？ |

这些层不是某个框架一次发明出来的。人们把 API、数据库、安全和评测中的成熟做法接到最小工具循环上，一层层补住新出现的问题。

一个系统可以同时拥有 Function Calling、MCP 和 Checkpoint：它能申请工具、连接工具，也能保存进度。但没有 Approval、Sandbox、幂等和 Ledger，它仍可能越权修改文件，或在崩溃后重复发送邮件。

所以，本章真正要记住的不是年份，而是一条判断：

> Agent 每向现实世界多走一步，Harness 就必须多承担一层可验证的责任。

## 7. 怎样使用这张历史地图？

这不是一张需要背年份的时间表。看到一个新名词时，先问它在补哪个缺口：是让 Model 能申请工具，还是让程序能恢复、限制权限、避免重复执行，或者比较系统是否真的变好？

最值得亲手做的是写出章首的最小循环，并标出 Model 与 Harness 分别负责什么。时间线和引用格式可以让 AI 帮忙，经典 BDI 的形式逻辑只需知道它提出了什么问题，不需要在这里重新实现。

项目和协议会继续变化。历史动机可以从本章理解，当前实现必须重新核验官方文档和固定源码版本。

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
7. Context 是本次 Model 可见内容；Session 是一段会话的容器；Checkpoint 是程序走到某处时留下的状态存档。
8. MCP 连接外部能力；A2A 连接远程 Agent；Harness 负责本地 Loop、策略、Context 和执行控制。
9. 外部动作可能成功，但进程在成功状态写盘前崩溃；恢复点只记录本地已知状态。
10. 它们依次处理结构化调用、状态恢复、强制边界、执行事实与系统质量判断。

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
