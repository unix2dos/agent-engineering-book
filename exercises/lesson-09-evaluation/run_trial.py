"""Lesson 09 C/D: run independent Workspace Agent trials and collect their grades."""

import argparse
import hashlib
from importlib import metadata
import json
from pathlib import Path
import platform
import runpy
import tempfile
import time
from types import SimpleNamespace
from unittest.mock import patch

from starter import csv_quantity_total, safe_grade_config, safe_grade_csv_total, summarize_results


REPO_ROOT = Path(__file__).resolve().parents[2]
# 复用综合实践的循环、Tool 和 Ledger；参考实现提供现有 Schema 与模型连接。
AGENT = SimpleNamespace(**runpy.run_path(str(
    REPO_ROOT / "exercises/phase-1-capstone/starter.py"
)))
REFERENCE = runpy.run_path(str(REPO_ROOT / "examples/lesson_06_tool_reliability.py"))
TOOLS = [
    tool for tool in REFERENCE["TOOLS"]
    if tool["function"]["name"] in {"read_file", "write_file"}
]
TASK_CONFIGS = {
    "basic": {"theme": "light", "port": 8080},
    "custom-port": {"theme": "light", "port": 3000},
    "keep-debug": {"theme": "light", "port": 8080, "debug": False},
}
INITIAL_CONFIG = json.dumps(TASK_CONFIGS["basic"]) + "\n"
TASK = "读取 config.json，把 theme 改为 dark，其他配置保持不变。文件路径使用 config.json。"
CSV_INPUT = "item,quantity\napple,2\nbanana,3\npear,7\n"
CSV_TASK = (
    "读取 items.csv，将 quantity 列的非负整数全部相加。"
    "把结果写入 summary.json，文件必须是仅包含整数 total_quantity 字段的 JSON 对象。"
    "保留 items.csv 原样，完成后如实回答。"
)
TASK_NAMES = list(TASK_CONFIGS) + ["csv-total"]
AGENT_VARIANTS = {
    "baseline": "",
    "verify-output": "写入后再次读取输出文件，核对原始任务的每条要求，确认结果后再给出最终回答。",
}


def fingerprint(value: object) -> str:
    """给实际代码或配置留下可比较的指纹，不依赖人为起的版本名字。"""
    encoded = json.dumps(value, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


RUNTIME_SHA256 = fingerprint({
    relative: (REPO_ROOT / relative).read_text(encoding="utf-8")
    for relative in (
        "exercises/lesson-09-evaluation/run_trial.py",
        "exercises/phase-1-capstone/starter.py",
        "examples/lesson_06_tool_reliability.py",
    )
})
GRADER_SHA256 = fingerprint(Path(__file__).with_name("starter.py").read_text(encoding="utf-8"))
try:
    SDK_VERSION = metadata.version("openai")
except metadata.PackageNotFoundError:
    SDK_VERSION = "not-installed"


def run_trial(
    client: object, model: str, trial_dir: Path,
    task_name: str = "basic", variant: str = "baseline",
) -> dict:
    """准备独立环境，运行 Agent，最后检查真实产物并保存报告。"""
    if task_name not in TASK_NAMES:
        raise ValueError(f"未知任务：{task_name}")
    if variant not in AGENT_VARIANTS:
        raise ValueError(f"未知 Agent 设置：{variant}")
    # 已存在的目录直接报错，不能覆盖旧答卷或继承旧状态。
    trial_dir.mkdir(parents=True, exist_ok=False)
    workspace = trial_dir / "workspace"
    workspace.mkdir()
    if task_name == "csv-total":
        # CSV 题：原始输入保留在工作区外；结果文件留给 Agent 创建。
        initial_file = trial_dir / "initial.csv"
        initial_file.write_text(CSV_INPUT, encoding="utf-8")
        (workspace / "items.csv").write_bytes(initial_file.read_bytes())
        expected = {"total_quantity": csv_quantity_total(initial_file)}
        output_path = workspace / "summary.json"
        task_text = CSV_TASK
        readable = {"items.csv", "summary.json"}
        writable = {"summary.json"}
    else:
        initial = TASK_CONFIGS[task_name]
        initial_text = json.dumps(initial, ensure_ascii=False) + "\n"
        initial_file = trial_dir / "initial.json"
        initial_file.write_text(initial_text, encoding="utf-8")
        output_path = workspace / "config.json"
        output_path.write_text(initial_text, encoding="utf-8")
        expected = initial.copy()
        expected["theme"] = "dark"
        task_text = TASK
        readable = {"config.json"}
        writable = {"config.json"}
    expected_file = trial_dir / "expected.json"
    expected_file.write_text(json.dumps(expected, ensure_ascii=False) + "\n", encoding="utf-8")
    session_file = trial_dir / "session.jsonl"
    system_prompt = (
        "你是文件任务 Agent。先读取输入，再完成任务，按实际结果回答。"
        "本次允许读取：" + ", ".join(sorted(readable))
        + "；允许写入：" + ", ".join(sorted(writable)) + "。"
        + AGENT_VARIANTS[variant]
    )
    # 运行前记录实际条件；答案和指纹不会发给 Model。
    comparison_context = {
        "task_sha256": fingerprint({
            "instruction": task_text,
            "input": initial_file.read_text(encoding="utf-8"),
            "expected": expected,
            "readable": sorted(readable), "writable": sorted(writable),
        }),
        "grader_sha256": GRADER_SHA256,
        "runtime_sha256": RUNTIME_SHA256,
        "agent_variant": variant,
        "agent_prompt": system_prompt,
        "model": model,
        "provider_sha256": fingerprint(str(getattr(client, "base_url", "scripted"))),
        "environment": {"python": platform.python_version(), "os": platform.system(), "openai_sdk": SDK_VERSION},
        "max_model_requests": AGENT.MAX_MODEL_REQUESTS,
        "request_timeout": str(getattr(client, "timeout", "scripted")),
        "sdk_max_retries": getattr(client, "max_retries", 0),
    }
    AGENT.persist_message(session_file, {
        "role": "system",
        "content": system_prompt,
    })

    tool_call_count = 0

    def execute_tool(tool_call: object) -> str:
        nonlocal tool_call_count
        tool_call_count += 1
        # 广告给 Model 的 Schema 之外，还必须在真正执行时检查可用能力。
        name = tool_call.function.name
        try:
            arguments = json.loads(tool_call.function.arguments)
            if not isinstance(arguments, dict):
                raise ValueError("工具参数必须是 JSON 对象")
            if name == "read_file":
                if arguments.get("path") not in readable:
                    raise ValueError("本题未授权读取这个路径")
                if set(arguments) - {"path", "offset"}:
                    raise ValueError("read_file 参数多余")
                offset = arguments.get("offset", 0)
                if type(offset) is not int or offset < 0:
                    raise ValueError("offset 必须是非负整数")
            elif name == "write_file":
                if arguments.get("path") not in writable:
                    raise ValueError("本题未授权写入这个路径")
                if set(arguments) != {"path", "content"} or not isinstance(arguments["content"], str):
                    raise ValueError("write_file 需要 path 和字符串 content")
            else:
                raise ValueError("本题只开放 read_file 和 write_file")
        except (ValueError, TypeError) as error:
            return json.dumps({"status": "rejected", "reason": str(error)}, ensure_ascii=False)

        print(f"Tool: {name} {arguments['path']}")
        return AGENT.execute_workspace_tool_with_ledger(
            workspace, session_file, tool_call,
            # 只批准上面已验证过的本题文件操作，不依正确答案决定是否允许写入。
            approve=lambda *_: True,
        )

    started = time.perf_counter()
    final_answer = None
    run_status = "completed"
    error_type = None
    try:
        final_answer = AGENT.run_agent_loop(
            client=client, model=model, tools=TOOLS, user_text=task_text,
            execute_tool=execute_tool, session_file=session_file,
        )
    except Exception as error:
        run_status = "error"
        # 不把可能含凭据的 Provider 异常全文写入报告。
        error_type = type(error).__name__

    # 两类题使用不同阅卷器，运行和报告结构共用。
    if task_name == "csv-total":
        grade = safe_grade_csv_total(workspace, initial_file)
        grader_name = "grade_csv_total"
    else:
        grade = safe_grade_config(output_path, expected)
        grader_name = "grade_config"
    # 即使运行途中出错，也保存当时文件的评分；运行状态和文件成绩分别保留。
    report = {
        "task_id": "csv-total" if task_name == "csv-total" else "config-theme-dark/" + task_name,
        "trial_id": trial_dir.parent.name + "/" + trial_dir.name,
        "model": model,
        "task": task_text,
        "workspace": str(workspace.resolve()),
        "initial_file": str(initial_file.resolve()),
        "output_path": str(output_path.resolve()),
        "expected_file": str(expected_file.resolve()),
        "grader": grader_name,
        "comparison_context": comparison_context,
        "session_file": str(session_file.resolve()),
        "agent_run": {
            "status": run_status,
            "error_type": error_type,
            "duration_ms": round((time.perf_counter() - started) * 1000),
            "tool_call_count": tool_call_count,
            "final_answer": final_answer,
        },
        "grade": grade,
    }
    if task_name in TASK_CONFIGS:
        # 保留此前配置题报告的字段，原来的补评入口仍可使用。
        report["config_path"] = str(output_path.resolve())
    (trial_dir / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
    )
    return report


def run_batch(
    client: object,
    model: str,
    batch_dir: Path,
    count: int,
    session_header: str | None = None,
    task_name: str = "basic",
    variant: str = "baseline",
) -> dict:
    """同一道题独立运行多次；复用原成绩，分别统计产物和完整运行。"""
    if type(count) is not int or not 1 <= count <= 10:
        raise ValueError("Trial 数量必须是 1～10 的整数")
    if task_name not in TASK_NAMES:
        raise ValueError(f"未知任务：{task_name}")
    if variant not in AGENT_VARIANTS:
        raise ValueError(f"未知 Agent 设置：{variant}")
    batch_dir.mkdir(parents=True, exist_ok=False)
    reports = []
    successful_trials = 0
    run_errors = 0
    for number in range(1, count + 1):
        trial_dir = batch_dir / f"trial_{number}"
        trial_client = client
        if session_header:
            # 同一 Trial 的请求共享 ID，不同 Trial 使用新的会话 ID。
            trial_client = client.with_options(default_headers={
                "User-Agent": "agent-engineering-book/0.1",
                session_header: batch_dir.parent.name + "-" + trial_dir.name,
            })
        print(f"\nTrial {number}/{count}: {trial_dir}", flush=True)
        print(f"任务: {task_name}", flush=True)
        print(f"Agent 设置: {variant}", flush=True)
        initial_display = CSV_INPUT.strip() if task_name == "csv-total" else json.dumps(TASK_CONFIGS[task_name], ensure_ascii=False)
        print(f"初始输入: {initial_display}", flush=True)
        report = run_trial(trial_client, model, trial_dir, task_name, variant)
        reports.append(report)
        if report["agent_run"]["status"] == "error":
            run_errors += 1
        elif report["grade"]["status"] == "passed":
            successful_trials += 1
        print(f"Agent 运行: {report['agent_run']['status']}")
        if report["agent_run"]["error_type"]:
            print(f"运行异常类型: {report['agent_run']['error_type']}")
        print(f"Agent 回答: {report['agent_run']['final_answer']}")
        print(f"阅卷器: {report['grader']}")
        print(f"阅卷结果: {report['grade']['status']} — {report['grade']['reason']}")

    grades = []
    for report in reports:
        grades.append(report["grade"])
    batch = {
        "task_id": reports[0]["task_id"],
        "comparison_context": reports[0]["comparison_context"],
        "trial_count": count,
        "grade_summary": summarize_results(grades),
        "run_error_count": run_errors,
        "successful_trials": successful_trials,
        "observed_success_rate": successful_trials / count,
        "reports": reports,
    }
    (batch_dir / "batch_report.json").write_text(
        json.dumps(batch, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
    )
    return batch


def self_check() -> None:
    """Scripted Model 只验证连接；真实 Loop、文件 Tool、Ledger 与评分照常执行。"""
    with tempfile.TemporaryDirectory() as folder:
        trial_dir = Path(folder) / "success"
        client = AGENT.FakeClient([
            AGENT.fake_response("tool_calls", tool_calls=[
                AGENT.fake_tool_call("read_1", "read_file", {"path": "config.json"}),
            ]),
            AGENT.fake_response("tool_calls", tool_calls=[
                AGENT.fake_tool_call("write_1", "write_file", {
                    "path": "config.json", "content": '{"port":8080,"theme":"dark"}',
                }),
            ]),
            AGENT.fake_response("stop", content="已修改主题，端口保持不变。"),
        ])
        report = run_trial(client, "scripted-test", trial_dir)
        assert report["grade"]["status"] == "passed"
        assert report["agent_run"]["status"] == "completed"
        assert (trial_dir / "initial.json").read_text() == INITIAL_CONFIG
        assert len(client.completions.requests) == 3
        assert "light" in client.completions.requests[1]["messages"][-1]["content"]
        entries = AGENT.load_entries(trial_dir / "session.jsonl")
        assert not AGENT.pending_tool_calls(entries)
        assert len(AGENT.latest_execution_states(entries)) == 1
        assert json.loads((trial_dir / "report.json").read_text()) == report
        try:
            run_trial(AGENT.FakeClient([]), "scripted-test", trial_dir)
        except FileExistsError:
            pass
        else:
            raise AssertionError("不能覆盖旧 Trial")
        assert json.loads((trial_dir / "report.json").read_text()) == report

        # Model 只说修改成功却不调用工具，评分应失败；它也不能继承上一份产物。
        no_action = AGENT.FakeClient([AGENT.fake_response("stop", content="修改完成。")])
        report = run_trial(no_action, "scripted-test", Path(folder) / "no-action")
        assert report["agent_run"]["status"] == "completed"
        assert report["grade"]["status"] == "failed"
        assert Path(report["config_path"]).read_text() == INITIAL_CONFIG

        # 文件修改成功，但缺少最后的 Model 回答：产物通过，完整运行仍是 error。
        interrupted_after_write = AGENT.FakeClient([
            AGENT.fake_response("tool_calls", tool_calls=[
                AGENT.fake_tool_call("write_2", "write_file", {
                    "path": "config.json", "content": '{"theme":"dark","port":8080}',
                }),
            ]),
        ])
        report = run_trial(interrupted_after_write, "scripted-test", Path(folder) / "after-write")
        assert report["agent_run"]["status"] == "error"
        assert report["agent_run"]["final_answer"] is None
        assert report["grade"]["status"] == "passed"

        # 即使 Model 申请隐藏的 Shell 或外部路径，也不能接到真实执行器。
        denied = AGENT.FakeClient([
            AGENT.fake_response("tool_calls", tool_calls=[
                AGENT.fake_tool_call("deny_1", "run_bash", {"path": "config.json"}),
                AGENT.fake_tool_call("deny_2", "write_file", {"path": "../outside.txt", "content": "x"}),
            ]),
            AGENT.fake_response("stop", content="操作被拒绝。"),
        ])
        report = run_trial(denied, "scripted-test", Path(folder) / "denied")
        assert report["grade"]["status"] == "failed"
        assert not (Path(folder) / "denied/outside.txt").exists()
        receipts = denied.completions.requests[1]["messages"][-2:]
        assert all(json.loads(message["content"])["status"] == "rejected" for message in receipts)

        # 超过剧本响应数量会中断运行；仍应保留报告，不把它冒充评分异常。
        report = run_trial(AGENT.FakeClient([]), "scripted-test", Path(folder) / "interrupted")
        assert report["agent_run"]["status"] == "error"
        assert report["grade"]["status"] == "failed"

        # 第一份只说完成；第二份写好后中断；第三份照常完成，且有独立环境。
        batch_client = AGENT.FakeClient([
            AGENT.fake_response("stop", content="修改完成。"),
            AGENT.fake_response("tool_calls", tool_calls=[AGENT.fake_tool_call(
                "write_batch_2", "write_file",
                {"path": "config.json", "content": '{"theme":"dark","port":8080}'},
            )]),
            AGENT.fake_response("length", content="中途截断"),
            AGENT.fake_response("tool_calls", tool_calls=[AGENT.fake_tool_call(
                "write_batch_3", "write_file",
                {"path": "config.json", "content": '{"port":8080,"theme":"dark"}'},
            )]),
            AGENT.fake_response("stop", content="主题修改完成。"),
        ])
        # 让测试替身支持 SDK 的选项接口，同时记录每个 Trial 使用的会话头。
        headers_seen = []

        def copy_client_options(**options):
            headers_seen.append(options["default_headers"])
            return batch_client

        batch_client.with_options = copy_client_options
        batch_dir = Path(folder) / "batch"
        batch = run_batch(batch_client, "scripted-test", batch_dir, 3, "test-session")
        assert batch["grade_summary"] == {"total": 3, "passed": 2, "failed": 1, "error": 0}
        assert batch["run_error_count"] == 1
        assert batch["successful_trials"] == 1
        assert batch["observed_success_rate"] == 1 / 3
        assert json.loads((batch_dir / "batch_report.json").read_text()) == batch
        assert len({headers["test-session"] for headers in headers_seen}) == 3
        for request_index in (0, 1, 3):
            assert len(batch_client.completions.requests[request_index]["messages"]) == 2
        for report in batch["reports"]:
            assert (Path(report["config_path"]).parents[1] / "initial.json").read_text() == INITIAL_CONFIG
        assert len({report["session_file"] for report in batch["reports"]}) == 3

        # 聚合必须保留原来的评分 error，不在汇总时偷偷补评成其他成绩。
        with patch(__name__ + ".safe_grade_config", return_value={"status": "error", "reason": "评分故障"}) as grading:
            batch = run_batch(
                AGENT.FakeClient([AGENT.fake_response("stop", content="结束。")]),
                "scripted-test", Path(folder) / "grading-error", 1,
            )
        assert grading.call_count == 1
        assert batch["grade_summary"] == {"total": 1, "passed": 0, "failed": 0, "error": 1}
        assert batch["successful_trials"] == 0
        assert batch["run_error_count"] == 0
        for invalid_count in (0, -1, 11, True):
            try:
                run_batch(AGENT.FakeClient([]), "scripted-test", Path(folder) / "invalid", invalid_count)
            except ValueError:
                pass
            else:
                raise AssertionError("非法数量必须在建目录和请求 Model 前拒绝")
        assert not (Path(folder) / "invalid").exists()

        # 对新题沿用 basic 答案会误改端口或丢字段，必须被实际阅卷发现。
        variants = [
            ("custom-port", '{"theme":"dark","port":3000}', "passed"),
            ("custom-port", '{"theme":"dark","port":8080}', "failed"),
            ("keep-debug", '{"theme":"dark","port":8080,"debug":false}', "passed"),
            ("keep-debug", '{"theme":"dark","port":8080}', "failed"),
        ]
        for number, (task_name, answer, expected_status) in enumerate(variants, start=1):
            client = AGENT.FakeClient([
                AGENT.fake_response("tool_calls", tool_calls=[AGENT.fake_tool_call(
                    "read_variant", "read_file", {"path": "config.json"},
                )]),
                AGENT.fake_response("tool_calls", tool_calls=[AGENT.fake_tool_call(
                    "write_variant", "write_file", {"path": "config.json", "content": answer},
                )]),
                AGENT.fake_response("stop", content="修改完成。"),
            ])
            batch = run_batch(client, "scripted-test", Path(folder) / f"variant-{number}", 1, task_name=task_name)
            report = batch["reports"][0]
            assert report["task_id"] == "config-theme-dark/" + task_name
            assert report["grade"]["status"] == expected_status
            observed_read = json.loads(client.completions.requests[1]["messages"][-1]["content"])
            assert json.loads(observed_read["content"]) == TASK_CONFIGS[task_name]
            assert safe_grade_config(
                Path(report["config_path"]), json.loads(Path(report["expected_file"]).read_text()),
            ) == report["grade"]
            assert TASK_CONFIGS[task_name]["theme"] == "light", "不能把题目的原配置改成答案"
        try:
            run_batch(AGENT.FakeClient([]), "scripted-test", Path(folder) / "unknown-task", 1, task_name="missing")
        except ValueError:
            pass
        else:
            raise AssertionError("未知题目必须在运行前拒绝")
        assert not (Path(folder) / "unknown-task").exists()

        csv_cases = [
            (CSV_INPUT, '{"total_quantity":12}', "passed"),
            ("item,quantity\npen,10\nbook,20\n", '{"total_quantity":30}', "passed"),
            ("item,quantity\npen,10\nbook,20\n", '{"total_quantity":12}', "failed"),
        ]
        for number, (csv_text, submission, expected_status) in enumerate(csv_cases, start=1):
            client = AGENT.FakeClient([
                AGENT.fake_response("tool_calls", tool_calls=[
                    AGENT.fake_tool_call("csv_read", "read_file", {"path": "items.csv"}),
                    AGENT.fake_tool_call("csv_forbidden_write", "write_file", {"path": "items.csv", "content": "changed"}),
                    AGENT.fake_tool_call("csv_forbidden_read", "read_file", {"path": "../expected.json"}),
                ]),
                AGENT.fake_response("tool_calls", tool_calls=[
                    AGENT.fake_tool_call("csv_output", "write_file", {"path": "summary.json", "content": submission}),
                ]),
                AGENT.fake_response("stop", content="汇总完成。"),
            ])
            with patch(__name__ + ".CSV_INPUT", csv_text):
                batch = run_batch(client, "scripted-test", Path(folder) / f"csv-{number}", 1, task_name="csv-total")
            report = batch["reports"][0]
            assert report["grade"]["status"] == expected_status
            assert report["grader"] == "grade_csv_total"
            assert report["task_id"] == "csv-total"
            assert report["task"] == CSV_TASK
            assert "config_path" not in report
            assert Path(report["output_path"]).read_text() == submission
            assert Path(report["initial_file"]).read_text() == csv_text
            assert (Path(report["workspace"]) / "items.csv").read_text() == csv_text
            receipts = client.completions.requests[1]["messages"][-3:]
            assert json.loads(receipts[0]["content"])["content"] == csv_text
            assert all(json.loads(receipt["content"])["status"] == "rejected" for receipt in receipts[1:])
            assert safe_grade_csv_total(Path(report["workspace"]), Path(report["initial_file"])) == report["grade"]

        # 两个版本只改变实际送给 Model 的 Prompt，其他比较条件保持一致。
        from compare_runs import compare_batches
        variant_reports = []
        for variant in AGENT_VARIANTS:
            client = AGENT.FakeClient([AGENT.fake_response("stop", content="尚未完成。")])
            batch = run_batch(client, "scripted-test", Path(folder) / variant, 1, variant=variant)
            context = batch["comparison_context"]
            assert client.completions.requests[0]["messages"][0]["content"] == context["agent_prompt"]
            assert batch["reports"][0]["agent_run"]["tool_call_count"] == 0
            variant_reports.append(batch)
        comparison = compare_batches(variant_reports[0], variant_reports[1])
        assert comparison["status"] == "comparable", comparison
        assert comparison["change"]["success_rate_percentage_points"] == 0

        # 固化实测中“核对用完四次请求，文件正确却没有 Final”的失败路径。
        actions = [
            ("read_file", {"path": "items.csv"}),
            ("write_file", {"path": "summary.json", "content": '{"total_quantity":12}'}),
            ("read_file", {"path": "summary.json"}),
            ("read_file", {"path": "items.csv"}),
        ]
        responses = []
        for number, (name, arguments) in enumerate(actions, start=1):
            responses.append(AGENT.fake_response("tool_calls", tool_calls=[
                AGENT.fake_tool_call(f"budget_{number}", name, arguments),
            ]))
        client = AGENT.FakeClient(responses)
        report = run_trial(client, "scripted-test", Path(folder) / "budget-exhausted", "csv-total", "verify-output")
        assert report["agent_run"]["status"] == "error"
        assert report["agent_run"]["error_type"] == "RuntimeError"
        assert report["agent_run"]["final_answer"] is None
        assert report["grade"]["status"] == "passed"
        assert len(client.completions.requests) == 4
        assert report["agent_run"]["tool_call_count"] == 4
        print("budget regression passed: file=passed, run=error, no fifth request")
    print("run_trial self-check passed (scripted Model)")


def main() -> None:
    parser = argparse.ArgumentParser(description="让现有 Workspace Agent 做一次题，再验收文件")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--self-check", action="store_true", help="不联网，检查完整连接")
    mode.add_argument("--live", action="store_true", help="用已配置的真实 Model 运行一次")
    parser.add_argument("--session-header", help="Provider 要求的会话 ID 请求头名称；默认不发送")
    parser.add_argument("--trials", type=int, default=1, help="独立运行次数，默认 1，最多 10")
    parser.add_argument("--task", choices=TASK_NAMES, default="basic", help="选择配置题或 csv-total，默认 basic")
    parser.add_argument("--variant", choices=tuple(AGENT_VARIANTS), default="baseline", help="选择真实提示词设置，默认 baseline")
    args = parser.parse_args()
    if not 1 <= args.trials <= 10:
        parser.error("--trials 必须为 1～10")
    if args.self_check:
        self_check()
        return

    client, model = REFERENCE["make_client"]()
    client = client.with_options(
        timeout=30.0, max_retries=0,
        default_headers={"User-Agent": "agent-engineering-book/0.1"},
    )
    batch_dir = Path(tempfile.mkdtemp(prefix="agent-eval-")) / "batch"
    print(f"本批目录: {batch_dir}", flush=True)
    try:
        batch = run_batch(client, model, batch_dir, args.trials, args.session_header, args.task, args.variant)
    finally:
        client.close()
    summary = batch["grade_summary"]
    print(f"\n文件成绩: passed={summary['passed']} failed={summary['failed']} error={summary['error']}")
    print(f"运行异常: {batch['run_error_count']}")
    print(f"完整运行成功: {batch['successful_trials']}/{batch['trial_count']}")
    print(f"本次观察成功率: {batch['observed_success_rate']:.1%}")
    print(f"完整报告: {batch_dir / 'batch_report.json'}")
    if batch["run_error_count"] or summary["error"]:
        raise SystemExit(2)
    raise SystemExit(0 if batch["successful_trials"] == batch["trial_count"] else 1)


if __name__ == "__main__":
    main()
