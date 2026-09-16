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

## 阅读主线与专题

主线按职责推进：第 1～3 课建立行动循环，第 4～7 课处理状态与执行边界，第 8～9 课看见和验证结果，第 10～11 课安排任务与执行位置，第 14 课深入持续运行时的资源控制。

第 0 课是历史选读；第 12 课 RAG、第 13 课 MCP 与 Skills 是按需专题。它们保留已有编号，但不是学习第 14 课的必修前置。编号方便引用，具体前置关系以下表为准。

## 章节职责表

每章负责一个主要问题。完成标准是读者需要展示的能力，不表示章节成稿或助手运行检查后，读者就已经掌握。

| 课次 | 主要问题 | 建议先读 | 完成标准 | 唯一实践入口 |
| --- | --- | --- | --- | --- |
| 0 工程史（选读） | Agent 工程中的关键问题怎样出现？ | 无 | 用具体变化解释工具、状态与控制为何进入运行时 | [正文](../chapters/00-Agent工程史.md)，无代码必做项 |
| 1 Agent 基础 | 这个任务为什么需要或不需要 Agent？ | 无 | 对一个需求选择普通程序、Workflow 或 Agent，并说明理由 | [正文](../chapters/01-Agent基础.md)，无代码必做项 |
| 2 Runtime | Model、Harness、Tool 与 Environment 各负责什么？ | 1 | 沿一次行动指出谁提出、谁执行、谁保存与限制 | [正文](../chapters/02-Agent运行时.md)，无代码必做项 |
| 3 工具循环 | 模型申请怎样成为实际动作，再回到模型？ | 2 | 解释完整调用顺序，保持调用编号配对，判断何时结束 | [订单排查](../practice/lesson-03/README.md) |
| 4 会话持久化 | 下次进入时，程序怎样知道之前发生了什么？ | 3 | 保存并读回记录，区分历史、恢复状态和长期信息 | [保存与读回](../practice/lesson-04/README.md) |
| 5 上下文工程 | 保存的材料很多，本次该给模型看哪些？ | 3、4 | 说明原文、摘要和当前输入的关系，保留完整工具消息组 | [压缩与保留](../practice/lesson-05/README.md) |
| 6 工具可靠性 | 动作可能已发生、回执却丢失，怎样安全接手？ | 3、4 | 核查未知结果，复用已确认回执，避免盲目重复副作用 | [写入后中断](../practice/lesson-06/README.md) |
| 7 执行安全 | 模型提出的动作，哪些真的允许执行？ | 2、3 | 区分审批、权限与系统隔离，用允许和拒绝结果验证边界 | [允许与拒绝](../practice/lesson-07/README.md) |
| 8 可观测性 | 一次运行慢或失败，问题发生在哪一步？ | 3、6 | 从 Trace 与 Span 还原调用、重试和等待，不把线索当根因 | [还原运行](../practice/lesson-08/README.md) |
| 9 评估 | 怎样证明任务完成，或改动没有破坏已有能力？ | 3、7、8 | 设计任务与验收规则，根据产物和证据作出版本判断 | [题表与版本判断](../practice/lesson-09/README.md) |
| 10 编排 | 下一步做什么、交给谁、何时合并验收？ | 3、6、9 | 解释修改、验收、修复与停止分支，以及交接和收集结果的责任 | [修改与验收](../practice/lesson-10/README.md) |
| 11 执行环境 | 任务在哪里运行，进程或机器更换后还能保留什么？ | 4、6、7 | 区分客户端、进程与环境丢失，判断恢复所需证据和执行位置 | [跨进程恢复](../practice/lesson-06/README.md)，复用已有实验 |
| 12 RAG（专题） | 怎样把适用的资料取回并交给模型回答？ | 3、5 | 根据候选取回原文，组装输入并说明适用范围 | [正文末尾](../chapters/12-RAG检索增强生成.md) |
| 13 MCP 与 Skills（专题） | 工具服务和任务方法怎样接入已有 Agent？ | 2、3、7 | 复述发现、调用与回传，区分方法说明和真实授权 | [正文末尾](../chapters/13-MCP与Skills.md) |
| 14 运行控制 | 多个动作怎样共享资源、受限推进并真正停止？ | 3、6、10 | 区分并发、频率、次数与时间，核对预算停止和收尾，说明资源释放条件 | [预算与收尾](../practice/lesson-14/README.md) |

## 第 10、11、14 课的边界

第 10 课负责控制流程：安排步骤、选择处理者、收集结果、验收与返工。预算和长任务状态只讲到理解分支所必需的程度；已有示例保持可运行。

第 11 课负责执行位置与持久状态：客户端关闭、进程退出、环境丢失分别意味着什么，厂商替应用接管哪些责任。会话格式和 Ledger 的完整基础说明仍由第 4、6 课负责。

第 14 课负责运行过程中的限制与资源回收：共享并发、请求频率、模型与工具次数、截止时间、取消信号、子进程和输出额度。它引用第 10 课的流程，复用同一个工作流实现，但文章和完成标准从自己的实践入口进入。

具体规则是：一个概念在负责它的章节完整解释，其他章节简要提醒并链接；复用代码不改变课程归属，也不要求复制一套实现。

## 材料、验证与学习进度分别记录

- **正文状态**：文章是否成稿，是否进入正式目录。当前正式正文为第 0～14 课，第 14 课是本轮新增。
- **实践证据**：具体命令、源码版本与哪些条件检查通过。最新运行约定放在对应实践入口，历史证据保留日期与范围。
- **学习进度**：读者能否独立解释或作出关键判断。不能由文章存在、助手运行通过或发布完成代替。
- **发布状态**：提交、推送与 GitBook 实际展示分别核验；工作区正文存在不等于已经发布。

第 14 课的配置工作流已经验证工具次数额度与无工具收尾；共享并发、总截止时间、进程回收和日志磁盘额度尚未全部集成。第 13 课的本地 MCP 实验已经验证跨进程调用和错误请求，尚未接入真实模型，详细条件见[实践记录](../practice/optional/mcp/README.md)。这些都是材料范围，不是读者成绩。

## 一个项目与各课入口

[Workspace Agent](../practice/workspace-agent/README.md)承载工具循环、文件工具、Session、Context 与 Ledger。第 9 课在外部组织验收，第 10 课添加修复流程，第 14 课在同一条流程中施加次数限制与收尾策略。

每课只有一个[实践入口](../practice/README.md)，入口说明目标、必做判断、运行方法和证据范围。入口可以引用已有实现；第 14 课复用 `practice/lesson-10/workflow_demo.py`，不增加转发脚本或另一套 Agent。

安全、Tracing、交接与恢复仍有独立机制实验，不能把它们都描述为已集成的生产系统。SQLite、目录分页和复杂交接继续作为可选实践。

## 开课与成文的停止条件

开始一个新主题前，先明确所属课程、主要问题、前置知识与完成标准。少量理解检查和一个相应实验足以回答该问题时，就转入成文；没有新证据缺口，不继续增加同类判断题。

成文时先核对章节边界，保留源码事实、应用策略和实验结果的区别。只有发现具体错误、读者卡点或状态变化，才修改旧章相应位置；新课的出现本身不触发旧章整体重写。

课程边界与前置关系统一维护在本文，README 和 SUMMARY 负责导航，各课实践说明维护运行与验收条件，不再各自重复一套学习进度。

## 后续范围

先把第 14 课读者练习与现有 Agent 对齐，再根据应用的实际缺口进入上线运行：配置与密钥、健康检查、部署和回滚，以及把线上失败补回评测任务集。后续课次暂不预分配，避免再次把所有生产问题塞进一课。

大规模 Multi-Agent、完整观测平台、高可用调度、A2A、浏览器和多模态都按真实需求进入，不阻塞当前主线。阶段结束后的面试表达应基于已完成的项目证据，不能反过来把正文扩成题库。

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
