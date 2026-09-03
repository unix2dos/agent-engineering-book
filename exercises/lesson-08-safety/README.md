# 第 8 课实践：批准执行，不等于安全执行

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

## 第一关 A：只改变工作目录，挡不住越界

运行：

```bash
python -B exercises/lesson-08-safety/starter.py --checkpoint-a
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
