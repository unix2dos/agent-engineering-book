# 第 10 课：一次真实工作流验证

2026-09-10，用环境中已配置的 mimo-v2.5 运行配置修改任务。结果是文件验收通过，但完整运行未完成。本记录是一次观察，不是成功率评测，也不是对模型或网络根因的判断。

## 运行条件

- Provider：opencode.ai；复用现有 OpenAI-compatible 客户端。
- 输入：`{"theme":"light","port":3000}`；要求主题变为 dark，其他配置不变。
- 工具：只允许读写临时工作区的 config.json；不开放 Shell、评分依据或其他项目文件。
- 总修改轮数上限：2，包含首次；模型请求总预算：6；原有单轮请求上限仍为 4。
- SDK 超时设置：30 秒；SDK 自动重试：0。
- 使用本实验的会话编号请求头 x-opencode-session。没有将 API Key 写入源码或报告。
- 本机 NO_PROXY 存在 HTTP 客户端不支持的 `::1/128` 项；只在测试子进程中规范化为 `::1`，未改 shell 配置或证书验证。

对应命令是 `workflow_demo.py --live --max-attempts 2 --model-budget 6 --session-header x-opencode-session`。默认模拟模式保持不变。

## 观察到什么

| 项目 | 结果 |
|---|---|
| 模型请求尝试数 | 3，剩余预算 3 |
| 文件工具 | read_file 一次，write_file 一次 |
| 实际文件 | `{"theme":"dark","port":3000}` |
| 写入账本 | succeeded，有已保存结果 |
| 文件评分 | passed：主题正确，其他配置保持不变 |
| 最终模型回答 | 未取得 |
| 异常类型 | APITimeoutError |
| 完整工作流 | run_error，退出码 2 |
| 本轮记录耗时 | 48950 毫秒 |

时间顺序是：模型申请读取，取得结果；模型申请写入，工具写入成功并保存 Ledger 和 Tool Result；第三次模型请求超时。程序之后读取文件评分，得到 passed，但没有把整次运行改成 completed，也没有开始第二轮写入。

## 能说明什么

现有模型与文件工具确实完成了这一次配置修改；执行回执得以保存，程序也区分了产物成绩与运行结束状态。它没有证明模型能在错误反馈后修复，因为这次产物第一轮已经正确；不能据此推断其他任务的效果。

APITimeoutError 只证明本次请求没有在客户端设置的时间内完成。现有证据不足以区分模型生成耗时、Provider 排队和网络问题，也不能证明服务端没有继续处理。没有追加模型调用来追求成功结果，原报告保留。

后续应先明确怎样继续已有会话、沿用剩余预算和已有写入结果；不能简单重新执行整个工作流。当前没有实现这一恢复入口。

## 可复查证据

原始运行目录由命令打印，目录名为 `agent-workflow-_i39avyv/run`，保存 report.json、session.jsonl、checkpoint.json、原始配置、预期配置与第一轮产物。它是本机临时目录，不是在线附件。

报告记录的源码 SHA-256：

```text
workflow_demo.py
a0433555b19985fbc078ab65b57fd5886ec650d10d6ad96d77c2a8c69c199097
phase-1-capstone/starter.py
9920d2723aa0c6cf341397c86d09a3448c006dff9f1ce9d4bd63723f317cf149
lesson-09-evaluation/starter.py
2d6fd59d183896faf123e2af7bc57bacbc45dbfec9fa45ee5956ae354ebcd79b
```

实测后，离线自检增加了“写入成功后最终回答超时”的回归用例。该用例使用模拟异常，不是另一次真实模型运行；它验证遇到该情况时保留文件成绩和账本、停止继续修改。新增测试后源文件指纹会变化，以原报告指纹描述本次运行版本。
