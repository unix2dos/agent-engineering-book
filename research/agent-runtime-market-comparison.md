# Agent 运行方案：产品分层对比资料

核验日期：2026-09-15。下列为官方文档能力与边界，不是故障压测，也不是模型能力排名。成品开发 Agent 与部署运行平台分开比较。

## Grok Bot 与 Amp 的来源可信度

Grok Bot 有 xAI 官方产品文档与设计文章，是可确认的官方产品。当前文档说明它保留 Bot 的上下文，并使用账号共享的云电脑；这能支持产品行为描述，不能单独证明它采用某种内部恢复算法。[产品概览](https://docs.x.ai/grok-bot/overview)、[设计说明](https://x.ai/news/designing-grok-bot)

Amp 来自 Sourcegraph 团队，2025-12-02 官方宣布独立为 Amp Frontier Corporation；Sourcegraph 也发布了分拆说明。它有可核查的团队与公司背景，但公司背景不是运行时可靠性的独立背书。[Amp 公告](https://ampcode.com/news/amp-frontier-corporation)、[Sourcegraph 公告](https://sourcegraph.com/blog/why-sourcegraph-and-amp-are-becoming-independent-companies)

本次确认了产品身份和公开契约，没有取得把这些产品放在同一故障注入条件下的独立横评数据。这里的比较不支持谁的成功率或恢复可靠性最高。

## 成品 Agent：用户直接交任务

| 方案 | 执行方式与工作对象 | 对第 11 课有用的事实和边界 |
| --- | --- | --- |
| OpenAI Codex Cloud | 创建容器并检出仓库，运行环境准备、修改和检查，交回结果与 diff | 官方说明容器缓存用于加速启动，不能将缓存当成任意故障下的业务恢复保证；产品层 Codex Cloud 与开发者平台 Agents API 分开理解。[环境文档](https://learn.chatgpt.com/docs/environments/cloud-environment) |
| Cursor Cloud Agents | 默认托管隔离 VM；也有 My Machines 和 Team Pools | 自托管只改变工具执行位置，Agent Loop 仍在 Cursor 云端。My Machines 和企业 Pool 的维护责任不同。[执行位置对照](https://cursor.com/docs/cloud-agent/self-hosted/choose-runtime) |
| GitHub Copilot cloud agent | 以仓库任务和 PR 为中心，使用 GitHub Actions 执行 | 支持自托管 runner；临时计算环境、会话日志和代码提交应分别判断。具体范围见下文。[官方环境说明](https://docs.github.com/en/copilot/how-tos/copilot-on-github/customize-copilot/customize-cloud-agent/customize-the-agent-environment) |
| Google Jules | 在短期云 VM 中异步处理仓库任务 | 未在本次资料中确认可自托管执行；CLI 是管理入口。成熟度标识有官方资料差异，见下文。[环境说明](https://jules.google/docs/environment/) |
| Amp | 线程可在托管 Orb、本地 CLI 或自有 Runner 执行 | Orb 支持休眠后继续，Runner 保留自有机器入口；同一产品内可以提供多种环境。[Orbs](https://ampcode.com/docs/orbs)、[Runners](https://ampcode.com/docs/cli/runners) |
| Grok Bot | 长期角色、文件和浏览器操作，使用持久云电脑 | 同一账号下 Bots 共享电脑、文件和登录状态；适合说明角色延续与环境共享，不能套成一任务一沙箱。[电脑与应用](https://docs.x.ai/grok-bot/computer-and-apps) |

Cursor 2026-09-02 的官方文章还明确说明：工具输出仍会回到云端参与推理，可能包含代码；自托管执行不等于全部数据都留在本地。Pool 释放机器后，若没有配置休眠恢复，后续请求可能获得新机器，原工作区不会自动迁移。[自托管公告](https://cursor.com/blog/self-hosted-machines)、[Pool 生命周期](https://cursor.com/docs/cloud-agent/self-hosted/pool#session-lifecycle)

## 运行平台：开发者搭建 Agent 系统

| 方案 | 厂商接管什么 | 执行位置与恢复边界 |
| --- | --- | --- |
| OpenAI Agents API | OpenAI 运行 Harness，应用发送任务、消费事件和处理自定义工具 | 环境可托管、自托管或不配置。自托管方负责机器生命周期与文件保存。[架构](https://developers.openai.com/api/docs/guides/agents-api/architecture) |
| Anthropic Claude Managed Agents | 托管 Harness、持久 Session 和事件，提供文件及工具执行 | 可使用厂商环境或自托管 Sandbox；目前 Beta。官方工程文章直接解释 Session/Harness/Sandbox 的拆分。[概览](https://platform.claude.com/docs/en/managed-agents/overview)、[架构说明](https://www.anthropic.com/engineering/managed-agents) |
| AWS Bedrock AgentCore Runtime | 部署开发者自己的 Agent/工具，提供运行与存储能力 | Session 和 compute 分开管理；跨停启文件保留依赖选定存储和挂载配置。它不是开箱即用的编码产品。[生命周期](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-sessions.html) |

OpenAI 的 Sessions 文档明确指出，turn completed 也不保证每个工具都成功；仍需检查实际输出。[运行与继续 Session](https://developers.openai.com/api/docs/guides/agents-api/sessions#follow-progress-and-handle-outcomes)

Agents SDK 是第三种选择：由应用运行 Harness，再选择沙箱后端。OpenAI 的相关文档将 RunState、沙箱 session state 与工作区 snapshot 分开，Sandbox Agents 当前为 Beta。不能把 SDK、托管 API 和 Codex 成品视为同一个产品的同一接口。[Sandbox Agents](https://developers.openai.com/api/docs/guides/agents/sandboxes)

## GitHub Copilot cloud agent：成品开发 Agent

- 原 coding agent 于 2025-09-25 GA：异步处理任务，在 GitHub Actions 环境修改代码、开草稿 PR，交回用户审阅。[GA 公告](https://github.blog/changelog/2025-09-25-copilot-coding-agent-is-now-generally-available/)
- 默认临时开发环境；当前也支持自托管 Actions runner，限 Ubuntu x64、Windows 64 位。自托管必须自己配置网络控制，内置防火墙不兼容。[环境契约](https://docs.github.com/en/copilot/how-tos/copilot-on-github/customize-copilot/customize-cloud-agent/customize-the-agent-environment)
- 会话日志和代码提交可追踪；官方将 cloud session 环境定义为结束后销毁。不能把 PR/日志留存解释为临时工作区或进程永远保存。[会话管理](https://docs.github.com/en/copilot/how-tos/copilot-on-github/use-copilot-agents/manage-and-track-agents)、[应用说明](https://docs.github.com/en/copilot/responsible-use/agents)
- 另有本地 CLI 与实验性 CLI cloud sandbox；它们不是上述 coding agent 的同义词。[本地与云沙箱](https://docs.github.com/en/copilot/concepts/about-cloud-and-local-sandboxes)

## Google Jules：成品开发 Agent

- Google 官方 2025-08-06 宣布脱离 Beta；FAQ 仍写 Public Beta。GA/Beta 标识存在官方资料差异，本次不作成熟度定论。[发布记录](https://jules.google/docs/changelog/2025-08-06)、[FAQ](https://jules.google/docs/faq/)
- 每项任务使用新的短期云 VM，克隆仓库、安装依赖、运行测试；提交任务后可以离开界面。失败会自动重试，持续失败则标记失败并通知。设置脚本不支持长期运行的 dev server/watch。[环境说明](https://jules.google/docs/environment/)、[FAQ](https://jules.google/docs/faq/)
- 本轮未查到自托管执行、精确 VM/文件保留期限或崩溃后检查点恢复承诺。CLI 是管理 Jules 的入口，不能据此认定计算转到本机。[CLI 说明](https://jules.google/docs/cli/reference)

## AWS Bedrock AgentCore Runtime：部署运行平台

- AgentCore 于 2025-10 GA；Runtime 托管开发者自己的 Agent 或工具，可选择不同模型/框架，并非开箱即用的编码同事。[发布记录](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/release-notes.html)、[Runtime](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/agents-tools-runtime.html)
- microVM 单次计算生命周期最长 8 小时；Instances 于 2026-08-06 GA，在客户 AWS 账号内由 AWS 管理 EC2，最长 14 天。这是客户账号内托管，不等于本地自部署。[Instances 公告](https://aws.amazon.com/about-aws/whats-new/2026/08/aws-bedrock-agentcore-runtime-instances-generally-available/)
- Session ID 可跨计算实例停启保留；默认闲置 15 分钟停止计算，后续调用创建新计算。配置存储后，指定路径文件可跨 stop/resume；microVM Session Storage 仍为 Preview，另有 Instances EBS 和自带文件系统选项。[生命周期](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-sessions.html)、[存储契约](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-filesystem-configurations.html)
- 上述契约证明计算和持久状态可分离；不等于恢复任意进程内存，也未证明外部动作不会重复执行。
- 存储类别还有不同失效边界：microVM Session Storage 空闲 14 天会过期，运行时版本更新会清空；Instances 的容量卷和自有文件系统规则不同。“支持持久化”仍须说明是哪种存储。[存储生命周期对照](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-filesystem-configurations.html)

## 对第 11 课的启示

这些资料共同支持“异步执行、状态与计算分离、执行位置多样化”；不足以支持“所有产品都采用同一种三层实现”或“所有环境必须上云”。GitHub 自托管 runner 是直接反例；AWS 则提供比产品宣传更细的生命周期和存储契约。

建议用 Anthropic 的工程架构与 OpenAI 的状态/执行接口建立主要论据，再用 Cursor、GitHub、Google 的产品行为交叉核验。Amp 作为 Orb/Runner 的补充案例；Grok Bot 用于说明长期通用助手与仓库任务的不同工作方式。选材优先看证据与论点的对应关系，而不是仅按品牌大小排序。

这些资料用于第 11 课的分层对照：熟悉的编码产品提出执行位置问题，托管平台说明 Harness 与状态责任，存储契约和文件实验约束恢复保证。正文保留核心机制，本记录保留更完整的产品范围与来源差异。
