"""Lesson 06 exercise: choose SQLite when query and constraints start to matter."""

import sqlite3
import sys


VALID_STATUSES = (
    "approved",
    "rejected",
    "running",
    "succeeded",
    "failed",
    "unknown",
)


def create_schema(database: sqlite3.Connection) -> None:
    """TODO: 第一关 A。建立三张表和一个状态索引。"""
    database.executescript(
        """
        CREATE TABLE IF NOT EXISTS execution_events (
            sequence INTEGER PRIMARY KEY AUTOINCREMENT,
            execution_id TEXT NOT NULL,
            status TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS execution_state (
            execution_id TEXT PRIMARY KEY,
            status TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS tool_operations (
            idempotency_key TEXT PRIMARY KEY,
            arguments_sha256 TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS execution_state_by_status
        ON execution_state(status);
        """
    )


def record_execution_state(
    database: sqlite3.Connection,
    execution_id: str,
    status: str,
) -> None:
    """TODO: 第一关 B。同时追加历史并更新最新状态。"""
    raise NotImplementedError("请实现 record_execution_state()")


def list_unknown_executions(database: sqlite3.Connection) -> list[str]:
    """TODO: 第一关 C。查询最终状态为 unknown 的 execution_id。"""
    raise NotImplementedError("请实现 list_unknown_executions()")


def claim_operation(
    database: sqlite3.Connection,
    idempotency_key: str,
    arguments_sha256: str,
) -> bool:
    """TODO: 第一关 D。首次占位返回 True，同一请求重试返回 False。"""
    raise NotImplementedError("请实现 claim_operation()")


def table_names(database: sqlite3.Connection) -> set[str]:
    rows = database.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table'"
    ).fetchall()
    return {row[0] for row in rows}


def checkpoint_a() -> None:
    database = sqlite3.connect(":memory:")
    create_schema(database)

    assert {
        "execution_events",
        "execution_state",
        "tool_operations",
    } <= table_names(database)

    database.execute(
        "INSERT INTO execution_events(execution_id, status) VALUES (?, ?)",
        ("exec_1", "running"),
    )
    database.execute(
        "INSERT INTO execution_events(execution_id, status) VALUES (?, ?)",
        ("exec_1", "unknown"),
    )
    assert database.execute(
        "SELECT status FROM execution_events ORDER BY sequence"
    ).fetchall() == [("running",), ("unknown",)]
    database.execute(
        "INSERT INTO execution_state(execution_id, status) VALUES (?, ?)",
        ("exec_1", "running"),
    )
    database.execute(
        "INSERT INTO tool_operations(idempotency_key, arguments_sha256) "
        "VALUES (?, ?)",
        ("write:file-a", "hash_a"),
    )

    try:
        database.execute(
            "INSERT INTO execution_state(execution_id, status) VALUES (?, ?)",
            ("exec_1", "succeeded"),
        )
    except sqlite3.IntegrityError:
        pass
    else:
        raise AssertionError("execution_id 必须由 PRIMARY KEY 保证唯一")

    indexes = {
        row[1]
        for row in database.execute(
            "PRAGMA index_list('execution_state')"
        ).fetchall()
    }
    assert "execution_state_by_status" in indexes
    assert database.execute(
        "PRAGMA index_info('execution_state_by_status')"
    ).fetchall()[0][2] == "status"
    print("checkpoint A passed")


def checkpoint_b() -> None:
    database = sqlite3.connect(":memory:")
    create_schema(database)

    record_execution_state(database, "exec_1", "running")
    record_execution_state(database, "exec_1", "unknown")
    record_execution_state(database, "exec_2", "running")
    record_execution_state(database, "exec_2", "succeeded")

    assert database.execute(
        "SELECT execution_id, status FROM execution_events ORDER BY sequence"
    ).fetchall() == [
        ("exec_1", "running"),
        ("exec_1", "unknown"),
        ("exec_2", "running"),
        ("exec_2", "succeeded"),
    ]
    assert database.execute(
        "SELECT execution_id, status FROM execution_state ORDER BY execution_id"
    ).fetchall() == [
        ("exec_1", "unknown"),
        ("exec_2", "succeeded"),
    ]

    try:
        record_execution_state(database, "exec_bad", "finished")
    except ValueError:
        pass
    else:
        raise AssertionError("未知状态必须被拒绝")

    database.execute(
        """
        CREATE TRIGGER fail_current_state
        BEFORE INSERT ON execution_state
        WHEN NEW.execution_id = 'exec_crash'
        BEGIN
            SELECT RAISE(ABORT, '模拟第二次写入失败');
        END
        """
    )
    try:
        record_execution_state(database, "exec_crash", "running")
    except sqlite3.IntegrityError:
        pass
    else:
        raise AssertionError("测试应该触发模拟写入失败")

    assert database.execute(
        "SELECT COUNT(*) FROM execution_events WHERE execution_id = ?",
        ("exec_crash",),
    ).fetchone()[0] == 0
    print("checkpoint B passed")


def main() -> None:
    if "--checkpoint-b" in sys.argv:
        checkpoint_a()
        checkpoint_b()
        return
    if "--checkpoint-a" in sys.argv:
        checkpoint_a()
        return
    print(
        "从第一关开始：python -B "
        "exercises/lesson-06-sqlite/starter.py --checkpoint-a"
    )


if __name__ == "__main__":
    main()
