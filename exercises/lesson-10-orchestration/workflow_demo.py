"""第 10 课综合实践：修改、程序验收、有限次修复、保存证据。

python -B exercises/lesson-10-orchestration/workflow_demo.py
python -B exercises/lesson-10-orchestration/workflow_demo.py --scenario always-wrong
python -B exercises/lesson-10-orchestration/workflow_demo.py --model-budget 5
python -B exercises/lesson-10-orchestration/workflow_demo.py --self-check
python -B exercises/lesson-10-orchestration/workflow_demo.py --live --max-attempts 2 --model-budget 6

默认模型回复是固定剧本；--live 才使用环境变量中的真实模型，需要 API Key 并可能产生费用。
复用综合实践的 Loop、文件工具、Ledger，以及第 9 课评分器；只修改临时工作区的 config.json。
不执行生成的代码。真实请求设置 30 秒超时、SDK 自动重试为 0。
默认保留运行目录供检查；自检使用的临时目录自动清理。
本例不实现自动重启续跑、后台调度或进程级 Sandbox。
"""

import argparse
import contextlib
import hashlib
import io
import json
from pathlib import Path
import runpy
import tempfile
import time
from types import SimpleNamespace
from urllib.parse import urlsplit
from unittest.mock import patch

from recovery_demo import write_checkpoint


ROOT = Path(__file__).resolve().parents[2]
AGENT = SimpleNamespace(**runpy.run_path(str(ROOT / "exercises/phase-1-capstone/starter.py")))
GRADER = SimpleNamespace(**runpy.run_path(str(ROOT / "exercises/lesson-09-evaluation/starter.py")))
REFERENCE = runpy.run_path(str(ROOT / "examples/lesson_06_tool_reliability.py"))
TOOLS = [tool for tool in REFERENCE["TOOLS"] if tool["function"]["name"] in {"read_file", "write_file"}]
INITIAL = {"theme": "light", "port": 3000}
TASK = "读取 config.json，把 theme 改成 dark，其他配置保持不变。"


class ModelBudgetExhausted(RuntimeError):
    """用于区分预算停止与其他运行异常。"""


def run_workflow(client, output: Path, max_attempts: int = 3, model_budget: int = 9,
                 *, model: str = "scripted-workflow", live: bool = False) -> dict:
    """重点读本函数末尾的循环：Agent 回答后，程序始终自行验收。"""
    if type(max_attempts) is not int or not 1 <= max_attempts <= 3:
        raise ValueError("总修改轮数必须为 1～3，包括首次修改")
    if type(model_budget) is not int or not 1 <= model_budget <= 30:
        raise ValueError("模型请求总预算必须为 1～30")
    if not isinstance(model, str) or not model.strip():
        raise ValueError("模型名称不能为空")
    output.mkdir(parents=True, exist_ok=False)  # 不覆盖旧实验。
    workspace = output / "workspace"
    workspace.mkdir()
    config = workspace / "config.json"
    config.write_text(json.dumps(INITIAL) + "\n", encoding="utf-8")
    expected = dict(INITIAL, theme="dark")
    # 原始条件、标准答案和所有报告放在工具不可访问的位置。
    write_checkpoint(output / "initial.json", INITIAL)
    write_checkpoint(output / "expected.json", expected)
    session = output / "session.jsonl"
    checkpoint = output / "checkpoint.json"
    state = {
        "phase": "ready", "mode": "live" if live else "scripted", "model": model,
        "provider_host": urlsplit(str(getattr(client, "base_url", ""))).hostname,
        "sdk_max_retries": getattr(client, "max_retries", 0),
        "request_timeout": str(getattr(client, "timeout", "scripted")),
        "attempt": 0,
        "max_attempts": max_attempts, "model_budget": model_budget,
        "remaining_calls": model_budget, "attempts": [],
        "source_sha256": {
            str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in (Path(__file__).resolve(), ROOT / "exercises/phase-1-capstone/starter.py",
                         ROOT / "exercises/lesson-09-evaluation/starter.py")
        },
    }
    write_checkpoint(checkpoint, state)
    AGENT.persist_message(session, {"role": "system", "content": "只允许读写 config.json；根据真实工具结果回答。"})

    def request(**kwargs):
        if state["remaining_calls"] == 0:
            raise ModelBudgetExhausted("共享模型请求预算已用完")
        state["remaining_calls"] -= 1
        # 先保存再发起请求；保存失败则不调用模型，失败请求也消耗额度。
        # ponytail: 单写者整体替换；不宣称并发、断电或分布式事务保证。
        write_checkpoint(checkpoint, state)
        return client.chat.completions.create(**kwargs)

    bounded_client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=request)))

    def execute_tool(call):
        name = call.function.name
        try:
            args = json.loads(call.function.arguments)
            if not isinstance(args, dict) or args.get("path") != "config.json":
                raise ValueError("只允许访问 config.json")
            if name == "read_file":
                offset = args.get("offset", 0)
                if set(args) - {"path", "offset"} or type(offset) is not int or offset < 0:
                    raise ValueError("读取参数不合法")
            elif name == "write_file":
                if set(args) != {"path", "content"} or not isinstance(args["content"], str):
                    raise ValueError("写入参数不合法")
            else:
                raise ValueError("只开放读取和写入工具")
        except (ValueError, TypeError) as error:
            return json.dumps({"status": "rejected", "reason": str(error)}, ensure_ascii=False)
        print(f"  Tool: {name} config.json")
        return AGENT.execute_workspace_tool_with_ledger(
            workspace, session, call, approve=lambda *_: True,
        )

    instruction = TASK
    for attempt in range(1, max_attempts + 1):
        state.update(phase="modifying", attempt=attempt)
        write_checkpoint(checkpoint, state)
        print(f"第 {attempt} 轮修改（总上限 {max_attempts}），剩余请求 {state['remaining_calls']}")
        run_status, answer, error_type = "completed", None, None
        started = time.perf_counter()
        try:
            answer = AGENT.run_agent_loop(
                client=bounded_client, model=model, tools=TOOLS,
                user_text=instruction, execute_tool=execute_tool, session_file=session,
            )
        except ModelBudgetExhausted:
            run_status = "model_budget_exhausted"
        except Exception as error:
            run_status, error_type = "run_error", type(error).__name__

        state["phase"] = "verifying"
        write_checkpoint(checkpoint, state)
        # 每轮保留自己的产物，下一轮不覆盖前一轮证据。
        snapshot = output / f"attempt_{attempt:02d}_config.json"
        snapshot.write_bytes(config.read_bytes())
        grade = GRADER.safe_grade_config(snapshot, expected)
        record = {
            "attempt": attempt, "agent_run": run_status, "answer": answer,
            "error_type": error_type, "grade": grade, "artifact": snapshot.name,
            "duration_ms": round((time.perf_counter() - started) * 1000),
            "remaining_calls": state["remaining_calls"],
        }
        state["attempts"].append(record)
        write_checkpoint(output / f"attempt_{attempt:02d}_report.json", record)
        print(f"  程序验收：{grade['status']} — {grade['reason']}")

        if run_status != "completed":
            state["phase"] = run_status
        elif grade["status"] == "error":
            state["phase"] = "grader_error"
        elif grade["status"] == "passed":
            state["phase"] = "completed"
        elif attempt == max_attempts:
            state["phase"] = "attempt_limit"
        elif state["remaining_calls"] == 0:
            state["phase"] = "model_budget_exhausted"
        else:
            state["phase"] = "needs_repair"
        write_checkpoint(checkpoint, state)
        if state["phase"] != "needs_repair":
            break
        instruction = (
            "程序验收未通过：" + grade["reason"] + "。请修复 config.json。"
            "原始配置是 " + json.dumps(INITIAL, ensure_ascii=False) + "。" + TASK
        )

    write_checkpoint(output / "report.json", state)
    print("工作流结果：", state["phase"])
    return state


def scripted_client(scenario: str):
    responses = []
    for attempt in range(1, 4):
        port = 3000 if scenario == "repair" and attempt > 1 else 8080
        responses.extend([
            AGENT.fake_response("tool_calls", tool_calls=[AGENT.fake_tool_call(
                f"read_{attempt}", "read_file", {"path": "config.json"},
            )]),
            AGENT.fake_response("tool_calls", tool_calls=[AGENT.fake_tool_call(
                f"write_{attempt}", "write_file",
                {"path": "config.json", "content": json.dumps({"theme": "dark", "port": port})},
            )]),
            AGENT.fake_response("stop", content="已修改主题。"),
        ])
    return AGENT.FakeClient(responses)


def self_check() -> None:
    with tempfile.TemporaryDirectory() as folder, contextlib.redirect_stdout(io.StringIO()):
        root = Path(folder)
        client = scripted_client("repair")
        report = run_workflow(client, root / "repair")
        assert report["phase"] == "completed"
        assert [r["grade"]["status"] for r in report["attempts"]] == ["failed", "passed"]
        assert len(client.completions.requests) == 6 and report["remaining_calls"] == 3
        assert report["mode"] == "scripted" and report["model"] == "scripted-workflow"
        feedback = client.completions.requests[3]["messages"][-1]["content"]
        assert "程序验收未通过" in feedback and "3000" in feedback
        assert json.loads((root / "repair/attempt_01_config.json").read_text())["port"] == 8080
        assert json.loads((root / "repair/attempt_02_config.json").read_text())["port"] == 3000
        entries = AGENT.load_entries(root / "repair/session.jsonl")
        assert not AGENT.pending_tool_calls(entries)
        assert len(AGENT.latest_execution_states(entries)) == 2
        assert json.loads((root / "repair/report.json").read_text()) == report
        named_client = scripted_client("repair")
        named = run_workflow(named_client, root / "named", model="configured-model")
        assert named["model"] == "configured-model"
        assert all(request["model"] == "configured-model" for request in named_client.completions.requests)

        wrong = run_workflow(scripted_client("always-wrong"), root / "wrong")
        assert wrong["phase"] == "attempt_limit" and len(wrong["attempts"]) == 3
        limited = run_workflow(scripted_client("always-wrong"), root / "limit", max_attempts=2)
        assert limited["phase"] == "attempt_limit" and len(limited["attempts"]) == 2
        budget_client = scripted_client("repair")
        exhausted = run_workflow(budget_client, root / "budget", model_budget=5)
        assert exhausted["phase"] == "model_budget_exhausted"
        assert exhausted["attempts"][-1]["grade"]["status"] == "passed"
        assert exhausted["attempts"][-1]["agent_run"] != "completed"
        assert len(budget_client.completions.requests) == 5

        with patch.object(GRADER, "safe_grade_config", return_value={"status": "error", "reason": "模拟评分失败"}):
            failed_grader = run_workflow(scripted_client("repair"), root / "grader")
        assert failed_grader["phase"] == "grader_error" and len(failed_grader["attempts"]) == 1
        silent = AGENT.FakeClient([AGENT.fake_response("stop", content="已完成")])
        no_action = run_workflow(silent, root / "silent", max_attempts=1)
        assert no_action["phase"] == "attempt_limit"
        interrupted = run_workflow(AGENT.FakeClient([]), root / "interrupted")
        assert interrupted["phase"] == "run_error" and len(interrupted["attempts"]) == 1

        # 固化实测路径：文件已写好，等待最后回答时超时，不能重跑写入。
        timeout_client = AGENT.FakeClient([
            AGENT.fake_response("tool_calls", tool_calls=[AGENT.fake_tool_call(
                "timeout_write", "write_file",
                {"path": "config.json", "content": json.dumps(dict(INITIAL, theme="dark"))},
            )]),
        ])
        create = timeout_client.completions.create

        def timeout_after_write(**request):
            if timeout_client.completions.requests:
                raise TimeoutError("模拟最终回答超时")
            return create(**request)

        timeout_client.completions.create = timeout_after_write
        timed_out = run_workflow(timeout_client, root / "timeout", model_budget=6)
        assert timed_out["phase"] == "run_error" and len(timed_out["attempts"]) == 1
        assert timed_out["attempts"][0]["grade"]["status"] == "passed"
        assert timed_out["attempts"][0]["error_type"] == "TimeoutError"
        assert timed_out["remaining_calls"] == 4
        states = AGENT.latest_execution_states(AGENT.load_entries(root / "timeout/session.jsonl"))
        assert len(states) == 1 and next(iter(states.values()))["status"] == "succeeded"

        denied = AGENT.FakeClient([
            AGENT.fake_response("tool_calls", tool_calls=[
                AGENT.fake_tool_call("deny_path", "write_file", {"path": "../expected.json", "content": "changed"}),
                AGENT.fake_tool_call("deny_shell", "run_bash", {"path": "config.json", "command": "false"}),
            ]), AGENT.fake_response("stop", content="被拒绝"),
        ])
        run_workflow(denied, root / "denied", max_attempts=1)
        assert json.loads((root / "denied/expected.json").read_text()) == dict(INITIAL, theme="dark")
        assert all(json.loads(m["content"])["status"] == "rejected" for m in denied.completions.requests[1]["messages"][-2:])
        try:
            run_workflow(scripted_client("repair"), root / "repair")
        except FileExistsError:
            pass
        else:
            raise AssertionError("不能覆盖已有实验")
    print("workflow self-check passed (real file tools and grader, scripted model)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--self-check", action="store_true")
    mode.add_argument("--live", action="store_true", help="调用环境变量配置的真实模型，可能产生费用")
    parser.add_argument("--session-header", help="仅 live：Provider 要求的会话 ID 请求头名称")
    parser.add_argument("--scenario", choices=["repair", "always-wrong"], default="repair")
    parser.add_argument("--max-attempts", type=int, choices=range(1, 4), default=3)
    parser.add_argument("--model-budget", type=int, choices=range(1, 31), default=9)
    args = parser.parse_args()
    if args.session_header and not args.live:
        parser.error("--session-header 只用于 --live")
    if args.live and args.scenario != "repair":
        parser.error("--scenario 只控制模拟模型，不能用于真实模型")
    if args.self_check:
        self_check()
    else:
        output = Path(tempfile.mkdtemp(prefix="agent-workflow-")) / "run"
        if args.live:
            client, model = REFERENCE["make_client"]()
            headers = {"User-Agent": "agent-engineering-book/0.1"}
            if args.session_header:
                headers[args.session_header] = output.parent.name
            client = client.with_options(timeout=30.0, max_retries=0, default_headers=headers)
        else:
            client, model = scripted_client(args.scenario), "scripted-workflow"
        print("真实模型" if args.live else "固定剧本模型", "；报告目录：", output, flush=True)
        try:
            result = run_workflow(client, output, args.max_attempts, args.model_budget,
                                  model=model, live=args.live)
        finally:
            if args.live:
                client.close()
        print("完整报告：", output / "report.json")
        raise SystemExit(0 if result["phase"] == "completed" else 2)
