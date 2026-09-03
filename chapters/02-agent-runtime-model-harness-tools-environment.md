# 第 2 课：模型、Harness、工具与环境

> 本章沿一次“读取配置文件”的调用，拆开 Agent Runtime 中四个部分的责任。资料最后核验于 2026-09-03；源码锚点见[第 1～5 课一手资料复核](../research/01-05-chapter-promotion-sources.md)。

第 1 课用一句话描述最小 Agent：模型根据环境反馈，在循环中动态决定下一步。真正写代码时，“循环”不能保持为一个模糊的箭头。

```text
Tool-using Agent Runtime
= Model + Harness + Tools + Environment
```

## 本章怎样学

| 类型 | 本章要求 |
| --- | --- |
| 必须亲写 | 把一次 Tool Call 展开成请求、校验、审批、执行、结果回传与 Final |
| 允许 AI | 生成 Provider 的类型定义和 SDK 样板，但必须自己检查真实 Message |
| 必须验证 | 同一轮返回两个 Tool Call，其中一个成功、一个拒绝；两个结果都要正确回传 |
| 只需读懂 | Anthropic 与 OpenAI-compatible 的字段差异，不要求背 API 字段表 |

## 1. 一次工具调用里，谁做了什么

用户要求“读取 `config.json` 并解释”。完整过程不是 Model 直接打开文件：

```text
User Request
-> Harness 把历史和 Tool Schema 发给 Model
-> Model 返回 read_file Tool Call
-> Harness 检查协议、参数、权限与审批
-> Tool 读取文件系统
-> Environment 返回内容或错误
-> Harness 写入 Tool Result
-> Model 根据真实结果继续调用工具或给出 Final
```

| 部分 | 负责什么 | 不负责什么 |
| --- | --- | --- |
| Model | 理解目标，选择下一步，生成工具名和参数 | 不直接拥有本地权限 |
| Harness | 维护消息和循环，校验协议，路由工具，控制权限与停止 | 不替 Model 做开放式决策 |
| Tool | 执行一个边界清楚的动作 | 不决定何时调用自己 |
| Environment | 提供文件、Shell、网页或 API 的真实状态 | 不保证返回内容安全或适合直接进入 Prompt |

Harness 不是只会转发的胶水。最大步骤、超时、参数校验、审批、持久化和恢复都要落在可执行程序里。Model 选择 `read_file`，Harness 判断本次是否允许，Tool 才真正接触 Environment。

[OpenCode 的 Session Processor](https://github.com/anomalyco/opencode/blob/50efc055de282e0e54a87ccebb8e2054cc45efd2/packages/opencode/src/session/processor.ts)、[Tool Registry](https://github.com/anomalyco/opencode/blob/50efc055de282e0e54a87ccebb8e2054cc45efd2/packages/opencode/src/tool/registry.ts)和[权限判断](https://github.com/anomalyco/opencode/blob/50efc055de282e0e54a87ccebb8e2054cc45efd2/packages/opencode/src/permission/evaluate.ts)分别落在不同模块，正说明“生成调用、找到实现、允许执行”不是同一个动作。

## 2. Tool Schema 是说明书，不是门禁卡

应用先把工具描述交给 Model。Anthropic 客户端工具使用 `input_schema`：

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

Schema 只说明工具叫什么、参数长什么样。它不会把 Python 函数上传给 Model，也不会赋予本地文件权限。

```text
Model     只看见工具说明
Harness   决定这次能否调用
Tool      使用当前进程已有的能力
OS        规定这个进程最终能访问什么
```

即使 Provider 支持严格 Schema，本地执行侧仍要验证未知工具、坏 JSON、额外参数、路径逃逸和业务权限。生成格式正确，不等于动作安全。

## 3. Tool Call 只是申请

Anthropic Messages API 的客户端工具请求使用 `tool_use` Content Block：

```json
{
  "type": "tool_use",
  "id": "toolu_A",
  "name": "read_file",
  "input": {"path": "config.json"}
}
```

应用执行后，在下一条 User Message 中返回 `tool_result`：

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
-> Tool Message 的 tool_call_id
```

字段名不同，责任相同：每份结果必须回答原来的那张申请单。没有 ID，系统不知道错误属于 `read_file` 还是 `run_bash`；配错 ID，格式看似完整，语义却已经错位。

当前 Anthropic 文档还区分客户端工具和服务端工具。客户端工具由应用执行并返回 `tool_result`；Web Search、Code Execution 等服务端工具可以在 Provider 内部运行。不能把“Model 不执行客户端工具”误写成“所有工具都在本机执行”。[Anthropic：How tool use works](https://platform.claude.com/docs/en/agents-and-tools/tool-use/how-tool-use-works)

## 4. 一批 Tool Call 要收齐一批结果

假设 Assistant Message 同时提出：

```text
toolu_A：read_file("config.json")
toolu_B：run_bash("rm -rf output")
```

Harness 可以顺序执行，也可以并行执行。第一项可能成功，第二项可能被策略拒绝。下一次请求仍要为两个调用各返回一份结果：

```text
toolu_A -> succeeded，附文件内容
toolu_B -> rejected，明确说明没有执行
```

拒绝、超时和失败也属于结果。静默丢掉 `toolu_B`，Model 会一直等待，或者误以为它仍在运行。

如果一次出现 30 个 Tool Call，协议上仍要逐个配对；工程上则应在 Harness 入口限制单轮工具数量、并发数和总预算，而不是执行到一半后随意丢掉结果。

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

## 6. 工具越强，边界越不能省

`read_file` 的路径不能只检查字符串前缀。`workspace/link/secret` 看似在 Workspace 内，`link` 却可能指向外部目录。必须解析真实路径，再检查最终目标仍在允许范围内。

Tool Result 也不是越完整越好。一个 500 KB 日志会挤占 Context，还可能带入提示注入。Tool 应返回受限片段、截断标记和回查位置，把完整事实留在文件或 Artifact 中。

```json
{
  "path": "logs/build.log",
  "content": "...最后一段错误...",
  "truncated": true,
  "next_offset": 51200
}
```

这些限制不会让 Tool 自动安全。路径检查挡不住网络访问，`cwd=workspace` 也不是 Sandbox。这里先明确责任边界，后续章节再分别处理 Context、Approval、Sandbox 与 Ledger。

现成框架不会改变上面的责任链。Agent SDK 可以封装部分 Harness，MCP 可以帮助 Harness 连接外部 Tool；但连接成功只证明“能通信”，不证明本次动作已经通过校验、审批和权限检查。更完整的协议与框架地图留在后续专题，本章只追踪一次 Tool Call 怎样从申请走到结果。

下一课会把这些箭头写成可运行代码：[跑通第一个 Tool Calling Loop](03-first-tool-calling-loop.md)。配套练习已经在[第一阶段综合实践](../exercises/phase-1-capstone/README.md)中覆盖多 Tool Call、矛盾停止状态、Workspace 边界和审批。

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

- [本批章节一手资料复核](../research/01-05-chapter-promotion-sources.md)
- [Anthropic：How tool use works](https://platform.claude.com/docs/en/agents-and-tools/tool-use/how-tool-use-works)
- [Anthropic Go SDK v1.69.0 工具示例](https://github.com/anthropics/anthropic-sdk-go/blob/v1.69.0/examples/tools/main.go)
- [Anthropic Go SDK v1.69.0 Tool Runner](https://github.com/anthropics/anthropic-sdk-go/blob/v1.69.0/examples/tool-runner/main.go)
- [OpenAI：Function calling](https://developers.openai.com/api/docs/guides/function-calling)
