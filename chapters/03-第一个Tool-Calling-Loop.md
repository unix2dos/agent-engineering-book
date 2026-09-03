# 第 3 课：跑通第一个 Tool Calling Loop

> 本章用一个无副作用的整数乘法工具，跑通有限步、可观察、协议完整的 OpenAI-compatible Tool Calling Loop。完整代码见 [`lesson_03_tool_calling_loop.py`](../examples/lesson_03_tool_calling_loop.py)。

本课只做一件事：让 Model 请求一次乘法工具，拿到结果，再回答用户。这个例子故意不从 `read_file` 或 Bash 开始。先把最小消息循环跑通，再增加权限、持久化和故障恢复；否则测试失败时，很难判断是 Tool Calling 断了，还是文件系统出了问题。

## 本章怎样学

| 类型 | 本章要求 |
| --- | --- |
| 必须亲写 | `run_agent_loop()` 的三个分支、Tool Result 配对和请求次数上限 |
| 允许 AI | SDK 初始化、Fake Response 和重复的类型转换代码 |
| 必须验证 | 先运行本课自检，再完成综合实践中的多 Tool Call、矛盾停止状态和请求上限测试 |
| 只需读懂 | OpenAI Responses 与 Chat Completions 的字段差异，本练习只实现后一种 |

## 1. 先看一次完整的四条 Message

用户要求计算 `248 × 15`。完整历史最后是：

```text
1. User：帮我算一下 248 乘以 15
2. Assistant Tool Call：multiply(a=248, b=15)，id=call_1
3. Tool Result：result=3720，tool_call_id=call_1
4. Assistant Final：248 乘以 15 等于 3720
```

四条 Message 不是一次 API 返回的。运行过程是：

```text
第一次请求：User + Tool Schema
第一次返回：Assistant Tool Call
本地执行：  multiply(248, 15)
第二次请求：前三条 Message + Tool Schema
第二次返回：Assistant Final
```

这里有四条 Message、两次模型请求、一次本地工具执行，但只处理了一个用户问题，所以它们共同组成一个 User Turn。

最重要的责任边界也已经出现：Model 只生成 `multiply` 的调用申请，真正执行 `a * b` 的是本地 Python。

## 2. 准备一个边界清楚的 Tool

本地工具只接收两个整数：

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

为什么不用更省事的 `eval(expression)`？因为 `expression` 来自 Model，而 Model 又受用户和外部内容影响。`eval()` 执行的是 Python 代码，不是受限数学语言；不可信输入可能借它读取文件、导入模块或启动进程。[Python `eval()`](https://docs.python.org/3/library/functions.html#eval)

固定的 `multiply()` 功能少，但边界清楚：Model 只能提供数据，不能改变程序准备执行什么代码。

`bool` 需要单独拒绝，因为 Python 中 `isinstance(True, int)` 是 `True`。如果只检查 `int`，`multiply(True, 15)` 会悄悄得到 `15`。

Model 还需要知道这个工具怎样申请。Tool Schema 就是说明书：

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

它告诉 Model：工具名是 `multiply`，必须提供整数 `a` 和 `b`，不能增加其他字段。Schema 不会执行 Python，也不是权限证明；它只提高 Model 生成正确申请的概率。

## 3. Harness 让四条 Message 跑起来

Agent Loop 每次请求后只做三种选择：执行工具并继续、返回 Final、或者报错停止。

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

每次返回后，Harness 先保存完整 Assistant Message。若里面有 Tool Call，就逐个执行并追加 Tool Result，然后 `continue` 发起下一次模型请求。若没有 Tool Call 且正常结束，才返回 Final。其他状态直接报错。

`step` 表示第几次模型请求，不是消息数。一次请求可能生成多个 Tool Call，因此也可能追加多条 Tool Result。

## 4. `tool_call_id` 把申请和回执配成一对

Assistant 可能一次请求两个工具：

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

`tool_call_id` 就像订单号。没有它，Model 无法判断哪份结果回答哪次调用。只有 Tool Result、没有前面的 Assistant Tool Call，也是一张找不到原订单的回执，Provider 可以拒绝整个请求。

同一批 Tool Call 可以顺序执行，也可以并行执行，但下一次请求必须包含每一个调用的结果。失败和拒绝也要带原来的 ID 返回，不能静默丢掉。

## 5. 跑通之后，再补失败路径

Schema 只负责引导 Model，本地 Router 仍要检查真实输入。下面的代码依次检查工具名、JSON 外形、字段集合和参数类型：

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

普通参数错误会变成受控 Tool Result，Model 可以据此修正申请。协议本身不可信时则要停止 Loop。例如：

```text
消息包含 Tool Call
但 finish_reason 表示输出被长度截断
```

此时参数可能只有半段，不能执行。`message.tool_calls` 回答“Model 生成了什么调用”；`choice.finish_reason` 回答“Provider 为什么停止本次生成”，两边必须一致。

最大请求次数是最后一道刹车。它能阻止 Agent 无限循环、持续花钱，却不能修复错误 Prompt 或反复失败的 Tool。

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

自检使用 Fake Model Response，验证一次成功调用、额外参数被拒绝、Tool Result ID 配对，以及长度截断不会被当作 Final。它不访问网络，也不能证明 API Key、模型名称或兼容 Provider 支持 Tool Calling。

在线运行使用当前 [openai-python v3.7.0](https://github.com/openai/openai-python/releases/tag/v3.7.0)：

```bash
python -m pip install openai

export OPENAI_API_KEY="your-api-key"
export OPENAI_MODEL="your-model"
# 第三方兼容端点才需要设置：
export OPENAI_BASE_URL="https://provider.example/v1"

python examples/lesson_03_tool_calling_loop.py
```

当前 OpenAI 官方指南主要使用 Responses API 的 `function_call -> function_call_output`。本章使用 Chat Completions 的 `assistant.tool_calls -> role=tool`，是为了观察许多 OpenAI-compatible Provider 仍在使用的四条 Message。字段外形不同，责任链相同：Model 申请，应用执行，结果回传。[OpenAI Function Calling](https://developers.openai.com/api/docs/guides/function-calling)

在线请求第一次就返回“模型不支持 tools”时，本地 `multiply()` 尚未执行。应先检查 Provider、模型能力、模型名和 API 路径，而不是修改乘法函数。

完整代码不要抄完就算结束。进入[第一阶段综合实践](../exercises/phase-1-capstone/README.md)，亲手完成第一关；它补充验证同批多个 Tool Call、Tool Call 与停止状态矛盾，以及达到模型请求上限。

## 7. 本课还没有解决什么

本课结束时，完整 Turn 只在 Python 内存里：

```text
User -> Assistant Tool Call -> Tool Result -> Assistant Final
```

程序退出后，消息全部消失；代码也没有 Context 预算、摘要、长期 Memory 或副作用恢复。下一课从这四条 Message 出发，区分 [Session、Checkpoint 与长期记忆](04-Session-Checkpoint与长期记忆.md)。

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
