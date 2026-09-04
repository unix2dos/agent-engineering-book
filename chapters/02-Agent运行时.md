# 第 2 课：Agent Runtime——Model、Harness、Tool 与 Environment

你让 Agent“读取 `config.json`，再告诉我里面使用什么主题”。Model 很快回答：“我来读取。”但这绝不等于文件已经被打开。

Model 只能生成一张 `read_file` 申请单。真正打开文件的，是它外面的宿主程序：它需要校验路径合法性、检查执行权限与停止条件，再将真实读取结果送回 Model。

## 1. Model 说要读文件，谁真的动手？

一次完整调用这样发生：

```text
User Request
→ Harness 把历史和 Tool Schema 发给 Model
→ Model 返回 read_file Tool Call
→ Harness 检查协议、参数、权限与审批
→ Tool 读取文件系统
→ Environment 返回内容或错误
→ Harness 写入 Tool Result
→ Model 根据真实结果继续调用工具或给出 Final
```

夹在 Model 和真实世界之间、负责推动这条流程的程序，通常叫 **Harness**。而由 Model、Harness、Tool 与 Environment 共同构成的可运行整体，就是 **Agent Runtime**。

现在再看这四个核心部分分别负责什么：

| 核心组件 | 职责描述 | 职责边界（不负责什么） |
| --- | --- | --- |
| Model | 判断下一步，写出工具名和参数 | 不直接拥有本地文件权限 |
| Harness | 保存消息、检查申请、找到工具并控制循环 | 不替 Model 决定开放任务该怎么做 |
| Tool | 完成一个具体动作，例如读取文件 | 不决定自己何时出场 |
| Environment | 文件、Shell、网页和 API 所处的真实世界 | 不保证返回内容安全可靠 |

Harness 不是只会转发消息。最大步骤、超时、参数检查、用户审批和崩溃恢复，最终都要由可以执行代码的程序完成。Model 选择 `read_file`，Harness 判断本次能不能执行，Tool 才真正接触文件系统。

OpenCode 也把这几件事放在不同模块：[Session Processor](https://github.com/anomalyco/opencode/blob/50efc055de282e0e54a87ccebb8e2054cc45efd2/packages/opencode/src/session/processor.ts)处理会话运行，[Tool Registry](https://github.com/anomalyco/opencode/blob/50efc055de282e0e54a87ccebb8e2054cc45efd2/packages/opencode/src/tool/registry.ts)寻找工具实现，[Permission Evaluation](https://github.com/anomalyco/opencode/blob/50efc055de282e0e54a87ccebb8e2054cc45efd2/packages/opencode/src/permission/evaluate.ts)判断是否允许。Model 写出调用、程序找到工具、策略允许执行，本来就是三个动作。

## 2. Model 怎样知道 `read_file` 要填什么？

应用要先给 Model 一张工具说明书，写清工具名、用途和参数。这个结构叫 Tool Schema。Anthropic 客户端工具把参数说明放在 `input_schema` 中：

```json
{
  "name": "read_file",
  "description": "Read a UTF-8 file inside the workspace",
  "input_schema": {
    "type": "object",
    "properties": {
      "path": {"type": "string"}
    },
    "required": ["path"]
  }
}
```

Schema 像一张空白申请表。它只说明工具叫什么、参数应该怎样填写，不会把 Python 函数上传给 Model，也不会赋予本地文件权限。

```text
Model     只看见工具说明
Harness   决定这次能否调用
Tool      使用当前进程已有的能力
OS        规定这个进程最终能访问什么
```

即使提供模型 API 的服务方（Provider）严格检查 Schema，本地程序仍要防住未知工具、坏 JSON、额外参数和路径逃逸。表格填对了，不代表这个动作应该获准。

## 3. Tool Call 怎样变成真正的执行结果？

Model 决定读取文件后，会返回一块结构化数据。在 Anthropic Messages API 中，这一块叫 `tool_use`：

```json
{
  "type": "tool_use",
  "id": "toolu_A",
  "name": "read_file",
  "input": {"path": "config.json"}
}
```

这仍然只是一张申请单。Harness 检查并执行后，下一次请求再用 `tool_result` 把结果送回：

```json
{
  "role": "user",
  "content": [
    {
      "type": "tool_result",
      "tool_use_id": "toolu_A",
      "content": "{\"theme\":\"dark\"}"
    }
  ]
}
```

OpenAI-compatible Chat Completions 使用另一套外形：

```text
Assistant tool_calls[].id
→ Tool Message 的 tool_call_id
```

字段名不同，责任相同：每份结果必须回答原来的那张申请单。没有 ID，系统不知道错误属于 `read_file` 还是 `run_bash`；配错 ID，格式看似完整，语义却已经错位。

上面的 `read_file` 由我们自己的应用执行，所以叫客户端工具。Web Search、Code Execution 等能力也可以由 Provider 直接执行，那是服务端工具。Model 自己不执行客户端工具，不等于所有工具都在本机运行。[Anthropic：How tool use works](https://platform.claude.com/docs/en/agents-and-tools/tool-use/how-tool-use-works)

## 4. 一次申请两个工具怎么办？

假设 Assistant Message 同时提出：

```text
toolu_A：read_file("config.json")
toolu_B：run_bash("rm -rf output")
```

Harness 可以顺序执行，也可以并行执行。第一项可能成功，第二项可能被策略拒绝。下一次请求仍要为两个调用各返回一份结果：

```text
toolu_A → succeeded，附文件内容
toolu_B → rejected，明确说明没有执行
```

拒绝、超时和失败也属于结果。静默丢掉 `toolu_B`，Model 会一直等待，或者误以为它仍在运行。

如果一次出现 30 个 Tool Call，仍要逐个配对。真正不希望一次调用太多工具，应该由 Harness 提前限制数量、并发和总预算，不能执行到一半后随意丢掉结果。

## 5. 一次生成停止，不等于一个 Turn 已完成

Model 每次调用最终都会停下来，但“这次生成停了”和“用户的任务完成了”不是一回事。

假设 Model 正在生成 `read_file` 的参数，却只生成到这里：

```text
tool_name = "read_file"
arguments = '{"path":"config'
stop_reason = "输出达到长度上限"
```

Provider 已经返回 Response，所以这次生成确实停止了。但 `arguments` 只有半段，既不是可以执行的 Tool Call，也不是面向用户的 Final。Harness 如果只判断“API 已经返回”，就可能把半截参数交给工具，或者把半截文字保存成成功答案。

Harness 要把停止后的 Response 分成三类：

| Response 状态 | Harness 的动作 |
| --- | --- |
| 包含完整客户端 Tool Call，停止状态也与工具调用一致 | 校验并执行工具，回传 Tool Result，继续循环 |
| 没有 Tool Call，并且是应用接受的正常结束 | 保存并返回 Assistant Final |
| 参数截断、暂停、拒绝、状态矛盾或达到 Harness 请求上限 | 不执行半截动作，也不冒充成功；按情况恢复或报错 |

下面的伪代码现在就有了明确含义：

```text
response = call_model(history, tools)

if response contains complete client tool calls:
    validate stop state
    execute every call with policy
    append every tool result
    continue

if response is an accepted normal ending:
    return final text

stop with a controlled error
```

流式输出也遵守同一条边界。已经生成的文字可以先显示给用户，但只有 Harness 接受正常结束状态后，才允许把整条消息保存成 Assistant Final。[Anthropic 当前工具循环](https://platform.claude.com/docs/en/agents-and-tools/tool-use/how-tool-use-works#the-agentic-loop-client-tools)

## 6. `read_file` 能用了，就已经安全吗？

`read_file` 的路径不能只检查字符串前缀。`workspace/link/secret` 看似在 Workspace 内，`link` 却可能指向外部目录。必须解析真实路径，再检查最终目标仍在允许范围内。

Tool Result 也不是越完整越好。一个 500 KB 日志会挤满 Model 本次能看的内容。日志里还可能夹着恶意文字，诱导 Model 请求危险动作，这叫提示注入。

Tool 应返回受限片段、截断标记和回查位置。完整日志可以另存成文件，需要时再查；这样的完整产物常叫 Artifact。

```json
{
  "path": "logs/build.log",
  "content": "...最后一段错误...",
  "truncated": true,
  "next_offset": 51200
}
```

这些限制仍不会让 Tool 自动安全。路径检查挡不住网络访问，`cwd=workspace` 也只规定命令从哪里开始。它不是一道由操作系统强制执行的隔离墙，也就是 Sandbox。

现成框架不会改变上面的责任链。Agent SDK 可以帮你封装部分 Harness，MCP 可以帮 Harness 连接外部 Tool。它们解决了“怎样接起来”，没有自动回答“本次是否应该执行”。

下一课会把这些箭头写成可运行代码：[Tool Calling Loop——从调用请求到最终回答](03-工具调用循环.md)。配套练习已经在[阶段一～二综合实践](../exercises/phase-1-capstone/README.md)中覆盖多 Tool Call、矛盾停止状态、Workspace 边界和审批。

## 7. 自己检查一次工具调用

最值得亲手做的是，把一次 Tool Call 写成完整顺序：Model 申请，Harness 检查，Tool 执行，Tool Result 回传，Model 再给 Final。

然后制造一个有两张申请单的场景：`read_file` 成功，危险的 `run_bash` 被拒绝。下一次模型请求必须同时带上成功结果和拒绝结果，两份回执都要保留原 ID。

SDK 类型定义与协议初始化可直接参考官方范式，核心精力应放在核验 Message 数组的真实结构上，确认每一个 Tool Call 与 Tool Result 的 ID 严格成对闭环。不同厂商的具体字段命名只需理解其映射关系，无需死记硬背。

## 主动回忆

1. Model、Harness、Tool 与 Environment 分别负责什么？
2. 为什么 Tool Schema 不是本地文件的权限证明？
3. Model 返回 Tool Call 后，Harness 至少还要做什么？
4. `tool_use_id` 与 `tool_call_id` 有什么共同作用？
5. 为什么已经流式显示的文字仍可能不是成功 Final？
6. 一批调用中一个成功、一个拒绝，下一次请求应该包含什么？
7. 为什么字符串前缀检查挡不住符号链接？
8. Model 生成了半截工具参数时，Harness 为什么既不能执行，也不能返回 Final？

<details>
<summary>检查简答</summary>

1. Model 选择动作；Harness 维护循环和策略；Tool 执行动作；Environment 返回真实状态。
2. Schema 只描述参数形状；实际权限来自 Harness 策略、进程身份和操作系统。
3. 检查工具、参数、路径、权限和审批，执行后用原 ID 回传结果。
4. 都把 Tool Result 对应回原 Tool Call。
5. 输出可能被截断、暂停或拒绝；只有接受的正常结束状态才结束轮次。
6. 同时返回成功结果与拒绝结果，两者都保留各自 ID。
7. 符号链接可能把表面上的内部路径指向 Workspace 外部。
8. 参数不完整，执行可能产生错误或危险副作用；任务也尚未正常结束，不能伪装成 Final。

</details>

## 参考资料

> 资料最后核验于 2026-09-03；会变化的源码锚点收录在下面的复核记录中。

- [本批章节一手资料复核](../research/01-05-chapter-promotion-sources.md)
- [Anthropic：How tool use works](https://platform.claude.com/docs/en/agents-and-tools/tool-use/how-tool-use-works)
- [Anthropic Go SDK v1.69.0 工具示例](https://github.com/anthropics/anthropic-sdk-go/blob/v1.69.0/examples/tools/main.go)
- [Anthropic Go SDK v1.69.0 Tool Runner](https://github.com/anthropics/anthropic-sdk-go/blob/v1.69.0/examples/tool-runner/main.go)
- [OpenAI：Function calling](https://developers.openai.com/api/docs/guides/function-calling)
