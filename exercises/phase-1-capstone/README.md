# 第一阶段综合实践：可靠的 Workspace Agent

这次不再新增一份完整 Agent 实现。`04_tool_reliability.py` 已经包含 Tool、Context、Compaction、Ledger 与恢复，继续复制只会产生两套答案。

综合实践采用另一种方式：从一个很小的 starter 开始，你亲手补上核心控制逻辑；每通过一关，再接入现有代码中的一层能力。`04_tool_reliability.py` 只在完成当前尝试后用于对照。

## 最终目标

这个 Agent 最终需要做到：

```text
用户请求
→ 有界 Agent Loop
→ read_file / write_file / run_bash
→ Workspace 路径与审批检查
→ JSONL Transcript 与 Prompt View
→ Execution Ledger
→ 崩溃后的 unknown 与恢复判断
→ Assistant Final
```

本实践不会自己实现模型 SDK、JSON 解析器、数据库、容器或操作系统 Sandbox。它们是成熟基础设施；我们只学习怎样正确调用并验证边界。

## 实践关卡

1. **有界 Tool Calling Loop**：消息顺序、Tool Result 配对、停止条件。
2. **受控本地工具**：读取、写入、Bash、参数与 Workspace 边界。
3. **Transcript 与 Prompt View**：完整历史和模型可见视图分离。
4. **Ledger 与幂等**：执行尝试、终态、`unknown` 与重试身份。
5. **故障注入**：在副作用之后、回执之前模拟崩溃。
6. **接入 Trace**：作为第 9 课的真实观察对象。

## 第一关：你现在要写什么

打开 [`starter.py`](starter.py)，只实现 `run_agent_loop()`。不要先翻看 `01-agent.py` 的答案。

你的实现必须满足这些可观察结果：

- 最多发出 `MAX_MODEL_REQUESTS` 次模型请求；
- 每次先保存完整 Assistant Message；
- 有 Tool Call 时，`finish_reason` 必须是 `tool_calls`；
- 每个 Tool Result 保留原 `tool_call_id`；
- 同一批 Tool Call 的结果全部回传后，才能再次请求模型；
- 只有无 Tool Call 且 `finish_reason == "stop"` 时返回 Final；
- `length`、矛盾响应和超过上限都必须停止，不能继续执行工具。

完成后运行：

```bash
python exercises/phase-1-capstone/starter.py --self-check
```

通过标志：

```text
checkpoint 1 passed
```

建议先独立写 20～30 分钟。卡住时只索要一个提示，不要直接索要完整答案。

