# 第 10 课：Agent Orchestration——Workflow、Routing 与长任务

上一课已经能发现“主题改对、端口改错”，并拦住不合格结果。现在让程序把失败原因交回助手，给它一次修复机会。

不能只加一句“改完记得检查”。如果是否检查、是否继续都由模型决定，它就同时兼任了施工队和验收员。程序要固定验收步骤，还要在预算用完时停下来。

安排步骤、选择处理者、收集结果和控制停止，这些工作合起来叫 **Orchestration（编排）**。先用一个 Agent 跑通修改与验收，再看什么时候需要交接和并行。

## 1. Workflow：修改、验收与反馈

继续第 9 课的任务：把 `config.json` 的主题改成 dark，其他字段不变。假设前后出现这三份配置：

```text
原始配置：{"theme":"light","port":3000}
第一轮后：{"theme":"dark","port":8080}
第二轮后：{"theme":"dark","port":3000}
```

第一轮不通过，原因是端口被改了。程序把这个原因交回助手，第二轮修复端口，才满足要求。路线由代码固定：

```text
Agent 修改文件
  -> 保存本轮产物并验收
  -> 通过且运行正常结束：完成
  -> 未通过且还有预算：反馈原因，继续修复
  -> 运行异常、评分异常或预算用完：停止并报告
```

固定步骤、条件和出口，就是这里的 **Workflow（工作流）**。模型判断怎样修，程序保证改后必查。即使模型没有调用工具、只说“已经完成”，也要接受同一套验收。

取得运行状态和评分以后，可以这样决定下一步：

```python
agent_run = "completed"
grade = "failed"
remaining_attempts = 2

if agent_run != "completed":
    next_step = "inspect_run"
elif grade == "error":
    next_step = "inspect_grader"
elif grade == "passed":
    next_step = "completed"
elif remaining_attempts > 0:
    next_step = "needs_repair"
else:
    next_step = "stop"

print(next_step)
```

输出为 `needs_repair`，表示可以进入修复。这里假定评分器只返回 passed、failed、error；片段只检查运行、评分与剩余轮次，总请求预算下一节再补上。

配套流程使用预设模型回复：第一轮写错端口，收到程序反馈后，第二轮读取当前文件并改回 3000。文件工具、Ledger 和评分器真实执行，两轮产物分别留存。这证明接线与分支成立，不证明真实模型一定能修好。

与上一课每次重置的独立 Trial 不同，**本例在同一任务里沿用当前工作区和会话**。第二轮能读到当前端口 8080，也能看到程序给出的失败原因。另存每轮快照，后续修复不会抹掉先前的错误证据。

评分规则仍受保护。模型可以指出测试与需求冲突并提交证据，但不能自行删除断言，再宣布通过。运行异常也不能直接当作“修得不对，再来一轮”：文件可能已经改好，缺的只是最后一条回执或回答。

## 2. Budget：统一额度与停止

工作流至少要区分两种额度：允许修改几轮，以及整个任务允许请求模型几次。一轮修改可能包含读取、写入和最终回答，不等于一次模型请求。

配套流程默认最多修改三轮，共用九次模型请求额度；每轮仍保留原 Agent Loop 的四次请求上限。用固定剧本可以观察：

| 条件 | 文件结果 | 工作流结果 |
| --- | --- | --- |
| 第二轮修好，六次请求完成 | passed | completed |
| 三轮都改错 | failed | attempt_limit |
| 总预算只有五次 | 第二轮已 passed，但没有最终回答 | model_budget_exhausted |

最后一种情况下，第二轮读取和写入用掉第四、第五次请求，没有第六次请求来生成回答。程序应保存文件成绩，同时保留运行未完成的事实。

预算属于主任务，换处理者也不能充值。下面只模拟共享计数，没有调用模型；reader、editor 表示不同处理者，交接细节留到下一节：

```python
state = {"remaining_calls": 2}

for agent in ["reader", "editor", "reader"]:
    state["active_agent"] = agent
    if state["remaining_calls"] == 0:
        print("停止：预算用完")
        break
    state["remaining_calls"] -= 1
    print(agent, "获准请求，剩余", state["remaining_calls"])
```

输出为：

```text
reader 获准请求，剩余 1
editor 获准请求，剩余 0
停止：预算用完
```

若预算按请求尝试计数，失败请求也消耗一次；SDK 自动重试是否计算在内，要事先约定。实际工作流在发请求前扣减并保存剩余额度，保存失败就不发请求。重启后应沿用余额，不能恢复初始额度。

扣减与请求发出之间仍有故障窗口；单进程计数不保证并发原子扣减，写了 Checkpoint 也不等于已经实现自动续跑。

已有一次真实运行验证了另一条停止路径：模型读写完成，文件评分 passed，最后的模型回答却出现 `APITimeoutError`。程序保存成功写入的 Ledger，整体停为 run_error，没有自动开始下一轮。这是一次历史观察，不是成功率评测，也没有验证模型收到错误反馈后会修复。[6]

## 3. Routing 与 Handoff：分支和处理权

用户只要求“解释配置”，读取分支就够了；要求修改且获得授权，才进入编辑分支。按请求选择处理分支、工具或模型，叫 **Routing（路由）**。明确规则可以直接用代码判断，需要理解自然语言时可以让模型提出选择。

路由不发放权限。即使模型选了编辑分支，执行器仍要检查这次操作是否被允许。隐藏 write_file 却开放任意 Shell，也不能让读取分支变成只读，边界仍按第 7 课落实。

任务需要专门处理者时，还要分清交出去的是什么：

| 安排 | 后续由谁推进 |
| --- | --- |
| 主 Agent 请子 Agent 分析错误，拿回建议 | 主 Agent 继续组织任务，这是委派 |
| 接待 Agent 把后续配置修改交给编辑 Agent | 接手者继续处理，这是 Handoff（交接） |

交接不等于销毁原 Agent，也不意味着任务完成；以后可以交回。实现上也未必有两个进程：LangChain 的交接示例既可以在不同 Agent 之间转交，也可以由一个 Agent 根据状态切换指令和工具。[1]

程序需要同时安排处理者与资料。例如，交给编辑者：“把主题改为 dark，保留端口；当前文件误改了端口”。只改一个 `active_agent` 字段，却没把要求和当前情况放入输入，接手者仍不知道要做什么。

长历史可以整理成交接摘要，短历史可以直接传相关消息。**交接决定谁接着做，压缩决定历史怎样缩短**，两者可以配合，但不互相依赖。若用工具调用表达交接，仍要保留完整的 Tool Call／Result 配对。[1]

资料里写着“之前已经批准”不能直接当授权。程序要核验可信审批记录是否仍覆盖当前对象、参数和处理者。有效授权可以沿用，不必换一个 Agent 就重新问；范围改变或授权失效，则重新审批。

当前配置任务用一个 Agent 加固定验收已经够用。职责、上下文或独立工作量确实需要拆分时，再引入协作者。

## 4. 并行与 Checkpoint：收集结果再验收

分析错误、修改代码、验证修改通常有依赖。分给三个 Agent，也不能让验收者提前拿到尚未完成的修改。测试旧版可以与分析并行，验收新版则必须针对完成后的那份代码。

独立模块的检查更适合并行。独立 worktree 能分开代码修改，却不隔离数据库、端口或外部服务；共享环境也要安排。每份测试报告应记下对应版本。

各自通过不等于合并后通过。一个任务修改接口字段，另一个新增按旧字段读取的功能，可能没有文本冲突，却在组合后出错。主任务收齐结果后，仍要验收合并版本。

为了恢复收集进度，主任务至少应记住：

```text
子任务 A：已完成，结果位置……
子任务 B：已完成，结果位置……
子任务 C：最后记录为运行中，下游编号 job_C
下一步：收齐结果，合并并验收
```

子任务的 Checkpoint 保存自己的进度，主任务的 Checkpoint 保存分工、收集进度和结果位置。它们可以存在同一个数据库，不必每个 Agent 各建一套存储。

主任务重启后，A、B 的结果直接复用；C 按原编号查询，不能重新提交一份。下面只处理成功、运行中和未知三种状态：

```python
def choose_next_step(statuses):
    if not statuses:
        raise ValueError("子任务列表不能为空")
    for status in statuses:
        if status not in {"succeeded", "running", "unknown"}:
            raise ValueError("这个短例不处理该状态")
    if "unknown" in statuses:
        return "reconcile"
    if "running" in statuses:
        return "wait"
    return "merge_and_validate"

print(choose_next_step(["running", "unknown"]))
print(choose_next_step(["succeeded", "succeeded"]))
```

输出依次为 `reconcile`、`merge_and_validate`：存在未知结果就先核对，成功结果收齐后才进入合并验收。明确失败的任务要有相应分支，不能悄悄归入“全部成功”。

配套恢复实验由一个进程保存状态，再由另一个进程读取；下游结果来自预设记录。它验证了复用、等待和核对决定，没有启动真实子 Agent、并行调度或执行合并。

## 5. 长任务：查询、取消与补偿

如果验收要等待远端构建，服务可能先返回 `job_id`，稍后才有结果。程序应保存本地任务与远端编号的对应关系、当前阶段和下次查询安排。当前请求可以结束，整个任务仍在等待。

查询间隔与等待上限由程序安排，不需要模型反复说“再等等”。一次查询超时只说明没拿到本次查询结果，不能认定构建失败，更不能因此重提交。

| 动作 | 实际改变什么 |
| --- | --- |
| 停止等待 | 本地不再等，远端未必停止 |
| 请求取消 | 请求远端停止，仍需确认是否真正取消 |
| 事后补偿 | 原操作已经完成，再执行一项获授权的补救动作 |

取消请求发出后，远端可能报告构建已成功。应保留成功事实与取消请求记录，不能为了配合用户指令，把状态改写成“已取消”。如果已经部署，回退是另一项操作，需要自己的权限与执行结果。

持久化让程序知道从哪里继续，不保证副作用不会重复。对成功操作复用回执，对未知操作按第 6 课核对。LangGraph 的持久执行机制也需要结合操作边界设计，不能只配一个 Checkpointer 就假定外部动作恰好执行一次。[2]

当前配套代码没有实现远端取消或通用后台续跑。写下一个任务编号，是继续查询的依据，不是远端任务已经完成的证明。

## 6. 框架定位：LangChain 与 LangGraph

前面的 Python 流程已有两层：内部 Agent Loop 组织模型与工具交互，外部 Workflow 决定验收、返工和停止。第 2 课的框架关系图，在这里可以对应到具体代码职责。

**LangChain 提供常见 Agent 循环的现成入口。** 把模型、工具和指令交给它，可以少写工具调用与结果回传的组织代码；在本例中，它能承担“让 Agent 修改配置”这一步。文件怎样读写、哪些路径允许访问，仍由应用定义。[4]

**LangGraph 用节点、连接与状态组织运行。** 修改是一个节点，验收是另一个节点，评分结果决定回去修复还是结束。节点可以调用现有 Agent，也可以只是普通 Python 函数。[5]

| 任务职责 | 当前 Python 实现 | 用 LangGraph 表达时 |
| --- | --- | --- |
| 修改配置 | 调用已有 Agent Loop | 修改节点调用同一个 Loop，或 LangChain Agent |
| 验收产物 | 调用配置评分器 | 验收节点调用同一个评分器 |
| 继续或停止 | 条件判断与循环 | 按运行、评分和预算状态选择连接 |
| 保存进度 | 保存阶段、轮次与余额 | 存入图状态，按恢复要求配置 Checkpointer |

LangChain 的 Agent 建立在 LangGraph 之上。直接使用 LangGraph 也可以组织模型与工具循环，不要求先使用 LangChain。区别在于采用现成的 Agent 组织方式，还是直接控制步骤；不是“单 Agent 对多 Agent”。[4][5]

框架不会自己知道“端口必须保持 3000”，也不会替应用决定可以修几轮。这些规则仍在评分器、分支和执行边界里。

我会先保留当前已经能表达清楚的短流程。以后确有迁移需要，再用相同输入、验收条件和停止规则比较两种实现。理解框架的价值，不要求立刻替换代码。

当前配置工作流已接通，交接与恢复则仍是独立机制实验。能解释一次任务为什么继续、等待或停止，比先给它安排几个 Agent 更重要。

## 资料与配套实践

1. [LangChain：Handoffs 与上下文传递](https://docs.langchain.com/oss/python/langchain/multi-agent/handoffs)
2. [LangGraph：持久执行与 Checkpoint](https://docs.langchain.com/oss/python/langgraph/durable-execution)
3. [第 10 课配套实践](../../exercises/lesson-10-orchestration/README.md)
4. [LangChain：Agent 框架与模型接口](https://docs.langchain.com/oss/python/langchain/overview)
5. [LangGraph：编排运行时与 LangChain 的关系](https://docs.langchain.com/oss/python/langgraph/overview)
6. [已有真实运行的条件、结果与边界](../../research/10-workflow-live-check.md)
7. [候选代码检查](check_lesson_10.py)：`python -B experiments/reading-pilot/check_lesson_10.py`，执行正文片段与离线自检，不调用真实模型、不启动远端任务。
