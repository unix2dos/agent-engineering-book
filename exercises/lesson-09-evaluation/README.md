# 第 9 课实践：为 Workspace Agent 设计评测并判断改动

先读[第 9 课正文](../../chapters/09-Agent评估.md)。本实践约 30 分钟，交付两样东西：一张说明“测什么、怎么测”的小题表，以及一份有证据、有边界的版本判断。

本轮复用历史模型实验和现有离线检查，不会自动调用付费模型。你要区分哪些是过去测到的模型表现，哪些是现在验证的程序行为。原来的 A～H 分步实现保留在文末，遇到代码细节再展开。

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
python -B exercises/lesson-09-evaluation/starter.py --checkpoint-b
python -B exercises/lesson-09-evaluation/starter.py --check-csv
python -B exercises/phase-1-capstone/starter.py --checkpoint-5
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
python -B exercises/lesson-09-evaluation/compare_runs.py \
  --baseline exercises/lesson-09-evaluation/evidence/baseline.json \
  --candidate exercises/lesson-09-evaluation/evidence/candidate.json \
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

## 准备开展下一次真实实验时

继续使用现有 `run_trial.py --live`，先为两版选定同一批任务和每题重复次数。每个命令会创建独立目录，不要覆盖旧报告。Provider 需要会话 Header 时，再加 `--session-header x-opencode-session`。

当前比较器专用于同一模型、同一任务和等量 Trial 的 Prompt/Runtime 对照；不能直接拿它比较不同模型或不同预算。若下一轮研究换模型，应先调整比较契约和报告核验，而不是手工改历史报告里的模型名。

开始前固定成功条件、停止规则和预算；结束后保存实际代码、Prompt、模型配置、题集、评分器版本及产物。下方分步说明包含各条命令的用法。

<details>
<summary>展开原有 A～H 分步实现与代码说明</summary>

任务开始前，`config.json` 的内容是：

```json
{"theme": "light", "port": 8080}
```

用户要求把 `theme` 改成 `dark`，其他配置保持不变。Agent 回复“修改完成”以后，我们还要打开实际文件检查。

这一关先写阅卷器。输入是任务结束后的文件路径，输出是一份包含 `status` 和 `reason` 的字典。它不调用 Model，也不修改被评分的文件，可以在评分代码修好后直接补评原产物。

## 先看两个检查

[`starter.py`](starter.py) 已提供第一、二关的参考实现。先读 `grade_config()`，暂时跳过后面的自检和命令行代码。

`content = config_path.read_text(encoding="utf-8")` 打开文件，得到文字。`actual = json.loads(content)` 再把 JSON 文字变成 Python 数据。

例如 `actual` 是 `{"port": 8080, "theme": "dark"}`，阅卷程序按顺序检查：

```python
if actual.get("theme") != "dark":
    return {"status": "failed", "reason": "theme 没有改成 dark"}

expected = {"theme": "dark", "port": 8080}  # 基础题的答案；后面的变式题传入各自答案。
if actual != expected:
    return {"status": "failed", "reason": "其他配置被修改、删除或新增"}

return {"status": "passed", "reason": "主题正确，其他配置保持不变"}
```

`get("theme")` 取出主题值，字段不存在时得到 `None`。`!=` 表示“不等于”。第一条检查通过以后，主题已经确定正确；第二条再比较完整字典，就能发现端口被改成 `9999`、被删除，或者多出一个 `debug` 字段。

字典比较不要求字段顺序相同。文件里的空格和换行在解析后也不会影响比较。完整函数还会先拒绝数组等不是 JSON 对象的结果，并检查本题各个简单字段的类型，避免把布尔值 `false` 和数字 `0` 混在一起。

## 文件错误和阅卷错误怎样分开？

| 检查结果 | status | 本题中的例子 |
| --- | --- | --- |
| 检查完成，产物符合要求 | `passed` | 主题为 dark，端口仍为 8080 |
| 检查完成，产物不符合要求 | `failed` | 端口被删除、文件缺失或 JSON 损坏 |
| 评分没能完成，成绩未知 | `error` | 阅卷程序变量名拼错，或文件读取发生其他系统错误 |

`grade_config()` 只把预期的产物问题变成 `failed`，例如 `json.loads()` 遇到坏 JSON 时产生的 `JSONDecodeError`。外面的 `safe_grade_config()` 接住其余异常，保留异常类型和原因，返回 `error`。这样不会把评分程序自己的故障扣到 Agent 头上。

文件缺失被判失败的前提，是测试环境正常，而且这里指向的确实是本题要求的输出位置。若测试环境丢失、路径配置错了，应先修评测环境；当前小函数无法独自判断这些上游问题。

## 运行第一关

在仓库根目录执行：

```bash
python -B exercises/lesson-09-evaluation/starter.py --checkpoint-a
```

自检会在临时目录制造正确文件、被删端口、错误主题和坏 JSON 等产物，再模拟一次阅卷程序异常。末尾应出现：

```text
阅卷程序出错: error
原文件补评: passed
checkpoint A passed
```

这证明阅卷器能处理这些情况，不代表真实 Agent 已经通过评测。要评现有 Workspace Agent，先在隔离的测试工作区恢复题目的初始文件，再让它执行修改任务，最后把那个实际输出路径传入 `--config`：

```bash
python -B exercises/lesson-09-evaluation/starter.py --config /你的测试工作区/config.json
```

这个命令只读文件。退出码 `0` 表示通过，`1` 表示任务失败，`2` 表示评分失败。本题先检查最终配置；运行中是否碰过其他文件、最终回答是否诚实，需要另外的过程证据和检查，不能从这一个文件推断。

## 这一关哪些代码要自己动手？

亲手改一次临时测试文件：删掉 `port`，再只改变字段顺序，观察为什么前者失败、后者通过。随后自己重写 `grade_config()` 的两个判断和返回结果，运行同一条自检命令。

这次的异常处理、临时目录、模拟故障和命令行入口已由 AI 提供。先理解它们怎样区分三种结果，不要求一次把所有样板代码背下来。

## 第二关 B：有一份答卷出错，其余继续阅卷

同一个配置修改任务运行了四次，会留下四份答卷。每份都有自己的编号 `trial_id` 和文件路径。这里仍是一个 Task、四个 Trial；自检使用手写产物模拟它们，不代表 Agent 真的运行了四次。

```text
trial_1  文件正确                         -> passed
trial_2  文件不是有效 JSON                -> failed
trial_3  文件正确，但这次阅卷代码出错      -> error
trial_4  文件正确                         -> passed
```

第一关的 `safe_grade_config()` 已经能检查一份文件。第二关的 `grade_trials(trials)` 用它依次处理全部答卷。参考实现已补齐，你可以先沿循环读一遍，再尝试自己重写。

输入 `trials` 是一个列表，每一项长这样，`config_path` 是一个 `Path` 对象：

```python
{"trial_id": "trial_1", "config_path": Path("trial_1/config.json")}
```

这个列表由评测程序准备，编号互不重复。函数要返回：

```python
{
    "results": [
        {"trial_id": "trial_1", "status": "passed", "reason": "主题正确，其他配置保持不变"},
        # 后面依次放 trial_2、trial_3、trial_4 的结果和原始评分原因。
    ],
    "summary": {"total": 4, "passed": 2, "failed": 1, "error": 1},
}
```

先准备空的 `results`，写普通循环，每次调用已有函数：

```python
for trial in trials:
    result = safe_grade_config(trial["config_path"])
    # 把原 trial_id、返回的 status 和 reason 组成一份成绩。
    # 用 results.append(...) 保留这份成绩。
```

计数现在放进共用的 `summarize_results(results)`：先建立全零的三类计数，`total` 使用 `len(results)`，再逐份累加。例如 `status = result["status"]` 得到 `"failed"` 时，`summary[status] = summary[status] + 1` 就是在把失败次数增加一。这里 `summary[status]` 等于 `summary["failed"]`。

第一版把计数写在 `grade_trials()` 内；接入真实批量运行后，把这几行原样提出来，供两个入口复用。这个函数只统计已经取得的成绩，不重新评分文件。

保留输入顺序，给每份成绩带上原编号和评分原因。遇到 `failed` 或 `error` 都继续循环，不提前 `return`；等所有答卷处理完，再返回整份报告。输入记录与原文件都不要修改。空列表则返回空的 `results` 和四个零。

运行：

```bash
python -B exercises/lesson-09-evaluation/starter.py --checkpoint-b
```

当前参考实现会先检查 A，再检查 B。末尾应出现：

```text
trial_1: passed
trial_2: failed
trial_3: error
trial_4: passed
total=4 passed=2 failed=1 error=1
checkpoint B passed
```

报告中有一份 `error`，意味着还有一份成绩未定。先保留三类原始数量，后续计算成功率时才有依据决定分母，不能悄悄丢掉评分失败。

这次循环、成绩追加和计数已由 AI 帮你补齐。读懂后可以遮住答案，亲手重写这三步，再运行同一条自检。临时文件、故障模拟和断言直接复用即可。自检通过只证明报告能正确汇总这些已知样例。

## 第三步 C：让 Agent 真做一次，再看成绩

A、B 中的文件是测试代码提前写好的，用来检查阅卷器。现在运行 [`run_trial.py`](run_trial.py)：它调用[综合实践里的 Agent](../phase-1-capstone/starter.py)，让 Agent 自己发出工具申请，再把实际改出的文件交给第一关的阅卷器。

```text
新建一份 config.json：light，端口 8080
-> Model 申请读取文件
-> 原来的 read_file 返回实际内容
-> Model 申请修改文件
-> 原来的 write_file 写入，Ledger 留下执行记录
-> Agent 返回回答
-> safe_grade_config 检查实际文件
-> 保存 report.json
```

这张图是一次正确完成任务的路径；Model 也可能只说“改好了”却没有写入，这时阅卷器仍会判失败。脚本只负责准备初始文件，运行后的答案由 Agent 的工具调用产生。

先使用已经配置好的 `OPENAI_API_KEY`、`OPENAI_MODEL` 和可选的 `OPENAI_BASE_URL`，在仓库根目录执行：

```bash
python -B exercises/lesson-09-evaluation/run_trial.py --live
```

这条命令会发送真实模型请求。它复用综合实践的最多 4 次模型请求上限，每次请求超时设为 30 秒，关闭 SDK 自动重试。

若 Provider 要求会话请求头，用 `--session-header` 指定名称，脚本会把本次目录的唯一编号用于整段会话，不用填写真实凭据。例如 [OpenCode Go 的接入要求](https://opencode.ai/docs/go/#where-can-i-use-it)包含自己的 User-Agent 和稳定 Session ID；脚本使用 `agent-engineering-book/0.1` 标识自己，在这个端点运行时使用：

```bash
python -B exercises/lesson-09-evaluation/run_trial.py --live --session-header x-opencode-session
```

命令会创建一个新批次目录，默认只有一次 Trial。屏幕打印各自的绝对路径：

```text
本批目录/
|- trial_1/
|  |- initial.json           原始文件，只供人和评测程序查看
|  |- expected.json          本题标准答案，Agent 无权访问
|  |- workspace/config.json  Agent 实际读写的文件
|  |- session.jsonl          对话与执行账本
|  `- report.json            这一次的运行状态、最终回答和文件成绩
`- batch_report.json         本批总表，包含每次完整报告
```

这次任务只开放 `config.json` 的 `read_file` 和 `write_file`。执行侧还会检查工具名和路径，文件写入由这道题的固定批准规则放行。Agent 可以写出错误配置，评分器再判错；它拿不到报告或标准答案文件，也没有 Shell 入口。这是固定能力的教学实验，不是通用 Shell Sandbox。

目录会保留，方便你打开修改前后的文件对照；系统临时目录可能被系统清理，不应当作永久归档。得到本次 `config.json` 的路径后，也可以用已有的 `starter.py --config <实际路径>` 只重新阅卷，不再次请求 Model。默认使用基础题的答案；其他题补评时要同时传入本次保存的 `--expected <expected.json 路径>`。

`report.json` 中两个状态要分别看：`agent_run` 说明运行是否正常结束，`grade` 说明实际文件是否符合题目。假如文件已改好，但 Model 在生成最终回答前超时，可以同时出现运行 `error`、文件成绩 `passed`；这次完整运行仍不能被当作成功放行。命令退出码 `0` 要求二者都正常，`1` 表示运行结束但文件评分失败，`2` 表示运行或评分发生异常。

想离线检查连接是否正确，可以运行：

```bash
python -B exercises/lesson-09-evaluation/run_trial.py --self-check
```

这条自检使用提前写好的 Model 响应，但真的运行原来的循环、读写工具、Ledger 和评分代码。它还检查了“只说成功却没改文件”会判失败、每次运行从初始文件开始，以及不在范围内的工具申请被拒绝。末尾的 `run_trial self-check passed (scripted Model)` 只证明连接正确。

这一步的接线由 AI 提供，你先运行并打开 `initial.json`、`workspace/config.json` 和 `report.json`，亲眼确认“任务、行动、成绩”对应起来。不同任务、重复 Trial 和旧新版对比，等这一次运行看明白后再接。

## 第四步 D：同一道题，独立做三次

一次通过以后，给原命令加上 `--trials 3`。模型、题目和评分规则保持不变，每次重新创建初始配置和会话：

```bash
python -B exercises/lesson-09-evaluation/run_trial.py --live --trials 3 --session-header x-opencode-session
```

普通 Provider 不需要 `--session-header` 时省略它。默认仍只运行一次，最多允许 10 次；每一次仍最多请求 Model 4 次。三次 Trial 是同一道 Task 的三次独立尝试，不能拿前一次改好的文件直接给后一次用。

批次目录里会出现 `trial_1`、`trial_2`、`trial_3`，每个都有自己的初始文件、结果文件、会话和报告。需要会话请求头时，同一次 Trial 的各轮请求使用同一个 ID，不同 Trial 会更换 ID。

连接关系现在是：

```text
run_trial.py 中的 run_batch
  -> run_trial：准备、运行 Agent、调用 starter.py 的阅卷器
  -> run_trial：换新环境，再做一次
  -> run_trial：换新环境，再做一次
  -> starter.py 的 summarize_results：汇总已经得到的文件成绩
  -> 保存 batch_report.json
```

总表同时保留两类统计。`grade_summary` 统计文件的 `passed / failed / error`；`successful_trials` 只统计“Agent 正常结束，而且文件通过”的次数，另用 `run_error_count` 记录运行异常。

假设三个文件都改对了，但其中一次在给出最终回答前超时：文件成绩是三个 `passed`，完整运行成功却只有 `2/3`。所以不能只看文件成绩就宣布整个 Agent 三次都成功。

本例的 `observed_success_rate` 用完整成功数除以本批全部 Trial 数；运行异常或评分异常都会保留在总数中，并单独报告，不归并成“Agent 产物错误”。有异常时先查清原因，不用这一个比例给模型能力下结论。

如果三次都成功，会看到 `完整运行成功: 3/3` 和 `本次观察成功率: 100.0%`。这只能说明这道固定题在本次三次运行中都成功，不能证明它对其他任务同样稳定。

运行或评分异常后仍继续后面的独立 Trial。创建目录、保存报告等评测设施本身失败则直接报错，避免报告假装齐全。命令退出码为 `0` 只表示本批所有完整运行均通过；它还没有加入业务发布门槛或旧新版比较。

你现在重点看 `run_batch()` 中的 `for` 循环和三个产物目录，暂时复用自检里的模拟代码。这一步接线由 AI 实现；亲手验证每份 `initial.json` 都是 `light`，再解释为什么不能只用 `grade_summary["passed"]` 当完整成功数。

## 第五步 E：换一道题，标准答案也要跟着换

如果 Agent 每次都写出 `{"theme":"dark","port":8080}`，基础题可以一直通过。但原文件端口是 `3000` 时，照抄这份答案就会把端口改错。现在增加两道同类题，仍然只要求修改主题：

| `--task` | 初始文件 | 除主题外要保留什么 |
| --- | --- | --- |
| `basic` | `{"theme":"light","port":8080}` | 端口 8080 |
| `custom-port` | `{"theme":"light","port":3000}` | 端口 3000 |
| `keep-debug` | `{"theme":"light","port":8080,"debug":false}` | 端口 8080、debug=false |

这三份初始配置在 `run_trial.py` 开头的 `TASK_CONFIGS` 中。用 `--task` 选题，用 `--trials` 决定这道题做几遍；省略 `--task` 时仍做 `basic`。

先试端口不同的题：

```bash
python -B exercises/lesson-09-evaluation/run_trial.py --live --task custom-port --trials 1 --session-header x-opencode-session
```

再把 `custom-port` 换成 `keep-debug`，就会运行需要保留额外字段的题。普通 Provider 不需要会话头时仍可省略 `--session-header`。

阅卷器的答案也必须改变。现在调用 `grade_config(config_path, expected)`，由运行程序提前准备本题的 `expected`：

```python
initial = {"theme": "light", "port": 3000}
expected = initial.copy()
expected["theme"] = "dark"
```

`copy()` 复制一份配置，修改副本的主题后，原题里的主题仍是 `light`。本题预期结果便是 `{"theme":"dark","port":3000}`。标准答案在 Agent 开始前生成并保存到 `expected.json`；不能读 Agent 改完的文件，再用它反过来决定哪些字段“应该保留”。

`initial.json`、`expected.json` 和报告都在可写工作区外。Agent 仍然只能读写 `workspace/config.json`，所以它不会提前拿到答案，也不能改阅卷规则让自己通过。

补评新题时，给阅卷器原产物与这道题的标准答案：

```bash
python -B exercises/lesson-09-evaluation/starter.py --config /本次目录/workspace/config.json --expected /本次目录/expected.json
```

不带 `--expected` 的旧命令仍可补评基础题，但不适合新题。如果标准答案文件本身缺失或损坏，结果应是评分 `error`，不能归成 Agent 的产物 `failed`。

三道题各跑一次，就是 3 个 Task、3 个 Trial；每题再独立跑三次，则是 3 个 Task、9 个 Trial。三个题目仍是很小的配置编辑样本，只检查主题修改和字段保留，尚未覆盖复杂编码、安全对抗或其他 Agent 能力。

这一步的接线已完成。你先选 `custom-port` 运行一次，对照 `initial.json`、`expected.json` 和 `workspace/config.json`：它们分别是原题、标准答案、Agent 的答卷。

## 第六步 F：换一种任务，换一套阅卷规则

前三道配置题使用同一种判断方法：比较完整配置。这次换成计算任务：读取 `items.csv` 的 `quantity` 列，把商品总数量写进 `summary.json`，原始 CSV 保持不变。

```csv
item,quantity
apple,2
banana,3
pear,7
```

输入中的数量是 `2 + 3 + 7`，这份数据的正确总数为 `12`。本题约定输出是仅含整数 `total_quantity` 字段的 JSON 对象：

```json
{"total_quantity": 12}
```

这次阅卷器叫 `grade_csv_total()`。它先从可信的原始 CSV 计算总数，再检查两件事：Agent 提交的总数是否相同，工作区里的 `items.csv` 是否保持原样。

计算答案的核心代码是：

```python
total = 0
for row in rows:
    total += int(row["quantity"])
```

`rows` 由 Python 自带的 `csv.DictReader` 逐行读取，每一行都是字段名到值的字典。`int()` 把数量文字变成整数，再逐行相加。换成数量 `10`、`20` 的 CSV，阅卷器就会算出 `30`，代码没有把答案固定为 `12`。

同一个 `run_trial.py` 继续负责准备文件、调用现有 Agent、记录过程与汇总成绩；只在准备任务和评分时根据题型选择分支：

```python
if task_name == "csv-total":
    grade = safe_grade_csv_total(workspace, initial_file)
else:
    grade = safe_grade_config(output_path, expected)
```

这一步没有复制 Agent Loop。变化的是任务要求、输入输出文件、可读写范围，以及对应的评分规则。报告里的 `grader` 会说明本次用了 `grade_config` 还是 `grade_csv_total`。

运行真实模型：

```bash
python -B exercises/lesson-09-evaluation/run_trial.py --live --task csv-total --trials 1 --session-header x-opencode-session
```

不需要会话请求头的 Provider 可以省略最后一个参数。每个 Trial 的文件为：

```text
trial_1/
|- initial.csv             可信的原始输入，位于 Agent 可读写范围外
|- expected.json           从原始输入算出的结果，供人核对
|- workspace/
|  |- items.csv            给 Agent 读取，禁止通过 Tool 修改
|  `- summary.json         Agent 创建的答卷
|- session.jsonl           消息与执行账本
`- report.json             本次成绩和原始数据路径
```

CSV 题允许读取 `items.csv`、`summary.json`，只允许写入 `summary.json`。阅卷器还会独立检查输入未被改变；因此即使工作区输入被篡改，也不能用篡改后的数量给答卷“对答案”。这是本题的工具范围，不是通用操作系统 Sandbox。

结果文件缺失、总数算错、字段类型不对或输入被修改，记为任务 `failed`。工作区外的原始数据丢失或损坏时，评测缺少可靠依据，记为评分 `error`。

只补评 CSV 答卷时，使用它的阅卷入口：

```bash
python -B exercises/lesson-09-evaluation/starter.py --csv-workspace /本次目录/workspace --original-csv /本次目录/initial.csv
```

这条命令不用 Model，会重新从 `initial.csv` 算出预期总数，并检查现有答卷。CSV 阅卷器自检用 `starter.py --check-csv`；`run_trial.py --self-check` 还会检查完整接线、输入写入被拒绝，以及换一份 CSV 后答案随之变化。

配置修改和 CSV 汇总现在共享运行流程，却用不同方法判断任务是否完成。以后修 Bug 可以检查受保护的测试，文章总结可以用人工或经过校准的模型评分。新增题型仍要明确成功条件，不能凭一个通用 JSON 比较函数就替所有任务判分。

这一步的接线和测试由 AI 提供。你先看 `grade_csv_total()` 中“原始数量怎么算出答案、实际提交怎样比较”的几行，再运行一次真实 CSV 题，打开原始输入与 `summary.json` 对照。

## 第七步 G：两版做同一道题，再比较已经保存的成绩

现在有了真实答卷和阅卷规则，但还没有证据说明某次修改让 Agent 变好。先做一个明确的 Prompt 实验：

| `--variant` | 实际变化 |
| --- | --- |
| `baseline` | 沿用当前“先读取输入，再完成任务，按实际结果回答”的提示词 |
| `verify-output` | 增加“写入后再次读取输出文件，核对原始任务的每条要求，确认结果后再回答” |

两种提示词都在 `run_trial.py` 的 `AGENT_VARIANTS` 中，`--variant` 真正选择发送给模型的内容。基础版也可能自行读回检查，所以不能预先认定候选版更好。

用同一个模型、同一道 CSV 题，各做三次：

```bash
python -B exercises/lesson-09-evaluation/run_trial.py --live --task csv-total --trials 3 --variant baseline --session-header x-opencode-session
python -B exercises/lesson-09-evaluation/run_trial.py --live --task csv-total --trials 3 --variant verify-output --session-header x-opencode-session
```

每次仍有独立文件和会话。两条命令分别打印自己的 `batch_report.json` 路径。执行期间不要修改题目、阅卷器或运行代码，否则会混入其他变化。

再把两个报告路径交给 [`compare_runs.py`](compare_runs.py)：

```bash
python -B exercises/lesson-09-evaluation/compare_runs.py --baseline /基础版目录/batch_report.json --candidate /候选版目录/batch_report.json
```

这条命令只读旧报告：不调用 Model，不再让 Agent 做题，也不重新阅卷。三个文件的分工因此是：`run_trial.py` 组织做题，`starter.py` 阅卷和计数，`compare_runs.py` 核对比较条件并对比成绩。

报告新增 `comparison_context`，在运行前记下真实 Prompt、模型、服务端地址的指纹、请求预算、Python/SDK 环境，以及题目、阅卷器、运行代码的指纹。指纹是根据内容计算的一串值，可以发现“名字相同，内容却变了”；它不是签名或防篡改保证，代码文件的注释变化也会改变源码指纹。

比较器会检查同一道题的原始输入、任务要求和标准答案是否一致，阅卷器与模型等已记录条件是否相同。本练习还要求两边 Trial 数相同。字段一致只是比较的前提，不能消除模型随机性、服务端变化和网络波动。

如果只有版本标签不同，实际代码和 Prompt 完全相同，就提示这不是两个不同版本。如果仍有评分 `error`，或报告缺少运行条件、混入不同配置、总表与逐次记录不一致，返回 `blocked` 并给出原因。之前没有记录这些条件的旧报告，不要事后随便补一个版本名字来比较。

通过条件检查后，返回 `comparable`，分别展示两版的成功数、运行异常数、平均耗时和平均 Tool Call 数，再给出“候选版减基础版”的差值：

- 成功率差值以百分点表示，例如 70% 到 82% 是增加 12 个百分点。
- Tool Call 数包含被执行入口处理的拒绝申请；次数增加不等于费用同比增加。
- 平均耗时取全部已记录 Trial，包括中途异常，不能只挑成功的几次。

运行 `error` 与评分 `error` 分开处理：前者是本批执行的实际观察，保留在分母和明细中；后者表示成绩尚未评完，阻止直接比较。出现运行异常时，要继续查看每次报告的异常类型，不能只凭总比例把服务故障归因给 Prompt。

如果两版都是 `3/3`，只能说本次观察成功率相同。再看耗时、调用次数是否变化，不能因为名称叫“候选版”就宣布它更好。默认比较命令退出码 `0` 只表示可以对照数据，不表示允许发布；下一步通过 `--gate` 执行门禁。

一次实际对比中，同一 `mimo-v2.5` 模型、同一道 CSV 题、每轮最多 4 次模型请求，两版各运行 3 次：基础版完整成功 `3/3`，候选版完整成功 `0/3`。其中候选版前两次文件都已写对，却又读取输出、读取原始输入，第四次模型响应仍在申请 Tool；预算已经用完，没有第五次请求生成 Final。第三次则是 `APIConnectionError`，不能把这次连接故障也归因给 Prompt。

候选版的平均耗时反而更短，因为几次运行提前结束了。这说明必须保留逐次原因，不能只看“更快”“文件 passed”或汇总的一个比例。发现这种结果后，先保留原始成绩和预算，定位多余读取；不能为了让候选版通过，事后把同一轮考试的预算改大。

`python -B exercises/lesson-09-evaluation/compare_runs.py --self-check` 使用模拟报告验证比较规则。你现在先看两版的真实 Prompt 和最后几项差值，报告校验与指纹计算由 AI 提供，不要求手写一遍。

## 第八步 H：固定回归题的最小门禁

`compare_runs.py` 新增 `release_gate()`，先复用比较条件检查，再要求候选的每一次 Trial 都正常结束且产物通过。有评分错误、运行异常或未通过的固定题，返回 `blocked`，命令退出码为 `2`；全部满足才返回 `passed` 和退出码 `0`。

这次没有修改候选提示词，也没有放宽四次模型请求的预算。`run_trial.py --self-check` 加入了与实测对应的四次工具请求，验证文件虽正确，但没有 Final 的运行仍被记为 `error`，并且不会偷偷发起第五次请求。

真实的基础版与候选版成绩已分别保存为 [baseline.json](evidence/baseline.json) 和 [candidate.json](evidence/candidate.json)，去掉了本机文件路径。运行以下命令只读取这些已保存的证据：

```bash
python -B exercises/lesson-09-evaluation/compare_runs.py \
  --baseline exercises/lesson-09-evaluation/evidence/baseline.json \
  --candidate exercises/lesson-09-evaluation/evidence/candidate.json \
  --gate
```

预期是 `status: blocked`，原因包括“候选有 3 次运行异常”和“固定回归题实际完整通过 0/3”。退出码 `2` 正是门禁生效；去掉 `--gate` 时则是 `comparable` 和退出码 `0`，表示数据可以比较。

这些旧成绩用来验收新写的门禁，不能说原实验已经按此门禁预先设计。以后新实验应先冻结发布标准。这个命令验收报告对应的候选版本和所选 Task，不会部署，也不证明当前工作树、其他任务或生产安全边界已经合格。

这些分步实现供查阅。综合实践的完成标准是本文开头的小题表与版本判断。

</details>
