# 第 11 课：Agent Runtime——持久状态与云端执行

设想一个配置修改任务：把 `config.json` 的主题改成 dark，端口保留 3000。助手已经写好文件，正在检查结果，这时你关掉了界面。

任务是否会继续，先要看执行程序在哪里。如果只是浏览器关了，远端程序可能仍在运行；如果执行进程也退出了，就需要从记录接续；如果连机器都被回收，还得找回修改过的文件。

本课沿这三种情况，拆开任务记录、运行程序和执行环境，再对照 OpenAI、Anthropic 等方案，判断哪些工作适合交给云端。开头是分析用的假设场景，第 4 节再用本地实验验证其中一个故障窗口。

## 1. Cloud Execution：界面与执行进程

先只关闭界面。假如修改和检查都由本机终端里的 Python 程序执行，终端关闭或电脑休眠就可能影响任务。如果执行程序在远端，浏览器只是发送要求、查看结果的入口，关掉浏览器时远端程序未必停止。

Codex Cloud 提供了后一种工作方式：它在托管容器里检出仓库、准备依赖，再调用终端工具修改和检查，最后交回回答与文件差异。[1] 放回配置任务，真正写入 `config.json`、运行检查的是远端环境里的程序，本机负责和它交互。

运行位置明确以后，还要分清这次停掉了什么：

| 发生的情况 | 先检查什么 | 接下来需要什么 |
| --- | --- | --- |
| 关闭浏览器 | 远端任务是否仍在执行 | 重新打开同一任务，查看进度和结果 |
| 执行进程退出 | 最后保存到哪一步，哪些动作结果不明 | 读取记录，核对后接续 |
| 执行机器被回收 | 修改过的文件和任务记录是否仍可取得 | 找回状态，重新准备执行环境 |

把这项任务的执行程序和所需文件一起放到云上，可以解除它对用户设备持续在线的依赖。后两种故障仍要单独处理；云上的程序也会退出，临时机器也会被回收。

## 2. Harness 与 Sandbox：运行控制和执行环境

现在让执行进程在检查结果之前退出。文件可能已经改好，但新启动的程序还需要知道：用户要求保留哪个端口，已经执行了哪些动作，哪些结果还没有拿到。

保存这些交互和执行事件的是会话记录，它们归属于同一个 **Session（会话）**。组织运行的宿主程序叫 **Harness**：它读取任务材料、调用模型、接收工具申请，再安排执行并处理结果。工具真正接触文件、运行命令的地方是 **Environment（环境）**；为执行增加隔离限制的环境通常称为 **Sandbox（沙盒）**。

在一个小程序里，这些职责可以放在一起。问题是恢复需要的材料存在哪里：如果只在旧进程的内存里，进程退出就丢了；如果放在会跟容器一起删除的目录里，换个容器仍然接不回来。

Anthropic 的 Managed Agents 工程文章描述了相应的拆分：会话日志保存在 Harness 之外，Sandbox 通过工具接口访问。Harness 故障后，新实例可以读回日志接续；执行环境的故障则作为工具执行问题处理。[8]

这里的“无状态 Harness”可以这样理解：恢复任务时，不需要保住原来那个进程本身。它运行时仍有内存和临时变量，但必须留下可供接手者读取的恢复记录。

OpenAI Agents API 也把运行控制与执行环境分开：OpenAI 运行 Harness，应用发送任务、接收事件；命令和文件操作可以交给托管环境，也可以交给客户自己的机器。[9] 对配置任务而言，发出写入申请的程序和保存 `config.json` 的机器，因此可以位于不同位置。

**职责拆开以后，可以分别安排故障处理；能否接上任务，还要看保存了哪些东西。**

## 3. Persistence：任务进度与工作区保存

假设新进程读到了“已经修改配置，等待检查结果”，却找不到那份配置文件。进度恢复了，工作现场仍然缺了一部分。

这次任务需要分别保管几类材料：

| 材料 | 在配置任务中对应什么 | 恢复时用来做什么 |
| --- | --- | --- |
| 会话历史与进度 | 修改要求、工具申请、已保存的结果 | 确定做到哪里、下一步准备处理什么 |
| 工作区文件与产物 | 当前 `config.json`，以及实际生成的检查报告 | 核对文件状态，继续检查或交付 |
| 跨任务记忆 | 经过确认、适用于其他任务的项目约定 | 帮助后续任务理解项目，不替代当前进度 |
| 运行中的进程与连接 | 检查进程、服务或数据库连接 | 确定能否重新连接，还是需要重建 |

OpenAI Sandbox Agents 将运行状态 `RunState`、沙箱会话状态和工作区快照分别处理：运行程序接续控制流程，沙箱后端负责重新连接或准备文件环境。该能力目前为 Beta。[13] 保存了对话，不代表已经备份文件；备份了文件，也不代表原来的检查进程能原地继续。

存储本身还有保留条件。AWS AgentCore 允许计算实例停止后沿用 Session ID 继续调用，但指定目录要配置相应存储，才能跨停启保留。其 microVM Session Storage 当前为 Preview，空闲 14 天会过期，运行时版本更新也会清空；其他存储类型的规则不同。[11][12]

因此，为配置任务选择环境时，要查的是 `config.json` 和任务记录实际放在哪里，机器回收、环境更新后能否取回。一个“持久化”选项，还不足以回答这些问题。

## 4. Recovery：回执丢失与文件对账

配套实验沿用开头的配置任务，复用文件工具与执行账本。这里只验证写入后丢失回执的恢复，工具申请由程序预设，不调用模型，也不运行完整的配置测试流程。

程序先记下工具准备执行，再修改文件。就在修改完成、成功回执尚未保存的位置，用 `os._exit(23)` 让执行进程退出。父进程确认它已经结束，然后启动另一个进程读取同一目录和账本。故障是主动注入的，文件写入与进程退出真实发生。

第一次，配置已经符合原请求。第二次，在启动恢复进程之前，模拟有人把端口改成了 8081。实际输出如下：

```text
文件符合原请求：进程退出码 23；running -> unknown -> succeeded；恢复未改写文件
文件被人修改：进程退出码 23；running -> unknown -> unknown；恢复未改写文件
```

`running` 是中断前留下的状态；`unknown` 表示当前还不知道那次动作的结果。新进程先把这份不确定性记下来，再检查文件。

第一种情况下，文件内容满足请求，可以记录“目标已满足”并补回结果。第二种情况下，文件已经不同，恢复逻辑保留 unknown，把未能确认的结果交回调用方。它没有用旧内容覆盖端口 8081。

这里用到的 **Ledger（执行账本）**，记录的是调用身份、参数和执行结果。它帮助恢复程序核对已经发生的动作。若把“没收到成功回执”直接当成“还没执行”，重跑一次就可能覆盖后来的修改。

这个实验也有清楚的边界：旧执行者已退出，同一时刻只有一个恢复进程，文件仍在同一块可访问的磁盘上。它没有验证断电、容器丢失、并发接管或厂商服务的恢复质量。内容匹配只能说明当前目标满足，不能证明历史动作是谁做的、做了几次；发送邮件之类的操作还需要查询对应服务的结果。

脚本在每个场景首次恢复结束后，再启动一个独立恢复进程，验证第二次正常退出，文件和账本的内容、文件标识与修改时间均不变，也不重复补回执。运行入口见文末配套实践。

## 5. 方案对照：成品 Agent 与运行平台

前面已经拆出了判断依据：谁继续执行、谁保存记录、文件能保留多久，以及结果不明时怎样核对。现在再看不同产品，可以把它们放回这些具体问题里。

直接使用成品 Agent 时，用户交出配置修改任务，由产品安排后续工作。各家的执行环境可以这样比较：

| 方案 | 执行环境 | 需要分清的边界 |
| --- | --- | --- |
| OpenAI Codex Cloud | 托管容器，按仓库配置准备依赖 | 环境缓存用于加速，不能直接当作完整故障恢复保证。[1] |
| Cursor Cloud Agents | 托管 VM，或自己的机器、企业 Worker Pool | 选择自有机器时，工具在那里执行，Agent Loop 仍在 Cursor 云端。[2] |
| GitHub Copilot cloud agent | GitHub Actions 环境，也支持自托管 Runner | 官方将开发环境描述为临时环境；代码成果与执行机器的寿命要分别判断。[3] |
| Google Jules | 每项任务使用短期云 VM，准备仓库和依赖 | 本次资料未确认自托管执行或崩溃后检查点恢复的具体承诺。[4] |
| Amp | 托管 Orb、本地 CLI 或自有 Runner | Orb 可以休眠后继续；Runner 的机器和进程由使用者管理。[5][6] |
| Grok Bot | 长期角色使用持久云电脑，处理文件与浏览器工作 | 同一账号的 Bots 共享电脑、文件和登录状态，并非每个任务都有隔离环境。[7] |

这里既有围绕仓库工作的编码 Agent，也有 Grok Bot 这样的长期角色与浏览器助手。它们的环境归属不同，不能把“有云电脑”一律理解成每个任务都有一台隔离机器。

如果要把这样的能力接入自己的应用，还要确定采用哪一层接口。以 OpenAI 为例，Agents SDK 是应用中使用的代码库，由应用运行 Harness；Agents API 提供托管 Harness；Codex Cloud 则是直接面向开发任务的产品。[1][9][13]

运行平台的对照因此要另列：

| 运行平台 | 提供的能力 | 应用仍需明确什么 |
| --- | --- | --- |
| OpenAI Agents API | 托管 Harness、Session 与事件接口，可连接托管或自有环境 | 自定义工具怎样处理；自托管机器怎样启停、重连和保存文件。[9] |
| Claude Managed Agents | 托管运行过程、会话事件和工具环境，支持自托管 Sandbox；当前为 Beta | 任务指令、工具权限、环境和成功标准怎样配置。[10] |
| AWS Bedrock AgentCore Runtime | 运行开发者自己的 Agent 或工具，提供计算与存储能力 | Agent 自身逻辑、Session 归属与存储挂载怎样安排。[11][12] |

这些表说明厂商接管了哪些工作，以及应用还要负责什么。它们依据公开文档整理，无法替代相同任务、相同故障条件下的可靠性测试。

## 6. 部署选择：数据条件与任务验收

回到配置任务。如果仓库能获取、依赖能够自动安装、检查不依赖本机设备，我会优先考虑托管环境，让任务在用户离开电脑后继续。若配置必须在某台设备或企业内网中验证，执行放在对应环境里可能更直接。

这种选择已经出现在实际产品中。Cursor 可以连接个人机器或企业管理的一组 Worker，由这些执行进程接收远端发来的工具调用；GitHub Copilot cloud agent 也支持自托管 Actions Runner，当前限定 Ubuntu x64 和 Windows 64 位。[2][3]

接入自己的机器以后，仍要安排状态保留。Cursor 的 Worker Pool 在机器释放后，如果没有配置休眠恢复，后续消息可能被分配到新机器，旧工作区不会自动带过去。[14] 对本例来说，配置文件若只留在旧机器上，新执行者仍需另找来源。

执行留在本地，也要检查哪些内容会传出去。Cursor 明确说明，工具输出仍会回到云端参与推理，可能包含代码。[15] 文件位置、模型推理位置和数据传输范围，需要分别确认。

我更看好标准化后台任务扩大采用托管环境的方向。它减少了用户保持设备在线和维护多个执行环境的负担。内网、专用设备、数据访问与成本条件不同，执行位置也应随之调整；若接入和运行成本抵消了收益，就不必为了跟随趋势迁移。

最后还要验收任务本身。OpenAI 的 Sessions 文档明确指出，turn completed 不保证每个工具都成功。[16] 对这次配置修改，应确认主题已经是 dark、端口仍为 3000，并取得针对最终文件的检查结果。任务在云端跑完、恢复进程正常退出，都不能省掉这一步。

## 配套实践

进入[第 6 课实践](../practice/lesson-06/README.md)的“选做：跨进程恢复”小节，运行同一配置任务的两个恢复场景，再解释为什么文件被人修改后应保留 unknown。该实验复用已有实现，故障范围见第 4 节。

## 资料

以下产品与平台资料于 **2026 年 9 月 15 日**核验。预览状态、执行限制与存储规则按该日期理解；没有使用这些资料给厂商作可靠性排名。

1. [OpenAI Codex：云端执行环境](https://learn.chatgpt.com/docs/environments/cloud-environment)
2. [Cursor：选择 Cloud Agents 的执行位置](https://cursor.com/docs/cloud-agent/self-hosted/choose-runtime)
3. [GitHub Copilot cloud agent：配置执行环境](https://docs.github.com/en/copilot/how-tos/copilot-on-github/customize-copilot/customize-cloud-agent/customize-the-agent-environment)
4. [Google Jules：执行环境](https://jules.google/docs/environment/)
5. [Amp：Orbs 执行环境](https://ampcode.com/docs/orbs)
6. [Amp：Runners](https://ampcode.com/docs/cli/runners)
7. [Grok Bot：电脑与应用](https://docs.x.ai/grok-bot/computer-and-apps)
8. [Anthropic：拆分运行控制与执行环境](https://www.anthropic.com/engineering/managed-agents)
9. [OpenAI Agents API：架构](https://developers.openai.com/api/docs/guides/agents-api/architecture)
10. [Claude Managed Agents：概览与 Beta 状态](https://platform.claude.com/docs/en/managed-agents/overview)
11. [AWS AgentCore：Session 与计算生命周期](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-sessions.html)
12. [AWS AgentCore：存储类型与生命周期](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-filesystem-configurations.html)
13. [OpenAI Sandbox Agents：状态与工作区恢复](https://developers.openai.com/api/docs/guides/agents/sandboxes#resume-or-seed-future-work)
14. [Cursor：Pool 的 Session 生命周期](https://cursor.com/docs/cloud-agent/self-hosted/pool#session-lifecycle)
15. [Cursor：云端 Agent 接入自有机器](https://cursor.com/blog/self-hosted-machines)
16. [OpenAI Agents API：执行结果与继续 Session](https://developers.openai.com/api/docs/guides/agents-api/sessions#follow-progress-and-handle-outcomes)

相关基础：[Runtime 的职责](02-Agent运行时.md)、[会话与恢复状态](04-会话持久化.md)、[执行账本与对账](06-工具可靠性.md)、[编排与长任务](10-Agent编排.md)。

来源适用范围与核验日期见[资料核验记录](../research/agent-runtime-progress-sources.md)，完整产品范围见[主流方案对比](../research/agent-runtime-market-comparison.md)。
