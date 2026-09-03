"""Lesson 08 exercise: approval and cwd are not sandbox boundaries."""

import subprocess
import sys
import tempfile
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


def main() -> None:
    if "--checkpoint-a" in sys.argv:
        checkpoint_a()
        return
    print(
        "从第一关开始：python -B "
        "exercises/lesson-08-safety/starter.py --checkpoint-a"
    )


if __name__ == "__main__":
    main()
