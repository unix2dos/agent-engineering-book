# 第 8 课实践：把一次运行的时间和结果接起来

先读[第 8 课：Agent 可观测性](../../chapters/08-Agent可观测性.md)。代码是完成版；本课观察运行证据，不要求重写 Tracing 库。

## 必做

```bash
python -B practice/lesson-08/check.py
```

观察 `operation_status=ok` 与 `business_outcome=failed` 同时出现：读取正常结束，不代表业务任务成功。模型计时使用受控数据，文件读取真实发生，没有发送遥测或调用真实模型。

在 [demo.py](demo.py) 中找到 `checkpoint_b()`，指出开始时间、结束时间、耗时和业务结果分别保存在哪里。再运行：

```bash
python -B practice/lesson-08/demo.py --checkpoint-e
```

比较运行中、错误、未知与成功运行的保留结果。把 `keep_success_sample` 的取值换掉，预测成功运行是否会被保留；错误和未知结果不能因成功采样关闭而丢弃。

## 完成标准

能沿 `trace_id` 和 `parent_span_id` 还原一次运行，区分模型 Tool Call 与实际执行尝试；解释为什么操作状态、业务结果和采样决定不能混为一个布尔值。

| 代码位置 | 职责 |
| --- | --- |
| `append_span()`、`finish_span()` | 创建、结束 Span，记录身份、耗时和结果 |
| `append_tool_attempt()` | 同一工具调用的多次尝试各有 Span |
| `select_export_attributes()` | 导出允许字段，避免带出敏感内容 |
| `decide_trace_retention()` | 未结束时等待；错误与未知优先保留 |

`demo.py --checkpoint-a` 至 `--checkpoint-e` 可单独观察各部分，命令前加 `python -B practice/lesson-08/`。

## 与综合项目的关系

本课独立验证 Trace/Span，不替代 Transcript 和 Ledger，也尚未把这些 Span 全部挂到综合项目中。示例按单进程、父 Span 先到达处理；不实现分布式乱序收集、Collector 或完整可视化平台。
