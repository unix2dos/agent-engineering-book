# 持久状态与云端执行：来源核验

对应[第 11 课](../chapters/11-Agent长期工作环境与云端执行.md)。最初核验于 2026-09-14；2026-09-15 在目录整理之后补充核验主流厂商方案，并调整正文案例。下表及正文新增比较以 2026-09-15 的官方页面为依据；它们仍是带日期的资料快照。

本课采用可独立阅读的 Agent 进展分析形式，不要求读者先完成前十课。它区分厂商公开契约、本地机制实验与作者的条件性趋势判断；通用定义见 [Agent Progress Analysis](../CONTEXT.md)。旧提纲与编辑清单由 Git 保存。

## 来源与对应问题

| 问题 | 资料线索 | 需要查清的边界 |
| --- | --- | --- |
| 成品 Agent 怎样运行仓库任务 | [Codex Cloud](https://learn.chatgpt.com/docs/environments/cloud-environment)、[Cursor](https://cursor.com/docs/cloud-agent/self-hosted/choose-runtime)、[GitHub Copilot](https://docs.github.com/en/copilot/how-tos/copilot-on-github/customize-copilot/customize-cloud-agent/customize-the-agent-environment)、[Jules](https://jules.google/docs/environment/) | 区分成品、托管平台与 SDK；异步执行不等于故障恢复保证 |
| 运行控制与执行地点怎样分开 | [OpenAI Agents API](https://developers.openai.com/api/docs/guides/agents-api/architecture)、[Claude Managed Agents](https://www.anthropic.com/engineering/managed-agents) | 公开接口与内部实现证据的区别，自托管方仍承担什么责任 |
| 恢复需要保存哪些状态 | [OpenAI Sandbox Agents](https://developers.openai.com/api/docs/guides/agents/sandboxes)、[AWS Session](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-sessions.html)、[AWS 存储](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-filesystem-configurations.html) | 运行状态、环境连接、文件及存储失效条件分别核对 |
| 为什么仍有本地与自有环境 | [Cursor 执行位置](https://cursor.com/docs/cloud-agent/self-hosted/choose-runtime)、[Cursor Pool](https://cursor.com/docs/cloud-agent/self-hosted/pool)、[GitHub 自托管 Runner](https://docs.github.com/en/copilot/how-tos/copilot-on-github/customize-copilot/customize-cloud-agent/customize-the-agent-environment) | 自托管方承担运维；工具输出仍可能送往云端；工作区不自动随新机器迁移 |
| 其他工作方式怎样补充主案例 | [Amp Orbs](https://ampcode.com/docs/orbs)、[Amp Runners](https://ampcode.com/docs/cli/runners)、[Grok Bot](https://docs.x.ai/grok-bot/computer-and-apps) | Orb/Runner 的环境选择、账号共享电脑与长期角色之间的区别 |
| 如何判断任务完成 | [OpenAI Session 结果](https://developers.openai.com/api/docs/guides/agents-api/sessions#follow-progress-and-handle-outcomes) | completed 不能替代工具结果与产物验收 |

更完整的厂商范围、产品背景与成熟度资料差异见[主流方案对比](agent-runtime-market-comparison.md)。正文以 OpenAI 与 Anthropic 的官方运行架构为主论据，其他产品承担交叉核验与差异案例。

## 证据边界

- 官方接口与工程文章说明公开支持的能力，不等于厂商内部源码或故障实测。
- 本轮 OpenAI Sandbox Agents、Claude Managed Agents 文档标为 Beta；AWS microVM Session Storage 标为 Preview。状态和保留规则不能外推到其他产品或未来版本。
- Jules 的脱离 Beta 公告与 FAQ 标签存在差异，正文只采用可确认的环境描述，不给出 GA/Beta 定论。
- 关闭客户端、执行进程退出、工作区丢失、断电和跨厂商迁移是不同故障或切换情境，不能互相替代证明。
- 本地实验只验证写入后丢失回执时的文件核对。运行入口、历史环境和指纹见[第 6 课实践](../practice/lesson-06/README.md)中的“选做：跨进程恢复”。
- 标准化后台任务更适合托管环境是文章的条件性判断；数据、权限、设备、成本与集成条件改变时，结论也应调整。用户确认文章立场不构成外部事实证据。
