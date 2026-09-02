# 第 1 课：从语言模型到行动系统

> 本章只回答一个问题：什么时候只是调用了 LLM，什么时候才需要一个 Agent？资料最后核验于 2026-09-03；会变化的项目状态收录在[第 1～5 课一手资料复核](../research/01-05-chapter-promotion-sources.md)。

假设你要求模型：“查询明天上海的天气；如果下雨，就提醒我带伞。”模型可以写出一段像真的天气预报，却不能自己访问天气服务，也不能在你的日历里创建提醒。

外部动作来自模型之外的程序。这个程序保存消息、描述工具、执行模型提出的动作，再把真实结果送回模型。本文把它叫作 **Agent Harness**。

```text
用户目标
-> Harness 调用 Model
-> Model 请求 Tool，或者给出 Final
-> Harness 执行 Tool
-> Environment 返回真实结果
-> Harness 把结果交回 Model
```

## 本章怎样学

| 类型 | 本章要求 |
| --- | --- |
| 必须亲写 | 画出一次 `Model -> Tool -> Result -> Model` 循环，并标出谁拥有真实权限 |
| 允许 AI | 帮忙找例子、解释术语，不替你判断任务是否真的需要 Agent |
| 必须验证 | 能用一个固定 Workflow 和一个动态 Agent 分别实现同一需求，并观察路径由谁决定 |
| 只需读懂 | ReAct、Self-Refine、Reflexion 和多 Agent 的用途与边界，本章不复现论文 |

## 1. 给“缸中大脑”接上外部世界

单独的大语言模型只接收输入并生成输出。它不会因为文字里写了 `read_file`，就自动获得本地磁盘权限。

一个最小的工具型 Agent 可以拆成四部分：

| 部分 | 负责什么 |
| --- | --- |
| Model | 理解目标，根据已有信息选择下一步 |
| Harness | 组织循环、消息、工具路由、权限与停止条件 |
| Tool | 执行一个边界明确的动作 |
| Environment | 文件系统、网页、数据库或外部 API 的真实状态 |

Model 可以提出“删除数据库”，却不能批准自己的请求。Harness 仍要独立检查参数、权限和审批策略。提出动作的人不能同时成为授权动作的人。

这是一种运行时拆法，不是行业唯一标准。规划、记忆、反思和多 Agent 都可以后来再加；最小系统首先要有人把 Model 与 Environment 接成反馈循环。[Anthropic 对 Agent 的运行解释](https://www.anthropic.com/research/building-effective-agents)

## 2. 有 LLM 和工具，不一定就是 Agent

还是天气提醒。如果代码把路径写死：

```text
查天气 -> 判断是否下雨 -> 创建提醒 -> 发送通知
```

下一步永远由程序提前决定。LLM 可以把天气文本整理成 JSON，但它没有控制执行路径。这是 **Workflow**。

如果程序只给模型目标和几个工具，模型查完天气后自己决定是否缺少城市、是否创建提醒、是否还要查询日历以及何时停止，那么下一步由模型根据环境反馈动态决定。这是本文所说的 **Agent**。

| 系统 | 谁决定下一步 |
| --- | --- |
| Workflow | 预先写好的代码路径 |
| Agent | Model 根据目标和环境反馈动态决定 |

二者可以混用。付款、审批、发布等高风险主流程适合确定性 Workflow；“调查失败原因”这种无法提前列完步骤的局部任务可以交给 Agent。

所以判断边界时，不要只问“有没有 LLM”“有没有工具”，而要问：

```text
下一步是谁决定的？
环境结果会不会改变后续路径？
```

## 3. Agent Loop 不等于 ReAct

最小 Agent Loop 只有：

```text
Model 判断 -> Tool 执行 -> Result 返回 -> Model 继续判断
```

命令返回 `403 Forbidden` 后，模型可能修改参数再试。它确实利用了环境反馈，但这还不能证明系统使用了 ReAct。

ReAct 原论文让 Reasoning Trace 与 Action 交错出现：推理帮助调整计划，Action 从环境取得 Observation，Observation 再影响下一步推理。[ReAct v3](https://arxiv.org/abs/2210.03629v3)

现代 Tool Calling Agent 可以使用“观察后再行动”的思想，却不必公开或保存论文形式的 Thought。最短区别是：

```text
Agent Loop 是外层的 Model、Tool、Result 循环
ReAct 是循环里一种具体的推理与行动组织方法
```

因此，只有思考链不等于 ReAct；遇错后换一个工具也不自动等于 ReAct。

## 4. 反思和多 Agent 都是可选增强

Agent 生成第一版后，让模型评审并立即重写当前结果，更接近 Self-Refine。任务结束后把失败教训保存起来，让下一次尝试先读取，更接近 Reflexion。[Self-Refine v2](https://arxiv.org/abs/2303.17651v2)、[Reflexion v4](https://arxiv.org/abs/2303.11366v4)

```text
Self-Refine 当场改这一次结果
Reflexion   保存教训，影响后续尝试
```

二者都不是模型天然自带的质量保证。系统仍要决定反馈从哪里来、何时触发、最多重复几次以及怎样判断结果真的变好。

多 Agent 也一样。分别调查三个互不依赖的仓库，适合并行；共同修改同一个函数，后一步依赖前一步时，多个 Agent 会重复读取、互相等待，并增加合并冲突。先把单 Agent 做好，只有任务确实能拆开时再增加协作角色。

## 5. Trace、Evaluation 与运行时止损不是一件事

进入多轮循环后，需要知道系统实际发生了什么。Trace 可以记录模型调用、工具参数、结果、耗时、Token、错误和父子关系。它像行车记录仪，可以回放一次运行，但不代表看到了模型全部隐藏思维。

Evaluation 用一批任务和评分方法比较版本，回答“整体是否变好”。它像考试和成绩单，不会在一次危险运行中自动踩刹车。

真正负责当场止损的是：

```text
最大模型请求次数
超时
Token 或费用预算
权限与审批
人工接管
```

Trace 能告诉你命令执行了三次，最大步骤数才能阻止第四次；Evaluation 能发现新版本更容易循环，却不能替正在运行的 Harness 停车。

## 6. 什么时候不该使用 Agent

Agent 用延迟、Token 成本和可预测性换取动态决策能力。路径固定的日报系统通常只需要：

```text
查询数据库 -> 调用一次 LLM 写摘要 -> 人工确认 -> 发送
```

这里可以使用 LLM，也可以调用工具，但没有必要让模型反复决定下一步。只有步骤难以预先写死，而且模型能根据环境反馈纠偏时，Agent Loop 才开始回本。

反例也很重要：一个 LLM 自己写答案，没有访问外部状态、没有连续行动，并不因为提示词里写了“你是 Agent”就成为行动系统。

下一课会沿一次真实 Tool Call 拆开四个部分：[模型、Harness、工具与环境](02-agent-runtime-model-harness-tools-environment.md)。如果你想先看代码，可以直接进入[第一阶段综合实践](../exercises/phase-1-capstone/README.md)。

## 主动回忆

1. Model、Harness、Tool 与 Environment 分别负责什么？
2. Workflow 与 Agent 的分界为什么不是“有没有工具”？
3. Agent Loop 与 ReAct 有什么区别？
4. Self-Refine 与 Reflexion 有什么区别？
5. 什么任务适合多个 Agent，什么任务可能因多 Agent 变差？
6. Trace、Evaluation 和运行时止损分别做什么？
7. 为什么 Model 不能批准自己的危险动作？
8. 固定付款流程和开放式故障调查应怎样组合？

<details>
<summary>检查简答</summary>

1. Model 选择下一步；Harness 管循环和策略；Tool 执行动作；Environment 返回真实状态。
2. Workflow 的路径由代码预设；Agent 的下一步由 Model 根据反馈决定。
3. Agent Loop 是外层反馈循环；ReAct 是一种显式交错 Reasoning、Action 与 Observation 的方法。
4. Self-Refine 当场重写当前结果；Reflexion 保存教训，影响后续尝试。
5. 独立、可并行的任务适合；共享状态、强顺序依赖的任务可能被通信和冲突拖慢。
6. Trace 回放一次运行，Evaluation 比较一批结果，最大步骤、超时、预算和权限负责当场止损。
7. Model 可能误判或受不可信输入影响，提出动作和授权动作必须分开。
8. Workflow 控制付款和审批，Agent 只处理无法预设路径的调查部分。

</details>

## 参考资料

- [本批章节一手资料复核](../research/01-05-chapter-promotion-sources.md)
- [Anthropic：Building Effective AI Agents](https://www.anthropic.com/research/building-effective-agents)
- [Anthropic：How tool use works](https://platform.claude.com/docs/en/agents-and-tools/tool-use/how-tool-use-works)
- [ReAct v3](https://arxiv.org/abs/2210.03629v3)
- [Self-Refine v2](https://arxiv.org/abs/2303.17651v2)
- [Reflexion v4](https://arxiv.org/abs/2303.11366v4)
