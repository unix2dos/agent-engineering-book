# Agent 工程学习路线：一手资料综合

> 核验日期：2026-09-04
> 目标读者：会基础 Python、Git 和命令行，但尚不能独立设计、实现和排查 Agent 系统的人。
> 研究原则：只使用官方文档、官方课程、规范和源码；路线按能力依赖组织，不按框架名组织。

## 结论先行

多个官方体系虽然使用不同术语，但反复出现的是同一条工程主线：

```text
判断是否需要 Agent
-> 跑通单 Agent Loop 与工具反馈
-> 管理状态、上下文与恢复
-> 限制工具副作用并允许人工介入
-> 用 Trace 看见真实运行
-> 用 Dataset、Evaluator 和回归测试判断是否变好
-> 有证据后再增加编排、Multi-Agent 和部署复杂度
```

这个顺序不是照抄某一套课程，而是对多份一手资料的综合判断：Anthropic 建议从最简单方案开始，只在结果证明有必要时增加复杂度；OpenAI 当前 Agent Eval 指南明确建议在仍处于行为调试阶段时先看 Trace，明确什么是“好”以后再建立可重复的 Dataset 和 Eval Run；LangGraph 则说明长任务、人工中断和故障恢复依赖持久化状态。[Anthropic Building Effective Agents](https://www.anthropic.com/research/building-effective-agents)；[OpenAI Agent Evals](https://developers.openai.com/api/docs/guides/agent-evals)；[LangGraph Checkpoint](https://github.com/langchain-ai/langgraph/blob/81bf17b23123e4ef8b9d5f49fa09a0122fc2edd1/libs/checkpoint/README.md#L17-L60)

因此，本书第 0～8 课已经完成“能行动、能保存、能恢复、能限制”这段主干。接下来最合理的三项能力仍是：

1. **Trace 与可观测性**：先把一次运行发生了什么看清楚；
2. **Evaluation**：再把“这次看起来不错”变成可重复实验；
3. **回归门禁与失败回流**：最后让关键错误阻止发布，并把新失败补回测试集。

这三项完成前，不建议把 Multi-Agent、RAG、MCP/A2A 或某个新框架插入主线。它们值得学，但属于后续能力或按需求选择的分支。

## 研究样本与版本锚点

下面不是“推荐框架排行榜”，而是本次用于交叉验证能力依赖的证据样本。

| 证据角色 | 一手资料 | 本次读取的固定版本或页面 |
| --- | --- | --- |
| 通用 Runtime、Guardrail、Trace 与测试 | OpenAI Agents SDK | [`89c02c8`](https://github.com/openai/openai-agents-python/commit/89c02c828ee8510fe9a84ee6675608193aa13b02)：[Runtime 能力边界](https://github.com/openai/openai-agents-python/blob/89c02c828ee8510fe9a84ee6675608193aa13b02/docs/index.md#L18-L48)、[Loop](https://github.com/openai/openai-agents-python/blob/89c02c828ee8510fe9a84ee6675608193aa13b02/docs/running_agents.md#L24-L45)、[Guardrails](https://github.com/openai/openai-agents-python/blob/89c02c828ee8510fe9a84ee6675608193aa13b02/docs/guardrails.md#L10-L38)、[Tracing](https://github.com/openai/openai-agents-python/blob/89c02c828ee8510fe9a84ee6675608193aa13b02/docs/tracing.md#L1-L59)、[Testing](https://github.com/openai/openai-agents-python/blob/89c02c828ee8510fe9a84ee6675608193aa13b02/docs/testing.md#L1-L23) |
| Eval 设计与生产约束 | OpenAI Platform | 2026-09-04 读取：[Agent Evals](https://developers.openai.com/api/docs/guides/agent-evals)、[Eval Best Practices](https://developers.openai.com/api/docs/guides/evaluation-best-practices)、[Production Best Practices](https://developers.openai.com/api/docs/guides/production-best-practices) |
| 克制复杂度、Workflow 与 Agent 的边界 | Anthropic | [Building Effective Agents](https://www.anthropic.com/research/building-effective-agents)。该文已由 Anthropic 标注其 2024 年工具生态内容可能过时，因此本报告只采用架构原则，不采用其中的当前产品清单。 |
| Claude Agent SDK 的真实开源边界 | Claude Agent SDK Python | [`0b08ed1`](https://github.com/anthropics/claude-agent-sdk-python/commit/0b08ed120ac6dd4ec132b997ddf44b4dc81545c2)：SDK 捆绑并驱动 Claude Code CLI，[README](https://github.com/anthropics/claude-agent-sdk-python/blob/0b08ed120ac6dd4ec132b997ddf44b4dc81545c2/README.md#L11-L35)；开源仓库能证明 Transport、消息和配置，不能冒充 Claude Code 完整 Runtime 源码。 |
| 完整开发生命周期 | Google ADK Python | [`89777c1`](https://github.com/google/adk-python/commit/89777c146bd26c04bd45d9ed67b5d3e64a6957f1)：[框架范围](https://github.com/google/adk-python/blob/89777c146bd26c04bd45d9ed67b5d3e64a6957f1/README.md#L32-L75)、[Runner](https://github.com/google/adk-python/blob/89777c146bd26c04bd45d9ed67b5d3e64a6957f1/docs/guides/runners/runner/index.md#L1-L11)、[Evaluation 样例](https://github.com/google/adk-python/blob/89777c146bd26c04bd45d9ed67b5d3e64a6957f1/contributing/samples/evaluation/README.md#L1-L47) |
| 长任务、状态与恢复 | LangGraph | [`81bf17b`](https://github.com/langchain-ai/langgraph/commit/81bf17b23123e4ef8b9d5f49fa09a0122fc2edd1)：[定位与能力](https://github.com/langchain-ai/langgraph/blob/81bf17b23123e4ef8b9d5f49fa09a0122fc2edd1/README.md#L24-L57)、[Checkpoint 与 Pending Writes](https://github.com/langchain-ai/langgraph/blob/81bf17b23123e4ef8b9d5f49fa09a0122fc2edd1/libs/checkpoint/README.md#L17-L60) |
| 广度型初学课程 | Microsoft AI Agents for Beginners | [`7b20684`](https://github.com/microsoft/ai-agents-for-beginners/commit/7b20684e56ae3e565d0568bb13de06912d4d19bc)：[当前课程目录](https://github.com/microsoft/ai-agents-for-beginners/blob/7b20684e56ae3e565d0568bb13de06912d4d19bc/README.md#L87-L115) |
| 基础、框架练习与 Benchmark | Hugging Face Agents Course | [`8c0832e`](https://github.com/huggingface/agents-course/commit/8c0832eae634ebb34541c65265caa6da4c5d2c57)：[四阶段课程](https://github.com/huggingface/agents-course/blob/8c0832eae634ebb34541c65265caa6da4c5d2c57/README.md#L7-L32)、[详细目录](https://github.com/huggingface/agents-course/blob/8c0832eae634ebb34541c65265caa6da4c5d2c57/units/en/_toctree.yml#L13-L158) |
| Trace、Dataset、Experiment 与 CI | Phoenix | [`a71218c`](https://github.com/Arize-ai/phoenix/commit/a71218c7349fb33d1e6d3612cf63cbc70e708c04)：[Trace/Span](https://github.com/Arize-ai/phoenix/blob/a71218c7349fb33d1e6d3612cf63cbc70e708c04/docs/phoenix/tracing/concepts-tracing/what-are-traces.mdx#L6-L65)、[pytest/CI 集成](https://github.com/Arize-ai/phoenix/blob/a71218c7349fb33d1e6d3612cf63cbc70e708c04/docs/phoenix/evaluation/integrations/pytest.mdx#L1-L41) |
| Evaluation 的最小结构 | Inspect AI | [`7aa7343`](https://github.com/UKGovernmentBEIS/inspect_ai/commit/7aa7343e4a14fa7be07e5a09c7431df5e88c17ee)：[Dataset + Solver + Scorer](https://github.com/UKGovernmentBEIS/inspect_ai/blob/7aa7343e4a14fa7be07e5a09c7431df5e88c17ee/docs/index.qmd#L85-L95)、[Agent Eval 与 Sandbox](https://github.com/UKGovernmentBEIS/inspect_ai/blob/7aa7343e4a14fa7be07e5a09c7431df5e88c17ee/docs/index.qmd#L147-L179) |
| 当前 Coding Agent Runtime 证据 | Pi、OpenClaw、Codex、Hermes、OpenCode、DeepSeek Harness | [Pi `6aedd10`](https://github.com/earendil-works/pi/commit/6aedd1066e540642165aa30fa7b4a1b863778aa7)、[OpenClaw `29b57be`](https://github.com/openclaw/openclaw/commit/29b57be03d2a26332f508d91cf54d58a9a42e7a2)、[Codex `b995d06`](https://github.com/openai/codex/commit/b995d06050ee3db5c6298f4a007975da94399c71)、[Hermes `6327930`](https://github.com/NousResearch/hermes-agent/commit/63279301bcbdc185c1b07b98a9312eb0c862f26d)、[OpenCode `c0f09af`](https://github.com/anomalyco/opencode/commit/c0f09afef5056cfbebdf5123162267cb6efbd960)、[DeepSeek Harness `76fda72`](https://github.com/deepseek-ai/deepseek-harness/commit/76fda729799fe9b3848dbe2c211d4b231032b81e) |

## 反复出现的能力域

| 能力域 | 一手资料反复出现的内容 | 对本书的含义 |
| --- | --- | --- |
| 判断何时使用 Agent | Anthropic 区分固定代码路径的 Workflow 与由模型动态决定过程的 Agent，并建议先寻找最简单方案；OpenAI 也区分应用代码编排与模型编排。[Anthropic](https://www.anthropic.com/research/building-effective-agents)；[OpenAI Orchestration](https://github.com/openai/openai-agents-python/blob/89c02c828ee8510fe9a84ee6675608193aa13b02/docs/multi_agent.md#L1-L50) | 第 1 课的“是否真的需要 Agent”是长期判断框架，不是入门铺垫。 |
| Loop、Tool 与 Environment Feedback | OpenAI Runner 按“调用模型—分类输出—执行 Tool/Handoff—把结果放回输入—继续或结束”运行；HF 基础单元也按 Thought/Action/Observation 讲解。[OpenAI Loop](https://github.com/openai/openai-agents-python/blob/89c02c828ee8510fe9a84ee6675608193aa13b02/docs/running_agents.md#L24-L45)；[HF Unit 1](https://github.com/huggingface/agents-course/blob/8c0832eae634ebb34541c65265caa6da4c5d2c57/units/en/_toctree.yml#L13-L42) | 必须先亲手跑通一个最小循环，才能正确理解框架替自己做了什么。 |
| Session、Context、Memory 与恢复 | Google ADK Runner 负责 Session 查找、Context 组装、事件流与持久化；LangGraph Checkpoint 保存每个 Superstep 的图状态及 Pending Writes；Pi 将完整 Session Entry 与给模型的压缩视图区分开。[ADK Runner](https://github.com/google/adk-python/blob/89777c146bd26c04bd45d9ed67b5d3e64a6957f1/docs/guides/runners/runner/index.md#L55-L89)；[LangGraph Checkpoint](https://github.com/langchain-ai/langgraph/blob/81bf17b23123e4ef8b9d5f49fa09a0122fc2edd1/libs/checkpoint/README.md#L17-L60)；[Pi Compaction](https://github.com/earendil-works/pi/blob/6aedd1066e540642165aa30fa7b4a1b863778aa7/packages/coding-agent/docs/compaction.md#L25-L81) | 第 4～6 课应继续区分“事实记录、恢复状态、模型本次视图和长期记忆”，不能合并成一个 `history` 概念。 |
| 工具可靠性与副作用 | DeepSeek Harness 在执行前记录 Tool Call，依次经过策略、审批、Guard、执行和结果归一化，再形成单一 Tool Result；OpenCode 分开维护 Session Processor 与 Permission Service。[DeepSeek Tool Pipeline](https://github.com/deepseek-ai/deepseek-harness/blob/76fda729799fe9b3848dbe2c211d4b231032b81e/docs/tool-execution-pipeline.zh.md#L8-L62)；[OpenCode Session Processor](https://github.com/anomalyco/opencode/blob/c0f09afef5056cfbebdf5123162267cb6efbd960/packages/opencode/src/session/processor.ts#L29-L75)；[OpenCode Permission](https://github.com/anomalyco/opencode/blob/c0f09afef5056cfbebdf5123162267cb6efbd960/packages/opencode/src/permission/index.ts#L28-L38) | `tool_call_id`、执行状态、幂等和对账是 Runtime 工程能力，不应被普通“Function Calling 教程”吞掉。 |
| 安全、权限与人工介入 | OpenAI 区分 Agent 输入/输出 Guardrail 和逐次 Tool Guardrail，并说明阻塞与并行检查的副作用差异；OpenClaw 把 Tool Policy、Sandbox 和 Elevated 分为三个控制面；Hermes 明确把 OS 级隔离视为对抗不可信模型的承重边界。[OpenAI Guardrails](https://github.com/openai/openai-agents-python/blob/89c02c828ee8510fe9a84ee6675608193aa13b02/docs/guardrails.md#L10-L38)；[OpenClaw Controls](https://github.com/openclaw/openclaw/blob/29b57be03d2a26332f508d91cf54d58a9a42e7a2/docs/gateway/sandbox-vs-tool-policy-vs-elevated.md#L8-L43)；[Hermes Security](https://github.com/NousResearch/hermes-agent/blob/63279301bcbdc185c1b07b98a9312eb0c862f26d/SECURITY.md#L32-L76) | 安全必须从第一次引入有副作用的 Tool 就开始；不能等到“部署篇”才补。 |
| Trace 与 Observability | OpenAI Trace 覆盖 Runner、模型 Turn、生成、Tool、Guardrail 和 Handoff；Phoenix 用父子 Span 表达一次请求中各项子操作，并保存时间和属性。[OpenAI Tracing](https://github.com/openai/openai-agents-python/blob/89c02c828ee8510fe9a84ee6675608193aa13b02/docs/tracing.md#L15-L47)；[Phoenix Trace](https://github.com/Arize-ai/phoenix/blob/a71218c7349fb33d1e6d3612cf63cbc70e708c04/docs/phoenix/tracing/concepts-tracing/what-are-traces.mdx#L6-L65) | Trace 不是漂亮日志；它要能回答哪个步骤、输入、Tool、耗时和父子关系导致结果。 |
| Evaluation 与回归 | OpenAI 建议从目标、Dataset、指标、比较到持续评估，并用生产失败扩充 Eval Set；Google ADK 的样例把同一 Agent 分别交给确定性匹配、自定义指标、LLM Judge、Rubric 和用户模拟；Inspect 把 Eval 最小化为 Dataset、Solver 和 Scorer。[OpenAI Eval Best Practices](https://developers.openai.com/api/docs/guides/evaluation-best-practices)；[ADK Evaluation Samples](https://github.com/google/adk-python/blob/89777c146bd26c04bd45d9ed67b5d3e64a6957f1/contributing/samples/evaluation/README.md#L1-L47)；[Inspect AI](https://github.com/UKGovernmentBEIS/inspect_ai/blob/7aa7343e4a14fa7be07e5a09c7431df5e88c17ee/docs/index.qmd#L85-L95) | 先定义“成功是什么”，再选择评分器。不能先装评测平台，再临时找指标。 |
| 编排与 Multi-Agent | Anthropic 把 Prompt Chaining、Routing、Parallelization、Orchestrator-workers 和 Evaluator-optimizer 视为可组合模式，并建议只在简单方案不足时增加复杂度；OpenAI 区分 Agents-as-tools、Handoff 和代码编排，并要求投入监控与 Eval。[Anthropic](https://www.anthropic.com/research/building-effective-agents)；[OpenAI Orchestration](https://github.com/openai/openai-agents-python/blob/89c02c828ee8510fe9a84ee6675608193aa13b02/docs/multi_agent.md#L20-L50) | Multi-Agent 不是“更高级的单 Agent”，而是已知瓶颈出现后的一种架构选择。 |
| 部署与持续运营 | Claude Agent SDK 的托管文档要求处理长驻子进程、Session 持久化、隔离、Observability、密钥、并发和多租户；OpenAI 生产指南把密钥、扩缩容、限流、延迟、成本、监控和合规列为生产问题。[Claude Agent SDK Hosting](https://platform.claude.com/docs/en/agent-sdk/hosting)；[OpenAI Production Best Practices](https://developers.openai.com/api/docs/guides/production-best-practices) | “本机成功运行”不等于可上线；部署是一个独立能力阶段。 |

## 真正的前置关系

### 1. 为什么 Trace 应在 Evaluation 前面？

如果一次任务失败时只能看到最终答案，就不知道问题来自 Prompt、Tool 选择、参数、Tool Result、Handoff 还是停止条件。OpenAI 当前 Agent Eval 指南把“仍在调试行为时先看 Trace”放在“明确什么是好以后建立 Dataset 与 Eval Run”之前；Phoenix 也把 Trace 拆成可定位的父子 Span。[OpenAI Agent Evals](https://developers.openai.com/api/docs/guides/agent-evals)；[Phoenix Trace](https://github.com/Arize-ai/phoenix/blob/a71218c7349fb33d1e6d3612cf63cbc70e708c04/docs/phoenix/tracing/concepts-tracing/what-are-traces.mdx#L45-L65)

因此，Trace 的学习目标不是接入某个 Dashboard，而是先获得一份能解释失败的因果记录。没有这份记录，Eval 即使给出低分，也很难指导修改。

### 2. 为什么 Evaluation 应在 Multi-Agent 前面？

增加 Agent 会新增路由、Handoff、并发、共享状态和责任边界。OpenAI 的 Eval 指南明确指出，是否使用 Multi-Agent 应由 Eval 驱动，并警告直接从 Multi-Agent 开始会增加不必要的复杂度；Anthropic 同样建议只有简单方案无法达到可测目标时才升级复杂度。[OpenAI Eval Best Practices](https://developers.openai.com/api/docs/guides/evaluation-best-practices#multi-agent-architectures)；[Anthropic](https://www.anthropic.com/research/building-effective-agents)

所以应先证明单 Agent 在什么具体样本上失败，再判断失败源是否真的是“一个 Prompt 承担太多职责”。

### 3. 为什么安全不能排到最后？

一旦 Tool 可以写文件、发邮件、付款或执行 Shell，系统就已经有真实副作用。OpenAI Guardrail 文档指出，并行 Input Guardrail 可能在判定完成前已经消耗 Token 或执行 Tool；Hermes 则直接声明进程内规则不是对抗恶意模型的隔离边界。[OpenAI Guardrails](https://github.com/openai/openai-agents-python/blob/89c02c828ee8510fe9a84ee6675608193aa13b02/docs/guardrails.md#L32-L38)；[Hermes Security](https://github.com/NousResearch/hermes-agent/blob/63279301bcbdc185c1b07b98a9312eb0c862f26d/SECURITY.md#L58-L65)

因此，本书把可靠性与 Sandbox 放在可观测性之前是合理的。未来所有有副作用的练习仍应默认继承第 7～8 课边界，而不是每次重新发明安全规则。

### 4. 为什么部署应晚于最小评估闭环？

部署会引入新的失效面：持久化、密钥、并发、限流、成本、延迟、多租户和观测数据隐私。Claude Agent SDK 托管文档与 OpenAI 生产指南都把这些列为独立的生产责任；Google ADK 也把本地 InMemoryRunner 与使用持久服务的生产 Runner 分开。[Claude Agent SDK Hosting](https://platform.claude.com/docs/en/agent-sdk/hosting)；[OpenAI Production Best Practices](https://developers.openai.com/api/docs/guides/production-best-practices)；[ADK Runner](https://github.com/google/adk-python/blob/89777c146bd26c04bd45d9ed67b5d3e64a6957f1/docs/guides/runners/runner/index.md#L121-L152)

没有回归样本时，上线只能证明“服务能启动”，不能证明 Agent 行为没有退步。

## 各套资料的分歧

### 分歧一：框架应该多早出现？

- Anthropic 建议优先直接使用模型 API，并提醒框架可能遮住底层 Prompt、Response 和调试细节。[Anthropic](https://www.anthropic.com/research/building-effective-agents)
- HF 在基本 Agent Loop 后立即进入 smolagents、LlamaIndex 和 LangGraph，适合快速体验多种工具，但课程组织明显偏框架实践。[HF 课程目录](https://github.com/huggingface/agents-course/blob/8c0832eae634ebb34541c65265caa6da4c5d2c57/units/en/_toctree.yml#L45-L110)
- Google ADK 把 Agent、Workflow、Evaluation 和 Deployment 放入同一开发套件，适合学习完整生命周期，但它的产品导航不等于教学前置关系。[ADK README](https://github.com/google/adk-python/blob/89777c146bd26c04bd45d9ed67b5d3e64a6957f1/README.md#L32-L75)

**本书取舍**：先手写一次最小 Runtime，再用框架验证相同责任如何被封装。框架是实现样本，不是课程主干。

### 分歧二：状态管理是基础能力还是高级能力？

LangGraph 把 Durable Execution、HITL、Memory 和 Deployment 作为核心定位；HF 主课程更重 Loop、框架和最终 Benchmark，没有把故障恢复作为同等独立主线。[LangGraph README](https://github.com/langchain-ai/langgraph/blob/81bf17b23123e4ef8b9d5f49fa09a0122fc2edd1/README.md#L35-L57)；[HF 课程目录](https://github.com/huggingface/agents-course/blob/8c0832eae634ebb34541c65265caa6da4c5d2c57/README.md#L15-L32)

**本书取舍**：目标是独立排查 Runtime，而不只是完成一个 Demo，因此 Session、Checkpoint、Compaction 和副作用恢复属于前置主干。

### 分歧三：Observability 与 Evaluation 应放在哪里？

HF 把 Observability/Evaluation 放在 Bonus Unit，但最终项目又使用 Benchmark；Microsoft 把生产、协议、Context、Memory、部署与安全并列为可独立进入的课程；OpenAI 当前明确给出 Trace → Dataset/Eval Run 的改进顺序。[HF README](https://github.com/huggingface/agents-course/blob/8c0832eae634ebb34541c65265caa6da4c5d2c57/README.md#L15-L32)；[Microsoft 课程目录](https://github.com/microsoft/ai-agents-for-beginners/blob/7b20684e56ae3e565d0568bb13de06912d4d19bc/README.md#L94-L115)；[OpenAI Agent Evals](https://developers.openai.com/api/docs/guides/agent-evals)

**本书取舍**：Trace 不是选读。它承接已经完成的 Runtime；Evaluation 和回归随后建立可测的改进闭环。

### 分歧四：Eval 是 Benchmark、评分平台，还是工程测试？

Inspect 用 `Dataset + Solver + Scorer` 描述 Eval；Google ADK 同时展示确定性匹配、自定义指标、Rubric、LLM Judge 和用户模拟；Phoenix 把可以严格判断的行为作为 CI 中的 `assert`，把开放质量作为趋势信号。[Inspect AI](https://github.com/UKGovernmentBEIS/inspect_ai/blob/7aa7343e4a14fa7be07e5a09c7431df5e88c17ee/docs/index.qmd#L85-L95)；[ADK Samples](https://github.com/google/adk-python/blob/89777c146bd26c04bd45d9ed67b5d3e64a6957f1/contributing/samples/evaluation/README.md#L1-L47)；[Phoenix pytest](https://github.com/Arize-ai/phoenix/blob/a71218c7349fb33d1e6d3612cf63cbc70e708c04/docs/phoenix/evaluation/integrations/pytest.mdx#L34-L41)

**本书取舍**：Evaluation 是“带样本和判断规则的重复实验”。Benchmark 和平台只是实现形式；正确的 Tool、禁止的副作用和完整协议可以设硬门禁，帮助度、语气等开放质量先记录趋势。

## 稳定能力与易变实现

| 相对稳定，适合成为课程主干 | 变化很快，应固定版本并作为案例 |
| --- | --- |
| Model 与 Harness 的责任边界 | SDK 类名、配置字段和事件名称 |
| Tool Call、Tool Result、停止条件与错误回传 | Provider 的 Tool Schema 方言和托管 Tool 清单 |
| Session、Transcript、Checkpoint、Prompt View 的职责差异 | Provider 托管 Conversation 与 Compaction 的具体 API |
| 事实记录与可重建索引的区别 | JSONL、SQLite、PostgreSQL 等某项目当下的默认选择 |
| 副作用、幂等、对账与故障恢复 | 某 Runtime 当前的状态枚举和恢复入口 |
| 最小权限、逐次批准和 OS 级隔离 | Seatbelt、Bubblewrap、容器、microVM 与云 Sandbox 产品配置 |
| Trace/Span 的父子关系与关联 ID | Dashboard、Exporter、Telemetry 字段和默认采集内容 |
| 目标、Dataset、Evaluator、比较与回归门禁 | LLM Judge 模型、Rubric 语法与具体 Eval 平台 |
| 固定 Workflow 与模型动态决策的取舍 | Handoff、Subagent、Graph API 和多 Agent 产品形态 |
| 版本、部署、监控、成本、延迟与反馈回流 | 模型名称、价格、限流、缓存和托管服务能力 |

“能力稳定、产品表面易变”并不是抽象提醒。2026-09-04 读取的 OpenAI Eval Best Practices 已声明旧 Evals Platform 将在 2026 年停止服务，但目标、Dataset、指标、比较和持续评估这套方法仍然成立。[OpenAI Eval Best Practices](https://developers.openai.com/api/docs/guides/evaluation-best-practices)

## 推荐能力阶段

### 前置能力：能运行和读懂最小程序

- 基础 Python：函数、字典/列表、异常、文件、异步代码的阅读能力；
- 基础 Git：能够查看 Diff、Commit 和固定源码版本；
- 基础 CLI：能够运行程序、读取退出码和定位错误栈；
- 基础模型 API：知道一次请求、一次响应和 Token 成本是什么。

这与 HF 课程声明的基础 Python、基础 LLM 前置要求一致；本书额外要求 Git 和 CLI，是因为目标包含源码核验与故障排查。[HF Prerequisites](https://github.com/huggingface/agents-course/blob/8c0832eae634ebb34541c65265caa6da4c5d2c57/README.md#L29-L32)

### 阶段一：判断与行动——已由第 0～3 课覆盖

学习判断任务是否需要 Agent，并亲手实现 `Model -> Tool Call -> Harness -> Tool -> Tool Result -> Model Final`。结束时，学习者应能解释 Tool Schema、Router、停止条件和最大请求次数，而不是只会调用一个框架的 `run()`。

### 阶段二：状态与控制——已由第 4～8 课覆盖

把完整事实记录、恢复点、模型视图、长期记忆、存储选择、执行账本和 Sandbox 分开。结束时，学习者应能在重启、输出截断、未知副作用和权限拒绝的情况下判断下一步。

这两阶段与当前 Coding Agent 源码能够互相验证：Pi 把 Session Entry 与压缩后模型视图区分开；DeepSeek Harness 展示 Tool Call 到单一 Tool Result 的完整流水线；OpenClaw 把 Tool Policy、Sandbox 与 Elevated 分开。[Pi Compaction](https://github.com/earendil-works/pi/blob/6aedd1066e540642165aa30fa7b4a1b863778aa7/packages/coding-agent/docs/compaction.md#L25-L81)；[DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness/blob/76fda729799fe9b3848dbe2c211d4b231032b81e/docs/tool-execution-pipeline.zh.md#L8-L62)；[OpenClaw](https://github.com/openclaw/openclaw/blob/29b57be03d2a26332f508d91cf54d58a9a42e7a2/docs/gateway/sandbox-vs-tool-policy-vs-elevated.md#L8-L43)

### 阶段三：看见与改进——接下来只详细规划这三项能力

#### 能力 1：Trace 与因果运行记录

在现有综合实践外包一层 `trace_id`，为每次 Model、Tool、Approval 和恢复尝试记录父子 `span_id`、开始/结束时间、状态、Token/成本和错误原因；同时显式决定哪些 Prompt、Tool 参数和结果允许进入遥测。OpenAI 和 Phoenix 都用 Trace 表示端到端操作、Span 表示子操作；Google ADK 当前文档还提醒 Prompt、回复、Tool 参数和结果可能经 Telemetry 离开进程。[OpenAI Tracing](https://github.com/openai/openai-agents-python/blob/89c02c828ee8510fe9a84ee6675608193aa13b02/docs/tracing.md#L15-L47)；[Phoenix Trace](https://github.com/Arize-ai/phoenix/blob/a71218c7349fb33d1e6d3612cf63cbc70e708c04/docs/phoenix/tracing/concepts-tracing/what-are-traces.mdx#L6-L65)；[ADK Telemetry](https://github.com/google/adk-python/blob/89777c146bd26c04bd45d9ed67b5d3e64a6957f1/docs/guides/telemetry/telemetry_config/index.md#L1-L39)

**最小证据**：给定一个失败 Trace，学习者能指出失败在 Model、Tool、Policy、Backend 还是恢复逻辑，而不是只说“Agent 答错了”。

#### 能力 2：Evaluation 的实验结构

从已经遇到的真实失败中选 10 个样本，给每个样本定义输入、预期不变量、允许变化的质量维度和评分方式。优先用普通代码判断 JSON 是否有效、Tool 是否选对、危险动作是否被拒绝；只有无法确定性判断的质量再使用人工或 LLM Judge，并检查自动评分与人工判断是否一致。OpenAI 建议使用任务特定目标、生产/历史样本并校准自动评分；Phoenix 区分硬不变量与质量信号；Inspect 把结构固定为 Dataset、Solver、Scorer。[OpenAI Eval Best Practices](https://developers.openai.com/api/docs/guides/evaluation-best-practices)；[Phoenix pytest](https://github.com/Arize-ai/phoenix/blob/a71218c7349fb33d1e6d3612cf63cbc70e708c04/docs/phoenix/evaluation/integrations/pytest.mdx#L34-L52)；[Inspect AI](https://github.com/UKGovernmentBEIS/inspect_ai/blob/7aa7343e4a14fa7be07e5a09c7431df5e88c17ee/docs/index.qmd#L85-L95)

**最小证据**：同一个 Agent 修改前后运行同一批样本，能够看到逐例结果和汇总变化，而不是凭一次对话判断好坏。

#### 能力 3：回归门禁与失败回流

把“绝不能退步”的硬不变量接入普通测试/CI；把非确定性质量作为多次运行后的趋势，避免一次 Judge 波动阻止所有发布；将线上或人工 Review 发现的新失败去敏后补入 Dataset。Phoenix 的 pytest 集成把 `assert` 结果直接接到 CI Exit Code，同时建议把开放质量作为趋势信号；HF 也把最终学习成果放到可自动评估的 Benchmark 中。[Phoenix pytest](https://github.com/Arize-ai/phoenix/blob/a71218c7349fb33d1e6d3612cf63cbc70e708c04/docs/phoenix/evaluation/integrations/pytest.mdx#L1-L41)；[HF Final Project](https://github.com/huggingface/agents-course/blob/8c0832eae634ebb34541c65265caa6da4c5d2c57/README.md#L24-L26)

**最小证据**：故意破坏 Tool Result 配对或安全拒绝规则时，CI 必须失败；只改变一句自然语言措辞时，不应因为精确字符串不同而误报。

### 阶段四：编排与长任务——完成阶段三后再展开

能力包括固定 Workflow、Routing、Parallel/Fan-out、Retry、Interrupt/Resume、Handoff、Subagent 和 Multi-Agent。选择标准是：现有单 Agent 的 Eval 已经证明需要职责拆分、并行或持续运行，而不是“多个 Agent 看起来更先进”。Anthropic 与 OpenAI 都明确把代码编排、模型编排及其成本/确定性取舍分开；LangGraph 专门为长任务、持久状态和人工中断提供低层编排。[Anthropic](https://www.anthropic.com/research/building-effective-agents)；[OpenAI Orchestration](https://github.com/openai/openai-agents-python/blob/89c02c828ee8510fe9a84ee6675608193aa13b02/docs/multi_agent.md#L1-L50)；[LangGraph README](https://github.com/langchain-ai/langgraph/blob/81bf17b23123e4ef8b9d5f49fa09a0122fc2edd1/README.md#L35-L57)

### 可选能力分支

- **知识与数据**：Retrieval、RAG、引用、长期 Memory 的写入/检索/遗忘与效果评估；
- **连接与协作**：MCP、A2A、远程 Tool、跨 Agent 协议与不可信边界；
- **交互环境**：Browser、Computer Use、Voice、Realtime 和多模态输入；
- **专用执行环境**：Coding Agent、数据分析 Agent、Sandbox Agent。

Microsoft 和 HF 的课程证明这些都是常见 Agent 主题，但它们的目录也显示课程更像可独立进入的广度集合；这不能证明 RAG、MCP 或 Browser 是 Runtime 的统一前置知识。[Microsoft 课程目录](https://github.com/microsoft/ai-agents-for-beginners/blob/7b20684e56ae3e565d0568bb13de06912d4d19bc/README.md#L94-L115)；[HF 课程目录](https://github.com/huggingface/agents-course/blob/8c0832eae634ebb34541c65265caa6da4c5d2c57/README.md#L15-L32)

### 阶段五：部署与运营

能力包括部署拓扑、持久化服务、密钥与租户隔离、并发与队列、限流与重试、延迟/成本预算、版本与回滚、线上监控、审计和事故处理。每个能力分支最终都要回到这个阶段，但只有在已有 Trace 与最小 Eval 后，生产结果才可观察、可比较。[Claude Agent SDK Hosting](https://platform.claude.com/docs/en/agent-sdk/hosting)；[OpenAI Production Best Practices](https://developers.openai.com/api/docs/guides/production-best-practices)

## 课程维护建议

1. 主目录始终展示完整能力阶段，但只为最近三项能力写具体教学计划。
2. 每一阶段至少留下一份可运行的综合证据，而不是只完成框架 Quickstart。
3. 新框架只有在能回答现有参考集回答不了的问题时，才加入 Topic Reference。
4. Vendor API、模型名、默认配置和产品能力必须固定版本；稳定的责任边界与判断方法写入正文。
5. 第 9～11 课完成后，根据综合实践和 Eval 结果决定先展开阶段四，还是插入一个确有需要的能力分支；阶段五仍在目标 Agent 具备最小评估闭环后进入。

## 当前资料中的风险提示

- Anthropic 的 Building Effective Agents 已主动提示 2024 年工具生态部分过时；只保留其“从简单方案开始、Workflow/Agent 区分、用测量证明复杂度”的原则。[Anthropic](https://www.anthropic.com/research/building-effective-agents)
- OpenAI 当前 Eval Best Practices 已公布旧 Evals Platform 的停止计划；课程应教授 Evaluation 方法，而不是绑定将被关闭的产品入口。[OpenAI Eval Best Practices](https://developers.openai.com/api/docs/guides/evaluation-best-practices)
- Google ADK 当前主分支是 2.0，并明确记录 Agent API、Event Model 和 Session Schema 的破坏性变化；正文若采用其字段，必须固定版本。[ADK README](https://github.com/google/adk-python/blob/89777c146bd26c04bd45d9ed67b5d3e64a6957f1/README.md#L40-L45)
- Claude Agent SDK Python 的公开源码是 CLI Transport 与 SDK 层，不能据此声称 Claude Code 核心 Runtime 已开源。[Claude Agent SDK README](https://github.com/anthropics/claude-agent-sdk-python/blob/0b08ed120ac6dd4ec132b997ddf44b4dc81545c2/README.md#L11-L35)
- Trace 可能保存 Prompt、Tool 参数和结果。OpenAI 与 Google ADK 都提供敏感内容控制，Observability 章节必须把数据最小化当成正文，而不是部署附注。[OpenAI RunConfig](https://github.com/openai/openai-agents-python/blob/89c02c828ee8510fe9a84ee6675608193aa13b02/docs/running_agents.md#L149-L155)；[ADK Telemetry](https://github.com/google/adk-python/blob/89777c146bd26c04bd45d9ed67b5d3e64a6957f1/docs/guides/telemetry/telemetry_config/index.md#L1-L39)
