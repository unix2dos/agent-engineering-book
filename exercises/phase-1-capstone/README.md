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

### 第二关 C：原子覆盖写入

接下来实现 `write_file()`。这一关先练写入本身，审批和 `run_bash` 留到后面：

- `path` 必须落在 Workspace 内，软链接也不能逃逸；
- 父目录必须已经存在，工具不能偷偷创建目录；
- 目标已经存在时，只允许覆盖普通文件；
- `content` 按 UTF-8 编码，`bytes_written` 返回实际 Byte 数；
- 先在目标文件旁边写临时文件，完成后再用 `Path.replace()` 替换目标；
- 返回 `status`、原始相对路径、写入 Byte 数和是否覆盖旧文件。

为什么不直接对目标执行 `write_text()`？如果进程写到一半崩溃，旧文件可能已经被破坏。临时文件没有完整写好时，目标文件仍保持原样。

继续运行：

```bash
python -B exercises/phase-1-capstone/starter.py --checkpoint-2
```

通过标志将变成：

```text
checkpoint 2C passed
```

### 第二关 D：Tool Router 与审批闸门

`read_file()` 和 `write_file()` 现在只是两个孤立函数。下一步实现 `execute_workspace_tool()`，让它成为模型 Tool Call 和本地函数之间的路由器：

- 从 `tool_call.function` 读取工具名和 JSON 参数；
- `read_file` 可以直接执行，不询问用户；
- `write_file` 必须先调用传入的 `approve(name, arguments)`；
- 用户拒绝时不写文件，返回 `status: rejected`；
- 未知工具不执行，返回包含 `unknown_tool` 的受控失败结果；
- 所有结果使用 `json.dumps(..., ensure_ascii=False)` 转成 Tool Result 字符串。

审批放在 Router，而不是写进 `write_file()`。这样同一个文件函数可以被测试和复用，而“本次是否允许执行”仍由 Harness 决定。`tool_call_id` 也不需要放进结果内容；外层 Agent Loop 会把它写在对应的 `role: tool` Message 上。

继续运行：

```bash
python -B exercises/phase-1-capstone/starter.py --checkpoint-2
```

通过标志将变成：

```text
checkpoint 2D passed
```

### 第二关 E：接入需要审批的 Bash

最后实现 `run_bash()`，并把它接入 `execute_workspace_tool()`：

- 使用 `subprocess.run()` 调用固定的 `/bin/zsh -lc`；
- 使用 `cwd=workspace`，让命令从 Workspace 开始运行；
- 设置固定超时，不能让命令无限运行；
- 捕获 `stdout`、`stderr` 和 `returncode`；
- `returncode == 0` 返回 `succeeded`，其他值返回 `failed`；
- 与 `write_file` 一样，Router 必须在执行前调用 `approve()`；
- 用户拒绝时不调用 `run_bash()`，返回 `rejected`。

`subprocess.run()` 的调用形式可以直接参考：

```python
completed = subprocess.run(
    ["/bin/zsh", "-lc", command],
    cwd=workspace,
    capture_output=True,
    text=True,
    timeout=5,
    check=False,
)
```

你需要亲手完成的是：根据 `completed.returncode` 组装结果，并在 Router 中加入 `run_bash` 的审批分支。

`cwd=workspace` 不是 Sandbox。Shell 仍可能通过绝对路径或 `..` 访问 Workspace 外部；这一关只证明 Harness 会先审批，真正的强制隔离仍要交给操作系统 Sandbox、容器或 microVM。

运行：

```bash
python -B exercises/phase-1-capstone/starter.py --checkpoint-2
```

通过标志将变成：

```text
checkpoint 2E passed
```

## 第三关：Transcript 与 Prompt View

第二关完成后，Agent 已经能调用本地工具，但所有消息仍只存在内存里。程序一退出，用户说过什么、模型调用过什么工具、工具返回了什么都会消失。

第三关先把“磁盘上的完整记录”和“真正发给模型的内容”分开实现。

### 第三关 A：追加写入 JSONL Transcript

先实现 `append_entry()` 和 `load_entries()`：

- Session 文件使用 JSONL，每一行保存一条完整记录；
- `append_entry()` 只在文件末尾追加，不覆盖旧内容；
- 父目录不存在时自动创建；
- 使用 `ensure_ascii=False`，让中文在磁盘上仍然可读；
- 每次写完调用 `flush()` 和 `os.fsync()`，尽量把本轮记录交给操作系统落盘；
- `load_entries()` 在文件不存在时返回空列表；
- 逐行解析 JSON，发现坏行时抛出带行号的 `ValueError`，不能悄悄跳过。

这一小关只建立 Transcript，也就是磁盘上的完整收据。下一小关才会从这些收据里组装 Prompt View。

运行：

```bash
python -B exercises/phase-1-capstone/starter.py --checkpoint-3
```

当前会停在 `NotImplementedError`。通过标志是：

```text
checkpoint 3A passed
```

### 第三关 B：从 Transcript 组装 Prompt View

Transcript 不只保存发给模型的 Message。以后它还会保存 `tool_execution`、Compaction 和恢复记录。Provider 不认识这些内部记录，所以不能把整个 JSONL 原样塞进 `messages`。

现在实现 `build_prompt_view()`：

- 按原顺序遍历全部 Transcript Entry；
- 只取 `type == "message"` 的 `message`；
- `tool_execution` 等内部记录仍留在磁盘，但不进入 Prompt；
- Assistant Tool Call 和对应 Tool Result 都必须完整保留，不能只留下其中一边；
- 不修改传入的 `entries`。

测试中的磁盘记录是：

```text
User Message
Assistant Tool Call
Tool Execution       <- 留在 Transcript，不发给模型
Tool Result
Assistant Final
```

模型实际看到四条 Message：

```text
User -> Assistant Tool Call -> Tool Result -> Assistant Final
```

继续运行：

```bash
python -B exercises/phase-1-capstone/starter.py --checkpoint-3
```

通过标志将变成：

```text
checkpoint 3B passed
```

### 第三关 C：把 Transcript 接入 Agent Loop

现在 `append_entry()`、`persist_message()` 和 `build_prompt_view()` 都能单独工作，但 Agent Loop 仍然只使用内存列表。程序重启后，它不会主动加载旧 Session。

这一步直接修改现有 `run_agent_loop()`，不要再复制一个新循环：

- 使用新增的可选参数 `session_file`；
- 传入 Session 文件时，先用 `load_entries()` 和 `build_prompt_view()` 恢复旧消息；
- 把本轮 User Message 追加到 Prompt View，并立即写入 Transcript；
- 每次收到 Assistant Message，先同时加入 Prompt View 和 Transcript，再判断是否调用工具；
- 每个 Tool Result 都同时加入 Prompt View 和 Transcript；
- 重启后只加载旧消息，不能把旧消息重新写一遍；
- `session_file is None` 时保持第一关的纯内存行为。

完成后，第一次运行应在磁盘留下一个完整工具轮次：

```text
User -> Assistant Tool Call -> Tool Result -> Assistant Final
```

第二次运行使用同一个 Session 文件。模型第一次请求就应该看到上一轮四条 Message，再加本轮新的 User Message。

继续运行：

```bash
python -B exercises/phase-1-capstone/starter.py --checkpoint-3
```

通过标志将变成：

```text
checkpoint 3C passed
```

### 第三关 D：用 Compaction 缩短 Prompt View

Session 可以重启恢复了，但消息会一直增长。Transcript 仍然保存所有原始记录；真正需要缩短的是每次发给模型的 Prompt View。

先实现 `append_compaction()`，写入下面这种 Entry：

```json
{
  "type": "compaction",
  "summary": "较早内容的摘要",
  "retained_tail": [],
  "is_split_turn": false
}
```

然后扩展 `build_prompt_view()`：

- 没有 Compaction 时，仍然返回全部 `type: message`；
- 有 Compaction 时，从最后一条 Compaction 开始恢复；
- Prompt View 的第一条是 `role: assistant` 的摘要消息，内容以 `Conversation summary:\n` 开头；
- 摘要后依次加入 `retained_tail`；
- 最后加入 Compaction Entry 之后新产生的 Message；
- Compaction 之前的原始 Message 仍留在 Transcript，但不再重复进入 Prompt；
- 空白 `summary` 必须拒绝。

可以把它记成：

```text
模型看到 = summary + retained_tail + compaction 后的新消息
磁盘保存 = 全部旧消息 + compaction + 全部新消息
```

这一关不要求调用模型生成摘要。先把数据结构和恢复规则写正确，下一步再决定什么时候触发压缩、在哪里切分完整轮次。

运行：

```bash
python -B exercises/phase-1-capstone/starter.py --checkpoint-3
```

通过标志将变成：

```text
checkpoint 3D passed
```

### 第三关 E：只在完整轮次之间切分

Compaction Entry 已经可以保存和恢复，但还缺少一个安全问题：哪些旧消息进入摘要，哪些原文留在 `retained_tail`？

这一小关只实现 `find_compaction_cut()`。返回值是一个列表位置：这个位置之前的消息进入摘要，从这个位置开始的消息保留原文。

在本练习中，一个完整轮次这样识别：

```text
从 User Message 开始
经过零个或多个 Assistant Tool Call 与 Tool Result
到不再包含 tool_calls 的 Assistant Final 结束
```

例如：

```text
T1 = User -> Assistant Final
T2 = User -> Assistant Tool Call -> Tool Result -> Assistant Final
T3 = User -> Assistant Tool Call                         当前未完成
```

当 `keep_recent_turns=1` 时，只摘要 T1，保留完整 T2 和当前 T3。切点应落在 T1 与 T2 之间，不能落在 T2 的 Tool Call 与 Tool Result 之间。

实现要求：

- `keep_recent_turns` 不能为负数；
- 先扫描 Message，记录每个完整轮次结束后的列表位置；
- 没有足够旧的完整轮次可以摘要时返回 `None`；
- 保留最近指定数量的完整轮次；
- 当前未完成轮次始终留在切点之后；
- Prompt View 开头已有的 Summary Message 不算一个用户轮次。

推荐使用普通循环。可以用一个布尔值记录“是否已经看到本轮 User Message”。

这一步不修改消息，也不生成摘要，只返回切点数字。运行：

```bash
python -B exercises/phase-1-capstone/starter.py --checkpoint-3
```

通过标志将变成：

```text
checkpoint 3E passed
```

### 第三关 F：超过预算才执行 Compaction

现在已经能找到安全切点，但不能因为“存在旧轮次”就每次都压缩。`maybe_compact()` 负责把预算判断、切分、摘要和写入 Compaction Entry 串起来。

函数按下面顺序工作：

```text
加载 Transcript
-> 组装当前 Prompt View
-> 没超过预算：返回 False
-> 寻找完整轮次切点
-> 没有安全切点：返回 False
-> prefix 交给 summarize()
-> tail 保存为 retained_tail
-> 追加 Compaction Entry
-> 返回 True
```

实现要求：

- 使用 `json.dumps(prompt_view, ensure_ascii=False)` 后的字符数和 `max_prompt_chars` 比较；
- `messages[:cut]` 是需要摘要的 `prefix`；
- `messages[cut:]` 是继续保留原文的 `retained_tail`；
- 只有真正需要压缩并且存在安全切点时，才能调用 `summarize(prefix)`；
- 使用已有的 `append_compaction()` 保存结果；
- 不删除、覆盖或改写原始 Message Entry。

这里使用字符数只是为了让自检简单稳定。生产 Agent 通常使用 Provider Token 计数或更保守的估算，并且会为下一次模型输出预留空间。

运行：

```bash
python -B exercises/phase-1-capstone/starter.py --checkpoint-3
```

通过标志将变成：

```text
checkpoint 3F passed
```
