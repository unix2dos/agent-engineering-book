# 第一阶段综合实践：可靠的 Workspace Agent

这次不再新增一份完整 Agent 实现。[`lesson_07_tool_reliability.py`](../../examples/lesson_07_tool_reliability.py) 已经包含 Tool、Context、Compaction、Ledger 与恢复，继续复制只会产生两套答案。

综合实践采用另一种方式：从一个很小的 starter 开始，你亲手补上核心控制逻辑；每通过一关，再接入现有代码中的一层能力。`lesson_07_tool_reliability.py` 只在完成当前尝试后用于对照。

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

打开 [`starter.py`](starter.py)，只实现 `run_agent_loop()`。不要先翻看 [`lesson_03_tool_calling_loop.py`](../../examples/lesson_03_tool_calling_loop.py) 的答案。

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

## 第二关：受控本地工具

第二关先只解决路径问题。打开 [`starter.py`](starter.py)，实现 `resolve_workspace_file()`：

- 相对路径可以解析到 Workspace 内；
- 拒绝绝对路径；
- 拒绝 `..` 逃出 Workspace；
- 即使路径经过软链接，最终目标也不能落到 Workspace 外；
- 目标文件暂时不存在时也能返回规范化路径。

不要自己实现文件系统，也不要靠字符串前缀判断路径。使用 Python `pathlib.Path` 提供的路径解析能力，策略判断由你完成。

运行第二关的第一组检查：

```bash
python -B exercises/phase-1-capstone/starter.py --checkpoint-2
```

通过标志：

```text
checkpoint 2A passed
```

### 第二关 B：分段读取文件

路径检查通过后，实现 `read_file()`：

- 只读取普通文件；
- `offset` 是非负的 Byte 位置；
- 一次最多返回 `MAX_READ_BYTES`；
- 后面还有数据时，`truncated` 为 `true`，`next_offset` 指向下一段；
- 已读到结尾时，`truncated` 为 `false`，`next_offset` 为 `null`；
- 返回的 `path` 使用用户提供的相对路径，不暴露本机绝对目录。

继续运行同一个命令：

```bash
python -B exercises/phase-1-capstone/starter.py --checkpoint-2
```

新的通过标志：

```text
checkpoint 2B passed
```
