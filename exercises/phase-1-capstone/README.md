# 阶段一～二综合实践：可靠的 Workspace Agent

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

### 第三关 G：在请求模型前刷新压缩视图

`maybe_compact()` 现在可以追加 Compaction Entry，但 Agent Loop 内存中的 `messages` 仍然是压缩前的完整列表。如果马上请求模型，刚才的压缩不会产生任何效果。

使用新增的 `compact_before_request` 参数完成最后连接：

- 每次调用模型之前执行 `compact_before_request()`；
- 使用这个参数时必须同时提供 `session_file`；
- 返回 `False` 表示没有产生 Compaction，继续使用当前 `messages`；
- 返回 `True` 表示磁盘出现了新 Compaction；
- 此时重新执行 `load_entries(session_file)` 和 `build_prompt_view()`，替换内存中的 `messages`；
- 当前 User Message 已经提前写进 Transcript，安全切点会让这个未完成轮次留在 `retained_tail`。

这里使用回调，而不是把具体摘要模型硬编码进 Agent Loop。循环只关心“是否发生压缩”，至于怎样计算预算、调用哪个模型生成摘要，由外面的 `maybe_compact()` 负责。

运行：

```bash
python -B exercises/phase-1-capstone/starter.py --checkpoint-3
```

通过标志将变成：

```text
checkpoint 3G passed
```

## 第四关：Ledger 与幂等

第三关已经保存了模型对话，但一次 Tool Result 只告诉 Model “最后拿到了什么”。它没有回答：工具获准后尝试执行了几次？程序是否在执行途中崩溃？

第四关开始保存另一类记录：Tool Execution Ledger，也就是工具执行流水。

### 第四关 A：保存状态变化，再恢复最后状态

先只处理一段已经发生的执行过程：

```text
exec_1：approved -> running -> unknown
exec_2：approved -> running -> succeeded
```

JSONL 必须保留上面的全部状态变化。程序重启后，还要能从这些记录算出：

```text
exec_1 当前是 unknown
exec_2 当前是 succeeded
```

在 [`starter.py`](starter.py) 中实现两个函数：

- `append_execution_state()`：校验状态，组装 `type: tool_execution` 的 Entry，然后使用已有的 `append_entry()` 追加到 JSONL；
- `latest_execution_states()`：按原顺序扫描 Entry，同一个 `execution_id` 后出现的状态覆盖先出现的状态。

每条 Ledger Entry 至少包含：

```json
{
  "type": "tool_execution",
  "execution_id": "exec_1",
  "tool_call_id": "call_1",
  "status": "running"
}
```

`tool_call_id` 标识 Model 发出的那一次工具申请；`execution_id` 标识 Harness 的一次具体执行尝试。以后重试同一个 Tool Call 时，前者不变，后者必须换新值。

`details` 用来增加工具名、参数 Hash、结果或错误等字段。先用普通的 `entry.update(details)` 合并，不需要学习新的 Python 技巧。

运行：

```bash
python -B exercises/phase-1-capstone/starter.py --checkpoint-4
```

当前会停在 `NotImplementedError`。完成这一小关后，输出最后一行应为：

```text
checkpoint 4A passed
```

这一关只保存事实，不执行工具，也不判断能否重试。下一小关再给同一次 Tool Call 计算稳定的参数 Hash 和幂等 Key。

### 第四关 B：给同一次调用固定身份

假设同一个 Tool Call 因为崩溃需要再次处理：

```text
第一次尝试：tool_call_id=call_1  execution_id=exec_1
第二次尝试：tool_call_id=call_1  execution_id=exec_2
```

`execution_id` 必须变化，用来区分两次尝试。`tool_call_id` 和 `idempotency_key` 必须保持不变，表示两次尝试都在完成同一个模型请求。

还要保存参数指纹 `arguments_sha256`。同一份 JSON 即使字段顺序不同，也必须得到相同 Hash：

```json
{"path":"demo.txt","content":"hello"}
{"content":"hello","path":"demo.txt"}
```

这要求先把参数转成稳定字符串：

- `json.dumps(..., sort_keys=True)` 固定字段顺序；
- `separators=(",", ":")` 去掉无意义空格；
- `ensure_ascii=False` 保留一致的 UTF-8 文本；
- 最后用 `hashlib.sha256()` 计算十六进制摘要。

在 [`starter.py`](starter.py) 中实现：

- `arguments_sha256(arguments)`：返回 64 个字符的参数 Hash；
- `make_idempotency_key(tool_name, tool_call_id)`：返回 `工具名:tool_call_id`，并拒绝空值。

这里故意不把参数 Hash 直接当作幂等 Key。用户可能在两个不同请求中执行完全相同的命令；参数相同，不代表它们是同一个逻辑请求。Hash 负责证明参数没变，Key 负责标识调用身份。

继续运行：

```bash
python -B exercises/phase-1-capstone/starter.py --checkpoint-4
```

4A 通过后，当前会停在 `arguments_sha256()`。完成后应继续看到：

```text
checkpoint 4B passed
```

下一小关再把这三个身份写进一次真实的 Tool 执行：`tool_call_id` 不变，`execution_id` 每次变化，`idempotency_key` 用来识别同一个请求。

### 第四关 C：把 Ledger 接到真实工具前后

现在实现 `execute_workspace_tool_with_ledger()`。它不复制第二关的 Router，而是在副作用工具外面增加执行记录，再调用已有的 `execute_workspace_tool()`。

用户拒绝 `write_file` 时：

```text
生成 execution_id
-> 写 rejected
-> 返回 rejected Tool Result
-> 不调用 write_file
```

用户允许时：

```text
生成 execution_id
-> 写 approved
-> 写 running
-> 调用已有 Router，执行 write_file
-> 写 succeeded / failed
-> 返回带 execution_id 的 Tool Result
```

实现要求：

- `read_file` 和未知工具仍交给原 `execute_workspace_tool()`，这一关只给 `write_file`、`run_bash` 记录 Ledger；
- 使用 `json.loads()` 解析参数，并要求结果是字典；
- 每次进入函数都生成新的 `exec_<uuid>`；
- 使用 4B 的两个函数生成 `arguments_sha256` 和 `idempotency_key`；
- 每条状态都写入相同的 `tool_name`、`idempotency_key` 和 `arguments_sha256`；
- 用户拒绝时只写 `rejected`，不能出现 `running`；
- 用户允许时，必须在调用真实工具之前写完 `running`；
- 调用旧 Router 时传入 `lambda *_: True`，因为用户已经在外层批准，不能重复询问；
- 把旧 Router 返回的 JSON 字符串解析为字典，加上 `execution_id`，再保存终态并重新转成 JSON 字符串。

同一个 Tool Call 重试时：

```text
tool_call_id     相同
idempotency_key 相同
arguments_sha256 相同
execution_id    不同
```

运行：

```bash
python -B exercises/phase-1-capstone/starter.py --checkpoint-4
```

完成后应继续看到：

```text
checkpoint 4C passed
```

这一关仍不捕获“工具执行到一半进程消失”。此时 Ledger 最后停在 `running`；第五关会把这种状态恢复成 `unknown`，再决定是否允许重试。

### 第四关 D：把一次完整轮次串起来

4D 不新增生产函数，只验证前四层能否一起工作。测试把带 Ledger 的 Router 作为 `run_agent_loop()` 的 `execute_tool` 参数传入，执行一次真实 `write_file`。

同一个 Session JSONL 应按顺序留下：

```text
User Message
Assistant Tool Call
Tool Execution：approved
Tool Execution：running
Tool Execution：succeeded
Tool Result：带原 tool_call_id 和 execution_id
Assistant Final
```

磁盘一共有七条 Entry，但 `build_prompt_view()` 过滤三条内部 Ledger 记录后，Model 仍只看到四条 Message：

```text
User -> Assistant Tool Call -> Tool Result -> Assistant Final
```

这说明 Transcript 和 Ledger 可以放在同一份 JSONL，却承担不同职责。Ledger 负责查账；Tool Result 负责把执行结果告诉 Model。

继续运行同一个命令。设计接缝正确时，无须再写代码，最后会出现：

```text
checkpoint 4D passed
```

## 第五关：故障注入与恢复

正常运行只证明成功路径能走通。第五关会主动在最危险的位置制造崩溃：Tool 已经产生副作用，但 Harness 还没保存终态和 Tool Result。

### 第五关 A：在副作用之后立即崩溃

给 `execute_workspace_tool_with_ledger()` 增加了可选回调 `after_effect`。它必须在下面两步之间执行：

```text
write_file 已经替换目标文件
-> after_effect(result) 在这里运行
-> Ledger 写 succeeded
-> Transcript 写 Tool Result
```

测试传入的回调会直接抛出 `RuntimeError`，模拟进程在这一刻消失。正确结果不是“什么都没发生”，而是：

```text
answer.txt 已经包含 done
Ledger 最后状态仍是 running
Transcript 已保存 Assistant Tool Call
Transcript 没有 Tool Result
Transcript 没有 Assistant Final
```

你只需要在真实工具返回结果后、追加终态前调用一次：

```python
if after_effect is not None:
    after_effect(result)
```

不能把回调放在工具执行前，否则文件不会改变；也不能放在 `succeeded` 之后，否则 Ledger 会错误地声称已经完整收尾。

运行：

```bash
python -B exercises/phase-1-capstone/starter.py --checkpoint-5
```

当前会提示“故障注入回调必须被执行”。位置正确后，最后一行会变成：

```text
checkpoint 5A passed
```

这一步只制造并观察故障。下一小关才会在重启时把遗留的 `running` 改成 `unknown`。

### 第五关 B：重启后把 running 标成 unknown

进程崩溃后，不会有人替它写最后一条状态。新进程启动时只能看到：

```text
approved -> running -> 记录中断
```

`running` 不等于失败。工具可能尚未执行，也可能已经完成，只是 Harness 没来得及保存结果。恢复程序只能追加 `unknown`：

```text
approved -> running -> unknown
```

实现 `mark_interrupted_executions_unknown(session_file)`：

- 加载完整 JSONL；
- 使用 `latest_execution_states()` 找到每次执行的最后状态；
- 只处理最后状态仍为 `running` 的执行；
- 继续使用原 `execution_id` 和 `tool_call_id`，因为这不是一次新尝试；
- 复制已有的 `tool_name`、`idempotency_key` 和 `arguments_sha256`；
- 追加 `message: "进程在 running 状态中断，副作用无法确认"`；
- 返回被标记的 `execution_id` 列表；
- 第二次运行不应重复追加 `unknown`。

不要修改或删除旧的 `running` Entry。Ledger 是流水，恢复动作本身也要留下记录。

运行：

```bash
python -B exercises/phase-1-capstone/starter.py --checkpoint-5
```

5A 通过后，当前会停在 `mark_interrupted_executions_unknown()`。完成后应继续看到：

```text
checkpoint 5B passed
```

此时 Ledger 已经诚实表达“不确定”，但 Prompt 中仍有一条没有 Tool Result 的 Assistant Tool Call。下一小关再修复这条消息协议。

### 第五关 C：给孤立 Tool Call 补一张回执

5B 处理完后，磁盘可能是：

```text
User Message
Assistant Tool Call：call_1
Tool Execution：approved -> running -> unknown
```

Ledger 已经能查账，但 Provider 需要的消息仍不完整：Assistant 发出了 `call_1`，后面却没有带 `tool_call_id=call_1` 的 Tool Result。此时直接加入新的 User Message，Provider 可能拒绝整个请求。

代码已经提供两个辅助函数：

- `pending_tool_calls(entries)`：找出有 Tool Call、没有对应 Tool Result 的申请；
- `latest_execution_by_tool_call(entries)`：按 `tool_call_id` 找到最后一条 Ledger 状态。

现在实现 `repair_missing_tool_results(session_file)`。它先调用 5B，把遗留 `running` 标成 `unknown`，然后为每个孤立 Tool Call 补写一条 `role: tool` Message。

不同 Ledger 状态这样处理：

```text
unknown
-> 返回 status=unknown、原 execution_id 和“不确定”说明
-> 不执行 Tool

rejected
-> 返回 status=rejected 和原 execution_id

succeeded / failed
-> 从 Ledger 的 result 字段重放已经保存的结果

没有 Ledger、状态仍是 approved/running、终态缺少 result
-> 抛出 RuntimeError，不能编造结果
```

回放前还要重新计算 Tool Call 参数 Hash，与 Ledger 的 `arguments_sha256` 比较。不同就停止恢复，说明调用内容和执行记录已经对不上。

每条补写 Message 的形状是：

```json
{
  "role": "tool",
  "tool_call_id": "call_1",
  "content": "{\"status\":\"unknown\",...}"
}
```

补写成功后返回 `tool_call_id` 列表。第二次运行时，这些调用已经有 Result，不能重复追加。

继续运行：

```bash
python -B exercises/phase-1-capstone/starter.py --checkpoint-5
```

完成后应继续看到：

```text
checkpoint 5C passed
```

这一步只把 Prompt 修成合法形状。下一小关才把修复后的 Tool Result 重新交给 Model，让它给出 Assistant Final。

### 第五关 D：继续旧 Turn，而不是开启新 Turn

5C 结束后，Prompt 是：

```text
User
Assistant Tool Call
Tool Result：unknown 或已保存结果
```

这一轮还没有 Assistant Final。此时若直接调用原 `run_agent_loop(..., user_text="新问题")`，代码会先追加新的 User Message：

```text
User -> Assistant Tool Call -> Tool Result -> 新 User
```

旧 Turn 被新问题从中间打断了。正确顺序应该先让 Model 阅读修复后的 Tool Result，完成旧 Turn：

```text
User -> Assistant Tool Call -> Tool Result -> Assistant Final
```

把 `run_agent_loop()` 的 `user_text` 类型改成 `str | None`：

- `user_text` 是字符串：保持原行为，追加新的 User Message；
- `user_text is None`：不追加 User Message，直接继续磁盘中的旧 Turn；
- 恢复模式必须提供 `session_file`；
- 恢复出的 Prompt 必须非空，并且最后一条是 `role: tool`；否则抛出 `ValueError`。

只修改加载 `messages` 后、进入 `for` 循环前的入口判断。后面的模型请求、Tool Call、停止条件和持久化全部复用。

运行：

```bash
python -B exercises/phase-1-capstone/starter.py --checkpoint-5
```

完成后应继续看到：

```text
checkpoint 5D passed
```

到这里，崩溃后的原子 Turn 才重新闭合。下一小关会区分哪些 `unknown` 能安全重试，哪些必须先询问用户或查询外部回执。

### 第五关 E：先对账，不要看到 unknown 就重试

`unknown` 只说明“Ledger 没拿到最终回执”，不等于 Tool 没有执行。恢复时首先应该检查外部世界现在是什么样。

对完整覆盖写入 `write_file(path, content)`，可以检查目标文件是否已经等于请求内容：

```text
目标文件 Byte 与 content 的 UTF-8 Byte 完全相同
-> 原请求要求的最终状态已经满足
-> 不重新写文件
-> 在原 execution_id 后追加 succeeded
-> result 标记 reconciled=true
```

这只能证明“目标状态已经满足”，不能证明旧进程到底写了几次。因此旧的 `unknown` 仍保留在 Ledger，新的结果必须带 `reconciled: true`。

以下情况保持 `unknown`：

- 文件不存在；
- 文件内容不同；
- Tool 是任意 `run_bash`；
- Tool Call 参数 Hash 与 Ledger 不一致。

内容不同时不能自动覆盖。文件可能在崩溃后被用户或另一个进程修改；当前 Ledger 又没有保存旧文件版本，无法判断覆盖是否安全。

实现 `reconcile_unknown_write_files(workspace, session_file)`：

- 只检查仍缺 Tool Result 的调用；
- 只处理最后状态为 `unknown` 的 `write_file`；
- 校验参数是字典，并核对 `arguments_sha256`；
- 使用已有的 `resolve_workspace_file()` 检查路径；
- 使用 `target.read_bytes()` 与 `content.encode("utf-8")` 比较；
- 匹配时沿用原 `execution_id`、`tool_call_id` 和三项身份字段；
- 追加带完整 `result` 的 `succeeded`；
- 返回已经对账成功的 `tool_call_id` 列表；
- 第二次运行不能重复追加。

结果使用：

```json
{
  "status": "succeeded",
  "execution_id": "exec_1",
  "path": "answer.txt",
  "bytes_written": 4,
  "reconciled": true
}
```

运行：

```bash
python -B exercises/phase-1-capstone/starter.py --checkpoint-5
```

完成后应继续看到：

```text
checkpoint 5E passed
```

此时 `repair_missing_tool_results()` 可以重放对账后的 `succeeded`，仍然不会再次执行 `write_file`。任意 Bash 保持 `unknown`，交给 Model 提醒用户核对。
