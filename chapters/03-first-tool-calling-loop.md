# 第 3 课：跑通第一个 Tool Calling Loop

> 本章用一个无副作用的整数乘法工具，跑通有限步、可观察、协议完整的 OpenAI-compatible Tool Calling Loop。完整代码见 [`lesson_03_tool_calling_loop.py`](../examples/lesson_03_tool_calling_loop.py)。

最终消息序列只有四条：

```text
User
-> Assistant(tool_calls)
-> Tool(tool_call_id, result)
-> Assistant(final)
```

这个例子故意不从 `read_file` 或 Bash 开始。先把消息协议跑对，再增加权限、持久化和故障恢复；否则测试失败时，很难判断是 Tool Calling 断了，还是文件系统出了问题。

## 本章怎样学

| 类型 | 本章要求 |
| --- | --- |
| 必须亲写 | `run_agent_loop()` 的分支、Tool Result 配对和请求次数上限 |
| 允许 AI | SDK 初始化、Fake Response 和重复的类型转换代码 |
| 必须验证 | 多 Tool Call、坏参数、矛盾停止原因、达到请求上限四条失败路径 |
| 只需读懂 | OpenAI Responses 与 Chat Completions 的字段差异，本练习只实现后一种 |

## 1. Model 只申请，Python 才执行

用户要求计算 `248 × 15`。第一次请求包含 User Message 和 Tool Schema：

```text
User: 帮我算一下 248 乘以 15
Tools: multiply(a: integer, b: integer)
```

Model 返回一张调用申请：

```json
{
  "id": "call_1",
  "type": "function",
  "function": {
    "name": "multiply",
    "arguments": "{\"a\":248,\"b\":15}"
  }
}
```

Python 解析参数，调用本地 `multiply()`，再把结果作为 `role: tool` Message 放回历史。第二次请求中，Model 看到真实结果 `3720`，才能给出 Final。

当前 OpenAI 官方 Function Calling 指南主要用 Responses API 展示 `function_call → function_call_output`。本章保留 Chat Completions 的 `assistant.tool_calls → role=tool`，因为很多兼容 Provider 仍使用它，而且四条 Message 更适合观察协议。两种外形不同，都是“Model 申请，应用执行，再回传结果”。[OpenAI Function Calling](https://developers.openai.com/api/docs/guides/function-calling)

## 2. 不要让 Model 控制 `eval()`

计算器教程常见：

```python
eval(expression)
```

但 `expression` 来自 Model，而 Model 又会受到用户和外部内容影响。`eval()` 执行 Python 代码，不是受限数学语言；它可能读文件、导入模块或启动进程。[Python `eval()`](https://docs.python.org/3/library/functions.html#eval)

本课只暴露固定运算：

```python
MAX_ABS_VALUE = 1_000_000


def multiply(a: int, b: int) -> int:
    if (
        isinstance(a, bool)
        or isinstance(b, bool)
        or not isinstance(a, int)
        or not isinstance(b, int)
    ):
        raise ValueError("a 和 b 必须是整数")
    if abs(a) > MAX_ABS_VALUE or abs(b) > MAX_ABS_VALUE:
        raise ValueError("数字太大")
    return a * b
```

Model 只能提供两个数据，程序执行的永远是固定乘法。这个接口功能少，却容易说明安全边界。

`bool` 需要单独拒绝，因为 Python 中 `isinstance(True, int)` 是 `True`。如果只检查 `int`，`multiply(True, 15)` 会悄悄得到 `15`。

## 3. Schema 和执行侧要各守一层

Tool Schema 告诉 Model 正确参数长什么样：

```python
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "multiply",
            "description": "Multiply two integers",
            "parameters": {
                "type": "object",
                "properties": {
                    "a": {"type": "integer"},
                    "b": {"type": "integer"},
                },
                "required": ["a", "b"],
                "additionalProperties": False,
            },
        },
    }
]
```

Schema 负责引导生成，本地 Router 才是执行前的门。Model 或兼容 Provider 仍可能给出坏 JSON、未知工具、错误类型或额外字段。

```python
def execute_tool(tool_call: object) -> str:
    try:
        if tool_call.function.name != "multiply":
            raise ValueError("未知工具")
        arguments = json.loads(tool_call.function.arguments)
        if not isinstance(arguments, dict):
            raise ValueError("工具参数必须是 JSON 对象")
        if set(arguments) != {"a", "b"}:
            raise ValueError("multiply 只接受 a 和 b")
        payload = {
            "status": "completed",
            "result": multiply(arguments["a"], arguments["b"]),
        }
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
        payload = {"status": "error", "message": str(error)}
    return json.dumps(payload, ensure_ascii=False)
```

普通参数错误可以变成受控 Tool Result，让 Model 修正后再试。若 Tool Call 缺少 ID、参数在生成中途被截断，或协议字段互相矛盾，当前状态已经不可信，Harness 应停止整个 Loop。

## 4. 有限步 Agent Loop

核心循环是两次模型请求，中间夹一次本地执行：

```python
for step in range(MAX_STEPS):
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        tools=TOOLS,
    )
    choice = response.choices[0]
    message = choice.message
    messages.append(assistant_message_from_api(message))

    if message.tool_calls:
        if choice.finish_reason != "tool_calls":
            raise RuntimeError("Tool Call 与停止原因不一致")
        for tool_call in message.tool_calls:
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": execute_tool(tool_call),
                }
            )
        continue

    if choice.finish_reason == "stop":
        return message.content or ""

    raise RuntimeError("模型没有正常结束")

raise RuntimeError("超过最大模型请求次数")
```

`message.tool_calls` 回答“Model 请求了哪些工具”；`choice.finish_reason` 回答“Provider 为什么停止这次生成”。正常工具调用要同时满足两边一致。

若 `message` 含有 Tool Call，停止原因却表示输出被截断，参数可能只生成了一半，绝不能交给执行器。最大请求次数也只是一条止损线：它能限制时间和费用，不能修复错误 Prompt 或反复失败的 Tool。

注意 `step` 表示第几次模型请求，不是消息数。一次请求可能生成多个 Tool Call，对应多个 Tool Result Message。

## 5. `tool_call_id` 是订单号

Assistant 一次请求两个工具：

```text
call_1 -> multiply(248, 15)
call_2 -> multiply(6, 7)
```

每份 Tool Result 都要带回原 ID：

```python
{
    "role": "tool",
    "tool_call_id": tool_call.id,
    "content": result,
}
```

没有 ID，Model 无法判断哪份结果回答哪次调用。只有 Tool Result、没有前面的 Assistant Tool Call，也是一条孤立回执，Provider 可以直接拒绝整个请求。

这个 ID 只标识模型协议中的一次 Tool Call。以后还会出现 `execution_id` 和 `idempotency_key`：前者标识某次真实执行尝试，后者标识不能重复产生副作用的业务动作。三者不能互换。

## 6. 运行和验证

先克隆仓库并运行本地自检：

```bash
git clone https://github.com/unix2dos/agent-engineering-book.git
cd agent-engineering-book
python -B examples/lesson_03_tool_calling_loop.py --self-check
```

预期输出：

```text
self-check passed
```

自检使用 Fake Model Response，验证本地 Router、参数校验、ID 配对和主要控制流。它不访问网络，也不能证明 API Key、模型名称或兼容 Provider 支持 Tool Calling。

在线运行使用当前 [openai-python v3.7.0](https://github.com/openai/openai-python/releases/tag/v3.7.0)：

```bash
python -m pip install openai

export OPENAI_API_KEY="your-api-key"
export OPENAI_MODEL="your-model"
# 第三方兼容端点才需要设置：
export OPENAI_BASE_URL="https://provider.example/v1"

python examples/lesson_03_tool_calling_loop.py
```

在线请求第一次就返回“模型不支持 tools”时，本地 `multiply()` 尚未执行。应先检查 Provider、模型能力、模型名和 API 路径，而不是修改乘法函数。

完整代码不要抄完就算结束。进入[第一阶段综合实践](../exercises/phase-1-capstone/README.md)，亲手完成第一关；它额外验证多 Tool Call、矛盾停止原因和请求次数上限。

## 7. 本课还没有解决什么

本课结束时，完整 Turn 只在 Python 内存里：

```text
User -> Assistant Tool Call -> Tool Result -> Assistant Final
```

程序退出后，消息全部消失；代码也没有 Context 预算、摘要、长期 Memory 或副作用恢复。下一课从这四条 Message 出发，区分 [Session、Checkpoint 与长期记忆](04-session-checkpoint-memory.md)。

## 主动回忆

1. 完整 Tool Calling Turn 的四条 Message 按什么顺序出现？
2. 为什么不能把 Model 生成的表达式交给 `eval()`？
3. 有 Tool Schema，执行侧为什么仍要验证？
4. 为什么必须先保存 Tool Call，再保存对应 Tool Result？
5. `message.tool_calls` 与 `choice.finish_reason` 分别说明什么？
6. 最大步骤数限制什么，又不能解决什么？
7. 为什么 `multiply()` 要拒绝 `bool`？
8. `--self-check` 能证明什么，不能证明什么？

<details>
<summary>检查简答</summary>

1. `user -> assistant(tool_calls) -> tool(tool_call_id, result) -> assistant(final)`。
2. `eval()` 会执行不可信 Python 代码；固定函数只接收数据并执行固定动作。
3. Schema 引导 Model 生成，本地校验才守住真实执行边界。
4. Tool Result 必须用 ID 回答已经存在的 Tool Call，否则请求与回执无法配对。
5. 前者保存 Model 生成的调用，后者说明 Provider 为什么停止生成。
6. 它限制模型请求次数、时间和费用；不能修复循环根因。
7. Python 把 `bool` 当作 `int` 的子类。
8. 它验证本地消息组织和控制流；不验证凭据、网络、Provider 或真实 Model。

</details>

## 参考资料

- [本批章节一手资料复核](../research/01-05-chapter-promotion-sources.md)
- [完整教学代码](https://github.com/unix2dos/agent-engineering-book/blob/main/examples/lesson_03_tool_calling_loop.py)
- [第一阶段综合实践](https://github.com/unix2dos/agent-engineering-book/tree/main/exercises/phase-1-capstone)
- [OpenAI Function Calling](https://developers.openai.com/api/docs/guides/function-calling)
- [openai-python v3.7.0](https://github.com/openai/openai-python/releases/tag/v3.7.0)
- [Python `eval()`](https://docs.python.org/3/library/functions.html#eval)
