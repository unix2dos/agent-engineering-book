"""运行全书现有离线检查；不调用真实模型，不修改历史报告。"""

from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    checks = [(f"practice/lesson-{number:02}/check.py",) for number in range(3, 11)]
    checks += [
        ("practice/workspace-agent/agent.py", flag)
        for flag in ("--self-check", "--checkpoint-2", "--checkpoint-3", "--checkpoint-4", "--checkpoint-5")
    ]
    checks += [
        ("practice/lesson-03/demo.py", "--self-check"),
        ("practice/lesson-03/multiply.py", "--self-check"),
        ("practice/lesson-03/directory/check.py",),
        ("practice/lesson-03/directory/run.py", "--self-check"),
        ("practice/lesson-04/demo.py",),
        ("practice/lesson-05/demo.py",),
        ("practice/lesson-06/demo.py",),
        ("practice/optional/sqlite/demo.py", "--checkpoint-d"),
    ]
    for script, *args in checks:
        print(f"检查：{script} {' '.join(args)}", flush=True)
        subprocess.run([sys.executable, "-B", str(ROOT / script), *args], cwd=ROOT, check=True, timeout=60)
    print(f"{len(checks)} 组离线检查通过；第 7 课包含本机 macOS 沙盒对照。")


if __name__ == "__main__":
    main()
