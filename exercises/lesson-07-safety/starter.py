"""Lesson 08 exercise: approval and cwd are not sandbox boundaries."""

import os
import subprocess
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path


def run_from_workspace(workspace: Path, command: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["/bin/sh", "-c", command],
        cwd=workspace,
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )


def run_with_macos_denied_read(
    workspace: Path,
    command: str,
    denied_path: Path,
) -> subprocess.CompletedProcess[str] | None:
    sandbox_exec = Path("/usr/bin/sandbox-exec")
    if sys.platform != "darwin" or not sandbox_exec.is_file():
        return None

    denied = str(denied_path.resolve()).replace("\\", "\\\\").replace(
        '"', '\\"'
    )
    profile = (
        "(version 1)\n"
        "(allow default)\n"
        f'(deny file-read-data (literal "{denied}"))\n'
    )
    return subprocess.run(
        [str(sandbox_exec), "-p", profile, "/bin/sh", "-c", command],
        cwd=workspace,
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )


def select_visible_tools(
    tools: list[dict],
    allowed_names: set[str],
    denied_names: set[str],
) -> list[dict]:
    """检查点 B：根据 Tool Policy 筛选交给 Model 的工具。"""
    visible = []
    for tool in tools:
        if tool["name"] in allowed_names and tool["name"] not in denied_names:
            visible.append(tool)
    return visible


def execute_if_approved(
    tool_name: str,
    visible_names: set[str],
    approve: Callable[[str], bool],
    execute: Callable[[], str],
) -> dict:
    """检查点 C：按 Tool Policy、Approval 的顺序决定是否执行。"""

    if tool_name in visible_names:
        if approve(tool_name):
            return {"status": "completed", "result": execute()}
        else:
            return {"status": "rejected"}
    else:
        return {"status": "denied_by_policy"}


def choose_execution_backend(
    tool_name: str,
    visible_names: set[str],
    *,
    approved: bool,
    sandbox_enabled: bool,
    elevated_requested: bool,
    elevated_allowed: bool,
) -> str:
    """检查点 F：按不可颠倒的顺序选择执行 Backend。"""
    if tool_name not in visible_names:
        return "denied_by_policy"
    if not approved:
        return "rejected"
    if not sandbox_enabled:
        return "host"
    if not elevated_requested:
        return "sandbox"
    if not elevated_allowed:
        return "elevation_denied"
    return "host"


def checkpoint_a() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        workspace = root / "workspace"
        workspace.mkdir()
        outside = root / "outside-secret.txt"
        outside.write_text("safe-demo-secret", encoding="utf-8")

        completed = run_from_workspace(
            workspace,
            "cat ../outside-secret.txt",
        )
        assert completed.returncode == 0
        assert completed.stdout == "safe-demo-secret"
        print("outside_read=true")

    print("checkpoint A passed")


def checkpoint_b() -> None:
    tools = [
        {"name": "read_file"},
        {"name": "write_file"},
        {"name": "run_bash"},
    ]
    original = [dict(tool) for tool in tools]
    visible = select_visible_tools(
        tools,
        allowed_names={"read_file", "write_file", "run_bash"},
        denied_names={"write_file"},
    )
    assert [tool["name"] for tool in visible] == ["read_file", "run_bash"]
    assert tools == original

    assert select_visible_tools(
        tools,
        allowed_names={"run_bash"},
        denied_names={"run_bash"},
    ) == []

    with tempfile.TemporaryDirectory() as temp:
        workspace = Path(temp)
        completed = run_from_workspace(
            workspace,
            "printf bypass > bypass.txt",
        )
        assert completed.returncode == 0
        assert (workspace / "bypass.txt").read_text(encoding="utf-8") == (
            "bypass"
        )
        print("bash_write=true")

    print("checkpoint B passed")


def checkpoint_c() -> None:
    approvals = []
    executions = []

    def approve(tool_name: str) -> bool:
        approvals.append(tool_name)
        return tool_name != "write_file"

    def execute() -> str:
        executions.append("ran")
        return "tool output"

    hidden = execute_if_approved(
        "run_bash",
        visible_names={"read_file"},
        approve=approve,
        execute=execute,
    )
    assert hidden == {"status": "denied_by_policy"}
    assert approvals == []
    assert executions == []

    rejected = execute_if_approved(
        "write_file",
        visible_names={"read_file", "write_file"},
        approve=approve,
        execute=execute,
    )
    assert rejected == {"status": "rejected"}
    assert approvals == ["write_file"]
    assert executions == []

    completed = execute_if_approved(
        "read_file",
        visible_names={"read_file", "write_file"},
        approve=approve,
        execute=execute,
    )
    assert completed == {"status": "completed", "result": "tool output"}
    assert approvals == ["write_file", "read_file"]
    assert executions == ["ran"]

    print("checkpoint C passed")


def checkpoint_d() -> None:
    if os.geteuid() == 0:
        print("permission_demo_skipped=root")
        print("checkpoint D passed")
        return

    with tempfile.TemporaryDirectory() as temp:
        workspace = Path(temp)
        protected = workspace / "protected.txt"
        protected.write_text("protected", encoding="utf-8")
        protected.chmod(0o000)
        try:
            approved = True
            assert approved is True
            completed = run_from_workspace(workspace, "cat protected.txt")
            assert completed.returncode != 0
            assert completed.stdout == ""
            print("approval=true")
            print("os_read=false")
        finally:
            protected.chmod(0o600)

    print("checkpoint D passed")


def checkpoint_e() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        workspace = root / "workspace"
        workspace.mkdir()
        outside = root / "outside-secret.txt"
        outside.write_text("safe-demo-secret", encoding="utf-8")

        host = run_from_workspace(workspace, "cat ../outside-secret.txt")
        assert host.returncode == 0
        assert host.stdout == "safe-demo-secret"

        sandboxed = run_with_macos_denied_read(
            workspace,
            "cat ../outside-secret.txt",
            outside,
        )
        if sandboxed is None:
            print("sandbox_demo_skipped=unsupported")
        else:
            assert sandboxed.returncode != 0
            assert sandboxed.stdout == ""
            print("host_read=true")
            print("sandbox_read=false")

    print("checkpoint E passed")


def checkpoint_f() -> None:
    assert choose_execution_backend(
        "run_bash",
        visible_names={"read_file"},
        approved=True,
        sandbox_enabled=True,
        elevated_requested=True,
        elevated_allowed=True,
    ) == "denied_by_policy"

    assert choose_execution_backend(
        "run_bash",
        visible_names={"run_bash"},
        approved=False,
        sandbox_enabled=True,
        elevated_requested=True,
        elevated_allowed=True,
    ) == "rejected"

    assert choose_execution_backend(
        "run_bash",
        visible_names={"run_bash"},
        approved=True,
        sandbox_enabled=True,
        elevated_requested=False,
        elevated_allowed=True,
    ) == "sandbox"

    assert choose_execution_backend(
        "run_bash",
        visible_names={"run_bash"},
        approved=True,
        sandbox_enabled=True,
        elevated_requested=True,
        elevated_allowed=False,
    ) == "elevation_denied"

    assert choose_execution_backend(
        "run_bash",
        visible_names={"run_bash"},
        approved=True,
        sandbox_enabled=True,
        elevated_requested=True,
        elevated_allowed=True,
    ) == "host"

    assert choose_execution_backend(
        "run_bash",
        visible_names={"run_bash"},
        approved=True,
        sandbox_enabled=False,
        elevated_requested=False,
        elevated_allowed=False,
    ) == "host"

    print("checkpoint F passed")


def main() -> None:
    if "--checkpoint-f" in sys.argv:
        checkpoint_a()
        checkpoint_b()
        checkpoint_c()
        checkpoint_d()
        checkpoint_e()
        checkpoint_f()
        return
    if "--checkpoint-e" in sys.argv:
        checkpoint_a()
        checkpoint_b()
        checkpoint_c()
        checkpoint_d()
        checkpoint_e()
        return
    if "--checkpoint-d" in sys.argv:
        checkpoint_a()
        checkpoint_b()
        checkpoint_c()
        checkpoint_d()
        return
    if "--checkpoint-c" in sys.argv:
        checkpoint_a()
        checkpoint_b()
        checkpoint_c()
        return
    if "--checkpoint-b" in sys.argv:
        checkpoint_a()
        checkpoint_b()
        return
    if "--checkpoint-a" in sys.argv:
        checkpoint_a()
        return
    print(
        "从第一关开始：python -B "
        "exercises/lesson-07-safety/starter.py --checkpoint-a"
    )


if __name__ == "__main__":
    main()
