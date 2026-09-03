# 第 6 课：什么时候该从 JSONL 换成 SQLite

`session.jsonl` 已经写了十万行。Agent 重启后，你想找出所有最终状态仍是 `unknown` 的工具执行。

文件里明明什么都有，为什么这件事开始麻烦了？

因为 `exec_2` 可能先是 `unknown`，后来又重试成功：

```jsonl
{"execution_id":"exec_1","status":"running"}
{"execution_id":"exec_1","status":"unknown"}
{"execution_id":"exec_2","status":"unknown"}
{"execution_id":"exec_2","status":"succeeded"}
```

只搜索 `unknown` 会错把 `exec_2` 也找出来。程序必须读到最后一行，才能知道每次执行现在是什么状态。

JSONL 没有坏。变化的是使用方式：原来只需追加和回放，现在开始反复查询、同时修改多份数据，还要防止两个 Worker 重复执行同一请求。SQLite 正是在这些问题出现后才开始有价值。

## 1. 文件很大，就一定要换数据库吗？

不一定。JSONL 就是一行一个 JSON 对象。新事件写到末尾，人能直接打开，程序也能从头回放。

一个本地 Agent 只有一个写者，平时只追加 Session Transcript，排查问题时才偶尔扫描一次，JSONL 往往已经够用。十万行只在归档时读一次，不必急着换；一万行却每次启动都按状态整理，数据库可能已经更省事。

关键不是文件有多大，而是程序平时怎样读写它。

## 2. 为了查得快，多存一张表之后发生了什么？

练习没有每次重放十万行，而是提前保存了当前答案：

```text
execution_events              execution_state
保存全部状态变化               保存每次执行的最新状态

exec_1 running                exec_1 unknown
exec_1 unknown                exec_2 succeeded
exec_2 unknown
exec_2 succeeded
```

`execution_events` 方便追查“发生过什么”。`execution_state` 让程序直接筛选“现在还有哪些 `unknown`”。给 `status` 建一个索引后，数据库也不用从第一行挨个找。

第二张表确实是重复数据。如果当前状态很少查询，就不该维护它。只有同一个计算被反复执行，提前保存结果才值得。数据库里常把这种提前算好的结果叫物化状态。

它可以根据完整历史重建，不是唯一事实来源。本练习发现两张表冲突时，会相信 `execution_events`，重新生成 `execution_state`。

查询变快以后，写入却多了一步。`exec_1` 变成 `unknown` 时，两张表必须一起修改：

```text
execution_events 追加 exec_1 unknown
execution_state  更新 exec_1 unknown
```

假设第一步成功，第二步失败。历史说它已经 `unknown`，当前状态却仍显示 `running`。

两次修改必须被绑成一个动作：全部成功才落库，其中一步失败就全部撤回。这个边界叫事务。

```python
with database:
    database.execute("INSERT INTO execution_events ...")
    database.execute("INSERT INTO execution_state ... ON CONFLICT ...")
```

练习会故意让第二次写入失败。如果第一张表也没有留下半条记录，就证明事务生效了。

JSONL 也能自己设计提交标记、锁和恢复流程。但当程序经常需要“几条记录一起成功”时，继续手写这些机制，就像在文件旁边重新造一小块数据库。

## 3. 已经先查过了，为什么还会重复？

现在两个 Worker 同时收到相同的 `idempotency_key`：

```text
Worker A：SELECT -> 不存在
Worker B：SELECT -> 不存在
Worker A：准备 INSERT
Worker B：也准备 INSERT
```

两次查询都没错。问题是它们发生在写入之前，两个 Worker 都看见了同一个旧状态。

练习把 `idempotency_key` 设为主键，也就是这列不能出现两个相同值。数据库在真正写入的瞬间只允许一个 Worker 成功：

```sql
INSERT INTO tool_operations(idempotency_key, arguments_sha256)
VALUES (?, ?)
ON CONFLICT(idempotency_key) DO NOTHING
```

第一次插入成功，函数返回 `True`。同一个 Key 和同一份参数再次出现，说明是同一请求重试，返回 `False`。同一个 Key 却带着不同参数，说明调用方误用了身份，代码会明确报错。

真正防重的是数据库主键。应用只负责解释冲突，不能用“先查一下”代替写入时的唯一约束。

## 4. Agent 写数据库时，界面还能读取吗？

后台 Agent 正在保存新消息，桌面界面同时打开 Session 列表。如果写入一直挡住读取，界面就会卡住。

SQLite 的 WAL 模式先把新事务追加到旁边的小账本。界面继续读取它开始查询时看到的旧快照：

```text
Writer -> 把新事务追加到 WAL
Reader -> 继续读取自己的旧快照
Checkpoint -> 稍后把 WAL 合并回主库
```

Writer 后来追加的内容不会突然混进 Reader 已经开始的查询，所以读写更少互相等待。[SQLite WAL](https://www.sqlite.org/wal.html)

WAL 只改善同一主机上的读写配合。SQLite 同一时刻仍只有一个 Writer，也没有因此变成多主机数据库。备份、Schema Migration 和高写入争用仍要单独处理。

测试中的 `sqlite3.connect(":memory:")` 运行的是真 SQLite，但数据库只活在当前连接的内存里。连接关闭，数据就消失。要验证重启恢复，应换成 `sqlite3.connect("agent.db")` 这样的文件路径。

## 5. 现在应该选 JSONL、SQLite，还是别的存储？

前面的变化已经给出了判断方法：

| 你真正遇到的问题 | 合适的起点 |
| --- | --- |
| 本地单 Writer，主要追加、回放和人工检查 | JSONL |
| 同一主机，需要事务、唯一约束或条件查询 | SQLite |
| 多 Worker 共享低延迟状态、TTL 或任务协调 | Redis，并另定持久化策略 |
| 多主机、多写者和复杂关系查询 | PostgreSQL |
| 只想让 Provider 续接模型对话 | Server-managed Conversation |

搜索也要看目标。查 `status = 'unknown'` 用普通索引；在消息正文里找“部署失败”用全文搜索，也叫 FTS；想用“发布前的检查”找到“部署博客前运行 `hexo g`”，才需要向量搜索。后两者不是换成 SQLite 后自动出现的能力，当前练习也不实现它们。[SQLite FTS5](https://www.sqlite.org/fts5.html)

Redis 是否能在故障后保留数据，取决于 RDB、AOF、复制和落盘配置。写进 Redis 不自动等于永久审计。[Redis Persistence](https://redis.io/docs/latest/operate/oss_and_stack/management/persistence/)

PostgreSQL 适合多实例和多租户，也会带来连接池、Migration、备份和监控。一个本地 CLI 为了“以后可能扩容”提前使用它，通常得不偿失。[PostgreSQL MVCC](https://www.postgresql.org/docs/current/mvcc-intro.html)

Provider 托管 Conversation 可以少管理一份模型历史，但不会替 Harness 保存 Tool Ledger、Artifact、审批记录和业务 Memory。Provider 看见 Model 请求 `send_email`，不等于它能证明邮件实际发送了几次。[OpenAI Conversation state](https://developers.openai.com/api/docs/guides/conversation-state)

存储介质也不会改变第 4、5 课的职责划分。Transcript 仍保存会话过程，Checkpoint 仍保存某个位置的状态，Prompt View 仍是本轮真正交给 Model 的内容。

真实项目的选择也落在同一张图上：

```text
Pi Coding Agent：本地追加、分支、人工检查      -> 默认 JSONL
OpenClaw / Hermes：列表、搜索、迁移、多入口访问 -> SQLite
LangGraph / Agents SDK：面对不同部署方式       -> 可替换 Backend
```

Pi 的 Agent Core 也提供 SQLite Session Backend，但当前 Backend 明确不提供 FTS 或 Search Service，搜索属于单独的 Projection。[Pi Session Format](https://github.com/earendil-works/pi/blob/007c0be640789b8971db6ecacdc96e61107d849f/packages/coding-agent/docs/session-format.md)、[Pi SQLite Backend](https://github.com/earendil-works/pi/blob/007c0be640789b8971db6ecacdc96e61107d849f/packages/session-backends/sqlite-node/README.md)

OpenClaw 当前把普通 Session 与 Transcript 放进每 Agent SQLite；Hermes 使用 `~/.hermes/state.db`，并增加 WAL、索引和 FTS5。[OpenClaw Session](https://github.com/openclaw/openclaw/blob/8544aed05a5dbffb871483be781f71351203319e/docs/concepts/session.md)、[Hermes Session Storage](https://github.com/NousResearch/hermes-agent/blob/561b053f794a1781868bb032029d589c67708119/website/docs/developer-guide/session-storage.md)

LangGraph 定义可替换的 Checkpointer；OpenAI Agents SDK 也提供 SQLite、Redis、SQLAlchemy、MongoDB 和 OpenAI Conversations 等 Session Backend。项目没有给出一个“最佳数据库”，只是让保存方式跟着运行方式变化。[LangGraph Checkpoint](https://github.com/langchain-ai/langgraph/blob/11738d83db4320bb191804342b5c76ae7eca54a0/libs/checkpoint/README.md)、[Agents SDK Sessions](https://github.com/openai/openai-agents-python/blob/89c02c828ee8510fe9a84ee6675608193aa13b02/docs/sessions/index.md)

## 6. 自己把这条变化链跑一遍

第 6 课练习只使用 Python 标准库，不需要 API Key：

```bash
python -B exercises/lesson-06-sqlite/starter.py --checkpoint-d
```

预期输出：

```text
checkpoint A passed
checkpoint B passed
checkpoint C passed
checkpoint D passed
```

四关分别让你看到：索引为什么出现、事务怎样撤回半次写入、当前状态为什么不能只搜历史、主键怎样挡住重复 Key。完整说明见[第 6 课 SQLite 练习](../exercises/lesson-06-sqlite/README.md)。

事务边界、Upsert、条件查询和幂等冲突判断，值得亲手写一次。建库样板、Migration 框架、连接池和向量扩展接入，可以交给成熟库或 AI。没有真实并发和搜索需求时，不要提前搭它们。

## 主动回忆

1. 十万行 JSONL 为什么仍然能查，却可能不再合适？
2. 决定是否更换存储的关键为什么不是文件大小？
3. `execution_events` 与 `execution_state` 分别回答什么？
4. 什么情况下不值得维护 `execution_state`？
5. 两张表为什么必须放在同一个事务中？
6. 为什么“先查再写”挡不住两个 Worker？
7. WAL 改善了什么，又没有解决什么？
8. 什么情况下才应该从 SQLite 升级到 PostgreSQL？

<details>
<summary>检查简答</summary>

1. 它可以扫描全部记录并计算最后状态；频繁执行时，应用会重复承担查询和索引成本。
2. 大文件若只偶尔顺序读取仍适合 JSONL；小文件若频繁按条件查询，也可能适合数据库。
3. 前者保存全部状态变化，后者保存每次执行的当前状态。
4. 当前状态很少查询，或者重放历史的成本很低时。
5. 否则崩溃可能只完成一张表，导致历史和当前状态不一致。
6. 两个 Worker 可能同时看见旧结果；主键必须在实际写入时裁决谁成功。
7. 它减少同机 Reader 与 Writer 的阻塞；没有提供多主机写入，也没有取消单 Writer、备份和 Migration 要求。
8. 出现多主机、多写者和复杂跨表约束，而且团队能承担数据库服务运维时。

</details>

## 参考资料

> 开源实现最后核验于 2026-09-03，完整变更记录见[第 6 课一手资料复核](../research/06-storage-source-verification.md)。

- [第 6 课 SQLite 练习](../exercises/lesson-06-sqlite/README.md)
- [SQLite WAL](https://www.sqlite.org/wal.html)
- [SQLite FTS5](https://www.sqlite.org/fts5.html)
- [Redis Persistence](https://redis.io/docs/latest/operate/oss_and_stack/management/persistence/)
- [PostgreSQL MVCC](https://www.postgresql.org/docs/current/mvcc-intro.html)
- [OpenAI Conversation state](https://developers.openai.com/api/docs/guides/conversation-state)
