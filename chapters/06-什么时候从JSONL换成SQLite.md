# 第 6 课：什么时候该从 JSONL 换成 SQLite

假设 `session.jsonl` 已经写了十万行。程序重启后，你想找出所有最终状态为 `unknown` 的工具执行。

JSONL 当然能查。但程序得从第一行读到最后一行，再按 `execution_id` 整理每次状态。偶尔查一次没问题；每次启动都查，代码就会慢慢长出索引、去重和锁。

这时真正变化的不是文件大小，而是使用方式。原来只需顺序追加和回放，现在开始频繁按条件查询，还要防止重复写入，并保证多次修改一起成功。存储选择应该跟着这些动作变化。

## 1. JSONL 为什么一直够用？

JSONL 是“一行一个 JSON 对象”的文本文件：

```jsonl
{"execution_id":"exec_1","status":"running"}
{"execution_id":"exec_1","status":"unknown"}
{"execution_id":"exec_2","status":"running"}
{"execution_id":"exec_2","status":"succeeded"}
```

它的长处就是简单：新事件写到文件末尾，人能直接打开，程序也能从头回放。一个本地 Agent 只有一个写者，平时只追加 Session Transcript，JSONL 往往已经够用。

问题出现在“找当前状态”。看到 `exec_2 unknown` 还不能返回，因为后面又出现了 `exec_2 succeeded`。程序必须读完全部记录，才能知道最后一条是什么。

这不代表 JSONL 不可靠。它只是把查询、索引、唯一约束和并发协调留给了应用。如果这些能力很少使用，自己承担反而更省事；如果每次启动都需要，应用就开始重复实现数据库已经做好的工作。

## 2. 为什么练习同时保存历史和最新状态？

第 6 课练习建立了两张表：

```text
execution_events              execution_state
保存全部状态变化               保存每个 execution_id 的最新状态

exec_1 running                exec_1 unknown
exec_1 unknown                exec_2 succeeded
exec_2 running
exec_2 succeeded
```

`execution_events` 回答“发生过什么”，方便追查。`execution_state` 回答“现在是什么”，方便直接筛选 `unknown`。

第二张表确实是重复数据。它是从完整历史提前算出的结果，可以根据 `execution_events` 重建。只有经常查询当前状态时，这份重复才值得；数据很少、偶尔查询时，只保留历史表更简单。

数据库里常把这种提前算好的结果叫作物化状态或物化视图。名字不重要，判断方法很直接：如果每次读取都在重复同一段昂贵计算，可以考虑提前保存结果；如果几乎不读，就不要多养一份数据。

## 3. 两张表为什么必须放进一个事务？

假设 `exec_1` 从 `running` 变成 `unknown`。程序要做两次写入：

```text
execution_events 追加 exec_1 unknown
execution_state  更新 exec_1 unknown
```

程序可能在两次写入之间崩溃。只写历史，当前状态仍显示 `running`；只写状态，又失去了变化过程。

事务把两次修改绑在一起：全部成功才提交，其中一步失败就全部撤回。Python 的 `sqlite3` 可以直接使用连接对象管理这条边界：

```python
with database:
    database.execute("INSERT INTO execution_events ...")
    database.execute("INSERT INTO execution_state ... ON CONFLICT ...")
```

练习故意让第二次写入失败。如果第一张表里也没有留下半条记录，就证明两次修改真的属于同一个事务。

JSONL 也能实现类似保证，但需要自己设计临时文件、提交标记、锁和崩溃恢复。需要经常跨多条记录原子修改时，SQLite 开始回本。

## 4. 为什么“先查再写”挡不住重复执行？

两个 Worker 可能同时检查同一个 `idempotency_key`：

```text
Worker A：SELECT -> 不存在
Worker B：SELECT -> 不存在
Worker A：INSERT -> 成功
Worker B：INSERT -> 也想成功
```

两次查询都没有撒谎，只是第二个 Worker 读取时，第一个还没写入。若防重只靠应用里的 `if`，两个 Worker 都可能越过检查。

练习把 `idempotency_key` 设为 `PRIMARY KEY`。数据库在真正写入的那一刻只允许一个成功：

```sql
INSERT INTO tool_operations(idempotency_key, arguments_sha256)
VALUES (?, ?)
ON CONFLICT(idempotency_key) DO NOTHING
```

第一次插入返回成功。同一个 Key 和同一份参数再次出现，说明是同一请求重试，可以复用旧操作；同一个 Key 却带着不同参数，说明调用方误用了身份，必须报冲突。

唯一约束不是为了让错误信息好看，而是把“只能有一个”放进与写入相同的原子边界。多进程可能绕过应用检查，却不能一起绕过数据库主键。

## 5. 索引、FTS 和向量索引解决的是同一个问题吗？

它们都让读取更快，但查找方式不同。

普通索引像按姓名排序的通讯录。练习给 `execution_state.status` 建索引，是为了快速找到状态等于 `unknown` 的行。

FTS 是全文索引。你搜索“部署失败”，它会在大量消息正文里找这些词。SQLite 可以使用 FTS5，但具体构建必须包含或加载该能力。[SQLite FTS5](https://www.sqlite.org/fts5.html)

向量索引用来找“意思接近”的内容。搜索“发布前的检查”，即使原文写的是“部署博客前运行 `hexo g`”，仍可能被找到。它通常需要额外扩展和向量模型，不能因为使用 SQLite 就自动获得。

索引属于可重建数据。若索引与原始 Memory 或 Transcript 冲突，应相信原文并重建索引，不能让目录覆盖正文。

## 6. WAL 为什么能让读取少等一会儿？

普通写入会修改数据库主文件。WAL 模式先把新事务追加到旁边的 Write-Ahead Log，可以把它理解成一本待合并的小账本：

```text
Writer -> 先追加 WAL
Reader -> 继续读取自己的旧快照
Checkpoint -> 稍后把 WAL 合并回主库
```

Reader 开始查询时会确定一个边界，只看这个边界之前已经提交的内容。Writer 后来追加的新事务，不会突然混进同一次读取。因此 Reader 和 Writer 更少互相阻塞。[SQLite WAL](https://www.sqlite.org/wal.html)

WAL 没有把 SQLite 变成分布式数据库。相关进程仍应位于同一主机，同一时刻也只有一个 Writer。它改善本地读写配合，不负责多主机共享、高写入争用、备份和 Schema Migration。

测试使用的 `sqlite3.connect(":memory:")` 也要单独看待。它运行的是真 SQLite，但数据库只活在当前连接的内存里，关闭后就消失。要验证重启恢复，必须改用 `sqlite3.connect("agent.db")` 这样的文件路径。

## 7. 换了数据库，Transcript 和 Memory 会跟着变吗？

不会。第 4、5 课中的术语描述职责，JSONL 和 SQLite 描述保存方式：

```text
Transcript   保存会话按顺序发生的事件
Checkpoint   保存某个位置上的状态
Memory       保存跨 Session 仍有用的事实
Prompt View  保存本轮真正交给 Model 的内容
```

这些数据可以放进同一份 SQLite，也可以分散在几个文件中。换存储不会自动决定什么该进入 Prompt，也不会自动证明 Tool 副作用执行了几次。

大型日志、图片和构建产物也不必硬塞进数据库。它们可以留在文件系统或对象存储，数据库只保存路径、Hash、状态和一小段预览。

## 8. 五个项目为什么没有使用同一种存储？

因为它们的访问方式不同。

- **Pi**：Coding Agent Session 当前默认使用 JSONL，Entry 用 `id/parentId` 形成分支树；Agent Core 另有 SQLite Session Backend。当前 SQLite Backend 明确不提供 FTS 或 Search Service，搜索是单独的 Projection。[Pi Session Format](https://github.com/earendil-works/pi/blob/007c0be640789b8971db6ecacdc96e61107d849f/packages/coding-agent/docs/session-format.md)、[Pi SQLite Backend](https://github.com/earendil-works/pi/blob/007c0be640789b8971db6ecacdc96e61107d849f/packages/session-backends/sqlite-node/README.md)
- **OpenClaw**：当前把控制面放进全局 SQLite，把普通 Session 与 Transcript 放进每 Agent SQLite。旧 JSON/JSONL 是迁移输入；Incognito Session 才只留在内存。[OpenClaw Session](https://github.com/openclaw/openclaw/blob/8544aed05a5dbffb871483be781f71351203319e/docs/concepts/session.md)、[Database Schemas](https://github.com/openclaw/openclaw/blob/8544aed05a5dbffb871483be781f71351203319e/docs/reference/database-schemas.md)
- **Hermes**：使用 `~/.hermes/state.db` 保存 Session 和 Message，并使用 WAL、普通索引与 FTS5。多入口访问、搜索和 Schema Migration 让 SQLite 值得维护。[Hermes Session Storage](https://github.com/NousResearch/hermes-agent/blob/561b053f794a1781868bb032029d589c67708119/website/docs/developer-guide/session-storage.md)
- **LangGraph**：定义可替换的 Checkpointer。内存适合测试，SQLite 适合本地持久化，PostgreSQL 适合共享服务；`thread_id` 负责关联一系列 Checkpoint。[LangGraph Checkpoint](https://github.com/langchain-ai/langgraph/blob/11738d83db4320bb191804342b5c76ae7eca54a0/libs/checkpoint/README.md)
- **OpenAI Agents SDK**：提供 SQLite、Redis、SQLAlchemy、MongoDB 和 OpenAI Conversations 等 Session Backend。选哪个仍取决于本地、共享、多进程或服务端托管需求。[Agents SDK Sessions](https://github.com/openai/openai-agents-python/blob/89c02c828ee8510fe9a84ee6675608193aa13b02/docs/sessions/index.md)

这些项目没有给出一个“最佳数据库”。它们共同说明：先看系统怎样读写，再选保存方式。

## 9. 什么时候选 JSONL、SQLite 或别的 Backend？

可以先用这组判断：

| 当前需求 | 合适的起点 |
| --- | --- |
| 本地单 Writer，主要追加、回放和人工检查 | JSONL |
| 同一主机，需要事务、约束、筛选或 FTS | SQLite |
| 多 Worker 共享低延迟状态、TTL 或任务协调 | Redis，另外决定持久化策略 |
| 多主机、多写者、强约束和复杂关系查询 | PostgreSQL |
| 只想让 Provider 续接模型对话 | Server-managed Conversation |

Redis 的数据能否在故障后保留，取决于 RDB、AOF、复制和落盘配置，不能把“写入 Redis”自动理解成永久审计。[Redis Persistence](https://redis.io/docs/latest/operate/oss_and_stack/management/persistence/)

PostgreSQL 适合多实例、多租户和多写者，但也带来连接池、Migration、备份和监控。一个本地 CLI 为了“以后可能扩容”提前引入它，通常没有收益。[PostgreSQL MVCC](https://www.postgresql.org/docs/current/mvcc-intro.html)

Provider 托管 Conversation 可以少传或少管一份模型历史，却不能代替本地 Ledger、Artifact、审批记录和业务 Memory。Provider 看见模型请求了 `send_email`，不等于它能证明邮件实际发送了几次。[OpenAI Conversation state](https://developers.openai.com/api/docs/guides/conversation-state)

## 10. 自己验证一次

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

四关分别验证建表与索引、事务、当前状态查询和幂等键唯一约束。完整说明见[第 6 课 SQLite 练习](../exercises/lesson-06-sqlite/README.md)。

需要亲手写一次的是事务边界、Upsert、条件查询和幂等冲突判断。建库样板、Migration 框架、连接池和向量扩展接入可以交给成熟库或 AI；没有真实并发和搜索需求时，不要提前搭它们。

## 主动回忆

1. 十万行 JSONL 为什么仍然“能查”，却可能不再合适？
2. `execution_events` 与 `execution_state` 分别回答什么问题？
3. `execution_state` 为什么是可重建数据？
4. 两张表为什么必须在同一个事务中更新？
5. 为什么应用里的“先查再写”挡不住并发重复？
6. 普通索引、FTS 和向量索引分别查什么？
7. WAL 改善了什么，又没有解决什么？
8. 为什么换成 SQLite 不会改变 Transcript 与 Prompt View 的职责？
9. Pi、OpenClaw 和 Hermes 为什么可以选择不同 Backend？
10. 什么信号出现时，SQLite 应继续升级为 PostgreSQL？

<details>
<summary>检查简答</summary>

1. 它可以顺序扫描；但频繁按状态查询时，每次都要读完并重新分组，应用开始重复实现索引。
2. 前者保存全部状态变化，后者保存每次执行的最新状态。
3. 它能从完整 `execution_events` 重算出来；冲突时应相信历史并重建当前状态。
4. 否则崩溃可能只完成一张表，造成历史和当前状态不一致。
5. 多个 Worker 可能同时查到“不存在”；唯一约束才能在实际写入时只接受一个。
6. 普通索引查精确字段，FTS 查正文关键词，向量索引查语义相近内容。
7. WAL 减少同机 Reader 与 Writer 的阻塞；它没有提供多主机写入，也没有取消单 Writer、备份和 Migration 要求。
8. 数据库是保存介质；Transcript 与 Prompt View 描述数据的职责和是否进入本轮模型输入。
9. 它们的写者数量、查询方式、迁移、搜索和产品运行形态不同。
10. 出现多主机、多写者、复杂跨表约束，并且团队能够承担数据库服务运维时。

</details>

## 参考资料

> 开源实现最后核验于 2026-09-03，完整变更记录见[第 6 课一手资料复核](../research/06-storage-source-verification.md)。

- [第 6 课 SQLite 练习](../exercises/lesson-06-sqlite/README.md)
- [SQLite WAL](https://www.sqlite.org/wal.html)
- [SQLite FTS5](https://www.sqlite.org/fts5.html)
- [Redis Persistence](https://redis.io/docs/latest/operate/oss_and_stack/management/persistence/)
- [PostgreSQL MVCC](https://www.postgresql.org/docs/current/mvcc-intro.html)
- [OpenAI Conversation state](https://developers.openai.com/api/docs/guides/conversation-state)
