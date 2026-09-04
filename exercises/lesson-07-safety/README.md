# 第 7 课实践：批准执行，不等于安全执行

Agent 在 Workspace 中运行：

```bash
cat ../outside-secret.txt
```

如果命令的 `cwd` 已经设为 Workspace，它还能读到外面的文件吗？

答案不能靠猜。第一关会在系统临时目录中创建：

```text
临时目录/
|- workspace/
`- outside-secret.txt
```

Shell 从 `workspace/` 启动，再尝试读取相邻的 `outside-secret.txt`。测试不会读取真实凭据，也不会修改你的项目文件。

## 学习路线

1. **CWD 不是 Sandbox**：亲眼看到命令从 Workspace 逃出去。
2. **Tool Policy**：先决定 Model 能不能申请某个工具。
3. **Approval**：工具可见后，再决定本次是否获准。
4. **Sandbox Backend**：获准命令究竟在 Host 还是受限环境执行。
5. **Elevated**：只能改变获准命令的执行边界，不能复活已被 Policy 禁止的 Tool。

## 检查点 A：只改变工作目录，挡不住越界

运行：

```bash
python -B exercises/lesson-07-safety/starter.py --checkpoint-a
```

预期输出：

```text
outside_read=true
checkpoint A passed
```

这证明：

```text
cwd=workspace
只决定命令从哪里开始
不限制命令最多能走到哪里
```

`../` 和绝对路径仍由当前进程的真实文件权限决定。真正的 Sandbox 必须让操作系统、容器或虚拟机拒绝越界访问，不能要求 Shell 自觉留在 Workspace。

这一关只需亲手运行并观察，不需要补代码。下一关才实现 Tool Policy，先从入口处减少 Model 能申请的能力。

## 检查点 B：隐藏 write_file，Shell 为什么还能写文件？

现在实现 `select_visible_tools()`。它接收全部 Tool、允许名单和禁止名单，返回真正交给 Model 的 Tool 列表。

规则只有三条：

- Tool 名必须出现在 `allowed_names` 中；
- 只要也出现在 `denied_names` 中，就必须删除，`deny` 优先；
- 保持原顺序，不修改传入的 `tools`。

例如：

```text
全部工具：read_file, write_file, run_bash
允许名单：read_file, write_file, run_bash
禁止名单：write_file

Model 最后看到：read_file, run_bash
```

这只能让 Model 无法直接申请名为 `write_file` 的入口。`run_bash` 仍然是一台通用机器，可以运行：

```bash
printf bypass > bypass.txt
```

测试会在临时 Workspace 中执行这条无害命令。若 `bypass.txt` 被创建，就证明：

```text
Tool Policy 禁止 write_file
不等于
整个执行环境禁止写文件
```

运行：

```bash
python -B exercises/lesson-07-safety/starter.py --checkpoint-b
```

完成后应看到：

```text
outside_read=true
checkpoint A passed
bash_write=true
checkpoint B passed
```

Tool Policy 只控制入口。下一关会在入口已经可见的前提下，决定某一次申请是否获得 Approval。

## 检查点 C：工具可见，不代表这一次获准

实现 `execute_if_approved()`，把 Tool Policy 和 Approval 按顺序接起来：

```text
Tool 不在 visible_names
-> 返回 denied_by_policy
-> 不询问用户
-> 不执行

Tool 可见，但用户拒绝
-> 返回 rejected
-> 不执行

Tool 可见，而且用户批准
-> 调用 execute()
-> 返回 completed 和执行结果
```

为什么 Policy 禁止后不再询问？因为这个 Tool 本来就不应该成为本次任务的可选能力。Approval 只能在允许入口内决定单次执行，不能推翻上层 Policy。

函数接收两个回调：

- `approve(tool_name)`：模拟询问用户，返回 `True` 或 `False`；
- `execute()`：模拟真正执行，返回结果字符串。

测试会记录两个回调分别被调用了几次，防止代码虽然返回正确状态，却仍偷偷询问或执行。

运行：

```bash
python -B exercises/lesson-07-safety/starter.py --checkpoint-c
```

完成后应看到：

```text
checkpoint A passed
checkpoint B passed
checkpoint C passed
```

Approval 仍然不是 Permission。下一关会让用户批准读取一个文件，但操作系统权限继续拒绝它。

## 检查点 D：用户批准了，操作系统仍可以拒绝

测试会创建一个临时文件，再用 `chmod 000` 去掉普通读取权限：

```text
Approval：用户同意执行 cat protected.txt
Permission：当前进程没有读取文件的权限
结果：操作系统拒绝读取
```

Approval 是 Harness 的决定；Permission 是进程真实拥有的能力。用户点击“允许”，不会自动修改文件权限、切换用户或获得 `root`。

运行：

```bash
python -B exercises/lesson-07-safety/starter.py --checkpoint-d
```

在普通 macOS/Linux 用户下应看到：

```text
approval=true
os_read=false
checkpoint D passed
```

测试结束前会恢复文件权限，只操作系统临时目录。如果 Python 进程本身是 `root`，测试会明确显示跳过，因为 root 可能绕过普通文件模式；这时不能拿结果证明普通用户权限边界。

这一关仍然没有 Sandbox。它只证明进程原有 Permission 可以拒绝动作。下一关会把获准命令路由到 Host 或受限 Backend，观察执行地点怎样改变边界。

## 检查点 E：同一条命令，换一个执行 Backend

这次仍然读取临时的 `../outside-secret.txt`，但会执行两遍：

```text
Host Backend
-> 直接使用当前用户权限
-> 读取成功

macOS Sandbox Backend
-> 仍在本机启动子进程
-> 操作系统规则明确禁止读取这个文件
-> 读取失败
```

测试使用 macOS 自带的 `sandbox-exec` 应用一条最小 Seatbelt 规则。Seatbelt 是 macOS 的进程限制机制；规则由操作系统强制，不依赖 Shell 自觉遵守。

运行：

```bash
python -B exercises/lesson-07-safety/starter.py --checkpoint-e
```

在支持 `sandbox-exec` 的 macOS 上应看到：

```text
host_read=true
sandbox_read=false
checkpoint E passed
```

其他系统会明确显示 `sandbox_demo_skipped=unsupported`，不会用假结果冒充硬隔离。

这条演示规则只禁止读取一个临时文件，其他操作仍是允许的。它只能证明“执行 Backend 可以让 OS 拒绝访问”，不是可以直接用于生产的完整 Agent Sandbox。

下一关加入 Elevated：它可以让一次已获准的命令选择 Host Backend，但不能让 Tool Policy 已经隐藏的工具重新出现。

## 检查点 F：Elevated 只能改变执行地点

实现 `choose_execution_backend()`。它按下面顺序判断：

```text
1. Tool 是否在 visible_names？
   否 -> denied_by_policy

2. 本次调用是否 approved？
   否 -> rejected

3. 是否启用 Sandbox？
   否 -> host

4. 是否请求 Elevated？
   否 -> sandbox
   是，但不允许 -> elevation_denied
   是，而且允许 -> host
```

Elevated 表示“这一次已获准调用是否离开外层 Sandbox，改到 Host 执行”。它不会：

- 让被 Tool Policy 隐藏的 `run_bash` 重新出现；
- 推翻用户对本次调用的拒绝；
- 永久关闭后续命令的 Sandbox；
- 自动获得 `root` 或超过当前进程的系统权限。

运行：

```bash
python -B exercises/lesson-07-safety/starter.py --checkpoint-f
```

完成后应看到：

```text
checkpoint A passed
checkpoint B passed
checkpoint C passed
checkpoint D passed
checkpoint E passed
checkpoint F passed
```

六个检查点合起来形成完整关系：

```text
应用内决策：Tool Policy -> Approval -> Backend / Elevated
操作系统执行：当前进程 Permission + Sandbox 规则
执行后记录：Tool Result + 第 6 课 Ledger
```

这套练习没有实现生产 Sandbox。它只验证每一层回答的问题不同，以及应用决策最终必须落到操作系统能够强制的执行 Backend。
