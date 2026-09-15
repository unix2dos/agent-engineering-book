# 第 0 课：历史来源与核验边界

核验快照：2026-09-01；补充核验：2026-09-09。这里保存[正式第 0 课](../chapters/00-Agent工程史.md)采用的来源、版本与证据边界，2026-09-15 的目录整理没有重新核验外部资料。

## 引用边界

- 论文、产品公告与可运行代码分别说明不同层次的事实；最早 Prompt 提交不能当作完整原型的证据。
- ReAct 的推理与行动轨迹、Toolformer 的训练方法，均不能直接扩写成完整 Runtime。
- MCP 的协议级无状态、业务状态、发现机制与可选 Tasks 扩展分别判断，不用一个“无状态”概括全部能力。
- 历史实现采用固定 Commit；表中的后续产品状态只代表标明的核验日期。旧稿原句、替换建议和已完成的修订清单交由 Git 历史保存。

## 固定证据与核验时状态

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

## 选读背景：Agent 问题早于大模型

以下保留原第 0 课的理论背景与出处，不作为入门主线的前置要求。

在大语言模型出现以前，人们已经在研究能自己选择动作的软件：它认为外部世界现在是什么状态，想完成什么目标，又准备执行什么计划。

研究者把这三个部分叫作 Belief、Desire 和 Intention，合起来简称 BDI。1990 年代的 Agent-Oriented Programming 与 BDI Agent 已经尝试把它们放进可执行系统。[Intelligent Agents: Theory and Practice](https://doi.org/10.1017/S0269888900008122)

这些研究提出了今天仍会遇到的问题，却不是 LLM Agent 的直接代码祖先。经典系统主要依赖手工规则和计划，今天的 LLM Agent 主要依赖生成模型、Context 和工具调用。

## 2026-09-09 补充核验

本轮只核对精简稿采用的历史节点；前文 2026-09-01 的项目版本快照不因此成为本轮重新验证的“最新状态”。

- GitHub API 返回根提交 b099adcb 的时间为 2023-03-16，文件列表只有 prompt.txt。因此正文区分最早 Prompt 与后续可运行循环，不再声称这是所有 Agent 的首个公开原型。
- 固定提交 68640a58 的 AutonomousAI/main.py 显示：请求模型、展示命令参数、等待 Enter 授权、执行命令、回传结果。原正文的“按 y 批准”与此出处不符，已按源码修正为敲回车或人工授权。
- 原正文“半小时花费数百美元”及“行业百亿美元学费”的说法没有对应的一手出处，本轮没有取得支持这些具体数字的证据，因此新版不采用；这不是对事件必然没有发生的证明。
- 已打开 ReAct v3、Toolformer v1、SWE-bench v3、SWE-agent v3、MemGPT v2 的论文页面，核对摘要与首次提交年份。
- 已核对 OpenAI 2023-06-13 Function Calling 公告、LangGraph 2024-08-07 v0.2 公告、MCP 2024-11-25 公告与 A2A 2025-04-09 公告。
- 早期 Agent 理论 DOI 页面本轮未能获取正文，保留原引用作为延伸阅读，不新增 BDI 细节断言。
- 责任地图是本书按工程问题整理的关系，不表示各项目按单一路线依次发展，也不把后续协议字段倒写进首发历史。

新增核验的原始入口继续使用前文“固定证据”中的论文、公告和源码链接。LangGraph v0.2 官方旧地址现跳转到 [官方新页面](https://www.langchain.com/blog/langgraph-v0-2)。

## 补充核验来源

以下为原核验记录中的额外出处，保留当时的版本和链接；旧稿修改对比见 Git 历史。

- [早期循环](https://github.com/Significant-Gravitas/AutoGPT/commit/68640a58640156398aea344da21683a5f7f27487)
- [Stateless 的精确定义](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/2026-07-28/docs/specification/2026-07-28/basic/index.mdx#L182-L214)
- [每请求必须携带的版本与 Client Capabilities](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/2026-07-28/docs/specification/2026-07-28/basic/index.mdx#L365-L390)
- [没有协商握手，server/discover 为 Client 可选](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/2026-07-28/docs/specification/2026-07-28/basic/versioning.mdx#L7-L78)
- [兼容旧 initialize 版本的 Dual-era 行为](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/2026-07-28/docs/specification/2026-07-28/basic/versioning.mdx#L126-L180)
- [Tasks 是长任务的可选扩展](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/2026-07-28/docs/extensions/tasks/overview.mdx#L17-L61)
- [冲突位置](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/2026-07-28/docs/specification/2026-07-28/index.mdx#L75-L84)
- [MCP 2026-07-28 固定 Changelog](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/2026-07-28/docs/specification/2026-07-28/changelog.mdx)
