"""验证第 9 课正式正文；复用离线自检，只读比较历史成绩，不运行真实模型。"""

from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import re
import subprocess
import sys


def self_check():
    here = Path(__file__).resolve().parent
    root = here.parents[1]
    chapter = root / "chapters/09-Agent评估.md"
    blocks = re.findall(r"```python\n(.*?)\n```", chapter.read_text(encoding="utf-8"), re.S)
    expected = ["False\n", "1/3\n", "拦截\n"]
    assert len(blocks) == len(expected)
    namespace = {}
    for block, output in zip(blocks, expected):
        with redirect_stdout(io.StringIO()) as captured:
            # 只执行仓库的教学片段，不执行模型返回的代码。
            exec(compile(block, str(chapter), "exec"), namespace)
        assert captured.getvalue() == output, captured.getvalue()
    assert namespace["before"] == {"theme": "light", "port": 3000}
    assert namespace["expected"] == {"theme": "dark", "port": 3000}
    gate = namespace["can_release"]
    assert gate([]) is False
    for run in ("completed", "error"):
        for grade in ("passed", "failed", "error"):
            report = {"run": run, "grade": grade}
            assert gate([report]) is (run == "completed" and grade == "passed")
            assert report == {"run": run, "grade": grade}

    exercise = root / "exercises/lesson-09-evaluation"
    for script, flag, marker in [
        ("starter.py", "--checkpoint-b", "checkpoint B passed"),
        ("starter.py", "--check-csv", "CSV grader self-check passed"),
        ("run_trial.py", "--self-check", "budget regression passed: file=passed, run=error, no fifth request"),
        ("compare_runs.py", "--self-check", "compare_runs self-check passed (synthetic reports)"),
    ]:
        result = subprocess.run(
            [sys.executable, "-B", str(exercise / script), flag], cwd=root,
            capture_output=True, text=True, timeout=30, check=True,
        )
        assert marker in result.stdout, result.stdout
        print(marker)

    baseline = exercise / "evidence/baseline.json"
    candidate = exercise / "evidence/candidate.json"
    originals = {path: path.read_bytes() for path in (baseline, candidate)}
    command = [
        sys.executable, "-B", str(exercise / "compare_runs.py"),
        "--baseline", str(baseline), "--candidate", str(candidate),
    ]
    comparison = subprocess.run(command, cwd=root, capture_output=True, text=True, timeout=30, check=True)
    compared = json.loads(comparison.stdout)
    assert compared["status"] == "comparable"
    assert compared["baseline"]["successful_trials"] == 3
    assert compared["candidate"]["successful_trials"] == 0
    assert compared["baseline"]["trial_count"] == compared["candidate"]["trial_count"] == 3
    archived = json.loads(originals[candidate])
    assert archived["grade_summary"] == {"total": 3, "passed": 2, "failed": 1, "error": 0}
    assert archived["comparison_context"]["max_model_requests"] == 4
    assert [report["agent_run"]["error_type"] for report in archived["reports"]] == ["RuntimeError", "RuntimeError", "APIConnectionError"]

    blocked = subprocess.run(command + ["--gate"], cwd=root, capture_output=True, text=True, timeout=30)
    decision = json.loads(blocked.stdout)
    assert blocked.returncode == 2, blocked.stdout
    assert decision["status"] == "blocked"
    assert decision["comparison"]["status"] == "comparable"
    assert decision["reasons"]
    for path, original in originals.items():
        assert path.read_bytes() == original, "不能修改历史成绩来获得通过"
    print("historical reports: baseline=3/3, candidate=0/3, comparable; gate=blocked (expected exit 2)")
    print("lesson 09 passed: grading, isolated trials, interrupted delivery, report comparison, release gate")


if __name__ == "__main__":
    self_check()
