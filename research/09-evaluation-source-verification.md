# 第 9 课：资料与实测核验

核验日期：2026-09-08。这里保存来源和历史实验边界；当前运行说明与完成标准统一放在[第 9 课实践](../practice/lesson-09/README.md)。

## 一手资料

| 来源 | 本章采用的内容 |
| --- | --- |
| [Anthropic Agent Eval 指南](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents) | Task、Trial、Grader 的职责；检查实际环境结果；每次尝试从独立环境开始。本文沿用这套 Task 定义，不把它强加给所有框架。 |
| [OpenAI Evaluation Best Practices](https://developers.openai.com/api/docs/guides/evaluation-best-practices) | 先定义成功目标和指标，再运行比较；自动评分需要人工校准；失败案例进入持续评估。未采用具体平台配置或模型推荐。 |
| [Inspect Scorers](https://inspect.aisi.org.uk/scorers.html) | 评分与汇总指标分离；提供文本匹配、模型评分和自定义规则。没有宣称本练习复用了 Inspect 内部代码。 |
| [LangSmith Agent 评估方式](https://docs.langchain.com/langsmith/evaluation-approaches) | 区分最终输出、单步选择和整段行为；合法解法可能有多条，精确匹配工具顺序需要具体理由。 |
| [LangSmith Evaluation](https://docs.langchain.com/langsmith/evaluation) | 发布前测试集评估与真实流量评估的用途，以及线上失败回流到测试集。本文不要求使用其服务。 |
| [Anthropic 基础设施噪声研究](https://www.anthropic.com/engineering/infrastructure-noise) | 资源限制本身会影响失败与可行解法；模型比较应记录环境条件，不能只看最终比例。 |
| [SWE-bench 评分实现](https://www.swebench.com/SWE-bench/api/harness/#swebench.harness.grading.get_resolution_status) | `FAIL_TO_PASS` 与 `PASS_TO_PASS` 同时满足时才判完全修复，作为“解决目标问题且保留旧行为”的实例。 |
| [Promptfoo CI/CD](https://www.promptfoo.dev/docs/integrations/ci-cd/) | Quality Gate 消费评测成绩并让流水线失败；退出码只是信号，仍需发布过程实际执行该检查。 |
| [NIST 两组比例比较](https://www.itl.nist.gov/div898/software/dataplot/refman2/auxillar/diffprop.htm) | 两组样本量可以不同；等量 Trial 是本练习的简化限制，不是通用统计要求。未把大样本近似直接套到各三个 Trial。 |

这些官方页面在上述核验日期已打开并核对正文；本次目录整理未重新联网核验。开源项目不作为名单铺陈，本课的实现证据来自仓库自己的 Agent、阅卷器和真实运行。

## 历史模型证据

- [baseline.json](../practice/lesson-09/evidence/baseline.json) 与 [candidate.json](../practice/lesson-09/evidence/candidate.json) 来自先前的真实模型实验。归档时只移除了本机路径，保留比较条件、成绩、异常类型、最终回答和耗时，没有重新请求模型或修改结果。

两批使用同一 `mimo-v2.5`、CSV 输入、工具范围与评分器，每次最多四次模型请求。基础版完整成功 `3/3`，候选版完整成功 `0/3`。候选前两次有四条 Assistant 工具调用响应，最后停在 Tool Result，文件评分通过但没有 Final；第三次记录 `APIConnectionError`，不能仅凭这次失败断言提示词有问题。

候选平均耗时约 17.16 秒，基础版约 24.24 秒。这个差异包含提前失败，不是候选版效率提升的证明。样本各三次，且按先基础版后候选版执行，网络与服务负载也可能影响耗时。

归档用于重现比较和门禁决定，不承诺重现实时模型输出。实验时练习尚未提交，源码指纹不能被当作可直接 Git checkout 的版本号。也不能拿这些历史报告替后来修改过的工作树提供发布证明。

## 已验证与未验证的范围

- 正文中的能力评估用于识别改进空间，回归评估保护已依赖的行为；当前三次 CSV 对照只覆盖一项小任务，不能代表整个能力集。
- 当前比较器只支持固定模型和预算等条件、同一任务、等量 Trial 的 Prompt/Runtime 对照。正文讨论的一般评估方法不意味着代码已支持任意模型或方案比较。
- 当前实验未接入第 8 课的正式 Trace/Span。失败路径来自会话、Ledger、运行报告及预算耗尽的离线复现；正文不再把它们冒称为已采集的 Trace。
- 快照的保护来自执行入口限制可读写路径且不开放 Shell，不是因为路径位于工作区外。输入未变也不能独自证明 Model 从未提出改写请求，或通用操作系统 Sandbox 已经验证。
- 产物评分与运行状态均有实现，但自然语言回答与实际产物是否完全一致尚未自动评分。
- `release_gate()` 读取旧报告并执行本例全通过规则。没有当前工作树身份核对、自动发布、通用统计检验或完整系统安全验收。
- 评分器自检、综合实践的 Context/恢复检查与真实模型 Trial 分别解释；不能混加得到“模型成功率”。综合实践中的 Scripted Model 只控制测试路径，不构成新的真实模型实验。

门禁是为这组固定回归题新增的教学规则。历史成绩用于验证门禁能否拒绝已知问题，不是按新规则重新开展的模型实验；正反例和运行命令在实践入口维护。
