"""一次受限日志排查：--self-check 使用剧本；--live 才调用已配置的模型。"""

import argparse
from contextlib import redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import runpy
import shutil
import tempfile
import time
from types import SimpleNamespace
from urllib.parse import urlsplit
import uuid

import tools

CORE = tools.reading_demo.CORE
MAX_REQUESTS = 4
MAX_OUTPUT_TOKENS = 2048
TASK = (
    "请排查 GET /orders/order_404 为什么返回 500。"
    "先用 list_files 查看可用材料，再按需要读取 server.log 和 order_service.py。"
    "给出出错位置、证据、原因和修复建议，不要修改文件，也不要声称已经修复。"
    "最多四次模型请求；取得足够证据后给出最终回答。"
)


def run_diagnosis(client, model, output: Path, mode="scripted"):
    output.mkdir(parents=True, exist_ok=False)
    workspace = output / "workspace"
    workspace.mkdir()
    source = tools.reading_demo.HERE / "order_service.py"
    shutil.copyfile(source, workspace / source.name)
    http = tools.reading_demo.reproduce(workspace, "order_404")
    before = {path.name: path.read_bytes() for path in workspace.iterdir()}
    session = output / "session.jsonl"
    report_path = output / "report.json"
    report = {
        "mode": mode, "model": model,
        "provider_host": urlsplit(str(getattr(client, "base_url", ""))).hostname,
        "max_model_requests": MAX_REQUESTS, "max_output_tokens_per_request": MAX_OUTPUT_TOKENS,
        "request_timeout": str(getattr(client, "timeout", "scripted")),
        "sdk_max_retries": getattr(client, "max_retries", 0),
        "task": TASK, "http": http, "status": "running",
        "requests": [], "tool_calls": [], "final_answer": None,
        "source_sha256": {
            str(path.relative_to(tools.ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in (Path(__file__).resolve(), Path(tools.__file__).resolve(),
                         tools.reading_demo.HERE / "demo.py", source,
                         tools.ROOT / "practice/workspace-agent/agent.py")
        },
    }

    def save_report():
        # 教学运行记录，不作为自动崩溃恢复的 Checkpoint。
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def request(**kwargs):
        if len(report["requests"]) >= MAX_REQUESTS:
            raise RuntimeError("本次模型请求预算用完")
        event = {"number": len(report["requests"]) + 1, "status": "running"}
        report["requests"].append(event)
        save_report()
        print(f"模型请求 {event['number']}/{MAX_REQUESTS}", flush=True)
        started = time.perf_counter()
        try:
            response = client.chat.completions.create(max_tokens=MAX_OUTPUT_TOKENS, **kwargs)
            event.update(status="returned", finish_reason=response.choices[0].finish_reason)
            usage = getattr(response, "usage", None)
            if usage is not None:
                event["usage"] = {name: getattr(usage, name, None) for name in ("prompt_tokens", "completion_tokens", "total_tokens")}
            return response
        except Exception as error:
            event.update(status="error", error_type=type(error).__name__, http_status=getattr(error, "status_code", None))
            raise
        finally:
            event["duration_ms"] = round((time.perf_counter() - started) * 1000)
            save_report()

    def execute(call):
        print(f"工具申请 {call.id}: {call.function.name} {call.function.arguments}", flush=True)
        result = tools.execute_tool(workspace, call)
        report["tool_calls"].append({"tool_call_id": call.id, "name": call.function.name, "arguments": call.function.arguments, "result": result})
        save_report()
        parsed = json.loads(result)
        print("工具结果：", parsed.get("error", "已返回"), flush=True)
        return result

    bounded = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=request)))
    CORE["persist_message"](session, {"role": "system", "content": "你是只读排查助手。依据真实工具结果判断；证据不足时说明缺口。"})
    try:
        report["final_answer"] = CORE["run_agent_loop"](bounded, model, tools.TOOLS, TASK, execute, session_file=session)
        report["status"] = "completed"
    except Exception as error:
        report.update(status="error", error_type=type(error).__name__)
    finally:
        report["inputs_unchanged"] = before == {path.name: path.read_bytes() for path in workspace.iterdir()}
        if not report["inputs_unchanged"]:
            report.update(status="error", error_type="InputChanged")
        save_report()
    print("运行状态：", report["status"], flush=True)
    if report["final_answer"] is not None:
        print(report["final_answer"], flush=True)
    else:
        print("异常类型：", report["error_type"], flush=True)
    print("输入未改变：", report["inputs_unchanged"], flush=True)
    print("完整报告：", report_path, flush=True)
    return report


def self_check():
    with tempfile.TemporaryDirectory(prefix="agent-diagnosis-check-") as folder, redirect_stdout(io.StringIO()):
        responses = []
        for number, (name, path) in enumerate((("list_files", "."), ("read_file", "server.log"), ("read_file", "order_service.py")), 1):
            responses.append(CORE["fake_response"]("tool_calls", tool_calls=[CORE["fake_tool_call"](f"call_{number}", name, {"path": path})]))
        client = CORE["FakeClient"](responses + [CORE["fake_response"]("stop", content="模拟诊断结束")])
        result = run_diagnosis(client, "scripted", Path(folder) / "success")
        assert result["http"]["status"] == 500 and result["status"] == "completed"
        assert result["inputs_unchanged"] and len(result["requests"]) == 4
        assert [event["name"] for event in result["tool_calls"]] == ["list_files", "read_file", "read_file"]
        assert all(request["max_tokens"] == MAX_OUTPUT_TOKENS for request in client.completions.requests)
        assert json.loads((Path(folder) / "success/report.json").read_text()) == result
        assert CORE["pending_tool_calls"](CORE["load_entries"](Path(folder) / "success/session.jsonl")) == []
        failed = run_diagnosis(CORE["FakeClient"]([]), "scripted", Path(folder) / "error")
        assert failed["status"] == "error" and failed["inputs_unchanged"]
        assert len(failed["requests"]) == 1 and failed["requests"][0]["status"] == "error"
        repeating = [CORE["fake_response"]("tool_calls", tool_calls=[CORE["fake_tool_call"](f"loop_{i}", "list_files", {"path": "."})]) for i in range(4)]
        exhausted = run_diagnosis(CORE["FakeClient"](repeating), "scripted", Path(folder) / "budget")
        assert exhausted["status"] == "error" and len(exhausted["requests"]) == 4
        assert exhausted["final_answer"] is None and exhausted["inputs_unchanged"]
    print("diagnosis self-check passed: real HTTP/files, scripted model, preserved error and four-request limit")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--self-check", action="store_true")
    mode.add_argument("--live", action="store_true")
    parser.add_argument("--session-header", help="可选的 Provider 会话 ID 请求头名称，不用于传 API Key")
    args = parser.parse_args()
    if args.self_check:
        if args.session_header:
            parser.error("--session-header 只用于 --live")
        self_check()
        return
    connection = runpy.run_path(str(tools.ROOT / "practice/workspace-agent/client.py"))
    client, model = connection["make_client"]()
    headers = {"User-Agent": "agent-engineering-book/0.1"}
    if args.session_header:
        headers[args.session_header] = uuid.uuid4().hex
    client = client.with_options(timeout=30.0, max_retries=0, default_headers=headers)
    output = Path(tempfile.mkdtemp(prefix="agent-live-diagnosis-")) / "run"
    print("真实模型：", model, "；证据目录：", output, flush=True)
    try:
        report = run_diagnosis(client, model, output, mode="live")
    finally:
        client.close()
    raise SystemExit(0 if report["status"] == "completed" else 2)


if __name__ == "__main__":
    main()
