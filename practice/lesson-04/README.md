# 第 4 课实践：保存历史，读回正确的状态

先读[第 4 课：会话持久化](../../chapters/04-会话持久化.md)。本课只用临时文件，不调用模型，不读取个人长期记忆。

## 必做

```bash
python -B practice/lesson-04/demo.py
```

观察同一段消息如何保存到 JSONL 历史和 JSON 快照，读回时如何核对 `processed_entries`。再比较旧会话与新会话：长期信息可被重新选用，等待日志的进度只属于旧会话。

在 [demo.py](demo.py) 的 `messages` 中增加一条“日志位于 server.log”的用户消息，重新运行。历史条数与快照位置都应增加，原来的消息仍保留。这个位置由消息数量计算，不要独立硬改计数来掩盖不一致。

## 完成标准

能指出 Transcript、Checkpoint 和本次选中的材料分别在哪里；解释为什么读回文件不等于重做工具，也不等于模型自动记住了内容。

```bash
python -B practice/lesson-04/check.py
```

它核对正文教学代码；演示自身也包含文件往返和会话材料隔离断言。文件保存采用单写者临时文件替换，不证明断电持久性或并发安全。

## 接到综合项目

[综合项目第三关](../workspace-agent/README.md#第三关transcript-与-prompt-view)提供真实 JSONL 追加与消息恢复。完成本课不要求再实现一套 Agent，跨进程副作用恢复在第 6 课验证。
