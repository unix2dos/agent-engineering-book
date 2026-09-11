"""验证第 10 课正式正文：复用离线工作流、交接与跨进程恢复检查。"""

from contextlib import redirect_stdout
import io
from pathlib import Path
import re
import subprocess
import sys


def self_check():
    here = Path(__file__).resolve().parent
    root = here.parents[1]
    chapter = root / "chapters/10-Agent编排.md"
    blocks = re.findall(r"```python\n(.*?)\n```", chapter.read_text(encoding="utf-8"), re.S)
    expected = [
        "needs_repair\n",
        "reader 获准请求，剩余 1\neditor 获准请求，剩余 0\n停止：预算用完\n",
        "reconcile\nmerge_and_validate\n",
    ]
    assert len(blocks) == len(expected)
    namespace = {}
    for block, output in zip(blocks, expected):
        with redirect_stdout(io.StringIO()) as captured:
            # 只执行仓库教学代码，不接受模型生成的代码。
            exec(compile(block, str(chapter), "exec"), namespace)
        assert captured.getvalue() == output, captured.getvalue()
    assert namespace["state"]["remaining_calls"] == 0

    choose = namespace["choose_next_step"]
    for statuses, next_step in [
        (["succeeded"], "merge_and_validate"),
        (["succeeded", "running"], "wait"),
        (["running", "unknown"], "reconcile"),
        (["unknown", "running"], "reconcile"),
    ]:
        original = list(statuses)
        assert choose(statuses) == next_step
        assert statuses == original
    for invalid in ([], ["failed"], ["succeeded", "cancelled"]):
        try:
            choose(invalid)
        except ValueError:
            pass
        else:
            raise AssertionError("空清单或未支持状态不能进入合并验收")

    exercise = root / "exercises/lesson-10-orchestration"
    for script, marker in [
        ("workflow_demo.py", "workflow self-check passed (real file tools and grader, scripted model)"),
        ("handoff_demo.py", "handoff self-check passed (permissions, shared budget, scripted requests)"),
        ("recovery_demo.py", "recovery self-check passed (3 scripted states, separate processes)"),
    ]:
        result = subprocess.run(
            [sys.executable, "-B", str(exercise / script), "--self-check"], cwd=root,
            capture_output=True, text=True, timeout=30, check=True,
        )
        assert marker in result.stdout, result.stdout
        print(marker)
    print("lesson 10 passed: workflow repair, stopping rules, shared budget, trusted approval, recovery decisions")


if __name__ == "__main__":
    self_check()
