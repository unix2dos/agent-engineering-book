# 第 14 课：运行控制的源码与实践核验

核验日期：2026-09-16。本文是第 14 课的证据记录，正文统一维护在 `chapters/14-Agent运行控制.md`；实践入口为 `practice/lesson-14/README.md`，预算实现复用第 10 课工作流。

## 固定来源与结论边界

Pi 固定提交：`e266507b606b9552fa277252644054afd4384b11`。下列结论只针对已读源码，不推断未来版本或整个产品的通用保证。

| 来源 | 核对到的行为 | 不能据此宣称 |
| --- | --- | --- |
| [工具调度](https://github.com/earendil-works/pi/blob/e266507b606b9552fa277252644054afd4384b11/packages/agent/src/agent-loop.ts#L409-L560) | 全局串行或任一被调用工具声明串行时整批串行；并行函数没有同时执行数上限 | 自动识别读写依赖、提供账号级共享限流 |
| [执行前检查](https://github.com/earendil-works/pi/blob/e266507b606b9552fa277252644054afd4384b11/packages/agent/src/agent-loop.ts#L607-L667) | beforeToolCall 可阻止调用并生成错误结果 | 自带工具预算或费用控制 |
| [轮次停止](https://github.com/earendil-works/pi/blob/e266507b606b9552fa277252644054afd4384b11/packages/agent/src/agent-loop.ts#L222-L255) | 工具结果加入上下文后才调用 shouldStopAfterTurn | 仅靠轮次结束检查即可严格限制本批执行数 |
| [命令执行](https://github.com/earendil-works/pi/blob/e266507b606b9552fa277252644054afd4384b11/packages/coding-agent/src/core/tools/bash.ts#L83-L150) | 收到取消或单次超时后调用 killProcessTree，并等待启动的子进程退出；timeout 可选 | 有默认任务总截止时间、全部后代进程必然退出 |
| [进程终止](https://github.com/earendil-works/pi/blob/e266507b606b9552fa277252644054afd4384b11/packages/coding-agent/src/utils/shell.ts#L216-L247) | Unix 先向进程组发 SIGKILL，失败时回退为单个 PID | 能清除所有脱离原进程组的进程或远端工作 |
| [输出收集](https://github.com/earendil-works/pi/blob/e266507b606b9552fa277252644054afd4384b11/packages/coding-agent/src/core/tools/output-accumulator.ts) | 保留有界尾部，超过阈值后将原始输出写到临时文件；该组件没有日志总容量额度 | 磁盘使用或全部写入缓冲都受正文返回上限约束 |
| [正文截断](https://github.com/earendil-works/pi/blob/e266507b606b9552fa277252644054afd4384b11/packages/coding-agent/src/core/tools/truncate.ts#L1-L11) | 默认上限为 2000 行和 50×1024 字节；命令工具使用尾部截断 | 元数据加上正文后的消息总大小恰好不超过 50 KiB |

## 项目实践：同一源码版本的离线观察

模式：固定剧本模型；真实文件工具、Ledger、Agent Loop 与评分器。没有网络请求或模型费用。下面参数接在 `python3 -B practice/lesson-10/workflow_demo.py` 后面。

| 参数 | 最终端口 | 产物评分 | 任务状态 | 总结状态 | 退出码 |
| --- | --- | --- | --- | --- | --- |
| `--tool-budget 3` | 8080 | failed | tool_budget_exhausted | not_requested | 2 |
| `--tool-budget 4` | 3000 | passed | completed | not_requested | 0 |
| `--model-budget 5` | 3000 | passed | model_budget_exhausted | not_requested | 2 |
| `--model-budget 5 --reserve-summary` | 8080 | failed | model_budget_exhausted | completed | 2 |

核验时工作文件指纹（包含尚未提交的修改；不是 Git 提交号）：

- `practice/lesson-10/workflow_demo.py`：`d29696c62e32ced92c0892aacec38a2988e64dc114f064f6322220656f82a3c5`
- `practice/workspace-agent/agent.py`：`3f43d75beff584937ec28536978fce325844d795a5300c4a192ae05d2b0dde5e`
- `practice/lesson-09/grader.py`：`2d6fd59d183896faf123e2af7bc57bacbc45dbfec9fa45ee5956ae354ebcd79b`

第 10 课离线检查已通过，覆盖三次工具额度跨轮共享、同批调用分别检查、四次额度恰好完成、预留总结占用第五次请求、总结错误工具调用不执行、总结超时不重试，以及正常完成不额外总结。

章节归位后运行 `python -B practice/check.py`，全书 22 组离线检查通过；新课复用已有自检，没有重复添加一组相同检查。目录、正文与实践入口的本地链接也已核对。这些结果不表示 GitBook 已发布。

这些结果不证明真实模型能可靠修复或准确总结。共享并发、请求频率、总截止时间、日志磁盘额度与远端取消在正文中是源码分析或应用策略，尚未集成到配置修改工作流。单写者 JSON 检查点不保证并发原子扣减、断电持久性或自动重启续跑。

## 补充的本地组件观察

一次临时实验直接复用了上述版本的 OutputAccumulator、truncate 与 killProcessTree，增加了教学用的 4096 字节日志额度。观察到：收到 4112 字节、保存 4096 字节、返回正文 498 字节（上限 512），记录到的父进程和子进程均已不存在。任务回执为 interrupted，logComplete=false。它只验证这次本地 Unix 进程组与受控写入路径，不验证完整 Pi Agent、脱离进程组的后代、远端任务或磁盘全局配额。

临时实验未作为另一套正式实践引入仓库；本章读者从第 14 课唯一实践入口运行上表四个配置工作流。临时材料可能被系统清理，上表命令与工作文件指纹用于正式实践复核。

## 2026-09-18：程序收尾结论与模型实验原文分开

后续真实模型实验发现“产物通过”被写成“任务通过”，原始证据及处理经过见[真实模型记录](../practice/lesson-14/live-check.md)。终端现在只打印程序生成的收尾结论；选做总结的原文和输入证据继续保存到 `report.json`，供实验对照。

新增 stdout 回归在修改前复现了错误原文出现在终端的问题，修改后通过，且核对磁盘报告仍保留原文、四次逻辑请求额度未改变。工作流自检和第 10 课检查通过；本轮未重跑全书检查，也未调用真实模型。上方历史指纹和实验结果保留为当时记录。
