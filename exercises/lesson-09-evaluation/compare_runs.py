"""Read two saved batches and compare observed results without calling a Model."""

import argparse
import copy
import json
import math
from pathlib import Path

from starter import summarize_results


CONTROLLED_FIELDS = (
    "task_sha256", "grader_sha256", "model", "provider_sha256",
    "environment", "max_model_requests", "request_timeout", "sdk_max_retries",
)
AGENT_FIELDS = ("agent_variant", "runtime_sha256", "agent_prompt")


def batch_metrics(batch: dict) -> dict:
    """核对逐次记录，再计算成绩；不用可疑的总表替代原始记录。"""
    context = batch["comparison_context"]
    for field in CONTROLLED_FIELDS + AGENT_FIELDS:
        if field not in context or context[field] is None or context[field] == "":
            raise ValueError(f"缺少运行条件：{field}")
    count = batch["trial_count"]
    reports = batch["reports"]
    if type(count) is not int or count <= 0 or not isinstance(reports, list) or len(reports) != count:
        raise ValueError("Trial 数量与实际记录不符，或没有可比较的记录")

    ids = set()
    successful = run_errors = duration = tool_calls = 0
    grades = []
    for report in reports:
        trial_id = report["trial_id"]
        if not isinstance(trial_id, str) or not trial_id or trial_id in ids:
            raise ValueError("批次内的 Trial ID 缺失或重复")
        ids.add(trial_id)
        if report["comparison_context"] != context or report["task_id"] != batch["task_id"]:
            raise ValueError("一批报告混入了不同题目或不同运行条件")
        if report["model"] != context["model"]:
            raise ValueError("Model 记录不一致")
        run = report["agent_run"]
        grade = report["grade"]
        if run["status"] not in {"completed", "error"} or grade["status"] not in {"passed", "failed", "error"}:
            raise ValueError("报告状态不完整或无法识别")
        for field in ("duration_ms", "tool_call_count"):
            if type(run[field]) is not int or run[field] < 0:
                raise ValueError(f"运行指标无效：{field}")
        duration += run["duration_ms"]
        tool_calls += run["tool_call_count"]
        grades.append(grade)
        if run["status"] == "error":
            run_errors += 1
        elif grade["status"] == "passed":
            successful += 1

    grade_summary = summarize_results(grades)
    if (
        batch["grade_summary"] != grade_summary
        or batch["successful_trials"] != successful
        or batch["run_error_count"] != run_errors
        or not math.isclose(batch["observed_success_rate"], successful / count)
    ):
        raise ValueError("批次总表与逐次成绩不一致")
    return {
        "variant": context["agent_variant"],
        "successful_trials": successful,
        "trial_count": count,
        "observed_success_rate": successful / count,
        "grading_errors": grade_summary["error"],
        "run_errors": run_errors,
        "mean_duration_ms": duration / count,
        "mean_tool_calls": tool_calls / count,
    }


def compare_batches(baseline: dict, candidate: dict) -> dict:
    try:
        before = batch_metrics(baseline)
        after = batch_metrics(candidate)
        old_context = baseline["comparison_context"]
        new_context = candidate["comparison_context"]
        reasons = []
        if baseline["task_id"] != candidate["task_id"]:
            reasons.append("两批不是同一道 Task")
        for field in CONTROLLED_FIELDS:
            if old_context[field] != new_context[field]:
                reasons.append(f"比较条件不同：{field}")
        if before["trial_count"] != after["trial_count"]:
            reasons.append("本练习要求两边 Trial 数量相同")
        if before["grading_errors"] or after["grading_errors"]:
            reasons.append("仍有评分 error，应修好阅卷器并补齐成绩")
        if (
            old_context["runtime_sha256"] == new_context["runtime_sha256"]
            and old_context["agent_prompt"] == new_context["agent_prompt"]
        ):
            reasons.append("代码和 Prompt 相同；只换标签不能当成两个不同版本")
        result = {"status": "blocked" if reasons else "comparable", "reasons": reasons, "baseline": before, "candidate": after}
        if not reasons:
            result["change"] = {
                "success_rate_percentage_points": round((after["observed_success_rate"] - before["observed_success_rate"]) * 100, 2),
                "mean_duration_ms": round(after["mean_duration_ms"] - before["mean_duration_ms"], 2),
                "mean_tool_calls": round(after["mean_tool_calls"] - before["mean_tool_calls"], 2),
            }
            if before["run_errors"] or after["run_errors"]:
                result["warnings"] = [
                    "存在运行异常，请结合逐次报告的 error_type 判断原因，不能把服务故障直接归因给 Prompt。",
                    "提前失败可能降低平均耗时和调用次数；数值更小不等于完成任务更高效。",
                ]
        return result
    except (KeyError, TypeError, ValueError, AttributeError, OverflowError) as error:
        return {"status": "blocked", "reasons": [f"报告缺少字段或格式有误：{error}"]}


def release_gate(baseline: dict, candidate: dict) -> dict:
    """固定回归题的最小门禁：条件可比，候选的每次运行都完整通过。"""
    comparison = compare_batches(baseline, candidate)
    reasons = list(comparison["reasons"])
    if comparison["status"] == "comparable":
        metrics = comparison["candidate"]
        if metrics["run_errors"]:
            reasons.append(f"候选有 {metrics['run_errors']} 次运行异常，不能放行")
        if metrics["successful_trials"] != metrics["trial_count"]:
            reasons.append(
                f"固定回归题要求全部完整通过，实际为 {metrics['successful_trials']}/{metrics['trial_count']}"
            )
    return {
        "status": "blocked" if reasons else "passed",
        "scope": "所提供报告对应的候选版本和固定 Task",
        "reasons": reasons,
        "comparison": comparison,
    }


def self_check() -> None:
    context = {
        "task_sha256": "task", "grader_sha256": "grader", "model": "scripted-test",
        "provider_sha256": "provider", "environment": {"python": "test"},
        "max_model_requests": 4, "request_timeout": "30", "sdk_max_retries": 0,
        "agent_variant": "baseline", "runtime_sha256": "code", "agent_prompt": "base prompt",
    }
    baseline = {
        "task_id": "test-task", "trial_count": 2, "comparison_context": context,
        "grade_summary": {"total": 2, "passed": 1, "failed": 1, "error": 0},
        "run_error_count": 0, "successful_trials": 1, "observed_success_rate": 0.5,
        "reports": [],
    }
    for number, status in enumerate(("passed", "failed"), start=1):
        baseline["reports"].append({
            "trial_id": f"trial_{number}", "task_id": "test-task", "model": "scripted-test",
            "comparison_context": context,
            "agent_run": {"status": "completed", "duration_ms": 100, "tool_call_count": 2},
            "grade": {"status": status, "reason": "test"},
        })
    candidate = copy.deepcopy(baseline)
    candidate["comparison_context"]["agent_variant"] = "verify-output"
    candidate["comparison_context"]["agent_prompt"] = "verify prompt"
    candidate["reports"][1]["grade"]["status"] = "passed"
    candidate["reports"][1]["agent_run"]["tool_call_count"] = 4
    candidate["grade_summary"] = {"total": 2, "passed": 2, "failed": 0, "error": 0}
    candidate["successful_trials"] = 2
    candidate["observed_success_rate"] = 1.0
    baseline_copy = copy.deepcopy(baseline)
    candidate_copy = copy.deepcopy(candidate)
    result = compare_batches(baseline, candidate)
    assert result["status"] == "comparable"
    assert result["change"]["success_rate_percentage_points"] == 50
    assert result["change"]["mean_tool_calls"] == 1
    assert release_gate(baseline, candidate)["status"] == "passed"
    assert release_gate(candidate, baseline)["status"] == "blocked"
    assert release_gate({}, candidate)["status"] == "blocked"
    assert baseline == baseline_copy and candidate == candidate_copy
    for field in CONTROLLED_FIELDS:
        changed = copy.deepcopy(candidate)
        changed["comparison_context"][field] = "different"
        assert compare_batches(baseline, changed)["status"] == "blocked", field
    relabeled = copy.deepcopy(baseline)
    relabeled["comparison_context"]["agent_variant"] = "only-a-new-label"
    assert compare_batches(baseline, relabeled)["status"] == "blocked"
    assert compare_batches({}, candidate)["status"] == "blocked"
    missing_report = copy.deepcopy(candidate)
    missing_report["reports"].pop()
    assert compare_batches(baseline, missing_report)["status"] == "blocked"
    grading_error = copy.deepcopy(candidate)
    grading_error["reports"][1]["grade"]["status"] = "error"
    grading_error["grade_summary"] = {"total": 2, "passed": 1, "failed": 0, "error": 1}
    grading_error["successful_trials"] = 1
    grading_error["observed_success_rate"] = 0.5
    assert "仍有评分 error" in compare_batches(baseline, grading_error)["reasons"][0]
    assert release_gate(baseline, grading_error)["status"] == "blocked"
    wrong_summary = copy.deepcopy(candidate)
    wrong_summary["successful_trials"] = 999
    assert compare_batches(baseline, wrong_summary)["status"] == "blocked"
    interrupted = copy.deepcopy(candidate)
    interrupted["reports"][1]["agent_run"]["status"] = "error"
    interrupted["run_error_count"] = 1
    interrupted["successful_trials"] = 1
    interrupted["observed_success_rate"] = 0.5
    result = compare_batches(baseline, interrupted)
    assert result["status"] == "comparable"
    assert result["candidate"]["run_errors"] == 1
    assert result["change"]["success_rate_percentage_points"] == 0
    assert len(result["warnings"]) == 2
    gate = release_gate(baseline, interrupted)
    assert gate["status"] == "blocked"
    assert "运行异常" in gate["reasons"][0]
    print("release_gate self-check passed (including file-passed / run-error)")
    print("compare_runs self-check passed (synthetic reports)")


def main() -> None:
    parser = argparse.ArgumentParser(description="只读比较两批已保存成绩，不调用模型、不重新阅卷")
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--candidate", type=Path)
    parser.add_argument("--self-check", action="store_true")
    parser.add_argument("--gate", action="store_true", help="要求候选的固定回归题全部完整通过，失败退出 2")
    args = parser.parse_args()
    if args.self_check:
        if args.baseline or args.candidate:
            parser.error("--self-check 不与报告路径混用")
        self_check()
        return
    if args.baseline is None or args.candidate is None:
        parser.error("需要 --baseline 和 --candidate 两份 batch_report.json")
    try:
        baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
        candidate = json.loads(args.candidate.read_text(encoding="utf-8"))
        result = release_gate(baseline, candidate) if args.gate else compare_batches(baseline, candidate)
    except (OSError, UnicodeError, ValueError) as error:
        result = {"status": "blocked", "reasons": [f"报告无法读取：{error}"]}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    # 门禁通过只验收这些报告对应的 Task；本程序不会执行部署或发布。
    expected_status = "passed" if args.gate else "comparable"
    raise SystemExit(0 if result["status"] == expected_status else 2)


if __name__ == "__main__":
    main()
