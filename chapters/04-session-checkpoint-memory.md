# 第 4 课：Session、Checkpoint 与长期记忆

> 本章只守住一条关系：数据留在磁盘，不等于 Model 这一次看得见。资料最后核验于 2026-09-03；相关实现锚点见[第 1～5 课一手资料复核](../research/01-05-chapter-promotion-sources.md)。

先做一个实验：

```text
你：记住，部署博客前必须运行 hexo g。
Agent：好的。

关闭程序，重新启动。

你：部署前要做什么？
```

如果程序只把对话放在内存里，旧进程退出后，`messages` 就消失了。如果程序已经把这句话写入 JSON，Model 仍不会自动知道；Harness 还要读取文件、选择相关内容，再放进本次请求。

> 模型不记事，程序递纸条。内存、JSON、SQLite 只是纸条放在哪里。

## 本章怎样学

| 类型 | 本章要求 |
| --- | --- |
| 必须亲写 | 把 Message 写入 Session，并在新进程中加载后重新组装 Context |
| 允许 AI | JSON 序列化、文件路径和 SDK 初始化样板 |
| 必须验证 | 分别验证“继续旧任务”和“新 Session 仍记得项目规则”，不能把两者当成同一能力 |
| 只需读懂 | Provider 托管 Conversation、数据库和向量检索的产品接口，本章先学责任边界 |

## 1. 保存了，不等于 Model 看到了

整个数据流是：

```text
磁盘保存的数据
-> Harness 读取、筛选和排序
-> 本次 Context
-> API Request
-> Model
```

**持久化**回答“程序重启后数据还在不在”；**Context** 回答“本次生成时 Model 实际拿到了什么”。磁盘里可以有 100 条消息，Harness 只发送最后两条，Model 就无法使用前面 98 条。

Provider 也可以用 Response ID 或 Conversation ID 在服务端保存和续接状态。这只是把一部分状态管理交给 Provider，仍不代表模型参数获得了跨请求的私人记忆。应用还要决定业务数据保存多久、怎样检索、哪些信息能进入这次请求。[OpenAI Conversation state](https://developers.openai.com/api/docs/guides/conversation-state)

## 2. Context 是一张有限的桌子

假设模型窗口只能放十页：

```text
System / Developer 指令：1 页
Tool Schema：1 页
当前问题：1 页
输出和推理预留：3 页
历史与 Tool Result：最多 4 页
```

输入预算不能直接等于标称窗口。工具定义、当前问题、输出和推理都需要空间。

如果 `read_file` 返回八页，不能先全部塞进 Prompt，再要求 Model 总结。请求可能在到达模型前就超窗，也可能把真正的问题挤走。Tool 应先过滤、分页或限制长度：

```json
{
  "path": "logs/build.log",
  "content": "...相关片段...",
  "truncated": true,
  "next_offset": 51200
}
```

完整文件仍留在 Workspace。Model 得到截断状态和下一段位置，需要时再回查。这不是丢数据，而是控制本轮可见视图。

## 3. Message、模型请求和 User Turn 不是一个计数

一次乘法任务可能产生：

```text
User：计算 248 x 15
Assistant：请求 multiply，call_id=7
Tool：返回 3720，call_id=7
Assistant：最终回答 3720
```

这里有四条 Message、两次模型 API 请求，但只有一个 User Turn。一个 User Turn 从用户问题开始，到面向用户的 Assistant Final 结束；中间可以有多次 Tool Call 和 Tool Result。

因此，历史不能简单保留“最后两条消息”。那会留下 Tool Result，却删掉发起它的 Tool Call。最保守的第一版策略是：

```text
旧历史按完整 User Turn 压缩或淘汰
最近完整 Turn 保留原文
当前未完成 Turn 完整保留
```

如果当前 Turn 自己已经大到放不下，就需要 Split Turn Compaction。但它也只能在已经闭合的 Tool Call/Result 之后切，不能从请求和回执中间剪开。下一课会结合 Pi 的实现展开。

## 4. Summary 和长期 Memory 解决不同问题

会话很长时，可以把早期历史压成摘要：

```text
Summary：旧目标、决定、完成项和待办
+ 最近完整 Turn 原文
+ 当前 Turn 原文
```

Summary 是有损的。如果它漏掉“部署前运行 `hexo g`”，后面的 Prompt View 就无法从摘要恢复这句话。

跨 Session 仍然成立的项目规则，不应只依赖当前 Session Summary。它更适合进入项目长期 Memory：

```text
Summary        帮当前 Session 继续任务
项目 Memory   保存这个项目长期遵守的规则
用户 Memory   保存跨项目仍成立的用户偏好
Transcript    保留实际发生过的完整事件
```

Memory 也不能把整份 Transcript 全抄进去。一次构建失败、临时日志、未经确认的推断和凭据都不应自动晋升为长期事实。

## 5. Session、Checkpoint、Transcript 与 Memory

这些词描述职责，不描述文件扩展名：

| 概念 | 回答的问题 | 教学实现 |
| --- | --- | --- |
| Context | 本次 Model 看到了什么？ | 每次组装的 `messages` |
| Session | 哪些交互属于同一段连续会话？ | `SESSION_ID` 或 Provider Conversation ID |
| Transcript | 这段会话实际发生过什么？ | 第 5 课的 JSONL Entry |
| Checkpoint | 程序从哪个已知状态恢复？ | 第 4 课的 Session State JSON |
| 项目 Memory | 这个项目跨 Session 仍遵守什么？ | 项目状态目录中的 Memory 文件 |
| 用户 Memory | 这个用户跨项目仍偏好什么？ | 用户状态目录中的 Memory 文件 |

同一份 SQLite 可以同时保存 Session、Checkpoint 和 Memory；也可以分成多个 JSON 文件。存储介质不会替应用决定数据的含义。

不同 Session 通常不共享当前 Summary，但可以读取同一份项目 Memory。项目 Memory 和用户 Memory 若同时写着不同语言偏好，冲突要在 Harness 组装 Context 时解决，例如：

```text
当前用户明确要求 > 项目规则 > 用户默认偏好
```

这不是行业唯一顺序，但应用必须选择一套可预测规则，不能把冲突原样丢给 Model 猜。

## 6. 为什么 Checkpoint 不能证明 Tool 没执行

教学示例只在 Assistant Final 后，把当前完整 Turn 放进已完成轮次并写入 Checkpoint。假设文件已经写入，程序却在 Tool Result 或 Final 落盘前崩溃：

```text
外部文件：可能已经改变
Checkpoint：仍停在上一个完整 Turn
```

Checkpoint 可以说明本地运行状态保存到哪里，不能凭空证明外部世界发生了几次。邮件、付款和文件写入还需要 Execution Ledger、幂等 Key 或人工核对。这个问题留到第 7 课。

纯读取或整数乘法通常不需要 Ledger，因为重复执行不会产生新的外部副作用。

## 7. 运行两组最小实验

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

第一组实验验证 Session：继续同一个 `SESSION_ID`，重启后仍能恢复旧任务。第二组实验验证长期 Memory：开启一个新 Session，仍能加载已经确认的项目规则。

不要用“同一会话继续成功”证明长期 Memory，也不要用“记得部署规则”证明工作流 Checkpoint 已恢复。二者恰好可能读取同一个磁盘，但回答的问题不同。

接着运行[第一阶段综合实践第三关](../exercises/phase-1-capstone/README.md#第三关transcript-与-prompt-view)，亲手实现 JSONL Transcript、Prompt View、重启恢复和 Compaction。

下一课继续回答：完整 Transcript 放不进窗口时，[怎样构造受预算控制的 Prompt View](05-context-engineering.md)？

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
6. Session 是会话身份；Transcript 是发生记录；Checkpoint 是可恢复状态。
7. 大结果可能超窗或挤走当前问题，应分页、截断并提供回查位置。
8. Tool 可能已经产生副作用，只是新状态还没来得及写盘。

</details>

## 参考资料

- [本批章节一手资料复核](../research/01-05-chapter-promotion-sources.md)
- [OpenAI Conversation state](https://developers.openai.com/api/docs/guides/conversation-state)
- [OpenAI Compaction](https://developers.openai.com/api/docs/guides/compaction)
- [Anthropic Compaction](https://platform.claude.com/docs/en/build-with-claude/compaction)
- [完整教学代码](https://github.com/unix2dos/agent-engineering-book/blob/main/examples/lesson_04_session_memory.py)
- [第一阶段综合实践](https://github.com/unix2dos/agent-engineering-book/tree/main/exercises/phase-1-capstone)
