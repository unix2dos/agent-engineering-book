# 第 4 课：一段会话如何保存——Session、Transcript、Checkpoint 与长期记忆

你刚让 Agent 记住一条规则：

```text
你：记住，部署博客前必须运行 hexo g。
Agent：好的。

关闭程序，重新启动。

你：部署前要做什么？
```

Agent 回答“好的”，不代表下次真的记得。如果对话只放在内存里，程序一关，`messages` 就消失了。

最直接的补救是把数据写进磁盘。但很快又会遇到三个问题：这一段会话叫什么？要保存完整过程，还是只保存当前进度？这条规则换一个新会话后，还应不应该继续生效？

这一课只回答这些保存问题。下一课再处理“历史太多，本次应该给 Model 看哪些”。

> 模型不记事，程序递纸条。Session、Transcript、Checkpoint 和 Memory 描述纸条各自负责什么；JSON、JSONL 和 SQLite 只描述纸条放在哪里。

## 1. 哪些记录属于同一段会话？

用户从“帮我修改文章”一路聊到“运行测试并发布”，这些交互需要一个共同编号。这个编号通常叫 `session_id`，被它圈在一起的连续会话就是 **Session**。

Session 是一个逻辑容器，不等于某个文件。它可以对应一个 JSON 文件、一份 JSONL、SQLite 中的一组记录，也可以对应 Provider 返回的 Conversation ID。

```text
Session demo
|- 这段会话发生过的事件
|- 这段会话当前走到哪里
`- 创建时间、模型等会话信息
```

状态也可以交给提供模型 API 的服务方保存。例如应用使用 Response ID 或 Conversation ID 续接会话。保存位置变了，Session 的职责没有变：它仍然回答“哪些交互属于同一段连续会话”。[OpenAI Conversation state](https://developers.openai.com/api/docs/guides/conversation-state)

## 2. 只想让程序接着做，需要保存什么？

假设 Agent 已经完成两轮工作。程序重启后，不一定要从第一条消息重新计算；只要知道旧任务摘要和最近完成的轮次，就能继续。

第 4 课的代码把这份状态写进 `session-demo.json`：

```json
{
  "summary": "正在整理 Agent 教程，第 1～3 课已经完成",
  "turns": [
    [
      {"role": "user", "content": "继续整理第 4 课"},
      {"role": "assistant", "content": "好的"}
    ]
  ]
}
```

为什么这里使用 `.json`？因为整个文件只表示一份最新状态。程序先读出一个完整对象，在内存里修改 `summary` 和 `turns`，再用新对象整体替换旧文件：

```text
读取旧 Checkpoint
-> 在内存中修改
-> 把完整新 Checkpoint 写回 session-demo.json
```

它保存的是“程序现在走到哪里”。这种某一时刻的状态快照叫 **Checkpoint**。

这里的 `turns` 不是随便几条 Message。一个 Turn 从 User 提问开始，到 Assistant Final 结束，中间可以包含 Tool Call 和 Tool Result。代码只有看到 Assistant Final，才把整个 Turn 放进 `state["turns"]`，然后覆盖写回最新 Checkpoint。

如果响应因长度限制中断，或者程序在 Tool 执行途中崩溃，这个未完成 Turn 不会冒充已完成进度写入 Checkpoint。

## 3. 只保存最新状态，为什么还不够？

`session-demo.json` 每次保存都会覆盖旧状态。程序能够继续工作，却无法仅靠它回答：前面调用过哪些工具？某条结论为什么出现？一个文件到底在哪一步被修改？

要追查过程，就需要按顺序保留发生过的事件。这组有序记录叫 **Transcript**。

当然也能把所有事件放进一个 JSON 数组，但每增加一条，程序通常都要读取并重写整个数组。Transcript 更适合“旧记录不动，新记录加在末尾”的写法。第 5 课会因此换成 JSONL：一行保存一个完整 JSON 对象。

把 Session 想成一个银行账户：

```text
第 1 笔：存入 10 元
第 2 笔：花掉 3 元
第 3 笔：存入 5 元
```

这三笔流水就是 Transcript。它说明余额怎样一步步变成 12 元。

```text
Transcript：之前按顺序发生了什么？
Checkpoint：截至某个位置，现在是什么状态？
```

只有 Transcript，程序可以从第一条开始重放，再算出当前状态。历史越长，恢复越慢。加上 Checkpoint 后，程序可以先恢复最近状态，再处理 Checkpoint 后面的新事件。

反过来，只有“余额 12 元”无法还原前面的三笔流水。Checkpoint 帮程序快速继续，不负责保存完整过程。

## 4. Checkpoint 一定是单独的 JSON 文件吗？

不一定。一种实现把完整过程和最新状态分开保存：

```text
session-demo.jsonl             完整 Transcript
session-demo.checkpoint.json   最新 Checkpoint
```

另一种实现把 Checkpoint 当作一条记录，追加到 Transcript：

```text
session-demo.jsonl
|- line 1  Message Entry
|- line 2  Message Entry
|- line 3  Checkpoint Entry：记录 line 2 之后的状态
`- line 4  新的 Message Entry
```

恢复时，程序从后往前找到最后一个 Checkpoint，再处理它后面的 Entry。此时整个 JSONL 是 Transcript，其中一行承担 Checkpoint 的职责，两者并不冲突。

同样，一份 SQLite 可以同时保存 Session、Transcript Entry、Checkpoint 和 Memory。文件格式不会替应用决定每条数据的意义。

## 5. 部署规则应该跟着当前 Session 一起结束吗？

“正在重写第 4 课”只是当前任务进度，换一个 Session 后通常不用保留。“部署博客前必须运行 `hexo g`”却是项目规则，新会话仍要遵守。

这就需要把当前会话状态和长期事实分开：

```text
Summary         当前 Session 的旧任务进度
项目 Memory    同一项目的新 Session 仍要遵守的规则
用户 Memory    换项目后仍成立的用户偏好
Transcript     当前 Session 按顺序发生过的事件
```

项目 Memory 可以保存 `hexo g` 规则。用户 Memory 可以保存“默认使用中文回答”。不同 Session 不共享当前 Summary，却可以读取同一份项目 Memory 和用户 Memory。

Memory 也不能把整份 Transcript 全抄进去。临时日志、失败尝试、未经确认的猜测和凭据，不应自动变成长期事实。只有稳定、以后仍有用，而且来源可信的内容，才值得留下。

项目规则和用户偏好发生冲突时，Harness 必须使用一套固定顺序。例如：

```text
当前用户明确要求 > 项目规则 > 用户默认偏好
```

这不是唯一方案，但结果必须能预测，不能把互相冲突的要求原样交给 Model 猜。

## 6. 已经写进磁盘，Model 为什么仍可能不知道？

Model 不会自己打开这些文件。Harness 必须先读取、筛选和排序，再把需要的内容放进本次请求：

```text
磁盘中的 Session / Memory
-> Harness 读取并选择
-> 本次请求的 messages
-> Model
```

程序重启后数据仍在，叫持久化。本次真正交给 Model 的内容，叫 Context。磁盘里即使有一百条记录，Harness 本次只递两条，Model 就只能使用这两条。

这一课先把数据保存正确。怎样在有限窗口里选择 Summary、最近原文和当前 Turn，是第 5 课的主线。

## 7. 第 4 课的代码到底保存了什么？

配套代码使用三份文件：

```text
项目目录/.agent_state/
|- session-demo.json       当前 Session 的最新 Checkpoint
`- project-memory.json     项目长期 Memory

用户状态目录/
`- user-memory.json        用户长期 Memory
```

`session-demo.json` 保存 `summary` 和完成的 `turns`。程序先在内存列表里增加完整 Turn，再覆盖写回这份最新状态。它是 Checkpoint，不是追加式 Transcript。

这一版还会根据预算选择最近 Turn，并把旧进度压成 Summary，为下一课做准备。但它没有逐条保存所有旧 Message、审批和工具执行状态，所以不能充当完整 Transcript 或完整工作流记录。

第 5 课会补上缺失的那一半：

```text
第 4 课：session-demo.json
          保存当前状态，方便继续

第 5 课：session-demo.jsonl
          保存完整事件，再组装有限 Prompt View
```

第 5 课写入的 `type="compaction"` Entry 会保存旧历史摘要和保留原文。它是 Transcript 中的一条压缩恢复点，也就是一种 Checkpoint。

## 8. Checkpoint 为什么不能证明 Tool 是否执行过？

教学代码只在 Assistant Final 出现后保存完整 Turn。假设文件已经写入，但程序还没来得及保存 Tool Result 就崩溃：

```text
外部文件：可能已经改变
Checkpoint：仍停在上一个完整 Turn
```

重启后看到旧 Checkpoint，只能说明“程序最后保存到哪里”。它不能证明写文件、发邮件或付款到底执行了几次。

这类动作需要单独的执行收据，记录何时获准、何时开始、最后确认成功还是状态不明。后面的可靠性课程会把这份收据叫作 Execution Ledger，并讨论怎样避免重复执行。

## 9. 自己验证一次

完整教学代码：[`lesson_04_session_memory.py`](../examples/lesson_04_session_memory.py)。

```bash
git clone https://github.com/unix2dos/agent-engineering-book.git
cd agent-engineering-book
python -B examples/lesson_04_session_memory.py --self-check
```

预期输出：

```text
self-check passed
```

然后做两组重启实验：

1. 继续使用同一个 `SESSION_ID`。Agent 应恢复旧任务进度。
2. 换一个新 `SESSION_ID`，但仍读取同一份项目 Memory。Agent 应忘记旧任务进度，却记得部署规则。

不要用“同一会话继续成功”证明长期 Memory，也不要用“记得部署规则”证明 Checkpoint 已恢复。两类数据可以放在同一块磁盘，却回答不同的问题。

`summary`、`turns` 和 Context 组装值得自己写一次。JSON 序列化、文件路径和 SDK 初始化可以让 AI 帮忙。数据库和 Provider 托管 Conversation 暂时只需看懂职责，不需要重复实现。

下一课继续运行[阶段一～二综合实践第三关](../exercises/phase-1-capstone/README.md#第三关transcript-与-prompt-view)，亲手实现 JSONL Transcript、Prompt View、重启恢复和 Compaction。

## 主动回忆

1. Session 为什么不是某一种文件？
2. Transcript 与 Checkpoint 分别回答什么问题？
3. 只有 Transcript 和只有 Checkpoint，各自缺少什么？
4. Checkpoint 为什么既能单独保存，也能成为 Transcript 的一条 Entry？
5. Summary、项目 Memory 和用户 Memory 的作用范围有什么不同？
6. 文件已经持久化，为什么 Model 仍可能不知道里面的内容？
7. 第 4 课为什么使用 JSON？`session-demo.json` 为什么不是 Transcript？
8. Checkpoint 没有当前 Turn，为什么不能断定 Tool 没执行？

<details>
<summary>检查简答</summary>

1. Session 是把连续交互归到一起的逻辑容器，可以使用 JSON、JSONL、SQLite 或 Provider ID 保存。
2. Transcript 回答“按顺序发生过什么”；Checkpoint 回答“截至某个位置，程序是什么状态”。
3. 只有 Transcript 可能需要从头重放；只有 Checkpoint 无法还原完整过程。
4. Checkpoint 描述数据的职责，不规定文件格式。它既可以放在单独文件中，也可以作为一条记录追加到 Transcript。
5. Summary 服务当前 Session；项目 Memory 跨同一项目的 Session；用户 Memory 跨项目保存用户偏好。
6. Harness 必须主动读取并把内容放进本次 Context，Model 不会自己访问磁盘。
7. 它只保存一份最新状态，所以适合整体替换 JSON；它没有按顺序保留所有事件，因此不是 Transcript。
8. Tool 可能已经产生副作用，只是新状态还没来得及写盘。

</details>

## 参考资料

> 资料最后核验于 2026-09-03；会变化的源码锚点收录在下面的复核记录中。

- [本批章节一手资料复核](../research/01-05-chapter-promotion-sources.md)
- [OpenAI Conversation state](https://developers.openai.com/api/docs/guides/conversation-state)
- [完整教学代码](https://github.com/unix2dos/agent-engineering-book/blob/main/examples/lesson_04_session_memory.py)
- [阶段一～二综合实践](https://github.com/unix2dos/agent-engineering-book/tree/main/exercises/phase-1-capstone)
