# 综合项目：可靠的 Workspace Agent

这是全书持续积累能力的一个项目。代码是已完成的教学实现，运行检查不需要先补全函数；检查通过也不等于学习者已经掌握。日常学习从[本课实践](../README.md)进入，只有需要接入或修改能力时再读对应函数。

## 项目里有什么

- [agent.py](agent.py)：工具循环、受控文件工具、JSONL 历史、上下文压缩、执行账本与恢复。后半部分是检查点与预设模型。
- [client.py](client.py)：工具说明与真实模型连接，导入时不会创建客户端。第 9、10 课复用这里的连接，不再依赖其他课的参考答案。

调用顺序是：

```text
用户请求 → 有界循环 → 工具路由与审批 → 文件或命令执行
        → 会话与执行账本 → 工具回执 → 下一次模型请求或最终回答
```

写入结果不明时先核对证据，再决定能否补回执；不自动重跑任意副作用。Workspace 路径检查与审批不是操作系统 Sandbox；尤其 `run_bash` 的工作目录不能阻止命令访问外部路径。系统边界在[第 7 课](../lesson-07/README.md)单独验证。

## 怎样做阶段实践

第 3 课后，选择一次调用顺序或停止条件，先独立写出关键判断，再运行第一关验证。第 6 课后，完成一个受控小需求，例如新增只读目录工具，或增加一种可核对结果的恢复分支。每次只改一个规则，先说明预期，再检查正常、拒绝和中断情况。

不要清空整个项目。已有[目录工具扩展](../lesson-03/directory/README.md)保留完成代码、真实运行记录和复盘，可用于对照；不要求每位读者重新手写分页、SDK 或测试脚手架。

## 第一关：有界工具循环

重点函数：`run_agent_loop()`、`assistant_message_from_api()`。

验证同批工具结果全部回传、调用编号配对、截断响应不执行工具、达到次数上限停止。

```bash
python -B practice/workspace-agent/agent.py --self-check
```

通过标志：`checkpoint 1 passed`。这个命令只检查第一关。

## 第二关：受控本地工具

重点函数：`resolve_workspace_file()`、`read_file()`、`write_file()`、`execute_workspace_tool()`、`run_bash()`。

验证路径与软链接不能逃出工作区、读取分段、写入使用临时文件替换、写入和 Shell 先经过审批。通用文件系统和进程调用直接使用标准库。

```bash
python -B practice/workspace-agent/agent.py --checkpoint-2
```

通过标志：`checkpoint 2E passed`。本关不证明 Shell 具有操作系统隔离。

## 第三关：Transcript 与 Prompt View

重点函数：`append_entry()`、`load_entries()`、`build_prompt_view()`、`find_compaction_cut()`、`maybe_compact()`。

完整记录持续追加；本轮输入从最新摘要、保留尾部和新增消息重建。按完整轮次切分，生成失败、空摘要或变长摘要不能成为新的成功压缩记录。长度采用字符数教学比较，真实模型预算需要对应 Token 计量。

```bash
python -B practice/workspace-agent/agent.py --checkpoint-3
```

通过标志：`checkpoint 3G passed`。详细的压缩失败与工具配对检查在[第 5 课](../lesson-05/README.md)。

## 第四关：Ledger 与幂等

重点函数：`append_execution_state()`、`latest_execution_states()`、`make_idempotency_key()`、`arguments_sha256()`、`execute_workspace_tool_with_ledger()`。

区分一次尝试的 `execution_id` 和同一个操作的幂等身份；先记执行中，再进行副作用，最后保存实际结果。拒绝审批不会执行工具。

```bash
python -B practice/workspace-agent/agent.py --checkpoint-4
```

通过标志到 `checkpoint 4D passed`；会先检查第三关。账本身份本身不保证任意外部系统幂等。

## 第五关：故障恢复

重点函数：`mark_interrupted_executions_unknown()`、`reconcile_unknown_write_files()`、`repair_missing_tool_results()`、`pending_tool_calls()`。

验证写后中断、不重做已经发生的写入、不同内容保持未知、补齐缺失回执，以及恢复旧轮次时不插入新的用户消息。重复核对与修复不能生成第二份副作用或回执。

```bash
python -B practice/workspace-agent/agent.py --checkpoint-5
```

通过标志到 `checkpoint 5E passed`；它包含第三、四关的前置检查，不包含第一、二关。

## 后续能力的入口

[第 9 课](../lesson-09/README.md)组织真实任务与独立评分；[第 10 课](../lesson-10/README.md)在这个 Agent 外加入有限次修复和共享预算。安全、Tracing、交接和子任务恢复仍有独立机制实验，尚未集成完整后台调度、自动重启续跑或生产隔离系统。

整个项目的离线验收可运行 `python -B practice/check.py`。普通演示、历史报告和真实模型运行分别标明证据范围；不要把教学检查通过写成生产可靠性或学习者已掌握。
