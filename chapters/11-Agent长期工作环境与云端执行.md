# 第 11 课：Agent Runtime——持久状态与云端执行

把修复任务交给 Codex，它可以在云端准备仓库、修改代码、运行检查，再交回结果。Cursor、GitHub Copilot 和 Google Jules 也提供后台处理仓库任务的方式。执行离开了用户的电脑，任务便有机会在人离开界面后继续。[1][2][3][4]

这能说明云端执行的用途，却还没有回答：执行程序崩溃以后谁接手，已经修改的文件保存在哪里，以及同一项工作为什么也可能适合放在公司自己的机器上。

本课以 OpenAI、Anthropic 的官方运行架构为主要依据，用其他厂商的产品方案交叉核验，再通过一个文件恢复实验检查“能够继续”的边界。

## 1. Cloud Execution：成品 Agent 与运行平台

Codex Cloud 的环境文档描述了一条具体流程：创建容器，检出指定版本的仓库，运行环境准备脚本，再由 Agent 调用终端工具修改和检查，最后交回回答与文件差异。界面负责交互，实际执行发生在远端环境里。[1]

其他产品也能接下类似的工作，但环境由谁管理、怎样保存，并不完全相同。下表比较的是用户直接交任务的成品 Agent：

| 方案 | 执行环境 | 需要分清的边界 |
| --- | --- | --- |
| OpenAI Codex Cloud | 托管容器，按仓库配置准备依赖 | 环境缓存用于加速，不能直接当作完整故障恢复保证。[1] |
| Cursor Cloud Agents | 托管 VM，或自己的机器、企业 Worker Pool | 选择自有机器时，工具在那里执行，Agent Loop 仍在 Cursor 云端。[2] |
| GitHub Copilot cloud agent | GitHub Actions 环境，也支持自托管 Runner | 官方将开发环境描述为临时环境；代码成果与执行机器的寿命要分别判断。[3] |
| Google Jules | 每项任务使用短期云 VM，准备仓库和依赖 | 本次资料未确认自托管执行或崩溃后检查点恢复的具体承诺。[4] |
| Amp | 托管 Orb、本地 CLI 或自有 Runner | Orb 可以休眠后继续；Runner 的机器和进程由使用者管理。[5][6] |
| Grok Bot | 长期角色使用持久云电脑，处理文件与浏览器工作 | 同一账号的 Bots 共享电脑、文件和登录状态，并非每个任务都有隔离环境。[7] |

Grok Bot 有 xAI 官方产品资料；Amp 来自 Sourcegraph 团队，后来独立为公司。[7][8] 它们可以提供有特点的案例。公司背景能帮助确认资料来源，运行能力仍要看具体契约；上表也不构成成功率或可靠性排名。

还有一类方案面对的是开发者：OpenAI Agents API、Claude Managed Agents 和 AWS AgentCore，提供搭建、运行 Agent 系统的能力。成品回答“我怎样把任务交出去”，运行平台则让我们继续追问“谁组织执行、谁保管状态”。

## 2. Harness 与 Sandbox：运行控制和执行环境

假设执行代码、会话记录和工具环境都放在同一个容器里，读取文件很直接，部署也容易开始。但如果重要记录随容器一起丢失，换一个新容器就无法知道旧任务做到哪里。文件位置与运行程序绑在一起，也会限制它访问其他环境。

Anthropic 的 Managed Agents 工程文章描述了团队实际遇到的这类问题，并给出三项职责：[9]

- **Session** 保存会话事件，让程序能够查回发生过什么。
- **Harness** 是组织运行的程序：调用模型，接收工具申请，安排执行并处理结果。
- **Sandbox** 提供代码与文件操作的执行环境，落实相应的隔离限制。

在其公开架构中，Session 日志保存在 Harness 之外；Harness 故障后，新实例可以读取日志接续。Sandbox 通过工具接口访问，可以独立处理执行环境的故障。这里的“无状态 Harness”强调它不独占必须保住的恢复状态，运行时仍然会使用内存和临时变量。[9]

OpenAI 的 Agents API 也明确分开 Harness 与 Environment：OpenAI 运行 Harness，应用发送任务、接收事件；需要命令和文件时，再连接执行环境。这个环境可以由 OpenAI 托管，也可以在客户自己的机器上。部分只调用外部工具的任务，甚至不需要单独配置 Sandbox。[10]

三家平台的责任范围可以这样对照：

| 运行平台 | 提供的能力 | 应用仍需明确什么 |
| --- | --- | --- |
| OpenAI Agents API | 托管 Harness、Session 与事件接口，可连接托管或自有环境 | 自定义工具怎样处理；自托管机器怎样启停、重连和保存文件。[10] |
| Claude Managed Agents | 托管运行过程、会话事件和工具环境，支持自托管 Sandbox；当前为 Beta | 任务指令、工具权限、环境和成功标准怎样配置。[11] |
| AWS Bedrock AgentCore Runtime | 运行开发者自己的 Agent 或工具，提供计算与存储能力 | Agent 自身逻辑、Session 归属与存储挂载怎样安排。[12][13] |

名称接近的接口也要分开。OpenAI Agents SDK 是应用中使用的代码库，由应用运行 Harness；Agents API 提供托管 Harness；Codex Cloud 则是直接面向开发任务的产品。[1][10][14] 它们都有工具循环，不代表它们接管了相同的部署责任。

这些资料使三项职责可以在真实系统里找到对应对象，但不能据此断言每家内部实现完全相同。

## 3. Persistence：会话状态、工作区与长期记忆

运行程序可以更换之后，下一步就要说明它拿什么继续。OpenAI Sandbox Agents 文档区分了运行状态 `RunState`、沙箱会话状态和工作区快照：分别用于接续运行控制、恢复环境连接，以及用保存的文件创建工作区。该能力目前为 Beta，具体恢复行为依赖所选后端。[14]

以一次修复任务为例，保存对象各有用途：

| 保存的东西 | 继续工作时有什么用 |
| --- | --- |
| 会话历史与任务进度 | 知道用户要求、已取得的证据和下一步安排 |
| 工作区文件与产物 | 接着处理已修改的代码，读取对应的测试报告 |
| 跨任务记忆 | 复用经过确认的项目约定与工作经验 |
| 临时进程与连接 | 维持运行中的服务；能否重建或恢复取决于环境能力 |

保存了“测试通过”的一句话，报告未必还在；恢复了代码目录，原来的数据库连接也可能已经断了。一个恢复按钮无法替这些对象约定保存范围。

AWS 的文档把边界写得更具体：计算实例停止后，可以沿用 Session ID 发起后续调用并获得新的计算实例；指定目录能否保留，要看是否配置了持久存储。microVM 的 Session Storage 当前为 Preview，空闲 14 天会过期，运行时版本更新也会清空；其他存储类别的规则不同。[12][13]

所以，看到“支持持久化”，要继续查它保存哪些路径、在哪些操作后仍然有效。把记录写到进程外，可以承受某些进程故障；若记录仍在随机器一起销毁的磁盘上，机器丢失时就需要额外的保存或重建方案。

## 4. Recovery：回执丢失与文件对账

为了看清这个问题，配套实验复用了已有的文件工具与执行账本。它不调用模型，而是给出一条固定请求：把配置中的主题改成 dark，端口保留 3000。

程序先记下工具准备执行，再修改文件。就在修改完成、成功回执尚未保存的位置，用 `os._exit(23)` 让执行进程退出。父进程确认它已经结束，然后启动另一个进程读取同一目录和账本。故障是主动注入的，文件写入与进程退出真实发生。

第一次，配置已经符合原请求。第二次，在启动恢复进程之前，模拟有人把端口改成了 8081。实际输出如下：

```text
文件符合原请求：进程退出码 23；running -> unknown -> succeeded；恢复未改写文件
文件被人修改：进程退出码 23；running -> unknown -> unknown；恢复未改写文件
```

`running` 是中断前留下的状态；`unknown` 表示当前还不知道那次动作的结果。新进程先把这份不确定性记下来，再检查文件。

第一种情况下，文件内容满足请求，可以记录“目标已满足”并补回结果。第二种情况下，文件已经不同，恢复逻辑保留 unknown，把未能确认的结果交回调用方。它没有用旧内容覆盖端口 8081。

这里用到的 **Ledger（执行账本）**，记录的是调用身份、参数和执行结果。它帮助恢复程序核对已经发生的动作。若把“没收到成功回执”直接当成“还没执行”，重跑一次就可能覆盖后来的修改。

这个实验也有清楚的边界：旧执行者已退出，只有一个恢复进程，文件仍在同一块可访问的磁盘上。它没有验证断电、容器丢失、并发接管或厂商服务的恢复质量。内容匹配只能说明当前目标满足，不能证明历史动作是谁做的、做了几次；发送邮件之类的操作还需要查询对应服务的结果。

脚本在每个场景首次恢复结束后，再启动一个独立恢复进程，验证第二次正常退出，文件和账本的内容、文件标识与修改时间均不变，也不重复补回执。运行入口见文末配套实践。

## 5. 部署选择：本地、自托管与云端

支持远端管理的产品，也可能允许在客户自己的环境里执行。Cursor 提供托管 Cloud Agents、个人 My Machines 和企业 Team Pools；GitHub Copilot cloud agent 也支持自托管 Actions Runner，当前限定 Ubuntu x64 和 Windows 64 位。[2][3]

这些选择有各自的成本。托管环境承担了一部分启动、隔离和容量管理；自有环境可以利用已经存在的文件、网络和硬件，但使用者要维护机器、工作进程与清理规则。GitHub 推荐临时、单次使用的 Runner，不能因为机器在自己手里，就假定旧工作区应当一直复用。[3]

Cursor 的 Pool 生命周期还提供了一个具体反例：机器释放后，如果没有安排休眠恢复，后续消息可能被分配到新机器，原工作区不会自动带过去。保存了聊天，与保留了那台机器的文件，仍然是两回事。[15]

自托管也要说清托管的是哪一部分。Cursor 明确说明，工具输出仍会回到云端参与推理，可能包含代码；把执行放在本机，并不自动让全部数据都留在本机。[16]

代码能从仓库获取、依赖可以自动安装、多个测试需要独立环境时，我更倾向托管云环境。若任务离不开本地 Obsidian 文件、桌面应用、USB 设备或难以接通的企业内网，执行留在相应环境里可能更直接。数据已经在云上，也可能位于客户自己的网络，而非 Agent 厂商的网络。

Amp 的 Orb/Runner 对照，以及 Grok Bot 共享长期工作电脑的方式，可以补充说明这些取舍。[5][6][7] 选择依据仍是任务需要访问什么、保留什么，以及由谁承担环境维护。

## 6. 趋势判断：产品承诺与验证依据

从这些公开方案看，我更看好标准化后台任务扩大采用托管环境的方向。用户离开设备后，任务仍可交给远端执行；多个独立任务也更容易获得各自的运行环境。但这不要求所有工具都搬到同一家云上，主流产品已经提供了不同程度的自有环境接入。

更值得跟踪的是，任务记录、计算环境和持久文件是否能够分别管理。原进程退出后，接手者能否找回有效状态；环境需要重建时，成果是否保得住；一个动作结果不明时，能否先核对再继续。

即使平台报告执行完成，也要核对产物。OpenAI 的 Sessions 文档明确指出，turn completed 不保证每个工具都成功。[17] 同样，恢复程序正常退出，只能证明这个恢复过程结束，不能替用户验收代码或报告。

判断新产品时，可以沿着“承诺的行为、保存的对象、覆盖的故障、完成的证据”去读资料。官方文档给出接口契约；故障实验只能验证所测情境；跨产品观察则帮助形成有条件的趋势判断。若环境准备、集成和运行成本持续抵消云端收益，就应收窄它的适用范围。

## 配套实践

[跨进程恢复实践](../practice/lesson-06/README.md#选做跨进程恢复)复用第 6 课的选做实验，提供运行命令、完整代码和历史验证记录。确认两个场景都通过，再解释为什么文件被人修改后应保留 unknown。实验不调用模型，故障范围见第 4 节。

## 资料

以下产品与平台资料于 **2026 年 9 月 15 日**核验。预览状态、执行限制与存储规则按该日期理解；没有使用这些资料给厂商作可靠性排名。

1. [OpenAI Codex：云端执行环境](https://learn.chatgpt.com/docs/environments/cloud-environment)
2. [Cursor：选择 Cloud Agents 的执行位置](https://cursor.com/docs/cloud-agent/self-hosted/choose-runtime)
3. [GitHub Copilot cloud agent：配置执行环境](https://docs.github.com/en/copilot/how-tos/copilot-on-github/customize-copilot/customize-cloud-agent/customize-the-agent-environment)
4. [Google Jules：执行环境](https://jules.google/docs/environment/)
5. [Amp：Orbs 执行环境](https://ampcode.com/docs/orbs)
6. [Amp：Runners](https://ampcode.com/docs/cli/runners)
7. [Grok Bot：电脑与应用](https://docs.x.ai/grok-bot/computer-and-apps)
8. [Amp：从 Sourcegraph 独立的公司公告](https://ampcode.com/news/amp-frontier-corporation)
9. [Anthropic：拆分运行控制与执行环境](https://www.anthropic.com/engineering/managed-agents)
10. [OpenAI Agents API：架构](https://developers.openai.com/api/docs/guides/agents-api/architecture)
11. [Claude Managed Agents：概览与 Beta 状态](https://platform.claude.com/docs/en/managed-agents/overview)
12. [AWS AgentCore：Session 与计算生命周期](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-sessions.html)
13. [AWS AgentCore：存储类型与生命周期](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-filesystem-configurations.html)
14. [OpenAI Sandbox Agents：状态与工作区恢复](https://developers.openai.com/api/docs/guides/agents/sandboxes#resume-or-seed-future-work)
15. [Cursor：Pool 的 Session 生命周期](https://cursor.com/docs/cloud-agent/self-hosted/pool#session-lifecycle)
16. [Cursor：云端 Agent 接入自有机器](https://cursor.com/blog/self-hosted-machines)
17. [OpenAI Agents API：执行结果与继续 Session](https://developers.openai.com/api/docs/guides/agents-api/sessions#follow-progress-and-handle-outcomes)

相关基础：[Runtime 的职责](02-Agent运行时.md)、[会话与恢复状态](04-会话持久化.md)、[执行账本与对账](06-工具可靠性.md)、[编排与长任务](10-Agent编排.md)。

来源适用范围与核验日期见[资料核验记录](../research/agent-runtime-progress-sources.md)，完整产品范围见[主流方案对比](../research/agent-runtime-market-comparison.md)。
