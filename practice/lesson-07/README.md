# 第 7 课实践：批准以后，系统仍然可以拒绝

先读[第 7 课：Agent 沙盒](../../chapters/07-Agent沙盒.md)。本课只操作临时假文件，不读取真实敏感材料。

## 必做

```bash
python -B practice/lesson-07/check.py
```

此检查使用支持 `sandbox-exec` 的 macOS。观察正文中的三个结果：宿主能读、沙盒允许的文件能读、明确拒绝的文件不能读。它还验证工作目录不隔离访问、工具是否可见、审批顺序与执行后端选择。

在 [demo.py](demo.py) 的 `checkpoint_d()` 中观察审批回调已经返回允许，但操作系统读取仍失败。再看 `checkpoint_c()`：把工具从可见清单中移除，应在请求审批前被拒绝。先预测执行是否会发生，再运行对应检查。

## 完成标准

能解释工具策略、审批和系统权限分别控制哪一步；知道 `cwd=workspace` 不会禁止读取绝对路径，也不会禁止 Shell 向工作区外写入。

代码重点是 `select_visible_tools()`、`execute_if_approved()` 和 `choose_execution_backend()`。下面按需单独复查，不要求逐个从空白实现：

| 检查 | 观察的机制 |
| --- | --- |
| `demo.py --checkpoint-a` | 工作目录之外仍可能可读 |
| `demo.py --checkpoint-b` | 不给写工具也不能阻止已放开的 Shell 写入 |
| `demo.py --checkpoint-c` | 工具策略与审批次序 |
| `demo.py --checkpoint-d` | 应用批准不覆盖系统拒绝 |
| `demo.py --checkpoint-e` | macOS 沙盒明确拒绝读取 |
| `demo.py --checkpoint-f` | 请求执行后端与允许升级分开判断 |

表中命令前加 `python -B practice/lesson-07/`。后续检查会运行部分前置检查。

## 与综合项目的关系

[Workspace Agent](../workspace-agent/README.md)已有应用侧路径和审批边界，本课独立验证操作系统边界。这个实验没有把完整 OS Sandbox 接入综合项目，也不提供生产容器、网络隔离或安全配置方案。
