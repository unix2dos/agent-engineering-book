# Agent 工程学习路线

学完第 8 课以后，面前会同时出现 RAG、Multi-Agent、MCP、Browser、Voice 和各种 Agent SDK。它们都值得学，但不能一起成为“下一课”。这张路线只回答一个问题：为了独立设计、实现和排查 Agent，下一项能力应该建立在哪项能力上？

框架会换名字，能力之间的依赖更稳定。因此主干按“能做什么”组织，只详细规划最近三课。

```text
前置：能读 Python、Git 和命令行
  |
  v
阶段一：判断与行动                         已完成，第 0～3 课
  |
  v
阶段二：状态、可靠性与控制                 已完成，第 4～8 课
  |
  v
阶段三：看见与改进                         下一步，第 9～11 课
  |
  +------> 可选能力分支
  |          Retrieval / RAG / Memory
  |          MCP / A2A / 远程 Tool
  |          Browser / Computer Use / Voice / 多模态
  |
  v
阶段四：编排与长任务
  |
  v
阶段五：部署与持续运营
```

可选分支不是跳级入口。无论 Agent 最后要搜索知识、操作浏览器还是与别的 Agent 通信，它都需要先留下可定位的运行记录，也需要能重复验证修改是否变好。

## 阶段一：判断与行动

第 0～3 课已经完成这一阶段。你先判断一个任务是否真的需要 Agent，再亲手跑通下面的循环：

```text
Model 提出 Tool Call
-> Harness 校验并执行 Tool
-> Tool Result 回到 Model
-> Model 给出 Final
```

这一阶段的完成标准不是“调用过某个 SDK”，而是能解释 Model、Harness、Tool 和 Environment 各自负责什么，并能识别错误参数、矛盾停止原因和无限循环。

## 阶段二：状态、可靠性与控制

第 4～8 课把一次成功演示变成可以恢复、可以限制的小型 Runtime：

- Session、Transcript、Checkpoint 和 Memory 不再混成一个 `history`；
- Prompt View 可以压缩，完整事实仍留在持久记录；
- JSONL 与 SQLite 根据访问方式选择，而不是根据文件大小贴标签；
- Ledger 记录真实执行尝试，`unknown` 副作用先对账再决定；
- Tool Policy、Approval 和 Backend 先做应用决策，Permission 与 Sandbox 由系统执行。

如果程序重启、Tool Result 丢失或命令被系统拒绝，你已经能判断应该查哪一层。这就是进入下一阶段的前提。

[阶段一～二综合实践](../exercises/phase-1-capstone/README.md)把最小 Loop、Workspace Tool、Transcript、Compaction、Ledger 和故障恢复接成一个系统；第 8 课的安全边界练习再补上 Policy、Approval、Permission 与 Sandbox。

## 阶段三：看见与改进

当前 Agent 能运行，却还不会系统回答两个问题：它为什么失败？修改以后真的更好吗？第 9～11 课只解决这两个缺口。

### 第 9 课：Trace——一次运行到底发生了什么？

先在现有综合实践外面加一层运行记录。一次任务共享 `trace_id`，每次 Model 请求、Tool 执行、Approval 和恢复尝试各有自己的 `span_id`，同时记录父子关系、开始和结束时间、状态、Token、成本与错误。

最小证据不是一个漂亮 Dashboard，而是一份失败 Trace：你能指出错误来自 Model、Tool、Policy、Backend 还是恢复代码。Prompt、Tool 参数和结果可能包含隐私，本课还要决定哪些内容可以写入遥测。

### 第 10 课：Evaluation——Agent 到底有没有变好？

看到一次 Trace 以后，再把真实失败整理成一小组样本。每个样本包含输入、必须满足的规则、允许变化的质量部分和评分方法。

JSON 是否有效、Tool 是否选对、危险动作是否被拒绝，优先用普通代码判断。只有“回答是否有帮助”这类不能精确计算的质量，才交给人工或 LLM Judge。完成时，同一个 Agent 修改前后要运行同一批样本，而不是凭一段顺利对话判断效果。

### 第 11 课：回归门禁——怎样阻止旧问题再次出现？

最后把确定性的底线接进测试和 CI。故意破坏 Tool Result 配对或安全拒绝规则时，测试必须失败；只改一句正常措辞时，不应因为字符串不同而误报。

线上和人工 Review 发现的新失败，在去掉敏感信息后补回 Dataset。这样一次事故不只得到解释，还会留下下一次发布前自动重跑的样本。

三课结束时，需要完成一个综合实践：制造一次 Agent 失败，用 Trace 定位原因，把它加入 Eval Dataset，修复后让回归门禁由失败变为通过。

## 阶段四：编排与长任务

完成最小评估闭环以后，才决定是否增加 Workflow、Routing、并行、Retry、Interrupt/Resume、Handoff、Subagent 或 Multi-Agent。

Multi-Agent 不是单 Agent 的高级版本。它会增加路由、并发、共享状态和责任边界。只有 Eval 已经证明单 Agent 在具体样本上受限，而且限制确实来自职责过多、需要并行或任务持续时间太长，拆分才有依据。

这一阶段现在只保留能力范围，不创建空章节。第 11 课完成后，再根据综合实践暴露的瓶颈安排具体课程。

## 可选能力分支

阶段三之后，可以按真实问题选择分支：

- 知识与数据：Retrieval、RAG、引用，以及长期 Memory 的写入、检索和遗忘；
- 连接与协作：MCP、A2A、远程 Tool 与跨 Agent 信任边界；
- 交互环境：Browser、Computer Use、Voice、Realtime 和多模态输入；
- 专用执行环境：Coding Agent、数据分析 Agent 与远程 Sandbox。

这些分支不进入固定主干。一个项目只有在回答了现有课程无法回答的问题时，才成为新的主题参考。

## 阶段五：部署与持续运营

本机成功运行不等于可以上线。部署会带来持久化服务、密钥与租户隔离、并发与队列、限流、延迟和成本、版本回滚、线上监控与事故处理。

这一阶段放在 Trace 和最小 Eval 之后。否则上线只能证明服务启动了，无法证明 Agent 行为没有退步。无论前面选择哪条能力分支，最终都要回到这里。

## 路线怎样维护

README 始终展示完整阶段，`SUMMARY.md` 只列已经存在的课程。这里只详细规划接下来三课；第 11 课完成后，再根据 Trace、Eval 和综合实践证据展开下一阶段。

旧章节也不定期返工。只有出现真实读者卡点、示例失败、主要源码变化，或后续章节暴露矛盾时，才重新打开。

## 一手资料

完整核验过程、固定源码版本和不同课程体系的分歧，见[学习路线一手资料综合](../research/learning-roadmap-primary-sources.md)。主要依据包括：

- [Anthropic：Building Effective Agents](https://www.anthropic.com/research/building-effective-agents)
- [OpenAI：Agent Evals](https://developers.openai.com/api/docs/guides/agent-evals)
- [OpenAI Agents SDK](https://github.com/openai/openai-agents-python/tree/89c02c828ee8510fe9a84ee6675608193aa13b02)
- [Google ADK](https://github.com/google/adk-python/tree/89777c146bd26c04bd45d9ed67b5d3e64a6957f1)
- [LangGraph](https://github.com/langchain-ai/langgraph/tree/81bf17b23123e4ef8b9d5f49fa09a0122fc2edd1)
- [Phoenix](https://github.com/Arize-ai/phoenix/tree/a71218c7349fb33d1e6d3612cf63cbc70e708c04)
- [Inspect AI](https://github.com/UKGovernmentBEIS/inspect_ai/tree/7aa7343e4a14fa7be07e5a09c7431df5e88c17ee)
