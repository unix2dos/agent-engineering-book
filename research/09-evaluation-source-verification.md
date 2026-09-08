# 第 9 课：资料与实测核验

核验日期：2026-09-08。只支持本章的最小任务验收与回归门禁，不扩展为平台选型报告。

## 一手资料

| 来源 | 本章采用的内容 |
| --- | --- |
| [Anthropic Agent Eval 指南](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents) | Task、Trial、Grader 的职责；检查实际环境结果；每次尝试从独立环境开始。本文沿用这套 Task 定义，不把它强加给所有框架。 |
| [OpenAI Evaluation Best Practices](https://developers.openai.com/api/docs/guides/evaluation-best-practices) | 先定义成功目标和指标，再运行比较；自动评分需要人工校准；失败案例进入持续评估。未采用具体平台配置或模型推荐。 |
| [Inspect Scorers](https://inspect.aisi.org.uk/scorers.html) | 评分与汇总指标分离；提供文本匹配、模型评分和自定义规则。没有宣称本练习复用了 Inspect 内部代码。 |

这些官方页面已在本轮打开并核对正文。开源项目不作为名单铺陈，本课的实现证据来自仓库自己的 Agent、阅卷器和真实运行。

## 本地实现与证据

- `run_trial.py` 复用综合实践的有界 Agent Loop、文件 Tool 与 Ledger。
- `starter.py` 的配置评分和 CSV 评分使用不同规则，返回相同三类状态。
- `compare_runs.py` 比较保存的报告；`--gate` 再检查固定回归题是否全部完整通过。
- [baseline.json](../exercises/lesson-09-evaluation/evidence/baseline.json) 与 [candidate.json](../exercises/lesson-09-evaluation/evidence/candidate.json) 来自先前的真实模型实验。本轮只移除了本机路径，保留比较条件、成绩、异常类型、最终回答和耗时，没有重新请求模型或修改结果。

两批使用同一 `mimo-v2.5`、CSV 输入、工具范围与评分器，每次最多四次模型请求。基础版完整成功 `3/3`，候选版完整成功 `0/3`。候选前两次有四条 Assistant 工具调用响应，最后停在 Tool Result，文件评分通过但没有 Final；第三次记录 `APIConnectionError`，不能仅凭这次失败断言提示词有问题。

候选平均耗时约 17.16 秒，基础版约 24.24 秒。这个差异包含提前失败，不是候选版效率提升的证明。样本各三次，且按先基础版后候选版执行，网络与服务负载也可能影响耗时。

归档用于重现比较和门禁决定，不承诺重现实时模型输出。实验时练习尚未提交，源码指纹不能被当作可直接 Git checkout 的版本号。也不能拿这些历史报告替后来修改过的工作树提供发布证明。

## 本轮最小验收

门禁规则是为这组固定回归题新增的教学规则：比较条件有效，候选没有运行或评分异常，每个 Trial 都完整通过。旧成绩用于测试门禁能否拒绝已知问题，不是按新规则重新开展的模型实验。

正例与反例由自检覆盖；真实候选报告应得到 `blocked` 和退出码 `2`。本轮另外用预设的四次工具调用重现请求预算耗尽，验证“文件正确但没有 Final”会保留为运行失败。自检只证明代码行为，模型表现仍以真实报告为准。

```bash
python -B exercises/lesson-09-evaluation/starter.py --checkpoint-b
python -B exercises/lesson-09-evaluation/starter.py --check-csv
python -B exercises/lesson-09-evaluation/run_trial.py --self-check
python -B exercises/lesson-09-evaluation/compare_runs.py --self-check
```
