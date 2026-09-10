# 第 10 课实践：让程序控制修改、验收与停止

正文见[第 10 课：Agent 编排](../../chapters/10-Agent编排.md)。

本轮沿用第 9 课的任务：把配置主题改成 dark，端口保持 3000。先看一次失败怎样进入修复，再看程序怎样停下来；不用从空白写函数。

默认模型回复是固定剧本，文件读写、工具账本和评分器都真实运行。这个模式验证工作流接线，不证明真实模型会自己修好问题，也不执行模型生成的代码。只有显式使用 `--live` 才会联网调用已配置的真实模型。

## 先跑完整流程

在仓库根目录运行：

```bash
python -B exercises/lesson-10-orchestration/workflow_demo.py
```

关键结果是：

```text
第 1 轮修改：程序验收 failed，端口被改成了 8080
第 2 轮修改：程序验收 passed，端口恢复为 3000
工作流结果：completed
```

这是输出摘要，不是另一份判卷逻辑。第一轮的模型回复也说已经修改主题，但程序会自己读取产物评分，再把失败原因交回同一个会话。

命令打印的运行目录会保留：

| 位置 | 用途 |
|---|---|
| `workspace/config.json` | Agent 可以修改的实际配置 |
| `initial.json`、`expected.json` | 工作区外的原始条件与评分依据，文件工具不能访问 |
| `attempt_01_config.json`、`attempt_02_config.json` | 每轮独立的产物快照，后续修复不覆盖旧证据 |
| `attempt_01_report.json` 等 | 每轮的运行状态、回复、评分和剩余预算 |
| `session.jsonl` | 复用综合实践保存的会话与工具 Ledger |
| `checkpoint.json`、`report.json` | 工作流阶段、限制与汇总结果 |

## 只改命令参数，观察两种停止

让预设模型每轮都改错：

```bash
python -B exercises/lesson-10-orchestration/workflow_demo.py --scenario always-wrong
```

总修改轮数上限为 3，包含首次修改。三轮验收都失败后，结果是 `attempt_limit`。这条命令退出码为 **2**，表示预期的“不通过”，不是要修改验收标准把它变绿。

再把整个任务的模型请求预算缩到 5 次：

```bash
python -B exercises/lesson-10-orchestration/workflow_demo.py --model-budget 5
```

第二轮文件已经写对，但预算不足以取得最后的模型回答：文件评分为 `passed`，工作流结果仍是 `model_budget_exhausted`，退出码为 **2**。程序不会把文件通过和运行完成混在一起。

每轮仍保留原 Agent Loop 的 4 次请求上限，外层预算跨轮共享。发生模型或工具运行异常时，本例停止；不会在副作用尚不明确时自动开启下一轮修改。评分器返回 `error` 时也停止，等待修正评分问题。

## 小规模真实模型验证

使用环境变量 `OPENAI_API_KEY`、`OPENAI_MODEL`，以及可选的 `OPENAI_BASE_URL`。真实调用可能产生费用；先限制为两轮修改、总共六次模型请求：

```bash
python -B exercises/lesson-10-orchestration/workflow_demo.py --live --max-attempts 2 --model-budget 6
```

客户端设置 30 秒超时、SDK 自动重试为 0。Provider 要求会话请求头时，再加 `--session-header 请求头名称`。该选项不用于传 API Key。

真实模型不按剧本行动，可能第一次就通过，也可能超时或失败。报告记录实际模型、运行模式、请求设置和源文件指纹；不要把模拟模式的“两轮成功”当作真实模型的结果。一次通过也不足以推导稳定成功率。

2026-09-10 的一次真实运行中，文件通过验收，但最后的模型回答超时，完整运行仍为 `run_error`。程序停止并保留成功的写入回执，没有自动重新写文件。实验过程见[真实验证记录](../../research/10-workflow-live-check.md)。

## 代码只看一段

打开 [workflow_demo.py](workflow_demo.py)，先找 `run_workflow()` 最后那段循环：

```text
调用现有 Agent → 保存本轮文件 → 程序评分 → 决定停止或反馈修复
```

里面的 `if / elif` 决定下一步。模型连接、文件工具和评分器均复用已有代码；本轮不用重写它们。想做一次小改动，只把命令中的 `--max-attempts` 改成 `1`，观察第一轮失败后是否还会继续。

## 前面的两个小例子按需回看

- [handoff_demo.py](handoff_demo.py)：交接处理者和必要上下文，程序侧审批不由交接文本提供；`--budget-demo` 验证交接不会重置模型请求额度。退款只追加内存记录，没有真实支付；审批集合只演示信任边界，不是完整的金额绑定或审批系统。
- [recovery_demo.py](recovery_demo.py)：独立进程保存和恢复主任务，复用两个已有结果，按第三个任务的模拟查询状态决定等待、核对或进入合并验收。没有真实子 Agent、并行执行或后台服务。

这两项目前是独立机制演示，并未合入上面的配置修改工作流。主工作流保留阶段与额度，但没有实现通用的自动重启续跑；单写者 JSON 替换也不证明断电持久性或并发原子扣减。

全部离线自检：

```bash
python -B exercises/lesson-10-orchestration/workflow_demo.py --self-check
python -B exercises/lesson-10-orchestration/handoff_demo.py --self-check
python -B exercises/lesson-10-orchestration/recovery_demo.py --self-check
```

上述自检没有网络调用或付费模型请求。自检临时目录自动清理，普通演示及 `--live` 的目录保留供你检查。
