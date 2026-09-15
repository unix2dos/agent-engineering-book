# 持久状态与云端执行：来源核验

对应[第 11 课](../chapters/11-Agent长期工作环境与云端执行.md)，核验日期为 2026-09-14。2026-09-15 仅整理材料职责，没有刷新产品事实；产品的版本、预览状态和承诺以当时记录为准。

本课采用可独立阅读的 Agent 进展分析形式，不要求读者先完成前十课。它区分厂商公开契约、本地机制实验与作者的条件性趋势判断；通用定义见 [Agent Progress Analysis](../CONTEXT.md)。旧提纲与编辑清单由 Git 保存。

## 来源与对应问题

| 问题 | 资料线索 | 需要查清的边界 |
| --- | --- | --- |
| 关闭界面后谁继续工作 | [Grok Bot](https://docs.x.ai/grok-bot/computer-and-apps)、[Amp Orbs](https://ampcode.com/docs/orbs) | 关闭客户端、执行进程故障和环境丢失分别能保证什么 |
| 运行控制与执行地点怎样分开 | [OpenAI Agents API](https://developers.openai.com/api/docs/guides/agents-api/architecture)、[Claude Managed Agents](https://www.anthropic.com/engineering/managed-agents) | 公开接口与内部实现证据的区别，自托管方仍承担什么责任 |
| 恢复需要保存哪些状态 | [OpenAI Sandbox Agents](https://developers.openai.com/api/docs/guides/agents/sandboxes) | 运行状态、沙箱连接状态、工作区快照的不同恢复范围 |
| 为什么仍有本地与自有环境 | [Amp Runners](https://ampcode.com/docs/cli/runners)、[OpenAI 自托管环境](https://developers.openai.com/api/docs/guides/agents-api/environments/self-hosted) | 执行位置可选择，不等于状态可跨厂商无缝迁移 |

## 证据边界

- 官方接口与工程文章说明公开支持的能力，不等于厂商内部源码或故障实测。
- 当时 OpenAI Sandbox Agents 文档标为 Beta；不能把核验日期的状态当作今后永久不变的承诺。
- 关闭客户端、执行进程退出、工作区丢失、断电和跨厂商迁移是不同故障或切换情境，不能互相替代证明。
- 本地实验只验证写入后丢失回执时的文件核对。运行入口、历史环境和指纹见[第 6 课实践](../practice/lesson-06/README.md)中的“选做：跨进程恢复”。
- 标准化后台任务更适合托管环境是文章的条件性判断；数据、权限、设备、成本与集成条件改变时，结论也应调整。用户确认文章立场不构成外部事实证据。
