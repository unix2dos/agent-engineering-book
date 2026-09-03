# 第 4 课：Session、Checkpoint 与长期记忆

你刚让 Agent 记住一条规则：

```text
你：记住，部署博客前必须运行 hexo g。
Agent：好的。

关闭程序，重新启动。

你：部署前要做什么？
```

它回答“好的”，不代表下次真的记得。如果对话只放在内存里，程序关闭后，`messages` 就消失了。

把这句话写进 JSON，也只解决了一半。文件还在，但 Model 不会自己打开它。Harness 必须先读取文件，挑出有用内容，再随本次请求交给 Model。

> 模型不记事，程序递纸条。内存、JSON、SQLite 只是纸条放在哪里。

## 1. 写进文件了，为什么 Model 还不知道？

整个数据流是：

```text
磁盘保存的数据
-> Harness 读取、筛选和排序
-> 本次递给 Model 的内容（Context）
-> API Request
-> Model
```

程序关闭后数据仍然存在，这叫**持久化**。本次 API 请求真正递给 Model 的内容，才是它这一次能使用的 **Context**。

磁盘里可以保存 100 条消息。Harness 本次只发送最后两条，Model 就只能使用这两条。前面 98 条没有丢，只是没有被放到它眼前。

状态也可以交给提供模型 API 的服务方（Provider）保存。例如应用用 Response ID 或 Conversation ID 续接会话。保存位置变了，关系没有变：应用仍要决定保存多久，以及哪些内容能进入下一次请求。[OpenAI Conversation state](https://developers.openai.com/api/docs/guides/conversation-state)

## 2. 一次能递给 Model 多少东西？

Context Window 就是 Model 面前那张桌子的大小。假设桌面只能放十页：

```text
System / Developer 指令：1 页
Tool Schema：1 页
当前问题：1 页
输出和推理预留：3 页
历史与 Tool Result：最多 4 页
```

历史记录不能占满十页。工具说明、当前问题和 Model 接下来的回答都需要空间。

如果 `read_file` 返回八页，不能先全部塞进 Prompt，再要求 Model 总结。请求可能在到达模型前就超窗，也可能把真正的问题挤走。Tool 应先过滤、分页或限制长度：

```json
{
  "path": "logs/build.log",
  "content": "...相关片段...",
  "truncated": true,
  "next_offset": 51200
}
```

完整文件仍留在 Workspace。`truncated: true` 表示“后面还有内容”，`next_offset` 表示“下一次从哪里继续读”。Model 需要时可以回查。这不是删文件，只是没有一次把所有内容堆到桌上。

## 3. 四条 Message 为什么仍然只算一轮？

一次乘法任务可能产生：

```text
User：计算 248 x 15
Assistant：请求 multiply，call_id=7
Tool：返回 3720，call_id=7
Assistant：最终回答 3720
```

这里有四条 Message，也调用了两次 Model，但只处理了一个用户问题。这整个过程叫一个 **User Turn**：从 User 提问开始，到 Assistant Final 结束。中间可以经过多次 Tool Call 和 Tool Result。

因此，历史不能简单保留“最后两条消息”。那会留下 Tool Result，却删掉发起它的 Tool Call。最保守的第一版策略是：

```text
旧历史按完整 User Turn 压缩或淘汰
最近完整 Turn 保留原文
当前未完成 Turn 完整保留
```

如果一个 Turn 自己已经大到放不下，也不能从 Tool Call 和 Tool Result 中间剪开。第 5 课会处理这种更难的情况。

## 4. 摘要和长期 Memory，分别该记什么？

会话很长时，可以把早期内容写成一份交接纪要。这个纪要就是 Summary：

```text
Summary：旧目标、决定、完成项和待办
+ 最近完整 Turn 原文
+ 当前 Turn 原文
```

Summary 会丢掉细节。如果纪要漏掉“部署前运行 `hexo g`”，后面真正发给 Model 的内容（Prompt View）就无法凭空找回这句话。

这条部署规则换一个 Session 后仍然有效，所以不该只放在当前会话纪要里。它更适合进入项目长期 Memory，也就是项目下次启动还会读取的规则纸条：

```text
Summary        帮当前 Session 继续任务
项目 Memory   保存这个项目长期遵守的规则
用户 Memory   保存跨项目仍成立的用户偏好
Transcript    保留系统记录到的会话事件
```

Memory 也不能把整份 Transcript 全抄进去。一次构建失败、临时日志、未经确认的推断和凭据都不应自动晋升为长期事实。

## 5. Transcript 是过程，Checkpoint 是过程中的状态

这几个词描述数据承担什么职责。JSON、JSONL 和 SQLite 描述数据放在哪里、怎样写入。两组问题不能混在一起。

把一个 Session 想成银行账户：

```text
Session    = 账户
Transcript = 账户流水
Checkpoint = 某个时刻的余额
```

假设流水是：

```text
第 1 笔：存入 10 元
第 2 笔：花掉 3 元
第 3 笔：存入 5 元
```

这三笔按顺序发生的记录就是 Transcript。它告诉我们余额怎样一步步变成 12 元。

Checkpoint 只记录某个位置上的状态：

```text
处理完第 3 笔后，余额是 12 元
```

所以它们回答的问题不同：

```text
Transcript：之前按顺序发生了什么？
Checkpoint：截至某个位置，程序处于什么状态？
```

只有 Transcript 时，程序可以从第一条开始重放，重新计算当前状态。历史越长，这个过程越慢。有了 Checkpoint，程序可以先恢复最近快照，再处理它后面的新记录。

反过来，只有“余额 12 元”通常无法还原前面的三笔流水。Checkpoint 适合快速恢复，不负责保留完整过程。

### Checkpoint 可以单独保存，也可以写进 Transcript

一种实现把两者分开：

```text
session-demo.jsonl          完整 Transcript
session-demo.checkpoint.json 最新 Checkpoint
```

另一种实现把 Checkpoint 作为一条记录（Entry）追加到 Transcript：

```text
session-demo.jsonl
|- line 1  Message Entry
|- line 2  Message Entry
|- line 3  Checkpoint Entry：记录 line 2 之后的状态
`- line 4  新的 Message Entry
```

恢复时，程序从后往前找到最后一个 Checkpoint，再处理它后面的 Entry。此时整个 JSONL 是 Transcript，其中一行是 Checkpoint。两者并不矛盾。

### 第 4、5 课实际实现了什么

| 概念 | 对应的逻辑实体 | 本书教学实现 |
| --- | --- | --- |
| Context | 本次 Model 实际收到的输入 | 每次组装的 `messages` |
| Session | 以 `session_id` 标识的会话容器 | `SESSION_ID="demo"`；没有单独的 Session 对象 |
| Transcript | 属于 Session 的有序 Entry 集合 | 第 5 课的 `session-demo.jsonl` |
| Checkpoint | Session 某个时刻的状态快照 | 第 4 课的 `session-demo.json` |
| Compaction Entry | 把旧内容改成摘要后留下的恢复点 | 第 5 课 JSONL 中的 `type="compaction"` |
| 项目 Memory | 跨 Session 生效的项目事实 | 项目状态目录中的 Memory 文件 |
| 用户 Memory | 跨项目生效的用户偏好 | 用户状态目录中的 Memory 文件 |

第 4 课的 `session-demo.json` 保存 `summary` 和 `turns`。它是一份不断覆盖的最新 Checkpoint；这一版没有独立追加式 Transcript。

第 5 课的 `session-demo.jsonl` 才是 Transcript。里面有一条把旧内容改成摘要的记录，也就是 Compaction Entry。它可以恢复压缩后的 Prompt View，因此属于“上下文 Checkpoint”。它没有保存工具审批、执行状态等全部运行信息，所以不能把它当作整个工作流的完整 Checkpoint。

同一份 SQLite 也可以同时保存 Session、Transcript Entry、Checkpoint 和 Memory。文件扩展名不会替应用决定数据的意义。

不同 Session 通常不共享当前 Summary，但可以读取同一份项目 Memory。项目 Memory 和用户 Memory 若同时写着不同语言偏好，冲突要在 Harness 组装 Context 时解决，例如：

```text
当前用户明确要求 > 项目规则 > 用户默认偏好
```

这不是行业唯一顺序，但应用必须选择一套可预测规则，不能把冲突原样丢给 Model 猜。

## 6. 有了存档，为什么仍不知道 Tool 是否执行过？

教学示例只在 Assistant Final 出现后，才把完整 Turn 写入 Checkpoint。假设文件已经写入，但程序还没来得及保存 Tool Result 就崩溃：

```text
外部文件：可能已经改变
Checkpoint：仍停在上一个完整 Turn
```

重新启动后，Checkpoint 仍停在上一轮。可是目标文件可能已经改变。存档只能说明“程序最后保存到哪里”，不能证明“外面的动作到底发生了几次”。

这类动作需要单独保存执行收据：何时获准、何时开始、最后确认成功还是状态不明。后面会把这份收据叫作 Execution Ledger，并讨论怎样防止同一个动作被重复执行。

纯读取或整数乘法通常没有这个负担。重复读取不会多发一封邮件，也不会再次扣款。

## 7. 自己动手验证一次

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

这次最值得亲手做的，不是抄完整代码，而是观察两次重启后的差别。

第一组实验继续使用同一个 `SESSION_ID`。重启后，Agent 应该恢复旧任务。第二组实验新建 Session，但仍读取同一份项目 Memory。它应该忘记旧任务进度，却记得已经确认的部署规则。

不要用“同一会话继续成功”证明长期 Memory，也不要用“记得部署规则”证明工作流 Checkpoint 已恢复。二者恰好可能读取同一个磁盘，但回答的问题不同。

`summary`、`turns` 和 Context 组装值得自己写一次。JSON 序列化、文件路径和 SDK 初始化可以让 AI 帮忙。数据库与 Provider 托管 Conversation 暂时只需看懂职责，不需要重新实现。

接着运行[第一阶段综合实践第三关](../exercises/phase-1-capstone/README.md#第三关transcript-与-prompt-view)，亲手实现 JSONL Transcript、Prompt View、重启恢复和 Compaction。

下一课继续回答：完整 Transcript 放不进窗口时，[怎样构造受预算控制的 Prompt View](05-上下文工程.md)？

## 主动回忆

1. JSON 已经保存规则，为什么 Model 仍可能看不到？
2. 持久化与 Context 分别回答什么？
3. 四条 Tool Calling Message 为什么只算一个 User Turn？
4. 为什么不能简单保留最后几条 Message？
5. Summary 与项目长期 Memory 分别保存什么？
6. Session、Transcript 与 Checkpoint 有什么区别？
7. Tool Result 太大时，为什么要在进入 Context 前限流？
8. Checkpoint 没有当前 Turn，为什么不能断定 Tool 没执行？

<details>
<summary>检查简答</summary>

1. 存储不会自动进入模型输入；Harness 必须读取、筛选并放入请求。
2. 持久化保证以后还能读取；Context 是本次生成真正可用的输入。
3. User Turn 按一个用户请求的完整处理过程划分，其中可以包含多次模型调用。
4. 可能剪断 Tool Call 与 Tool Result，也可能丢失用户目标。
5. Summary 保存当前 Session 的旧进度；项目 Memory 保存跨 Session 仍有效的稳定规则。
6. Session 是会话容器；Transcript 是按顺序发生的过程；Checkpoint 是过程走到某处时的状态快照。Checkpoint 可以单独保存，也可以作为一条 Entry 写进 Transcript。
7. 大结果可能超窗或挤走当前问题，应分页、截断并提供回查位置。
8. Tool 可能已经产生副作用，只是新状态还没来得及写盘。

</details>

## 参考资料

> 资料最后核验于 2026-09-03；会变化的源码锚点收录在下面的复核记录中。

- [本批章节一手资料复核](../research/01-05-chapter-promotion-sources.md)
- [OpenAI Conversation state](https://developers.openai.com/api/docs/guides/conversation-state)
- [OpenAI Compaction](https://developers.openai.com/api/docs/guides/compaction)
- [Anthropic Compaction](https://platform.claude.com/docs/en/build-with-claude/compaction)
- [完整教学代码](https://github.com/unix2dos/agent-engineering-book/blob/main/examples/lesson_04_session_memory.py)
- [第一阶段综合实践](https://github.com/unix2dos/agent-engineering-book/tree/main/exercises/phase-1-capstone)
