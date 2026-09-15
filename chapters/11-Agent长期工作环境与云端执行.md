# 第 11 课：Agent Runtime——持久状态与云端执行

假设你交给助手一个任务：把 `config.json` 的主题改成 `dark`，端口保持 `3000`。文件已经写好，检查还没结束，你关掉了网页。再次打开时，能看到结果吗？

这要看关掉了哪一部分。网页关闭，远端程序可能仍在工作；程序退出，需要别的进程接手；如果机器和磁盘一起消失，刚改的文件还得能找回来。

前面的会话持久化、工具可靠性和沙盒，分别解决保存、对账和限制访问的问题。本课把这些机制用到同一个任务中，判断执行放在哪里、哪些材料必须保住，以及厂商替你负责了哪部分。前三节讨论不同故障下的处理条件，第 4 节用实际实验核对其中一种情况。

## 1. 关闭网页：先看任务在哪里执行

先只关闭网页。假设任务已经被远端接收，由能独立运行的程序处理，浏览器只负责显示进度。关掉浏览器后，远端仍可以修改文件、运行检查。再次打开同一任务时，应用把保存的进度和结果取回来。

如果运行程序就在本机终端里，关闭终端或让电脑休眠，则可能影响任务。看不见界面时工作是否继续，取决于程序怎样运行。

Codex Cloud 是一种远端执行方式：它在托管容器里检出仓库、准备依赖，通过终端工具修改和检查，最后交回回答与文件差异。[1] 在这样的环境中，实际接触 `config.json` 的程序位于远端，本机可以只作为交互入口。

看到关网页以后仍有结果，能说明这次任务不需要网页一直开着。但执行程序也可能崩溃，承载它的机器也可能被回收。这两种情况还要分别处理。

## 2. 程序退出：让接手者知道做到哪一步

现在换一种故障：执行程序在检查结束前退出了。新启动的程序打开 `config.json`，看见主题已经是 `dark`，却不知道端口应该是多少，也不知道旧程序是否做过检查。

要接手，它至少得读到原来的要求、已经发出的工具申请和保存下来的结果。同一段任务交互归属于一个会话，叫 **Session**。第 4 课介绍了怎样保存这些记录；放到这里，还要确认它们存在哪里。只留在旧进程内存里的信息，进程退出后就拿不到了。

读回记录后，需要有程序继续调用模型、安排工具执行、处理结果。这个负责组织运行的程序叫 **Harness**。

工具真正读文件、跑命令的地方是执行环境。系统在这里强制限制能读哪些文件、能访问哪些网络，就形成了 **Sandbox（沙盒）**。换一个程序接手任务时，这些限制也要继续生效。

Anthropic 的 Managed Agents 工程文章给出了这样的拆分：会话日志保存在 Harness 之外，执行环境通过工具接口访问。Harness 故障后，新实例可以读回日志继续处理；执行环境发生的错误则通过工具结果交回来。[8]

这样，换掉运行程序所在的进程后，另一个进程仍能依据记录接手。文档把这种安排称为“无状态 Harness”。程序运行时照样用内存，恢复任务靠的是留在进程外的记录。

OpenAI Agents API 同样允许分开安排：由 OpenAI 运行 Harness，应用发送任务、接收事件，文件和命令操作则交给托管环境或客户自己的机器。[9] 因而，决定下一步做什么的程序，与实际保存 `config.json` 的机器，可以不在同一个地方。

## 3. 机器被回收：把记录和文件分别保住

再看机器和本地磁盘一起被清理的情况。假设聊天记录保存在另一项服务里，其中写着“配置已经修改”。新机器能读到这句话，但没有修改后的 `config.json`，仍然接不上原来的工作状态。

即使在旧机器上做过 `git commit`，提交也还在那块磁盘里。要承受这次磁盘丢失，需要已推送的提交，或保存在机器外的文件副本。保存某个时刻的工作区文件版本，通常叫工作区快照。若记录确实包含完整改动，也可以核对后重建文件；只记下一句“写入成功”，就不够了。

几类材料要分别找回：

| 材料 | 在这个任务中的作用 |
| --- | --- |
| 会话历史与执行记录 | 找回修改要求，知道哪些动作已有结果、哪些还不确定 |
| 工作区文件与产物 | 找回实际的配置和检查报告，继续核对或交付 |
| 跨任务记忆 | 提供经过确认的项目约定，帮助理解要求 |
| 进程与连接信息 | 判断原检查是否仍在运行，能否重新连接，或需要重建 |

OpenAI Sandbox Agents 的接口把“运行到哪一步”“怎样连接沙箱”和“用哪些文件准备工作区”分别处理，对应运行状态 `RunState`、沙箱会话状态和工作区快照。这项沙箱能力在核验时仍处于 Beta 测试阶段。[13] 恢复了会话，文件和原来的检查进程未必也能一并回来。

存储还可能有保留条件。按本章核验的 AWS AgentCore 文档，计算实例停止后，可以沿用 Session ID 继续调用；指定目录要配置相应存储，才能跨停启保留。microVM Session Storage 当时还是预览功能（Preview），空闲 14 天会过期，运行时版本更新也会清空；其他存储类型的规则不同。[11][12]

因此，检查一种方案的恢复能力时，要找到实际的保存位置和保留规则：机器消失以后，谁还能把任务记录和修改过的文件交给新执行者？

## 4. 文件已改好，结果却没记下来

文件还在，也不能直接把旧工具调用全部重做一遍。旧程序可能已经完成写入，只是没来得及记下结果。

配套实验就停在这个位置。程序预设一条写入申请，把配置改成 `dark`、`3000`；文件写好后，立即用 `os._exit(23)` 退出进程，让成功结果来不及记入账本。这里把工具返回的执行结果称为回执。父进程确认旧进程已经结束，再启动新的恢复进程。文件写入与进程退出真实发生，实验没有调用模型。

实验用两个独立目录模拟两种情况：一份文件保持原样；另一份在恢复前，模拟有人把端口改成 `8081`。每个场景都先后启动两次恢复进程，第二次用来检查恢复流程能否安全重复。原来的写入任务不会被重新执行。

实际输出是：

```text
文件符合原请求：进程退出码 23；running -> unknown -> succeeded；恢复未改写文件
再次启动恢复进程：succeeded；文件和账本均未变化，未重复补回执。
文件被人修改：进程退出码 23；running -> unknown -> unknown；恢复未改写文件
再次启动恢复进程：unknown；文件和账本均未变化，未重复补回执。
PASS：两个场景各启动两次独立恢复进程；未调用模型、未验证断电或容器丢失。
```

`running` 是中断前留下的“正在执行”。新进程先记为 `unknown`，承认结果尚未确认，再拿原请求与文件对照。这些调用身份、参数和结果，保存在 **Ledger（执行账本）** 中。

文件符合原请求时，程序补记“目标已满足”的成功结果；端口变成 `8081` 时，继续保持 `unknown`，保留现有文件。当前产物不合格，不足以证明原来那次写入失败：可能先写对了，后来又被人修改。反过来，内容符合要求也不能证明是谁写的、写过几次。

第二次恢复没有新回执要补，两份现场都保持原状。最后的 `PASS` 说明这些检查符合预期，不能把仍为 `unknown` 的任务算成成功。

这次验证的前提是旧执行者已退出、恢复进程依次运行、文件仍在同一块可访问的磁盘上。它没有验证断电、容器丢失或并发接管。换成发邮件等操作，还要查询对应服务的结果，不能靠文件比较判断是否已经执行。第 6 课详细解释对账规则；本课借这个实验检查新进程接手时需要什么证据。

## 5. 选择产品：看厂商替你接管了哪些工作

有了前面的判断依据，再看产品里的“后台运行”“持久化”“可恢复”，就能追到具体对象：哪个程序继续执行，哪些记录和文件被保存，发生故障后由谁处理。

如果想直接交任务，由产品安排执行，可以先看成品 Agent：

| 方案 | 执行环境 | 选用前需要看清什么 |
| --- | --- | --- |
| OpenAI Codex Cloud | 托管容器，按仓库配置准备依赖 | 环境缓存用于加速启动，不能直接当作完整故障恢复保证。[1] |
| Cursor Cloud Agents | 托管虚拟机、自己的机器，或企业统一管理的机器 | 选择自有机器时，工具在那里执行，Agent Loop 仍在 Cursor 云端。[2] |
| GitHub Copilot cloud agent | GitHub Actions 环境，也支持自托管 Runner | 开发环境是临时的，代码成果要与机器的寿命分开判断。[3] |
| Google Jules | 每项任务使用短期云虚拟机，准备仓库和依赖 | 本次资料未确认自托管执行或崩溃后检查点恢复的具体承诺。[4] |
| Amp | 托管 Orb、本地 CLI 或自有 Runner | Orb 可以休眠后继续；自有 Runner 的机器和进程由使用者管理。[5][6] |
| Grok Bot | 长期角色使用持久云电脑，处理文件与浏览器工作 | 同一账号的 Bots 共享电脑、文件和登录状态，并非每个任务都有隔离环境。[7] |

如果要把 Agent 能力接入自己的应用，还要选择代码库或运行平台。以 OpenAI 为例：使用 Agents SDK，由应用运行 Harness；使用 Agents API，由服务方托管 Harness；Codex Cloud 则是直接接收开发任务的产品。[1][9][13]

这些运行平台接管的范围也不同：

| 运行平台 | 提供的能力 | 应用仍需负责什么 |
| --- | --- | --- |
| OpenAI Agents API | 托管运行程序、会话记录和事件接口，可连接托管或自有环境 | 处理自定义工具；安排自托管机器的启停、重连和文件保存。[9] |
| Claude Managed Agents | 托管运行过程、会话事件和工具环境，支持自托管 Sandbox；核验时为 Beta | 配置任务指令、工具权限、执行环境和成功标准。[10] |
| AWS Bedrock AgentCore Runtime | 运行开发者自己的 Agent 或工具，提供计算与存储能力 | 实现 Agent 逻辑，安排 Session 归属与存储挂载。[11][12] |

这里比较的是公开文档中的责任范围。它能帮助筛选方案；要判断谁在相同故障下恢复得更可靠，还需要实际测试。

## 6. 选择执行位置：跟着数据和验收条件走

回到配置任务。如果仓库可以获取、依赖能够自动安装，检查也不依赖本机设备，我会优先考虑托管环境，让工作在用户离开电脑后继续。若配置必须在企业内网或某台专用设备上验证，执行放在对应环境里可能更省事。

现有产品也保留了这种选择。Cursor 可以连接个人机器或企业管理的一组执行进程；GitHub Copilot cloud agent 支持自托管 Actions Runner，核验时限定 Ubuntu x64 和 Windows 64 位。[2][3]

机器由自己提供，也要安排文件保存。Cursor 可以使用企业统一管理的一组机器，称为 Worker Pool。某次任务释放机器后，如果没有配置休眠恢复，后续消息可能分配到新机器，旧工作区不会自动带过去。[14]

文件位置也不能说明全部数据的去向。Cursor 明确说明，工具输出仍可能包含代码，并被送回云端参与推理。[15] 因此，执行放在哪里、文件保存在哪里、哪些内容会传出去，要分别核对。

我更看好标准化后台任务扩大采用托管环境的方向，因为它能减少用户保持设备在线、维护多套环境的负担。但接入、运行、数据搬运和验收都有成本。若这些成本抵消了收益，就没有必要为了迁到云上而改变原来的工作方式。

最后打开实际产物验收。配置的主题是否为 `dark`、端口是否仍为 `3000`，检查结果是否对应这份最终文件？OpenAI 的 Sessions 文档也说明，turn completed 不保证每个工具都成功。[16] 选定执行位置后，任务是否完成，仍要由这些具体结果回答。

## 配套实践

进入[第 6 课实践](../practice/lesson-06/README.md)的“选做：跨进程恢复”，运行上面的两个场景，再解释为什么一个可以补记成功、另一个应保持 `unknown`。该实验复用已有实现，故障范围见第 4 节。

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
