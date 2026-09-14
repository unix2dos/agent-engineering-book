# 第 6 课实践：文件写好了，回执却丢了

先读[第 6 课：工具可靠性](../../chapters/06-工具可靠性.md)。本课复用同一个 [Workspace Agent](../workspace-agent/README.md)，只操作临时文件。

## 必做

```bash
python -B practice/lesson-06/demo.py
```

在 [demo.py](demo.py) 中，`interrupt()` 故意在文件写入后、账本终态保存前抛出异常。观察三个阶段：

1. 文件内容已经是 `done`，账本却停在 `running`。
2. 恢复时先记为 `unknown`，不直接宣布失败或重做。
3. 核对现有文件与原请求一致，补写成功记录和工具回执；重复核对没有再次写文件。

完成一次小改动：在核对前插入 `target.write_text("changed by user")`，先预测是否还能补写成功回执。原成功路径断言应失败；根据返回状态解释为什么此时必须保持 `unknown`，不能覆盖用户后续修改。运行下列检查可看到两种情况的完整验证。

## 完成标准

能区分“工具失败”和“结果未知”，并指明核对依据来自哪里。文件内容不同、参数冲突、回执缺失都不能靠重试掩盖。

```bash
python -B practice/lesson-06/check.py
```

检查覆盖正文代码、写后中断、核对、回执修复、冲突拒绝和事务回滚。[综合项目第五关](../workspace-agent/README.md#第五关故障恢复)保留更完整的恢复检查。

这个例子验证可核对的文件覆盖写入，不提供任意 Shell 命令或外部副作用的自动重试保证。

## 选做

[SQLite 事务与唯一约束](../optional/sqlite/README.md)演示什么时候数据库能减少查询和一致性负担。完成主线不要求把整个 Agent 改成 SQLite 存储。
