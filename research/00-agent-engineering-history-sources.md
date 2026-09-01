# 第 0 课一手资料复核：从工具循环到可靠运行时

> 用途：核验 Blog 第 0 课和旧研究稿中的关键历史事实，不直接修改正文。
>
> 核验快照：2026-09-01（Asia/Shanghai）。
>
> 证据规则：只采用论文原文、官方公告、官方文档与官方 GitHub 仓库；历史论文固定 arXiv 版本，项目状态固定 Release 或 Commit。

## 1. 审计结论

正文的主线可以保留：ReAct 与 Toolformer 把 LLM 推向工具使用，Function Calling 建立结构化调用边界，SWE-bench 与 SWE-agent 把 Coding Agent 变成可测系统，MemGPT 与 LangGraph 分别处理有限 Context 和可恢复工作流状态，MCP 与 A2A 解决不同层次的互操作，Agents SDK 则封装运行时能力。

发布前必须修正两处：

1. Auto-GPT 的最早 Commit b099adcb 只有一份 prompt.txt，不能证明“公开可运行原型”；而且 2023-03-28 的早期循环里，浏览器操作与子实例仍标作 TODO。
2. MCP 的大方向正确，但必须限定为“移除协议级 Session”。Stateless 不等于 Server 不能保存业务数据，server/discover 不是新的强制初始化握手，Tasks 也是可选官方扩展而非核心必选能力。

另有两处建议收紧：

- ReAct 是 prompting 与交互轨迹，不宜直接称为完整“任务运行时”。
- 当前项目状态已经变化：SWE-agent 官方建议改用 mini-SWE-agent；letta-ai/letta 已变成入口页，活跃代码迁到 letta-ai/letta-code。

## 2. 固定证据与当前状态

| 节点 | 经一手资料确认的历史事实 | 截至 2026-09-01 的状态 | 固定证据 |
| --- | --- | --- | --- |
| ReAct | v1 于 2022-10-06 提交；v3 于 2023-03-10 成为 ICLR camera-ready。论文明确让 reasoning trace 与 task-specific action 交错，Action 从外部环境取得信息，再更新后续判断。 | 官方实验仓库无 GitHub Release；默认分支仍停在 2023-07-14 的 6bdb3a1。ReAct 是 prompting 范式，不是通用 Tool Protocol 或完整 Runtime。 | [ReAct v3](https://arxiv.org/abs/2210.03629v3)、[仓库固定 Commit 6bdb3a1](https://github.com/ysymyth/ReAct/commit/6bdb3a1fd38b8188fc7ba4102969fe483df8fdc9) |
| Toolformer | v1 于 2023-02-09 提交。它通过自监督数据让模型学习调用哪个 API、何时调用、传什么参数，以及怎样把结果纳入后续 Token Prediction。论文明确写出：当前方法不能链式调用工具，也不能交互式浏览结果或改写搜索查询。 | arXiv 只有 v1；它仍应被描述为训练方法，而不是 Agent Runtime。 | [Toolformer v1](https://arxiv.org/abs/2302.04761v1)、[论文 Limitations](https://arxiv.org/html/2302.04761v1#S7) |
| Auto-GPT 早期实现 | 2023-03-16 的根 Commit b099adcb 只有 prompt.txt，其中列出了搜索、长期记忆、子实例和网站操作等设想。到 2023-03-28 的 68640a58，源码已经有连续命令循环、每步人工授权、搜索、网页摘要和内存列表；但网站操作和子实例仍在 TODO 区域。 | 当前仓库已经是可视化 Agent Platform，不应拿 2026 README 反推 2023 原型。当前固定 HEAD 为 32a43d0（2026-08-29），最新 Release 为 autogpt-platform-beta-v0.7.3（2026-08-28）。 | [最早 Commit b099adcb](https://github.com/Significant-Gravitas/AutoGPT/commit/b099adcb0830ab00c003749c2ae2cf0f5ec5524a)、[最早 Prompt](https://github.com/Significant-Gravitas/AutoGPT/blob/b099adcb0830ab00c003749c2ae2cf0f5ec5524a/prompt.txt)、[早期循环 68640a58](https://github.com/Significant-Gravitas/AutoGPT/blob/68640a58640156398aea344da21683a5f7f27487/AutonomousAI/main.py#L188-L229)、[当时仍未实现的能力](https://github.com/Significant-Gravitas/AutoGPT/blob/68640a58640156398aea344da21683a5f7f27487/AutonomousAI/commands.py#L51-L70)、[当前固定 HEAD](https://github.com/Significant-Gravitas/AutoGPT/commit/32a43d005c0c42079ceba68d9a49c28e0eeaa6c7)、[当前 Release](https://github.com/Significant-Gravitas/AutoGPT/releases/tag/autogpt-platform-beta-v0.7.3) |
| OpenAI Function Calling | OpenAI 于 2023-06-13 在 Chat Completions 中发布 Function Calling：开发者用 JSON Schema 描述函数，模型返回函数名与 JSON 参数，应用执行函数，再把结果回传给模型。发布公告同时提醒 Tool Output Prompt Injection，并建议真实世界高影响动作加入用户确认。 | 当前官方文档也称 Function Calling / Tool Calling；函数通常放在 tools 参数中，应用仍负责执行并回传结果。历史正文应保留 2023 当时的 functions / function_call 语境，不要把当前参数名倒写进首发史实。 | [2023-06-13 官方公告](https://openai.com/index/function-calling-and-other-api-updates/)、[当前官方 Function Calling 指南](https://developers.openai.com/api/docs/guides/function-calling) |
| SWE-bench | v1 于 2023-10-10 提交；建议正文固定 v3（2024-11-11）。原论文包含 2,294 个来自 12 个 Python 仓库的真实 GitHub Issue / PR 问题，任务是根据仓库和 Issue 生成修复 Patch。 | 它仍是 Benchmark 与 Evaluation Harness，不是 Coding Agent。当前固定 HEAD 为 334882d（2026-09-01），README 同日宣布 SWE-bench Multimodal v2；仓库没有 GitHub Release。 | [SWE-bench v3](https://arxiv.org/abs/2310.06770v3)、[初始 Commit e5878aa](https://github.com/SWE-bench/SWE-bench/commit/e5878aa0d7d4ee3b500a980bf77e3b6856b55298)、[当前固定 HEAD](https://github.com/SWE-bench/SWE-bench/commit/334882dd1f2664cc55c1abfe9de4884af023c0c0) |
| SWE-agent | 代码于 2024-04-02 首次公开；论文 v1 于 2024-05-06 提交，建议正文固定 v3（2024-11-11）。论文提出 Agent-Computer Interface，并用定制导航、编辑、运行与测试接口说明工具界面会显著改变 Agent 表现。 | 当前固定 HEAD 为 3ea751c（2026-07-16），最新 Release v1.1.0 发布于 2025-05-22。README 明确表示 mini-SWE-agent 已取代 SWE-agent，并建议新用户改用前者。 | [SWE-agent v3](https://arxiv.org/abs/2405.15793v3)、[初始 Commit 5b143857](https://github.com/SWE-agent/SWE-agent/commit/5b143857cb7af8b22fd421a103429f76f5259f08)、[当前 README 的取代说明](https://github.com/SWE-agent/SWE-agent/blob/3ea751c087f32b16e039a2233dd6eefecef325d5/README.md#L19-L24)、[Release v1.1.0](https://github.com/SWE-agent/SWE-agent/releases/tag/v1.1.0) |
| MemGPT / Letta | MemGPT v1 于 2023-10-12 提交；建议正文固定 v2（2024-02-12）。论文提出受操作系统分层内存启发的 Virtual Context Management，用外部存储和内存层次突破有限 Context，评测覆盖长文档与多 Session 对话。 | MemGPT 后续项目名为 Letta，但 letta-ai/letta 当前只是入口页，旧 V1 Server 在 archive 分支；活跃代码在 letta-ai/letta-code。当前固定 HEAD 为 9167b00（2026-09-01），最新 Release v0.31.8 同日发布。旧研究稿把 letta-ai/letta 的 0.16.8 当“当前实现”已经过时。 | [MemGPT v2](https://arxiv.org/abs/2310.08560v2)、[Letta 入口页固定 Commit](https://github.com/letta-ai/letta/blob/4511fa0bc91f68fbab32b91f694617271ea9012b/README.md#L1-L8)、[活跃代码固定 HEAD](https://github.com/letta-ai/letta-code/commit/9167b001406a31da365fbd2459460fa62d84e2ba)、[当前 Release v0.31.8](https://github.com/letta-ai/letta-code/releases/tag/v0.31.8) |
| LangGraph | 2024-01-17 的官方介绍把 LangGraph 定位为适合 Agent Runtime 的循环图；State、Node、Edge 和条件边是首发核心。2024-08-07 的 v0.2 把 Base、SQLite、Postgres Checkpointer 拆成独立库；官方列出的能力包括 Session Memory、Error Recovery、Human-in-the-loop 与 Time Travel。 | 主包当前最新相关 Release 为 1.2.11（2026-08-11，Tag Commit 644815f）；仓库首页“Latest”可能显示同一 Monorepo 的 SDK 子包，不能混称为 LangGraph 主包版本。 | [2024-01-17 官方介绍](https://blog.langchain.com/langgraph/)、[v0.2 官方说明](https://blog.langchain.com/langgraph-v0-2/)、[v0.2.0 固定 Commit](https://github.com/langchain-ai/langgraph/commit/172b4af6ed088c74f9a53346e9b8017270cc85c0)、[当前主包 Release 1.2.11](https://github.com/langchain-ai/langgraph/releases/tag/1.2.11)、[Tag Commit 644815f](https://github.com/langchain-ai/langgraph/commit/644815f9e5bc52ad8f7a5227a456227e9c3e639b) |
| MCP | Anthropic 于 2024-11-25 发布 MCP，目标是让 AI 应用以统一方式连接外部数据源与工具。Host—Client—Server，以及 Tool、Resource、Prompt 的能力边界可以保留。2026-07-28 稳定规范移除了协议级 Session、Mcp-Session-Id 与 initialize / notifications/initialized 握手，改成每个请求自带版本和 Client Capabilities。 | 2026-07-28 是稳定 Release，Tag Commit 5f5440b。当前主分支固定 HEAD 为 3ff697d（2026-08-31），但正文讲“当前规范”应固定稳定 Tag，不应引用 Draft 或滚动 HEAD。 | [MCP 发布公告](https://www.anthropic.com/news/model-context-protocol)、[2026-07-28 Release](https://github.com/modelcontextprotocol/modelcontextprotocol/releases/tag/2026-07-28)、[Tag Commit 5f5440b](https://github.com/modelcontextprotocol/modelcontextprotocol/commit/5f5440bb26a62e2cf3440b92da5a667efa03b267)、[固定 Changelog](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/2026-07-28/docs/specification/2026-07-28/changelog.mdx#L10-L28) |
| A2A | Google 于 2025-04-09 发布 A2A，面向由不同厂商、框架和服务器实现的 Agent 之间的能力发现、消息交换与长任务协作；Agent 可以保持内部状态、记忆和工具不透明。2025-06-23，项目进入 Linux Foundation。 | 当前稳定 Release 为 v1.0.1（2026-05-28，Tag Commit 3303592）；当前 README 仍明确称其为“opaque agentic applications”之间的互操作协议。 | [2025-04-09 发布公告](https://developers.googleblog.com/en/a2a-a-new-era-of-agent-interoperability/)、[2025-06-23 Linux Foundation 公告](https://developers.googleblog.com/en/google-cloud-donates-a2a-to-linux-foundation/)、[v1.0.1 固定 README](https://github.com/a2aproject/A2A/blob/v1.0.1/README.md#L48-L57)、[Release v1.0.1](https://github.com/a2aproject/A2A/releases/tag/v1.0.1)、[Tag Commit 3303592](https://github.com/a2aproject/A2A/commit/3303592588e388e62e0f69f701af531d2f4e3991) |
| OpenAI Agents SDK | OpenAI 于 2025-03-11 发布 Responses API 与 Agents SDK。SDK 首发重点包括 Agent、Handoff、Guardrail 与 Trace；现在还包含内置 Loop、Session 等 Runtime 能力。 | Python SDK 当前 Release 为 v0.22.0（2026-08-19，Tag Commit 4df9ecf）；固定文档把 Responses API 与 Agents SDK 分为不同层：直接用 Responses 时应用自己管理 Loop、工具分发和状态；用 SDK 时 Runtime 可管理 Turn、工具执行、Guardrail、Handoff 与 Session。Session 保存对话 Item，不等同业务副作用 Ledger。 | [2025-03-11 官方公告](https://openai.com/index/new-tools-for-building-agents/)、[v0.22.0 固定 Runtime 说明](https://github.com/openai/openai-agents-python/blob/v0.22.0/docs/index.md#L18-L45)、[v0.22.0 固定 Session 说明](https://github.com/openai/openai-agents-python/blob/v0.22.0/docs/sessions/index.md#L1-L7)、[Release v0.22.0](https://github.com/openai/openai-agents-python/releases/tag/v0.22.0)、[Tag Commit 4df9ecf](https://github.com/openai/openai-agents-python/commit/4df9ecfae1761ca6fea67cc5a20b383c1d492024) |

## 3. 正文可保留的事实

以下句意已有足够一手证据，可原样保留或只做文风调整：

1. ReAct 让 reasoning trace、action 与 observation 交错，外部观察会影响下一步判断。
2. Toolformer 研究模型怎样通过训练学会何时调用哪个 API、传什么参数，并吸收返回结果；它不是完整 Runtime。
3. OpenAI Function Calling 建立“模型提出结构化调用—宿主执行—结果回传”的边界；Schema 不会替应用完成授权、业务校验、幂等与副作用审计。
4. SWE-bench 是真实仓库任务 Benchmark，SWE-agent 是参加评测的 Agent System；Harness / ACI 会改变同一模型能看到和做到什么。
5. MemGPT 解决有限 Context 下的信息分层与外部记忆，不负责工具权限或外部副作用。
6. LangGraph Checkpoint 能支持状态恢复、Human-in-the-loop 与 Time Travel，但不能证明邮件、支付或 Shell 在外部世界只执行了一次。
7. MCP 连接 AI 应用与 Tool、Resource、Prompt 等外部能力；A2A 连接不透明远程 Agent；两者都不是 Agent Runtime。
8. OpenAI Agents SDK 封装 Loop、Handoff、Guardrail、Tracing 与 Session；SDK Session 主要保存交互 Item，不等于业务 Ledger。
9. “能调用工具、能恢复状态”不等于“可靠执行真实动作”，仍需 Approval、Sandbox、Idempotency、Receipt / Ledger 与 Reconciliation。

## 4. 需要修正的原句与建议替换文本

### 4.1 ReAct：不要把 Prompting 范式写成完整 Runtime

现有正文：

> 说白了，ReAct 关心的是任务运行时：先做一步，看见结果，再调整下一步。

问题：这句话作为直觉没有错，但“任务运行时”容易让读者误以为 ReAct 已经定义了 Tool Protocol、执行器、权限和持久状态。论文只证明了交错 reasoning / action 的 prompting 与轨迹。

建议替换：

> 说白了，ReAct 给出的是一种推理—行动轨迹：模型先决定并执行一步，看到 Observation 后再调整下一步；它没有定义完整 Agent Runtime。

### 4.2 Auto-GPT：最早 Commit 不是可运行代码，浏览器与子实例也未实现

现有正文：

> 2023 年的 Auto-GPT 原型把长期目标、记忆、搜索与浏览器串成长循环。它证明“让模型持续决定下一步”可以成为公开可运行原型，也暴露了无限循环、费用、权限与恢复等问题。

问题：

- 所引 b099adcb 只有 prompt.txt，不能支撑“公开可运行原型”。
- 68640a58 已经有循环、搜索、网页摘要、内存与人工授权，但 navigate_website、start_instance 等仍在 TODO，不能写成浏览器和子实例已经串入执行链。
- “暴露无限循环、费用、权限与恢复问题”属于从架构与后续实践作出的工程推论，应明确是总结，不是假装源码作者在同一 Commit 中给出的结论。

建议替换：

> Auto-GPT 在 2023 年 3 月从一份长期目标与工具设想的 Prompt，很快演变成公开可运行的连续命令循环。到 3 月 28 日，源码已经能让模型反复选择搜索、网页摘要和内存操作，并在每一步等待人工授权；当时浏览器操作与子实例仍是 TODO。这个原型展示了“让模型持续决定下一步”怎样落到代码里，也让循环失控、费用、权限与故障恢复成为必须面对的工程问题。

引用建议：第一句同时引用 [b099adcb](https://github.com/Significant-Gravitas/AutoGPT/commit/b099adcb0830ab00c003749c2ae2cf0f5ec5524a) 与 [68640a58](https://github.com/Significant-Gravitas/AutoGPT/commit/68640a58640156398aea344da21683a5f7f27487)，不要再把 b099adcb 单独标成“初始实现”。

旧研究稿时间线也应拆成两个节点：

| 日期 | 更准确的节点 |
| --- | --- |
| 2023-03-16 | Auto-GPT / Entrepreneur-GPT 最早 Prompt：列出目标、搜索、内存、网站操作与子实例设想，但没有可运行代码 |
| 2023-03-28 | 早期连续命令循环：实现搜索、网页摘要、内存与逐步人工授权；浏览器操作和子实例仍是 TODO |

### 4.3 MCP：Stateless、Session、握手和 Tasks 必须分开

现有正文：

> MCP 不是 Agent Runtime，也不是 Agent-to-Agent 协议。当前 2026-07-28 规范已经移除核心 Session 与初始化握手，转向 Stateless 请求；长任务进入 Tasks Extension。

这里的方向正确，但有四个术语风险：

1. 应写“协议级 Session”，因为被移除的是 Streamable HTTP 的 Mcp-Session-Id 等协议上下文，不是 Agent Runtime 的对话 Session 或所有业务状态。
2. 2026-07-28 的 Stateless 指每个请求自带处理所需的协议版本与 Client Capabilities；Server 仍可保存任务或业务数据，但跨请求关联必须靠每次请求显式携带的 Handle。
3. initialize / notifications/initialized 的强制握手确实移除。server/discover 是 Server 必须实现、Client 可选调用的普通 RPC，不是新的强制握手；Client 也可以直接调用任意 RPC，再处理 UnsupportedProtocolVersionError。
4. Tasks 是可选的官方 Extension。更准确的历史描述是“实验性 Tasks 从 Core 移到官方扩展”，不是所有长任务自动由 MCP Core 接管。

建议正文采用完整版本：

> MCP 不是 Agent Runtime，也不负责 Agent-to-Agent 协作。2026-07-28 核心规范取消了协议级 Session（包括 Streamable HTTP 的 Mcp-Session-Id）以及 initialize / notifications/initialized 握手。新版让每个请求自带协议版本与 Client Capabilities；Server 必须实现、Client 可选调用的 server/discover 不是新的强制握手。跨请求状态通过显式标识关联，长任务可选使用官方 Tasks 扩展。

若正文需要更短：

> 2026-07-28 核心规范改为按请求无状态：每个请求自带协议版本与 Client Capabilities，不再依赖协议级 Session 或初始化握手。跨请求状态用显式标识关联；长任务可选使用官方 Tasks 扩展。

固定规范依据：

- [Changelog：移除协议级 Session、握手与 Core Tasks](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/2026-07-28/docs/specification/2026-07-28/changelog.mdx#L10-L28)
- [Stateless 的精确定义](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/2026-07-28/docs/specification/2026-07-28/basic/index.mdx#L182-L214)
- [每请求必须携带的版本与 Client Capabilities](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/2026-07-28/docs/specification/2026-07-28/basic/index.mdx#L365-L390)
- [没有协商握手，server/discover 为 Client 可选](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/2026-07-28/docs/specification/2026-07-28/basic/versioning.mdx#L7-L78)
- [兼容旧 initialize 版本的 Dual-era 行为](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/2026-07-28/docs/specification/2026-07-28/basic/versioning.mdx#L126-L180)
- [Tasks 是长任务的可选扩展](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/2026-07-28/docs/extensions/tasks/overview.mdx#L17-L61)

旧研究稿第 4 节建议把原有项目符号改为：

- 移除协议级 Session 和 Streamable HTTP 的 Mcp-Session-Id；
- 移除 initialize / notifications/initialized 握手；
- 每个请求在 _meta 中携带协议版本与 Client Capabilities；
- Server 必须实现 server/discover，Client 可选调用，它不是新的强制握手；
- 跨请求状态必须通过每次请求携带的显式标识关联；
- 实验性 Tasks 从核心移入可选的官方扩展；
- Roots、Sampling、Logging 被标记 Deprecated，但仍在弃用期内保留。

推荐的一句话结论：

> MCP 统一 AI 应用与外部能力的协议边界；截至 2026-07-28，核心协议按请求无状态：每个请求自带版本与 Client Capabilities，跨请求状态则通过显式标识关联。

研究注意：2026-07-28 的版本化总览仍有一处“extensions negotiated during initialization”的旧措辞，与同版 Changelog、Versioning 和每请求 Capabilities 规则冲突。[冲突位置](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/2026-07-28/docs/specification/2026-07-28/index.mdx#L75-L84)。这是根据同版更具体规范作出的文档一致性判断；正文不要引用这句旧措辞。

### 4.4 当前状态表：需要刷新，不影响历史主线

旧研究稿“2026 年源码快照”至少更新以下行：

| 项目 | 旧状态的问题 | 建议新状态 |
| --- | --- | --- |
| AutoGPT | HEAD 停在 2026-08-28 | 当前固定 HEAD 32a43d0，2026-08-29；Release 仍为 beta v0.7.3，2026-08-28 |
| SWE-bench | HEAD 停在 2026-08-18 | 当前固定 HEAD 334882d，2026-09-01；README 同日加入 Multimodal v2 |
| Letta | 把 letta-ai/letta 0.16.8 当活跃实现 | letta-ai/letta 已是入口页；活跃代码 letta-ai/letta-code，HEAD 9167b00，Release v0.31.8，均为 2026-09-01 |
| MCP | HEAD 停在 2026-08-26 | 滚动 HEAD 为 3ff697d，2026-08-31；讲规范仍固定稳定 Tag 2026-07-28 / Commit 5f5440b |
| A2A | HEAD 停在 2026-08-28 | 滚动 HEAD 为 98853be，2026-09-01；稳定 Release 仍为 v1.0.1 |

LangGraph 主包 1.2.11、OpenAI Agents SDK v0.22.0、SWE-agent v1.1.0 在本次核验中仍与旧研究稿一致。

## 5. 建议正文使用的最小引用集

正文不必把所有当前 HEAD 搬进去。保留以下 11 组即可：

1. [ReAct v3](https://arxiv.org/abs/2210.03629v3)
2. [Toolformer v1](https://arxiv.org/abs/2302.04761v1)
3. [Auto-GPT 最早 Prompt](https://github.com/Significant-Gravitas/AutoGPT/commit/b099adcb0830ab00c003749c2ae2cf0f5ec5524a) 与 [早期循环](https://github.com/Significant-Gravitas/AutoGPT/commit/68640a58640156398aea344da21683a5f7f27487)
4. [OpenAI Function Calling 首发公告](https://openai.com/index/function-calling-and-other-api-updates/)
5. [SWE-bench v3](https://arxiv.org/abs/2310.06770v3)
6. [SWE-agent v3](https://arxiv.org/abs/2405.15793v3)
7. [MemGPT v2](https://arxiv.org/abs/2310.08560v2)
8. [LangGraph v0.2](https://blog.langchain.com/langgraph-v0-2/)
9. [MCP 2026-07-28 固定 Changelog](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/2026-07-28/docs/specification/2026-07-28/changelog.mdx)
10. [A2A v1.0.1 固定 README](https://github.com/a2aproject/A2A/blob/v1.0.1/README.md#L48-L57)
11. [OpenAI Agents SDK v0.22.0 固定 Runtime 说明](https://github.com/openai/openai-agents-python/blob/v0.22.0/docs/index.md#L18-L45)

## 6. 最终判定

- 历史主线：可保留。
- 必修错误：Auto-GPT 最早 Commit 的证据等级；MCP Stateless / Session / 握手 / Tasks 的术语边界。
- 建议修订：ReAct 不直接称完整 Runtime；刷新 SWE-agent 与 Letta 当前状态。
- 不必扩写：不需要增加更多产品年表，也不需要把当前 Release 列表塞入正文；Release / HEAD 快照留在研究报告。
