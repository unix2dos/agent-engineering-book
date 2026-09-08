"""Lesson 09: task-specific config/CSV graders and shared score summaries."""

import argparse
import csv
import json
from pathlib import Path
import tempfile
from unittest.mock import patch


def grade_config(config_path: Path, expected: dict | None = None) -> dict:
    """阅卷：theme 改为 dark，其他字段和值按这道题的标准答案检查。"""
    if expected is None:
        expected = {"theme": "dark", "port": 8080}
    if not isinstance(expected, dict) or expected.get("theme") != "dark":
        raise ValueError("标准答案必须是包含 theme=dark 的配置对象")
    try:
        content = config_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return {"status": "failed", "reason": "没有生成 config.json"}
    except IsADirectoryError:
        return {"status": "failed", "reason": "config.json 变成了目录"}
    except UnicodeDecodeError:
        return {"status": "failed", "reason": "文件不是有效的 UTF-8 文本"}

    try:
        actual = json.loads(content)
    except json.JSONDecodeError:
        return {"status": "failed", "reason": "文件不是有效 JSON"}

    if not isinstance(actual, dict):
        return {"status": "failed", "reason": "配置必须是 JSON 对象"}

    if actual.get("theme") != "dark":
        return {"status": "failed", "reason": "theme 没有改成 dark"}

    if actual != expected:
        return {"status": "failed", "reason": "其他配置被修改、删除或新增"}
    # 这三道题的字段都是简单值；不能把 Python 中相等的 False 和 0 当成同一配置。
    for name in expected:
        if type(actual[name]) is not type(expected[name]):
            return {"status": "failed", "reason": f"字段 {name} 的类型被改变"}

    return {"status": "passed", "reason": "主题正确，其他配置保持不变"}


def safe_grade_config(config_path: Path, expected: dict | None = None) -> dict:
    """保留评分异常，避免把阅卷程序的错误归给 Agent。"""
    try:
        return grade_config(config_path, expected)
    except Exception as error:
        return {
            "status": "error",
            "reason": f"评分未完成：{type(error).__name__}: {error}",
        }


def csv_quantity_total(original_csv: Path) -> int:
    """从可信的原始 CSV 算答案；题目数据有误时抛出异常。"""
    total = 0
    with original_csv.open(encoding="utf-8", newline="") as file:
        rows = csv.DictReader(file)
        if rows.fieldnames != ["item", "quantity"]:
            raise ValueError("原始 CSV 必须有 item,quantity 两列")
        for row in rows:
            if set(row) != {"item", "quantity"} or not row["item"] or row["quantity"] is None:
                raise ValueError("原始 CSV 有缺失或多余的字段")
            quantity = int(row["quantity"])
            if quantity < 0:
                raise ValueError("原始 CSV 的数量不能为负数")
            total += quantity
    return total


def grade_csv_total(workspace: Path, original_csv: Path) -> dict:
    """阅卷：从原始 CSV 计算总数，检查实际结果和输入未变。"""
    if original_csv.resolve().is_relative_to(workspace.resolve()):
        raise ValueError("原始 CSV 必须使用工作区外保存的快照")
    expected_total = csv_quantity_total(original_csv)
    original_bytes = original_csv.read_bytes()
    try:
        submitted_input = (workspace / "items.csv").read_bytes()
    except (FileNotFoundError, IsADirectoryError):
        return {"status": "failed", "reason": "原始输入 items.csv 没有保留为文件"}
    if submitted_input != original_bytes:
        return {"status": "failed", "reason": "输入 items.csv 被修改"}

    try:
        actual = json.loads((workspace / "summary.json").read_text(encoding="utf-8"))
    except (FileNotFoundError, IsADirectoryError, UnicodeDecodeError, json.JSONDecodeError):
        return {"status": "failed", "reason": "summary.json 缺失或不是有效 JSON 文件"}
    if not isinstance(actual, dict) or set(actual) != {"total_quantity"}:
        return {"status": "failed", "reason": "summary.json 必须是仅含 total_quantity 的对象"}
    if type(actual["total_quantity"]) is not int:
        return {"status": "failed", "reason": "total_quantity 必须是整数"}
    if actual["total_quantity"] != expected_total:
        return {"status": "failed", "reason": f"总数量应为 {expected_total}"}
    return {"status": "passed", "reason": f"总数量 {expected_total} 正确，原始 CSV 未改变"}


def safe_grade_csv_total(workspace: Path, original_csv: Path) -> dict:
    try:
        return grade_csv_total(workspace, original_csv)
    except Exception as error:
        return {
            "status": "error",
            "reason": f"CSV 评分未完成：{type(error).__name__}: {error}",
        }


def summarize_results(results: list[dict]) -> dict:
    """只统计已经得到的成绩，不重新读取文件或调用阅卷器。"""
    summary = {
        "total": len(results),
        "passed": 0,
        "failed": 0,
        "error": 0,
    }
    for result in results:
        status = result["status"]
        summary[status] = summary[status] + 1
    return summary


def grade_trials(trials: list[dict]) -> dict:
    """检查点 B：逐份评分，保留 trial_id/status/reason，并汇总三类数量。"""
    # trials 中的每一项都有唯一 trial_id，以及 Path 类型的 config_path。
    results = []

    for trial in trials:
        # 1. 取出这一份文件的路径，交给第一关的阅卷器。
        result = safe_grade_config(trial["config_path"], trial.get("expected"))

        # 2. 把原编号、成绩和原因放入成绩单。
        results.append({
            "trial_id": trial["trial_id"],
            "status": result["status"],
            "reason": result["reason"],
        })

    # 所有答卷处理完，再交回整份报告。
    return {"results": results, "summary": summarize_results(results)}


def checkpoint_a() -> None:
    """制造不同产物，检查阅卷器本身；不调用真实 Model。"""
    with tempfile.TemporaryDirectory() as folder:
        config_path = Path(folder) / "config.json"
        cases = [
            ("正确修改", '{"theme":"dark","port":8080}', "passed"),
            ("顺序与空格变化", '{\n  "port": 8080, "theme": "dark"\n}', "passed"),
            ("主题未改", '{"theme":"light","port":8080}', "failed"),
            ("端口被修改", '{"theme":"dark","port":9999}', "failed"),
            ("端口被删除", '{"theme":"dark"}', "failed"),
            ("额外字段", '{"theme":"dark","port":8080,"debug":true}', "failed"),
            ("JSON 损坏", '{"theme":', "failed"),
            ("不是对象", '[]', "failed"),
        ]
        for label, content, expected_status in cases:
            config_path.write_text(content, encoding="utf-8")
            result = safe_grade_config(config_path)
            assert result["status"] == expected_status, (label, result)
            assert result["reason"]
            assert config_path.read_text(encoding="utf-8") == content
            print(f"{label}: {result['status']}")

        config_path.write_bytes(b"\xff")
        assert safe_grade_config(config_path)["status"] == "failed"
        assert safe_grade_config(Path(folder) / "missing.json")["status"] == "failed"
        assert safe_grade_config(Path(folder))["status"] == "failed"

        # 只模拟阅卷代码出错；题目的实际文件仍然是正确的。
        config_path.write_text('{"theme":"dark","port":8080}', encoding="utf-8")
        with patch(__name__ + ".grade_config", side_effect=NameError("评分变量拼错")):
            result = safe_grade_config(config_path)
            assert result["status"] == "error"
            assert "NameError" in result["reason"]
            print(f"阅卷程序出错: {result['status']}")

        # 移除模拟异常后，直接对同一文件补评，无需重跑 Agent。
        assert safe_grade_config(config_path)["status"] == "passed"
        print("原文件补评: passed")

        # 新题要用各自的标准答案；字段顺序仍然不影响成绩。
        expected_port = {"theme": "dark", "port": 3000}
        expected_debug = {"theme": "dark", "port": 8080, "debug": False}
        variants = [
            ('{"port":3000,"theme":"dark"}', expected_port, "passed"),
            ('{"theme":"dark","port":8080}', expected_port, "failed"),
            ('{"theme":"dark","port":8080}', expected_debug, "failed"),
            ('{"debug":false,"port":8080,"theme":"dark"}', expected_debug, "passed"),
            ('{"theme":"dark","port":8080,"debug":0}', expected_debug, "failed"),
        ]
        for content, expected, status in variants:
            config_path.write_text(content, encoding="utf-8")
            assert safe_grade_config(config_path, expected)["status"] == status
        assert safe_grade_config(config_path, {"port": 8080})["status"] == "error"
        print("按题目使用标准答案: passed")
    print("checkpoint A passed")


def checkpoint_b() -> None:
    """验证任务失败和评分失败之后，后面的答卷仍会被评分。"""
    with tempfile.TemporaryDirectory() as folder:
        trials = []
        snapshots = []
        contents = [
            '{"theme":"dark","port":8080}',
            '{"theme":',
            '{"theme":"dark","port":8080}',
            '{"port": 8080, "theme": "dark"}',
        ]
        for number, content in enumerate(contents, start=1):
            config_path = Path(folder) / f"trial_{number}" / "config.json"
            config_path.parent.mkdir()
            config_path.write_text(content, encoding="utf-8")
            trials.append({"trial_id": f"trial_{number}", "config_path": config_path})
            snapshots.append(config_path.read_bytes())

        real_grade_config = grade_config

        def grade_with_one_error(config_path: Path, expected: dict | None = None) -> dict:
            if config_path == trials[2]["config_path"]:
                raise NameError("评分变量拼错")
            return real_grade_config(config_path, expected)

        # 第 3 份产物是正确的，但它的阅卷代码暂时故障；第 4 份仍须照常评分。
        with patch(__name__ + ".grade_config", side_effect=grade_with_one_error) as grader:
            report = grade_trials(trials)
            assert grader.call_count == 4, "每份答卷应该评分一次"
            assert [call.args[0] for call in grader.call_args_list] == [
                trial["config_path"] for trial in trials
            ], "必须读取每份答卷自己的文件"

        expected_statuses = ["passed", "failed", "error", "passed"]
        assert len(report["results"]) == 4, "不能漏掉失败或评分出错的答卷"
        for index, result in enumerate(report["results"]):
            assert result["trial_id"] == trials[index]["trial_id"], "保留原 ID 和顺序"
            assert result["status"] == expected_statuses[index], result
            assert result["reason"], "每份成绩都要留下原因"
            assert trials[index]["config_path"].read_bytes() == snapshots[index]
            assert set(trials[index]) == {"trial_id", "config_path"}, "不要修改输入记录"
            print(f"{result['trial_id']}: {result['status']}")
        assert "JSON" in report["results"][1]["reason"]
        assert "NameError" in report["results"][2]["reason"]
        assert report["summary"] == {"total": 4, "passed": 2, "failed": 1, "error": 1}
        print("total=4 passed=2 failed=1 error=1")

        assert grade_trials([]) == {
            "results": [],
            "summary": {"total": 0, "passed": 0, "failed": 0, "error": 0},
        }, "没有答卷时，不应凭空产生通过记录"
    print("checkpoint B passed")


def check_csv_grader() -> None:
    """验证 CSV 评分规则，包含原始数据变化和输入篡改。"""
    with tempfile.TemporaryDirectory() as folder:
        original = Path(folder) / "initial.csv"
        workspace = Path(folder) / "workspace"
        workspace.mkdir()
        original.write_text('item,quantity\n"apple, green",2\nbanana,3\npear,7\n', encoding="utf-8")
        source = workspace / "items.csv"
        source.write_bytes(original.read_bytes())
        output = workspace / "summary.json"
        assert safe_grade_csv_total(workspace, source)["status"] == "error"
        assert csv_quantity_total(original) == 12
        for submission, expected_status in [
            ('{"total_quantity":12}', "passed"),
            ('{\n "total_quantity": 12\n}', "passed"),
            ('{"total_quantity":11}', "failed"),
            ('{"total_quantity":"12"}', "failed"),
            ('{"total_quantity":true}', "failed"),
            ('{"total_quantity":12,"extra":0}', "failed"),
            ('[]', "failed"),
            ('{', "failed"),
        ]:
            output.write_text(submission, encoding="utf-8")
            result = safe_grade_csv_total(workspace, original)
            assert result["status"] == expected_status, result
            assert output.read_text() == submission
            assert source.read_bytes() == original.read_bytes()
        output.unlink()
        assert safe_grade_csv_total(workspace, original)["status"] == "failed"

        original.write_text('item,quantity\napple,10\nbanana,20\n', encoding="utf-8")
        source.write_bytes(original.read_bytes())
        output.write_text('{"total_quantity":30}', encoding="utf-8")
        assert safe_grade_csv_total(workspace, original)["status"] == "passed"
        source.write_text('item,quantity\napple,999\n', encoding="utf-8")
        output.write_text('{"total_quantity":999}', encoding="utf-8")
        assert safe_grade_csv_total(workspace, original)["status"] == "failed"

        original.write_text('item,quantity\napple,not-a-number\n', encoding="utf-8")
        assert safe_grade_csv_total(workspace, original)["status"] == "error"
        original.unlink()
        assert safe_grade_csv_total(workspace, original)["status"] == "error"
    print("CSV grader self-check passed")


def main() -> None:
    parser = argparse.ArgumentParser(description="第 9 课：配置修改与 CSV 汇总阅卷器")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--checkpoint-a", action="store_true", help="运行单份阅卷自检")
    mode.add_argument("--checkpoint-b", action="store_true", help="运行 A 和逐份评分自检")
    mode.add_argument("--config", type=Path, help="评分的 config.json 路径")
    mode.add_argument("--csv-workspace", type=Path, help="包含 items.csv 与 summary.json 的答卷目录")
    mode.add_argument("--check-csv", action="store_true", help="运行 CSV 阅卷器自检")
    parser.add_argument("--expected", type=Path, help="本题保存的 expected.json；省略时使用原基础题答案")
    parser.add_argument("--original-csv", type=Path, help="CSV 题在工作区外保存的原始输入")
    args = parser.parse_args()
    if args.expected is not None and args.config is None:
        parser.error("--expected 需要与 --config 一起使用")
    if (args.csv_workspace is None) != (args.original_csv is None):
        parser.error("--csv-workspace 和 --original-csv 需要一起使用")
    if args.checkpoint_a:
        checkpoint_a()
        return
    if args.checkpoint_b:
        checkpoint_a()
        checkpoint_b()
        return
    if args.check_csv:
        check_csv_grader()
        return
    if args.csv_workspace is not None:
        result = safe_grade_csv_total(args.csv_workspace, args.original_csv)
        print(json.dumps(result, ensure_ascii=False))
        raise SystemExit({"passed": 0, "failed": 1, "error": 2}[result["status"]])

    expected = None
    try:
        if args.expected is not None:
            expected = json.loads(args.expected.read_text(encoding="utf-8"))
            if not isinstance(expected, dict):
                raise ValueError("标准答案必须是 JSON 对象")
    except (OSError, UnicodeError, ValueError) as error:
        result = {"status": "error", "reason": f"标准答案读取失败：{error}"}
    else:
        result = safe_grade_config(args.config, expected)
    print(json.dumps(result, ensure_ascii=False))
    # 命令返回 0 表示通过；任务失败和评分失败都不能让发布检查放行。
    raise SystemExit({"passed": 0, "failed": 1, "error": 2}[result["status"]])


if __name__ == "__main__":
    main()
