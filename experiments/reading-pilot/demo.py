"""真实 HTTP / 文件工具 + 预设模型替身；不访问云端模型。"""

import argparse
from contextlib import redirect_stdout
from http.server import BaseHTTPRequestHandler, HTTPServer
import io
import json
from pathlib import Path
import runpy
import shutil
import tempfile
from threading import Thread
import traceback
from types import SimpleNamespace
from urllib.error import HTTPError
from urllib.request import ProxyHandler, build_opener

import order_service

HERE = Path(__file__).resolve().parent
CORE = runpy.run_path(str(HERE.parents[1] / "exercises/phase-1-capstone/starter.py"))
ALLOWED_FILES = {"server.log", "order_service.py"}
TOOLS = [{
    "type": "function",
    "function": {
        "name": "read_file",
        "description": "读取本次请求的 server.log 或订单业务源码 order_service.py。",
        "parameters": {
            "type": "object",
            "properties": {"path": {"type": "string", "enum": sorted(ALLOWED_FILES)}},
            "required": ["path"],
            "additionalProperties": False,
        },
    },
}]


def reproduce(workspace, order_id):
    """启动临时本地服务，实际发一次 HTTP 请求，再关闭服务。"""
    route = f"/orders/{order_id}"

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            if self.path != route:
                self.send_error(404)
                return
            detail = ""
            try:
                body = order_service.get_order(order_id)
                status = 200
            except Exception:
                # HTTP 边界记录真实异常；客户端只拿到错误代号。
                detail = traceback.format_exc()
                body = {"error": "internal_server_error"}
                status = 500
            (workspace / "server.log").write_text(
                f"GET {route} -> {status}\n{detail}", encoding="utf-8"
            )
            raw = json.dumps(body).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

    with HTTPServer(("127.0.0.1", 0), Handler) as server:
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            # 忽略系统代理，确保请求只发往本机。
            opener = build_opener(ProxyHandler({}))
            url = f"http://127.0.0.1:{server.server_port}{route}"
            try:
                response = opener.open(url, timeout=5)
            except HTTPError as error:
                response = error
            with response:
                return {"path": route, "status": response.code,
                        "body": json.loads(response.read())}
        finally:
            server.shutdown()
            thread.join(timeout=5)


def execute_read(workspace, call):
    """模型只能申请读取两个文件；Schema 外还要在执行入口检查。"""
    try:
        if call.function.name != "read_file":
            raise ValueError("本样章只开放 read_file")
        arguments = json.loads(call.function.arguments)
        if not isinstance(arguments, dict) or set(arguments) != {"path"}:
            raise ValueError("参数必须只包含 path")
        path = arguments["path"]
        if not isinstance(path, str) or path not in ALLOWED_FILES:
            raise ValueError("只能读取 server.log 和 order_service.py")
        result = CORE["read_file"](workspace, path)
        print(f"Tool: read_file {path}")
    except (OSError, ValueError, TypeError) as error:
        result = {"error": str(error)}
    return json.dumps(result, ensure_ascii=False)


def scripted_model(**request):
    """只认识本样例的预设替身，读取实际 Tool Result 后走固定分支。"""
    results = [json.loads(message["content"]) for message in request["messages"]
               if message["role"] == "tool"]
    if not results:
        path = "server.log"
    elif any("error" in result or result.get("truncated") for result in results):
        return CORE["fake_response"]("stop", content="证据读取失败或不完整，无法下结论。")
    elif len(results) == 1:
        log = results[0]["content"]
        if " -> 200\n" in log:
            return CORE["fake_response"]("stop", content="本次请求返回 200，未复现 500；不能据此声称缺陷已修复。")
        if " -> 500\n" not in log:
            return CORE["fake_response"]("stop", content="未识别本次请求状态，证据不足。")
        path = "order_service.py"
    else:
        log, source = results[0]["content"], results[1]["content"]
        # ponytail: 这只是固定故障的规则匹配；验证模型诊断能力时换成真实模型。
        if ("TypeError: 'NoneType' object is not subscriptable" in log
                and "order = ORDERS.get(order_id)" in source
                and 'order["total"]' in source):
            line = next(number for number, text in enumerate(source.splitlines(), 1)
                        if 'order["total"]' in text)
            answer = (
                f"定位：order_service.py:{line}，读取 order[\"total\"] 时出错。\n"
                "原因：订单未找到，ORDERS.get(order_id) 得到 None；代码仍把它当订单读取金额。\n"
                "建议：增加订单不存在的分支，并让接口返回 404。这里只给建议，没有修改代码。\n"
                "验证：缺失订单应返回 404；已有订单仍应返回 200 和原来的金额。"
            )
        else:
            answer = "当前证据不符合预设故障，无法下结论。"
        return CORE["fake_response"]("stop", content=answer)
    call = CORE["fake_tool_call"](f"read_{len(results) + 1}", "read_file", {"path": path})
    return CORE["fake_response"]("tool_calls", tool_calls=[call])


def run_demo(folder, order_id):
    workspace = folder / "workspace"
    workspace.mkdir()
    source_path = HERE / "order_service.py"
    shutil.copyfile(source_path, workspace / source_path.name)
    source_before = source_path.read_bytes()
    http = reproduce(workspace, order_id)
    before = {path.name: path.read_bytes() for path in workspace.iterdir()}
    print("模型：预设替身（不调用真实模型，不验证模型诊断能力）")
    print(f"HTTP: GET {http['path']} -> {http['status']}")
    print(f"响应: {json.dumps(http['body'], ensure_ascii=False)}")
    session_file = folder / "session.jsonl"
    client = SimpleNamespace(chat=SimpleNamespace(
        completions=SimpleNamespace(create=scripted_model)))
    answer = CORE["run_agent_loop"](
        client, "scripted", TOOLS,
        f"请排查 GET {http['path']} 是否复现 500。先查日志，必要时读源码，引用证据并建议修复，不要修改文件。",
        lambda call: execute_read(workspace, call), session_file=session_file,
    )
    after = {path.name: path.read_bytes() for path in workspace.iterdir()}
    assert before == after and source_before == source_path.read_bytes(), "排查不得修改输入文件"
    report = {"model_mode": "scripted", "http": http, "answer": answer,
              "inputs_unchanged": True, "session_file": str(session_file)}
    (folder / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(answer)
    print("检查：排查前后，源码与日志均未改变。")
    print(f"完整证据: {folder}")
    return report


def self_check():
    with tempfile.TemporaryDirectory(prefix="agent-reading-check-") as temporary:
        root = Path(temporary)
        for order_id, expected_status, expected_reads in [
            ("order_404", 500, 2), ("order_001", 200, 1),
        ]:
            folder = root / order_id
            folder.mkdir()
            with redirect_stdout(io.StringIO()):
                report = run_demo(folder, order_id)
            assert report["http"]["status"] == expected_status
            assert report["inputs_unchanged"]
            messages = CORE["build_prompt_view"](CORE["load_entries"](folder / "session.jsonl"))
            calls = [call["id"] for message in messages for call in message.get("tool_calls", [])]
            results = [message for message in messages if message["role"] == "tool"]
            assert len(results) == expected_reads
            assert calls == [message["tool_call_id"] for message in results]
            assert messages[-1]["role"] == "assistant"
            if expected_status == 500:
                assert "TypeError" in json.loads(results[0]["content"])["content"]
                assert "ORDERS.get(order_id) 得到 None" in report["answer"]
            else:
                assert report["http"]["body"] == {"order_id": "order_001", "total": 128}
                assert "未复现 500" in report["answer"]
        workspace = root / "order_404/workspace"
        for name, arguments in [
            ("write_file", {"path": "order_service.py", "content": "overwritten"}),
            ("bash", {"command": "echo forbidden"}),
            ("read_file", {"path": "../report.json"}),
            ("read_file", {"path": "/etc/passwd"}),
            ("read_file", {"path": []}),
            ("read_file", {"path": "server.log", "extra": True}),
        ]:
            call = CORE["fake_tool_call"]("denied", name, arguments)
            assert "error" in json.loads(execute_read(workspace, call))
        assert (workspace / "order_service.py").read_bytes() == (HERE / "order_service.py").read_bytes()
        request = {"messages": [{"role": "tool", "content": json.dumps({"error": "不可读"})}]}
        assert "无法下结论" in scripted_model(**request).choices[0].message.content
    print("self-check passed: real HTTP 500/200, Tool Result 回传、读取边界、输入未改动")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--order-id", choices=["order_404", "order_001"], default="order_404")
    parser.add_argument("--self-check", action="store_true")
    args = parser.parse_args()
    if args.self_check:
        self_check()
    else:
        run_demo(Path(tempfile.mkdtemp(prefix="agent-reading-pilot-")), args.order_id)
