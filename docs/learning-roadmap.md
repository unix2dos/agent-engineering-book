# Agent 工程学习路线

Agent 能跑起来以后，RAG、MCP、Multi-Agent、Trace、Eval 和部署会一起出现。如果“热门框架有这个功能”就足以成为下一课，这条路线永远走不完。

本书用两个问题筛选核心内容：它是否会改变大多数 Agent 项目的关键判断？这个判断是否需要亲手实现或验证？两个答案都是“是”，才值得进入主线。

## 什么叫核心？

“默认开启”不能判断一项能力的价值。Trace Exporter 可能因隐私和成本而关闭，测试也不会运行在每次用户请求里，但它们仍可能决定一个 Agent 能否被安全修改和发布。

这里把能力分成三层：

| 层级 | 判断标准 | 例子 |
| --- | --- | --- |
| 运行必需 | 缺少它，Agent 无法完成一次任务 | Model、Harness、Tool、Loop、停止条件 |
| 可靠工程必需 | Agent 能跑，但无法安全修改、验证或发布 | 状态恢复、安全边界、最小观测、Evaluation、回归检查 |
| 规模化或可选 | 达到特定流量、复杂度或业务需求后才值得建设 | Recorded-session Replay、完整 OTel、RAG、MCP、大规模 Multi-Agent |

这本书不只追求“能跑”。目标是做出一个可以安全修改、验证和运行的 Agent，同时停在单个学习者能够完成的范围内。

## 职业方向与学习比例

主方向是 Agent Runtime / AI Systems Engineer，同时保留 Agent 应用工程能力：

```text
70% 系统原理
+
30% 真实应用
=
用一个可运行项目证明 Runtime 能力
```

Runtime 深度包括 Harness、Session、可靠性、Sandbox、Evaluation、编排和生产运行。应用部分负责把这些能力放进一个真实 Workspace/Coding Agent，而不是为每个概念创建新 Demo。

这个方向与当前岗位的交集很直接：OpenAI 的 Codex Agent Systems 职位把 Harness、Sandbox、Orchestration、Evals、生产可靠性、Observability、延迟和成本放在同一条职责链上；Anthropic 的 Applied AI Engineer 同时要求 Agent Framework、Evaluation、Transcript Analysis、MCP 和部署经验。[OpenAI Codex Agent Systems](https://openai.com/careers/ai-systems-engineer-codex-agents-san-francisco/)、[Anthropic Applied AI Engineer](https://job-boards.greenhouse.io/anthropic/jobs/5057647008)

## 最终主线

```text
前置：能读 Python、Git 和命令行
  |
  v
阶段一：判断与行动                         已完成，第 1～3 课；第 0 课选读
  |
  v
阶段二：状态、可靠性与控制                 已完成，第 4～7 课
  |
  v
阶段三：看见与验证                         第 8 课已完成，第 9 课正文与实践已成稿
  |
  v
第 10 课：Orchestration 与长任务
  |
  v
第 11 课：Production Runtime
  |
  v
综合项目：可验证、可恢复、可部署的 Workspace Agent
  |
  +------> 按真实需求进入可选分支
```

## 已完成的能力

第 1～3 课解决 Agent 怎样行动：判断任务是否需要 Agent，区分 Model、Harness、Tool 和 Environment，亲手跑通 Tool Calling Loop，并正确处理 Tool Result 与停止条件。第 0 课只提供工程史地图，不是后续课程的前置要求。

第 4～7 课解决 Agent 怎样保存和控制：Session、Transcript、Checkpoint、Memory、Context、JSONL、SQLite、Ledger、幂等、故障恢复、Approval、Permission 与 Sandbox 都已经通过文章和代码练习验证。SQLite 是贯穿持久化与可靠性的专项实践，不再单独占用一课。

第 8 课解决一次运行怎样被还原。它保留为支撑可靠工程的基础课，但不再扩展 Collector、完整 Tail Sampling 平台或可视化产品。

第 9 课已经有真实任务运行、独立评分、两版对比和最小门禁的证据，正文与实践已成稿。它验证的是一组固定任务，不代表整个 Agent 已具备生产质量。接下来把重心放到长任务编排和生产运行。

## 第 9 课：Agent Evaluation——任务验收与回归门禁

见[第 9 课正文](../chapters/09-Agent评估.md)和[实践说明](../exercises/lesson-09-evaluation/README.md)。概念解释、真实 CSV 实验和门禁规则统一维护在正文，这里只记录范围。

最小实践已经覆盖：按任务检查实际产物、区分任务失败与评分故障、在相同条件下比较两版，以及让固定回归检查返回明确的通过或拦截。读完正文并复现一次离线门禁后，本阶段即可收尾，不再追加题型和逐题考试。

完整评测平台、LLM Judge 和 Recorded-session Replay 暂缓。只有现有检查无法回答真实质量问题，或测试确实变慢、变贵、难复现时，再补相应能力。

## 第 10 课：Agent Orchestration——Workflow、Routing 与长任务

一个 Agent 能完成短任务，不代表它适合把所有步骤都交给 Model 决定。第 10 课先把确定部分收回代码，再处理真正需要动态选择的部分：

- Workflow 固定哪些步骤；
- Routing 怎样选择模型、工具或处理分支；
- Handoff 怎样转交责任和上下文；
- 少量 Subagent 什么时候带来并行收益；
- 后台任务怎样等待、取消和恢复；
- 长任务怎样留下可继续的状态。

这一课不会把 Multi-Agent 当成单 Agent 的升级版。只有 Evaluation 已经证明单 Agent 的失败来自职责过多、需要并行或任务持续时间太长，才增加另一个 Agent。

## 第 11 课：Production Runtime——并发、队列与持续运行

本机运行成功之后，还要面对同时到来的 Session、Provider 限流、进程重启和版本发布。第 11 课只保留上线最常遇到的系统问题：

- 多 Session 并发与隔离；
- 队列、积压时减慢或拒绝新任务的 Backpressure，以及取消；
- Provider 限流、超时与故障；
- Token、延迟和成本；
- 密钥与用户数据边界；
- 健康检查、部署和回滚；
- 线上失败怎样回到 Evaluation Task Set。

课程不会展开完整的多租户平台或高可用数据库集群。那些能力只有在真实规模出现后才进入新的学习阶段。

## 一个项目贯穿后续课程

后续不再创建互不相关的练习项目。现有[阶段一～二综合实践](../exercises/phase-1-capstone/README.md)会逐步变成最终的 Workspace/Coding Agent：

```text
现有 Tool Loop、Session、Ledger 与 Sandbox
+ 第 9 课的任务集和回归检查
+ 第 10 课的 Workflow、后台任务与取消
+ 第 11 课的并发、配置、健康检查和部署
= 一份可以演示、解释和继续维护的项目
```

项目最终要证明：它能完成一个真实 Workspace 任务；失败可以定位；程序重启后可以恢复；关键安全规则不能被新版本破坏；部署后能够检查健康状态并回退。

## 面试与项目表达

正文继续按工程问题组织，不改成题库。每个阶段结束后，单独整理：

- 五到十个口头复述题；
- 一道系统设计题和常见追问；
- 项目中的代码与运行证据；
- 可以写进简历的表述；
- 尚未掌握、不能宣称的能力。

面试内容检验能否把项目讲清楚，不负责决定课程顺序。

## 可选分支

下面这些内容有价值，但不阻塞主线：

- 知识与数据：Retrieval、RAG、引用和长期 Memory 检索；
- 连接与协作：MCP、A2A 和远程 Tool；
- 测试加速：Recorded-session Replay；
- 观测平台：完整 OpenTelemetry、Collector、生产 Tail Sampling 和 Trace UI；
- 复杂协作：大规模 Multi-Agent 与插件平台；
- 交互环境：Browser、Computer Use、Voice、Realtime 和多模态。

RAG 与 MCP 可以在 Workspace Agent 真正需要知识检索或外部能力时加入。它们是应用侧的重要能力，但不是所有 Runtime 的前置条件。

## 路线怎样维护

README 展示完整主线，`SUMMARY.md` 只列已经存在的课程。当前只详细规划第 9～11 课，不创建空章节。

旧章节只在出现真实读者卡点、示例失败、主要源码变化，或后续课程暴露矛盾时重新打开。一个新框架或醒目的产品功能，不会单独触发全书重写。

## 一手资料

完整核验过程和固定源码版本见[学习路线一手资料综合](../research/learning-roadmap-primary-sources.md)。主要依据包括：

- [Anthropic：Building Effective Agents](https://www.anthropic.com/research/building-effective-agents)
- [Anthropic：Demystifying Evals for AI Agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)
- [OpenAI：Agent Evals](https://developers.openai.com/api/docs/guides/agent-evals)
- [OpenAI Agents SDK](https://github.com/openai/openai-agents-python/tree/89c02c828ee8510fe9a84ee6675608193aa13b02)
- [Google ADK](https://github.com/google/adk-python/tree/c7ffcfa85a8e8970f6318306479d9c4c110583b2)
- [LangGraph](https://github.com/langchain-ai/langgraph/tree/81bf17b23123e4ef8b9d5f49fa09a0122fc2edd1)
- [Phoenix](https://github.com/Arize-ai/phoenix/tree/a71218c7349fb33d1e6d3612cf63cbc70e708c04)
- [Inspect AI](https://github.com/UKGovernmentBEIS/inspect_ai/tree/7aa7343e4a14fa7be07e5a09c7431df5e88c17ee)
