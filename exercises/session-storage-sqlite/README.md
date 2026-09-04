# 专项实践：什么时候该从 JSONL 换成 SQLite

假设 `session.jsonl` 已经写了十万行。程序重启后，你想找出所有最终状态为 `unknown` 的工具执行。

JSONL 当然能查。但程序得从第一行读到最后一行，再按 `execution_id` 整理每次状态。偶尔查一次没问题；每次启动都查，代码就会慢慢长出索引、去重和锁。

这个练习不重写完整 Agent。我们只用 Python 自带的 `sqlite3` 做一件小事：同时保存“全部状态变化”和“每次执行的最新状态”。它连接第 4 课的存储选择与第 6 课的可靠执行，但不单独占用一课。

```text
execution_events              execution_state
保存全部变化                   只保存每个 execution_id 的最新状态

exec_1 running                exec_1 unknown
exec_1 unknown                exec_2 succeeded
exec_2 running
exec_2 succeeded
```

前者方便追查，后者方便查询。它们必须在同一个事务里更新，否则程序可能只写成功一半。

`execution_state` 是从完整历史提前算出的结果，可以根据 `execution_events` 重建。只有经常查询当前状态时，这张表才值得维护；数据很少、偶尔查询时，只保留历史表会更简单。本练习保留两张表，是为了让事务和查询成本变得可见。

## 第一关 A：建立表和索引

打开 [`starter.py`](starter.py)，先只实现 `create_schema()`。

你需要建立三张表：

- `execution_events`：`sequence INTEGER PRIMARY KEY AUTOINCREMENT`、`execution_id TEXT NOT NULL`、`status TEXT NOT NULL`；
- `execution_state`：`execution_id TEXT PRIMARY KEY`、`status TEXT NOT NULL`；
- `tool_operations`：`idempotency_key TEXT PRIMARY KEY`、`arguments_sha256 TEXT NOT NULL`。

再用 `CREATE INDEX execution_state_by_status ON execution_state(status)` 为状态建目录。这样以后查询全部 `unknown` 时，不必逐行扫描整张状态表。

Python 的 `database.executescript("""...""")` 可以一次执行多条建表语句。你要亲手写的是三条 `CREATE TABLE` 和一条 `CREATE INDEX`。

测试里的 `sqlite3.connect(":memory:")` 会建立一份只存在于内存中的临时数据库。它不会生成本地 `.db` 文件；连接关闭后，表和数据一起消失，所以每次自检都能从空库开始。真正需要重启恢复时，应传入文件路径，例如 `sqlite3.connect("agent.db")`。

运行：

```bash
python -B exercises/session-storage-sqlite/starter.py --checkpoint-a
```

通过标志：

```text
checkpoint A passed
```

这一关只需要学会四个 SQL 词：

- `CREATE TABLE`：建表；
- `PRIMARY KEY`：这一列不能重复；
- `NOT NULL`：这一列不能空着；
- `CREATE INDEX`：给常查的列建立目录。

先完成 A，不要一次写完后面的函数。

## 第一关 B：两张表必须一起成功

现在实现 `record_execution_state()`。

假设 `exec_1` 从 `running` 变成 `unknown`。程序要做两次写入：

```text
execution_events 追加一行：exec_1 unknown
execution_state  更新一行：exec_1 unknown
```

如果只完成第一行，查询最新状态时仍会看到旧值。如果只完成第二行，以后又无法追查状态怎样变化。这里需要一个**事务**：把两次写入装进同一个袋子，要么一起落库，要么一起撤回。

Python 的写法是：

```python
with database:
    database.execute(...)  # 追加完整历史
    database.execute(...)  # 更新最新状态
```

你需要满足四条规则：

- `status` 必须属于已有的 `VALID_STATUSES`，否则抛出 `ValueError`；
- 向 `execution_events` 追加一行，旧记录不能覆盖；
- 向 `execution_state` 写入最新状态；相同 `execution_id` 已存在时更新 `status`；
- 两条 SQL 必须放在同一个 `with database:` 中。

更新最新状态可以使用 SQLite 自带的 Upsert：

```sql
INSERT INTO execution_state(...)
VALUES (...)
ON CONFLICT(execution_id) DO UPDATE
SET status = excluded.status
```

`excluded.status` 指这次本来想写入、但遇到主键冲突的新值。

运行：

```bash
python -B exercises/session-storage-sqlite/starter.py --checkpoint-b
```

通过标志：

```text
checkpoint A passed
checkpoint B passed
```

这一关的测试会故意让第二次写入失败。如果第一条历史也随之消失，就证明事务真的把两次写入绑在了一起。

## 第一关 C：只找现在仍是 unknown 的执行

现在实现 `list_unknown_executions()`。先看三次执行：

```text
exec_1：running -> unknown
exec_2：unknown -> succeeded
exec_3：running -> unknown
```

正确答案只有 `exec_1` 和 `exec_3`。`exec_2` 以前出现过 `unknown`，但它现在已经成功，所以不能返回。查询应读取 `execution_state`，而不是在完整历史里搜索所有 `unknown`。

`fetchall()` 返回的是多行数据库记录：

```python
[("exec_1",), ("exec_3",)]
```

函数声明要求返回 `list[str]`，所以最终结果应该是：

```python
["exec_1", "exec_3"]
```

请使用参数占位符查询，并按 `execution_id` 排序，让结果稳定：

```sql
SELECT execution_id
FROM execution_state
WHERE status = ?
ORDER BY execution_id
```

运行：

```bash
python -B exercises/session-storage-sqlite/starter.py --checkpoint-c
```

通过标志：

```text
checkpoint A passed
checkpoint B passed
checkpoint C passed
```

## 第一关 D：让数据库裁决幂等键

现在实现 `claim_operation()`。它要区分三种情况：

```text
第一次看到 key_1 + hash_a       -> 占位成功，返回 True
再次看到 key_1 + hash_a         -> 同一请求重试，返回 False
再次看到 key_1 + hash_b         -> Key 被不同参数误用，抛出 ValueError
```

不能先执行 `SELECT`，确认不存在后再 `INSERT`。两个 Worker 可能同时读到“不存在”，然后都以为自己可以执行：

```text
Worker A：SELECT -> 没有
Worker B：SELECT -> 没有
Worker A：INSERT -> 成功
Worker B：INSERT -> 主键冲突
```

真正防重的是数据库里的 `PRIMARY KEY`。应用只负责解释结果。可以使用：

```sql
INSERT INTO tool_operations(idempotency_key, arguments_sha256)
VALUES (?, ?)
ON CONFLICT(idempotency_key) DO NOTHING
```

执行后检查 Cursor 的 `rowcount`：

- `1`：本次真的插入了一行，返回 `True`；
- `0`：Key 已存在。再读取旧 `arguments_sha256`；相同返回 `False`，不同抛出 `ValueError`。

查询和插入都使用参数占位符，并放进 `with database:`。

运行：

```bash
python -B exercises/session-storage-sqlite/starter.py --checkpoint-d
```

通过标志：

```text
checkpoint A passed
checkpoint B passed
checkpoint C passed
checkpoint D passed
```

这一关证明的不是“先查一下有没有”，而是让数据库在写入发生的那个瞬间保证同一个 Key 只有一个占位。

## 完成后你应该能解释

- 为什么 `execution_events` 与 `execution_state` 必须在同一个事务里更新；
- 为什么查询当前 `unknown` 状态不能只搜索历史记录；
- 为什么 `PRIMARY KEY` 比应用里的“先查再写”更可靠；
- 为什么同一个 `idempotency_key` 配上不同参数必须报冲突。

这些关卡完成后，你应该能说明：JSONL 何时已经够用，SQLite 又是在什么读写压力下开始省事。然后把事务与唯一约束带回第 6 课的 Tool Reliability 场景，判断它们怎样约束真实副作用。
