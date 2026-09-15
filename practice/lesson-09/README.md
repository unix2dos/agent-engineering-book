# 第 9 课实践：为 Workspace Agent 设计评测并判断改动

先读[第 9 课正文](../../chapters/09-Agent评估.md)。本实践约 30 分钟，交付两样东西：一张说明“测什么、怎么测”的小题表，以及一份有证据、有边界的版本判断。

本轮复用历史模型实验和现有离线检查，不会自动调用付费模型。你要区分哪些是过去测到的模型表现，哪些是现在验证的程序行为。代码只需按文末的职责表查阅，不必再逐关重写基础设施。

## 0～5 分钟：确定这次想判断什么

本轮材料里的改动是：给 CSV Agent 增加“写入后读回核对”的 Prompt。判断目标是这条改动在原预算下是否值得保留。

先检查已有题目能覆盖什么：

| 编号 | 测试任务 | 检查依据 | 当前入口或证据 |
| --- | --- | --- | --- |
| E1 | 修改主题，保留端口 | 修改前快照与实际配置 | `run_trial.py --live --task basic` |
| E2 | 额外的 debug 字段仍被保留 | 目标正确，其他字段和值未变 | `run_trial.py --live --task keep-debug` |
| E3 | 汇总 CSV，原始输入不变 | 可信原始总数与实际文件 | `evidence/` 中两版各三次历史 Trial；可用 `--task csv-total` 新跑 |
| R1 | 压缩后保留完整 Tool Call / Result | 确定性的 Prompt View 断言 | 综合实践 `--checkpoint-3` |
| R2 | 中断恢复不盲目重做副作用 | Ledger 状态与执行次数 | 综合实践 `--checkpoint-5` |

E1～E3 可观察真实模型完成任务的表现。R1～R2 检查运行时规则；这两个命令使用预设输入或模型回复，不是新的真实模型 Trial。上表前两条只是可用入口，本轮不能假设它们已有这两个 Prompt 的对比成绩。

在表里补一行尚未覆盖、但你认为重要的任务，写清：

```text
要保护或改进的能力：
初始状态和用户要求：
怎样判通过，证据从哪里来：
它属于模型表现评测，还是运行时规则检查：
```

本轮目标是设计这条检查，不要求立刻实现。不要把设计中的任务写成“已通过”。

## 5～12 分钟：检查阅卷依据和已有保证

在仓库根目录运行：

```bash
python -B practice/lesson-09/grader.py --checkpoint-b
python -B practice/lesson-09/grader.py --check-csv
python -B practice/workspace-agent/agent.py --checkpoint-5
```

预期分别以 `checkpoint B passed`、`CSV grader self-check passed`、`checkpoint 5E passed` 收尾。第三条会连带运行 Context 与 Ledger 的前置检查，无需另跑 `--checkpoint-3`。

先确认阅卷器允许等价答案、拒绝坏产物，并能把自身故障保留为 `error`。再确认恢复和消息组装的确定规则仍然成立。把结果记在“小题表的检查记录”中，不要与历史 CSV 的 3/3 合并计算成功率。

如果某条检查失败，保留输出并先定位。不能通过删除失败记录来得到完整通过的结论。

## 12～22 分钟：读取两版成绩，执行门禁

归档的 [baseline.json](evidence/baseline.json) 和 [candidate.json](evidence/candidate.json) 来自之前的真实实验；本轮只是重新读取，不是模型重新考试。

重点看三处：

- `comparison_context`：实际 Prompt、模型、四次请求预算及内容指纹。
- `reports`：每次的 `agent_run` 与 `grade`，不要只读总成功率。
- 异常类型：请求预算耗尽与 API 连接失败需要分别解释。

执行：

```bash
python -B practice/lesson-09/compare_runs.py \
  --baseline practice/lesson-09/evidence/baseline.json \
  --candidate practice/lesson-09/evidence/candidate.json \
  --gate
```

预期外层 `status=blocked`，内部 `comparison.status=comparable`，进程退出码为 2。这个退出码是预期拦截；不是让你修改门槛把它变绿。

代码只检查这些历史报告。它没有验证当前代码版本、补评原始文件或部署任何东西。已知旧成绩是在门禁规则形成前收集的，本轮用它们学习决策；下一次正式实验应先确定条件与放行标准。

## 22～30 分钟：写一份能指导下一步的结论

用下面六行组织判断，每项都指向已有证据：

```text
本次判断针对哪个改动、哪些任务和哪个预算：
观察到的产物成绩与完整运行成绩：
哪些具体失败支持什么原因假设：
哪些异常还不能归因于改动：
当前建议保留、修改还是暂缓，理由是什么：
这份结果还没有覆盖什么，下一次补哪项验证：
```

检查你的结论有没有越过证据：两版各三次只覆盖归档 CSV；当前运行时检查通过，不代表候选模型通过了 Context 或权限任务；更短的失败耗时也不能当作效率收益。

完成标准是“小题表能解释选题理由，结论能区分观察与推断”，不要求重写运行器、Mock 或指纹逻辑。

## 选做：下一次真实实验

继续使用现有 `run_trial.py --live`，先为两版选定同一批任务和每题重复次数。每个命令会创建独立目录，不要覆盖旧报告。Provider 需要会话 Header 时，再加 `--session-header x-opencode-session`。

当前比较器专用于同一模型、同一任务和等量 Trial 的 Prompt/Runtime 对照；不能直接拿它比较不同模型或不同预算。若下一轮研究换模型，应先调整比较契约和报告核验，而不是手工改历史报告里的模型名。

开始前固定成功条件、停止规则和预算；结束后保存实际代码、Prompt、模型配置、题集、评分器版本及产物。下方列出代码职责与命令用法。

## 代码与运行参数

| 文件 | 职责 |
| --- | --- |
| [grader.py](grader.py) | 根据可信题目条件验收真实文件，区分 passed、failed、error |
| [run_trial.py](run_trial.py) | 准备独立工作区，调用综合项目，保存每次运行和评分 |
| [compare_runs.py](compare_runs.py) | 核对比较条件，读取报告并执行门禁 |

整章离线检查：

```bash
python -B practice/lesson-09/check.py
```

真实模型调用的配置见[实践总览](../README.md)中的“运行约定”。以下命令是选做，需要显式开启，可能产生费用：

```bash
python -B practice/lesson-09/run_trial.py --live --task csv-total --trials 3 --variant baseline
python -B practice/lesson-09/run_trial.py --live --task csv-total --trials 3 --variant verify-output
```

`--task` 可选 `basic`、`custom-port`、`keep-debug`、`csv-total`；`--trials` 默认 1，允许 1～10。每次最多 4 次模型请求；客户端超时 30 秒、SDK 自动重试 0。Provider 要求会话请求头时再加 `--session-header 请求头名称`。

每次都会重新准备工作区并保存题目、运行产物、会话和报告。标准答案在 Agent 工作区外，不能让 Agent 自己改答案来获得通过。命令打印的是临时目录，需要长期留存时自行归档。

文件已写对，但缺少正常 Final 的运行仍是 `error`，不能只拿文件评分算成功率。评分器本身出错也要保留为 `error`，不能归成 Agent 的错误答案。

重新评分不调用模型。配置题需用对应的原始标准答案；CSV 题需用工作区外的原始输入：

```bash
python -B practice/lesson-09/grader.py --config /本次目录/workspace/config.json --expected /本次目录/expected.json
python -B practice/lesson-09/grader.py --csv-workspace /本次目录/workspace --original-csv /本次目录/initial.csv
```

新的两版成绩用各自 `batch_report.json` 传给 `compare_runs.py`。相同任务、模型、预算和评分条件才有比较意义；正常比较的退出码 0 不代表允许发布，`--gate` 才执行放行规则。

本目录的历史报告保留原始代码指纹。当前目录和运行代码已经调整，本轮未重新请求模型，不能把旧成绩当作整理后版本的实测表现。
