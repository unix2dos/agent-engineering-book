# 第 5 课：从完整 Transcript 到有限 Prompt View

> 本章结合 Pi、OpenClaw 与 Hermes 的当前源码，解释长会话怎样保留事实、缩短输入并安全恢复。源码固定于 2026-09-02 的 Commit，审计记录见[第 1～5 课一手资料复核](../research/01-05-chapter-promotion-sources.md)。

Agent 运行几个小时后，磁盘上可以有全部消息和完整日志，但 Model 窗口早已放不下。上下文工程不是删得越多越好，而是把“完整事实”和“本轮输入”分开：

> 完整事实留在持久层，Model 每轮只接收受预算控制的 Prompt View。

## 本章怎样学

| 类型 | 本章要求 |
| --- | --- |
| 必须亲写 | JSONL Transcript、Prompt View 投影、Compaction Entry 和安全切点 |
| 允许 AI | 摘要 Prompt、Token 估算适配和 Provider SDK 样板 |
| 必须验证 | 程序重启、重复 Compaction、超大 Tool Result，以及 Tool Call/Result 不会被切开 |
| 只需读懂 | Pi 分支树、OpenClaw SQLite 热路径、Hermes Prompt Cache 权衡，不复制完整框架 |

## 1. 先分清四个对象

| 名称 | 保存什么 | 例子 |
| --- | --- | --- |
| Artifact | Tool 产生的完整文件 | Bash 完整日志、构建产物 |
| Transcript | Session 实际发生过什么 | User、Assistant、Tool Call、Tool Result、执行事件 |
| Compaction Entry | 一次压缩后的恢复点 | Summary、保留原文、切点信息 |
| Prompt View | 本轮真正发给 Model 的消息 | 摘要、最近原文、当前 Turn |

Artifact 不是全部会话记录。完整 Bash 输出属于 Artifact；谁请求了命令、Tool Result 返回了什么，属于 Transcript。二者都可以留在磁盘，但只有 Harness 选中的部分进入 Prompt View。

```text
Artifact / Transcript / Memory
              |
              | Harness 按预算选择
              v
          Prompt View
              |
              v
            Model
```

Compaction 也有两种说法：Compaction 动作负责找切点和生成摘要；Compaction Entry 是动作成功后写进 Session Store 的记录。

本书的最小 JSONL 结构是：

```json
{
  "type": "compaction",
  "summary": "m1-m3 的摘要",
  "retained_tail": ["m4 原文", "m5 原文"],
  "is_split_turn": false
}
```

Model 不直接接收这个外壳。Harness 把它展开成：

```text
summary + retained_tail + Compaction 后的新 Message
```

被摘要的旧 Message 仍留在更早的 Transcript 中。

## 2. Pi：JSONL 可以保存树，也可以保存压缩点

Pi Coding Agent 默认每个 Session 使用一个 JSONL。Entry 通过 `id/parentId` 组成逻辑树：

```text
m1
|- m2 -> m3
`- m4
```

从 `m1` 重新尝试时，只要追加 `m4(parentId=m1)`。当前分支变成 `m1 -> m4`，旧分支仍留在同一个文件里。JSONL 的物理顺序是追加日志，`parentId` 决定逻辑路径。[Pi Session Format](https://github.com/earendil-works/pi/blob/e266507b606b9552fa277252644054afd4384b11/packages/coding-agent/docs/session-format.md)

这不代表 Pi 只能使用 JSONL。它的 Core 还提供 SQLite Backend。单用户 CLI 的顺序追加和人工检查适合 JSONL；并发、事务和复杂查询出现时，数据库更省事。

Pi 在 Context 接近 `contextWindow - reserveTokens` 时执行 Compaction，为下一次输出预留空间。压缩后，下一次请求使用 Summary 加保留消息，旧 Entry 不必删除。[Pi Compaction](https://github.com/earendil-works/pi/blob/e266507b606b9552fa277252644054afd4384b11/packages/coding-agent/docs/compaction.md)

## 3. 大 Tool Result 先变小，再考虑压缩会话

`read_file` 常保留文件 Head，Bash 常保留输出 Tail，并把完整日志留成 Artifact。Head 往往包含声明和配置，Tail 往往包含退出码和最终错误。这只是启发式，不保证根因一定在那里。

如果错误在中间，Model 可以根据 Artifact 路径搜索完整日志，再读取命中附近的小片段。数据没有消失，只是没有一次性进入 Context。

```text
read_file -> 限制长度，返回 truncated 和 next_offset
run_bash  -> 返回受限 Tail、退出状态和 Artifact Path
write_file -> 返回路径、状态和写入 Byte 数
```

先缩 Tool Result，比频繁摘要整段对话更便宜，也更少改变稳定的 Prompt 前缀。

## 4. 安全切点不能拆开 Tool Call 与 Result

一个很大的 Turn 可能是：

```text
User
Assistant(tool_call A)
Tool(result A)
Assistant(tool_call B)
Tool(result B)
Assistant(final)
```

下面两处不能切：

```text
tool_call A | result A
tool_call B | result B
```

它们会让一边只剩申请、另一边只剩回执。完整 Turn 之间是最容易处理的安全边界。

如果单个 Turn 本身已经超窗，Pi 允许 Split Turn：在已经闭合的 Tool Call/Result 之后切开，把前缀压成 Turn Prefix Summary，后面的消息保留原文。切点前的用户目标必须进入摘要，否则后半段不知道自己在完成什么。

当前综合实践采用更保守的第一版：`find_compaction_cut()` 只返回完整 Turn 结束位置；没有安全旧 Turn 时不压缩。它暂时不实现 Split Turn，这是一条有意保留的能力边界。

## 5. OpenClaw：Transcript、Pruning、Compaction 与 Memory 分层

OpenClaw 当前普通 Session 行和 Transcript 默认保存在每 Agent 一个 SQLite：

```text
~/.openclaw/agents/<agentId>/agent/openclaw-agent.sqlite
```

旧 `sessions.json` 与 Transcript JSONL 仍用于迁移或归档。Incognito Session 才把 Session、Transcript 和 Compaction 状态留在进程内存，Gateway 重启后消失。[OpenClaw Session](https://github.com/openclaw/openclaw/blob/ad3268ecccbc7758878662b31adcd72475343d3e/docs/concepts/session.md)

这再次说明 JSONL 与 SQLite 只是存储选择，不能拿扩展名定义 Session。

OpenClaw 还区分两种缩短输入的方法：

| 机制 | 改变什么 | 是否写持久恢复点 |
| --- | --- | --- |
| Pruning | 请求前的旧 Tool Result 视图 | 否 |
| Compaction | 较早历史在后续 Prompt 中的表示 | 是 |
| Transcript | 保存完整会话事实 | 它本身就是持久记录 |

Pruning 可以把旧 Tool Result 换成头尾片段或占位符，不修改磁盘 Transcript。Compaction 生成 Summary 并保存在 Transcript。当前 OpenClaw 的 Compaction 还会保护 Tool Call/Result 配对；摘要质量检查失败时，不写入新的压缩点。[Session Pruning](https://github.com/openclaw/openclaw/blob/ad3268ecccbc7758878662b31adcd72475343d3e/docs/concepts/session-pruning.md)、[Compaction](https://github.com/openclaw/openclaw/blob/ad3268ecccbc7758878662b31adcd72475343d3e/docs/concepts/compaction.md)

Summary 仍可能漏掉跨 Session 有用的规则。因此 OpenClaw 默认会在 Compaction 前尝试 Memory Flush，把经过筛选的稳定事实写入 Memory 文件。[OpenClaw Memory](https://github.com/openclaw/openclaw/blob/ad3268ecccbc7758878662b31adcd72475343d3e/docs/concepts/memory.md)

```text
稳定、跨 Session 有用 -> Memory
当前任务进度          -> Summary
完整发生事实          -> Transcript
```

Memory Flush 不是复制 Transcript。临时日志、失败尝试、未经确认的猜测和敏感内容通常不应晋升为长期 Memory。

## 6. Hermes：Prompt 变短不一定更便宜

Hermes 当前使用 `~/.hermes/state.db` SQLite 保存 Session 和 Message，并提供全文搜索。它的 Micro-compaction 默认关闭：开启后，每个完成 Turn 吸收一个旧 Exchange，滚动更新 Summary。[Hermes Session Storage](https://github.com/NousResearch/hermes-agent/blob/afc3d9d34c9c3b01fa2e1332d2c66a5b5fabae3f/website/docs/developer-guide/session-storage.md)、[Micro-compaction](https://github.com/NousResearch/hermes-agent/blob/afc3d9d34c9c3b01fa2e1332d2c66a5b5fabae3f/docs/micro-compaction.md)

它解决的是“不要突然发生一次很长的摘要停顿”，代价是旧内容更早变成摘要，而且每次改写早期历史都会破坏 Provider 的 Prompt Cache 前缀。

```text
压缩净收益
= 回收的 Context 空间
- 摘要调用成本
- 缓存失效
- 延迟
- 语义损失
```

因此，Prompt 更短不自动等于请求更便宜。稳定前缀很大、缓存折扣很深时，频繁改写早期消息可能比偶尔批量 Compaction 更贵。

## 7. 三个项目的共同结构

| 问题 | Pi | OpenClaw | Hermes |
| --- | --- | --- | --- |
| 持久 Session | CLI 默认 JSONL；Core 可选 SQLite | SQLite；Incognito 在内存 | SQLite |
| 大 Tool Result | Head/Tail 与完整输出文件 | Prompt Pruning | Tool Result Prune |
| 持久压缩 | Compaction Entry | Transcript 中的 Summary | Batch 或滚动 Summary |
| 长期事实 | Context Files | Memory Flush | Memory Hook |
| 特别权衡 | 分支树与 Split Turn | Transcript/Prompt/Memory 分层 | Prompt Cache 与摊销成本 |

共同点不是文件扩展名，而是：持久层保存可以追查的事实，Prompt View 只投影当前任务需要的内容。

## 8. 本书的最小 JSONL Context Agent

配套实现分成两个入口：

- [`lesson_05_context_compaction.py`](../examples/lesson_05_context_compaction.py) 是完整参考实现，包含 Tool 输出限制、Artifact、Transcript、Compaction 和在线运行入口。
- [第一阶段综合实践](../exercises/phase-1-capstone/README.md)要求你亲手从 JSONL 追加、Prompt View、重启恢复一路写到请求前 Compaction。

综合实践第三关最终数据流是：

```text
User Message 先写入 Transcript
-> 请求前检查 Prompt 预算
-> 超预算时寻找完整 Turn 切点
-> summarize(prefix)
-> append Compaction(summary, retained_tail)
-> 从 Transcript 重新 build_prompt_view()
-> 把新 Prompt View 发给 Model
```

最容易漏掉的是倒数第二步。Compaction Entry 已经写盘，不代表旧 Python `messages` 自动改变；Harness 必须重新加载并构造视图。

第二次 Compaction 也必须继承第一次 Summary：

```text
第一次：summary_1 = summarize(m1-m80)
        tail_1    = m81-m100

第二次：summary_2 = summarize(summary_1 + m81-m120)
        tail_2    = m121-m140
```

若第二次完全丢掉 `summary_1`，`m1-m80` 的信息会永久离开未来 Prompt。只需要保留最新 `summary_2`，因为它应当已经吸收旧 Summary；把所有旧摘要一起重复发送也会浪费空间。

本地 JSONL 示例帮助理解责任，不能替 Provider 托管状态。OpenAI 和 Anthropic 都提供服务端 Compaction，但应用自己的完整 Transcript、业务 Memory 与副作用 Ledger 仍有独立价值。[OpenAI Compaction](https://developers.openai.com/api/docs/guides/compaction)、[Anthropic Compaction](https://platform.claude.com/docs/en/build-with-claude/compaction)

## 主动回忆

1. Artifact、Transcript、Compaction Entry 与 Prompt View 分别保存什么？
2. Model 会直接收到 Compaction JSON 外壳吗？
3. Pruning 与 Compaction 分别改变什么？
4. Pi 的 `id/parentId` 为什么能在 JSONL 中表达分支？
5. Split Turn 的切点为什么不能落在 Tool Call 与 Result 之间？
6. OpenClaw 普通 Session 与 Incognito Session 有什么区别？
7. Memory Flush 为什么不能复制整段 Transcript？
8. Prompt 变短为什么可能因 Prompt Cache 失效而更贵？
9. 第二次 Compaction 为什么必须继承旧 Summary？
10. Compaction 写盘后，为什么还要重新构造 Prompt View？

<details>
<summary>检查简答</summary>

1. Artifact 保存完整 Tool 产物；Transcript 保存会话事实；Compaction Entry 保存压缩恢复点；Prompt View 是本轮模型输入。
2. 不会。Harness 展开为 Summary、保留原文和后续 Message。
3. Pruning 只改请求视图；Compaction 写入持久 Summary，改变后续恢复视图。
4. 每个新 Entry 指向父节点，因此追加新节点就能创建分支而不覆盖旧分支。
5. 否则一边只剩调用申请，另一边只剩无法配对的回执。
6. 普通 Session 写 SQLite，可重启恢复；Incognito 只在进程内存中。
7. Transcript 含临时、未经确认和敏感内容；Memory 只保存稳定且未来有用的事实。
8. 改写早期历史会破坏稳定缓存前缀，增加重算、延迟和缓存写入成本。
9. 新 Summary 必须覆盖旧 Summary 与新进入 Prefix 的消息，否则更早历史会丢失。
10. 磁盘增加 Entry 不会自动修改进程内已有的 `messages`。

</details>

## 参考资料

- [本批章节一手资料复核](../research/01-05-chapter-promotion-sources.md)
- [完整 Context Agent](https://github.com/unix2dos/agent-engineering-book/blob/main/examples/lesson_05_context_compaction.py)
- [第一阶段综合实践](https://github.com/unix2dos/agent-engineering-book/tree/main/exercises/phase-1-capstone)
- [Pi Session Format](https://github.com/earendil-works/pi/blob/e266507b606b9552fa277252644054afd4384b11/packages/coding-agent/docs/session-format.md)
- [Pi Compaction](https://github.com/earendil-works/pi/blob/e266507b606b9552fa277252644054afd4384b11/packages/coding-agent/docs/compaction.md)
- [OpenClaw Session](https://github.com/openclaw/openclaw/blob/ad3268ecccbc7758878662b31adcd72475343d3e/docs/concepts/session.md)
- [OpenClaw Pruning](https://github.com/openclaw/openclaw/blob/ad3268ecccbc7758878662b31adcd72475343d3e/docs/concepts/session-pruning.md)
- [OpenClaw Compaction](https://github.com/openclaw/openclaw/blob/ad3268ecccbc7758878662b31adcd72475343d3e/docs/concepts/compaction.md)
- [OpenClaw Memory](https://github.com/openclaw/openclaw/blob/ad3268ecccbc7758878662b31adcd72475343d3e/docs/concepts/memory.md)
- [Hermes Session Storage](https://github.com/NousResearch/hermes-agent/blob/afc3d9d34c9c3b01fa2e1332d2c66a5b5fabae3f/website/docs/developer-guide/session-storage.md)
- [Hermes Micro-compaction](https://github.com/NousResearch/hermes-agent/blob/afc3d9d34c9c3b01fa2e1332d2c66a5b5fabae3f/docs/micro-compaction.md)
