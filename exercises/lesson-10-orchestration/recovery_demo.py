"""第 10 课：主任务重启后，复用结果并核对未完成的子任务。

在仓库根目录运行：
    python -B exercises/lesson-10-orchestration/recovery_demo.py
    python -B exercises/lesson-10-orchestration/recovery_demo.py --observed unknown
    python -B exercises/lesson-10-orchestration/recovery_demo.py --observed running
    python -B exercises/lesson-10-orchestration/recovery_demo.py --self-check

先看 recover_parent()，再看 prepare() 中的主任务和模拟下游记录。
独立进程分别保存、恢复；下游状态是预设数据，没有真实 Agent 或网络请求。
只验证结果收集，不验证并行调度、工具幂等、实际合并或任务验收。
临时目录在实验结束后自动清理，不修改工作区文件。
"""

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path


def write_checkpoint(path: Path, checkpoint: dict) -> None:
    # 沿用第 4 课的整体替换方式，不导入其会话配置和 Memory 逻辑。
    # ponytail: 单写者、受控退出；并发更新需事务，断电持久性另行验证。
    temporary = path.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(checkpoint, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    temporary.replace(path)


def recover_parent(checkpoint: dict, observed_jobs: dict) -> None:
    """恢复收集进度；只复用和查询，不提交任何新子任务。"""
    for child in checkpoint["children"]:
        if child["status"] == "succeeded":
            if not isinstance(child.get("result"), str):
                raise ValueError(f"{child['id']} 已完成，但缺少结果")
            print(f"{child['id']}：复用已保存结果")
            continue

        if child["status"] not in {"running", "unknown"}:
            raise ValueError(f"不支持的子任务状态：{child['status']}")

        job_id = child["job_id"]
        # 用记录表模拟按原 job_id 查询，不调用模型，不重新启动任务。
        observed = observed_jobs.get(job_id, {"status": "unknown"})
        status = observed["status"]
        if status == "succeeded":
            if not isinstance(observed.get("result"), str):
                raise ValueError(f"{job_id} 显示成功，但缺少可取回的结果")
            child["status"] = "succeeded"
            child["result"] = observed["result"]
            print(f"{child['id']}：查询 {job_id}，取回已完成结果")
        elif status == "running":
            child["status"] = "running"
            print(f"{child['id']}：查询 {job_id}，仍在运行，继续等待")
        elif status == "unknown":
            child["status"] = "unknown"
            print(f"{child['id']}：查询 {job_id}，结果未知，停止自动推进")
        else:
            raise ValueError(f"不支持的下游状态：{status}")

    if not checkpoint["children"]:
        raise ValueError("主任务缺少子任务清单")
    statuses = [child["status"] for child in checkpoint["children"]]
    if "unknown" in statuses:
        checkpoint["next_step"] = "reconcile"
    elif "running" in statuses:
        checkpoint["next_step"] = "wait"
    else:
        checkpoint["next_step"] = "merge_and_validate"
    print(f"主任务下一步：{checkpoint['next_step']}")


def prepare(directory: Path, observed: str) -> None:
    checkpoint = {
        "task_id": "review_1",
        "owner": "main_agent",
        "next_step": "collect_results",
        "children": [
            {"id": "A", "status": "succeeded", "result": "配置检查完成"},
            {"id": "B", "status": "succeeded", "result": "文档检查完成"},
            {"id": "C", "status": "running", "job_id": "job_C"},
        ],
    }
    # 模拟下游是独立系统：主任务旧记录为 running，下游未必仍在运行。
    job = {"status": observed}
    if observed == "succeeded":
        job["result"] = "测试检查完成"
    write_checkpoint(directory / "jobs.json", {"job_C": job})
    write_checkpoint(directory / "parent.json", checkpoint)
    print("进程 1：保存 A、B 的结果，C 记为 running；退出。")


def run_experiment(observed: str, *, show_output: bool) -> None:
    with tempfile.TemporaryDirectory(prefix="agent-orchestration-") as folder:
        directory = Path(folder)

        def run_phase(phase: str) -> None:
            completed = subprocess.run(
                [sys.executable, "-B", str(Path(__file__).resolve()),
                 "--phase", phase, "--directory", folder, "--observed", observed],
                text=True, capture_output=True, timeout=10,
            )
            if completed.returncode:
                raise RuntimeError(completed.stdout + completed.stderr)
            if show_output:
                print(completed.stdout, end="")

        run_phase("prepare")
        before = json.loads((directory / "parent.json").read_text(encoding="utf-8"))
        jobs_before = (directory / "jobs.json").read_bytes()
        run_phase("recover")
        after = json.loads((directory / "parent.json").read_text(encoding="utf-8"))
        expected_step = {
            "succeeded": "merge_and_validate", "running": "wait", "unknown": "reconcile"
        }[observed]
        assert after["children"][:2] == before["children"][:2], "不能丢失 A、B 的成果"
        assert after["children"][2]["job_id"] == "job_C", "必须保留原下游任务编号"
        assert after["children"][2]["status"] == observed
        assert after["next_step"] == expected_step
        assert (directory / "jobs.json").read_bytes() == jobs_before, "不能改写下游记录"
        if observed == "succeeded":
            assert after["children"][2]["result"] == "测试检查完成"
        # 再恢复一次也不改变已经收集的结果。
        if show_output:
            print("再次启动恢复进程，检查重复恢复：")
        run_phase("recover")
        assert json.loads((directory / "parent.json").read_text(encoding="utf-8")) == after
        if show_output:
            print("检查通过：重复恢复不改变结果。临时目录将清理。")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--observed", choices=["succeeded", "running", "unknown"], default="succeeded")
    parser.add_argument("--self-check", action="store_true")
    parser.add_argument("--phase", choices=["prepare", "recover"], help=argparse.SUPPRESS)
    parser.add_argument("--directory", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.phase:
        if args.directory is None:
            parser.error("内部进程需要 --directory")
        if args.phase == "prepare":
            prepare(args.directory, args.observed)
        else:
            print("恢复进程：从磁盘加载主任务，开始恢复。")
            path = args.directory / "parent.json"
            checkpoint = json.loads(path.read_text(encoding="utf-8"))
            jobs = json.loads((args.directory / "jobs.json").read_text(encoding="utf-8"))
            recover_parent(checkpoint, jobs)
            write_checkpoint(path, checkpoint)
    elif args.self_check:
        for state in ("succeeded", "running", "unknown"):
            run_experiment(state, show_output=False)
        print("recovery self-check passed (3 scripted states, separate processes)")
    else:
        run_experiment(args.observed, show_output=True)


if __name__ == "__main__":
    main()
