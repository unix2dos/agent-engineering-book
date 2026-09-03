# 第 6 课实践：什么时候该从 JSONL 换成 SQLite

假设 `session.jsonl` 已经写了十万行。程序重启后，你想找出所有最终状态为 `unknown` 的工具执行。

JSONL 当然能查。但程序得从第一行读到最后一行，再按 `execution_id` 整理每次状态。偶尔查一次没问题；每次启动都查，代码就会慢慢长出索引、去重和锁。

这一课不重写完整 Agent。我们只用 Python 自带的 `sqlite3` 做一件小事：同时保存“全部状态变化”和“每次执行的最新状态”。

```text
execution_events              execution_state
保存全部变化                   只保存每个 execution_id 的最新状态

exec_1 running                exec_1 unknown
exec_1 unknown                exec_2 succeeded
exec_2 running
exec_2 succeeded
```

前者方便追查，后者方便查询。它们必须在同一个事务里更新，否则程序可能只写成功一半。

## 第一关 A：建立表和索引

打开 [`starter.py`](starter.py)，先只实现 `create_schema()`。

你需要建立三张表：

- `execution_events`：`sequence INTEGER PRIMARY KEY AUTOINCREMENT`、`execution_id TEXT NOT NULL`、`status TEXT NOT NULL`；
- `execution_state`：`execution_id TEXT PRIMARY KEY`、`status TEXT NOT NULL`；
- `tool_operations`：`idempotency_key TEXT PRIMARY KEY`、`arguments_sha256 TEXT NOT NULL`。

再用 `CREATE INDEX execution_state_by_status ON execution_state(status)` 为状态建目录。这样以后查询全部 `unknown` 时，不必逐行扫描整张状态表。

Python 的 `database.executescript("""...""")` 可以一次执行多条建表语句。你要亲手写的是三条 `CREATE TABLE` 和一条 `CREATE INDEX`。

运行：

```bash
python -B exercises/lesson-06-sqlite/starter.py --checkpoint-a
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

## 后续关卡

- B：在一个事务中同时追加历史、更新最新状态；
- C：直接查询所有 `unknown` 执行；
- D：用主键保护 `idempotency_key`，区分“同一请求重试”和“同一个 Key 被不同参数误用”。

这些关卡完成后，再把第 6 课 Blog 整理成正式书籍章节。
