# 第 1 课：Agent 基础——从语言模型到行动系统

你对 Model 说：“查一下明天上海的天气。如果下雨，早上八点提醒我带伞。”

它回答：“好的，我会提醒你。”第二天早上，手机没有任何动静。

问题不在于这句话像不像承诺。Model 只生成了文字：它没有查询明天的天气，也没有在日历里创建提醒。要让一句回答变成真实动作，还需要一套能调用外部工具的程序。

## 1. Model 会回答，为什么不会自己动手？

单独的大语言模型接收输入，再生成输出。它不会因为写出 `read_file`、`send_email` 或 `create_reminder`，就自动获得文件、邮箱和日历权限。

真正执行动作的是 Model 外面的程序。它保存消息，告诉 Model 有哪些工具，检查 Model 提出的调用，再把工具结果送回去。这套负责推动运行的程序通常叫 **Agent Harness**。

天气提醒会这样走：

```text
用户提出目标
→ Harness 把目标和工具说明交给 Model
→ Model 申请调用天气工具
→ Harness 执行工具，拿到真实天气
→ Model 判断是否需要提醒
→ Harness 检查并创建日历提醒
→ Model 给出最终回答
```

现在四个部分都有了可以指认的对象：

| 直观职责 | 核心组件 |
| --- | --- |
| 判断下一步的模型 | Model |
| 推动循环并守住规则的程序 | Harness |
| 查询天气、创建提醒的具体能力 | Tool |
| 天气服务、日历、文件系统等真实世界 | Environment |

Model 可以申请“删除所有日历”，却不能批准自己的申请。Harness 还要检查参数、用户权限和审批规则。提出动作和允许动作必须分开。

## 2. 路线写死，还是让 Model 临场决定？

天气提醒可以写成一条固定路线：

```text
查询天气
→ 判断是否下雨
→ 下雨就创建提醒
→ 返回结果
```

每一步都由代码提前规定。语言模型（LLM）可以参与，例如把天气说明整理成结构化数据，但它不能改变路线。这种“程序提前编排好步骤”的系统叫 Workflow。

另一种写法只给 Model 一个目标和几个工具。Model 查完天气后，自己判断是否缺少城市、是否需要查看日历冲突、应该调用哪个工具以及什么时候结束。这才是本文所说的 Agent。

| 系统 | 谁决定下一步 |
| --- | --- |
| Workflow | 预先写好的代码 |
| Agent | Model 根据目标和刚得到的结果决定 |

两者可以放在同一个系统里。付款和发布适合让 Workflow 控制固定步骤；遇到失败以后“接下来查日志、看配置还是问用户”，可以交给 Agent 决定。

在技术选型时，区分二者的本质标准只有两条：**下一步由谁决定？** 以及 **刚得到的结果会不会动态改变后续路线？**

## 3. Agent Loop 一定是 ReAct 吗？

Agent 需要反复做三件事：Model 选择动作，Tool 返回真实结果，Model 根据结果再选下一步。这个来回过程叫 Agent Loop。

```text
Model 判断 → Tool 执行 → Result 返回 → Model 继续判断
```

例如命令返回 `403 Forbidden`，Model 看到错误后修改请求头再试。它利用了环境反馈，但这还不能证明系统使用了 ReAct。

ReAct 是一种更具体的组织方法。原论文让推理、行动和环境观察交错出现：先想一步，再做一步，看见结果后继续调整。[ReAct v3](https://arxiv.org/abs/2210.03629v3)

现代 Tool Calling Agent 可以直接返回结构化 Tool Call，由 Harness 驱动循环，不必公开或保存论文形式的 Thought。简而言之，**Agent Loop 是 Model 与 Tool 来回协作的外层循环，而 ReAct 只是该循环中一种具体的推理与行动组织模式**。

让 Agent 自己修改答案、保存失败教训、与其他 Agent 协作、记录运行过程或批量比较结果，都是后续增强。没有这些模块，一个最小 Agent 仍然可以成立。

## 4. 什么时候根本不该使用 Agent？

Agent 会增加模型请求次数、等待时间和出错路径。它用这些成本换取“Model 可以根据现场改变路线”。如果路线本来就固定，这笔交换通常不划算。

| 任务 | 最小选择 | 原因 |
| --- | --- | --- |
| 翻译一句话 | 一次 LLM 调用 | 没有外部动作，也不需要循环 |
| 查询数据库、生成日报、人工确认后发送 | Workflow | 步骤固定，代码更容易预测 |
| 调查一个从未见过的线上故障 | Agent | 下一步取决于刚拿到的日志和错误 |

固定日报即使使用 LLM 和邮件工具，也不一定是 Agent。提示词里写着“你是 Agent”，也不会让一次普通文本生成自动变成行动系统。

## 5. 动手设计与边界判断

先别急着写代码。拿出一个具体需求，先在纸上画出执行链条：每一步的决策者是谁？当前获得的结果会不会颠覆下一步的路线？只要业务流程可以静态穷举，优先选择单次调用或 Workflow；只有当外部环境的不确定性会不断倒逼重选动作时，才引入 Agent Loop。

最值得亲手推演的，是画出一次完整的 `Model → Tool → Result → Model` 闭环，并标出权限边界：Model 没有任何本地特权，Tool 以宿主进程权限受限运行，而 Harness 负责卡死审批与执行规则。“系统是否真正需要自主行动能力”，始终需要工程师结合成本与风险独立决断。

下一课会沿一次真实 Tool Call，继续拆开[Agent Runtime——Model、Harness、Tool 与 Environment](02-Agent运行时.md)。想直接动手，也可以进入[阶段一～二综合实践](../exercises/phase-1-capstone/README.md)。

## 主动回忆

1. Model 为什么答应“会提醒”，第二天却可能什么都没有发生？
2. Model、Harness、Tool 与 Environment 分别对应什么？
3. Workflow 与 Agent 的分界为什么不是“有没有 LLM 或工具”？
4. Agent Loop 与 ReAct 有什么区别？
5. 固定日报为什么更适合 Workflow？
6. 付款流程和开放式故障调查可以怎样组合？

<details>
<summary>检查简答</summary>

1. Model 只生成文字；没有 Harness 和 Tool，天气查询与日历提醒都不会真实执行。
2. Model 选择下一步；Harness 推动循环并检查规则；Tool 执行动作；Environment 提供真实状态。
3. Workflow 的路线由代码预设；Agent 的下一步由 Model 根据新结果决定。
4. Agent Loop 是 Model 与 Tool 的外层反馈循环；ReAct 是循环里一种具体的推理和行动组织方法。
5. 它的步骤可以提前写死，使用 Agent 只会增加成本和不确定性。
6. Workflow 控制付款和审批，Agent 只负责无法提前列完步骤的调查部分。

</details>

## 参考资料

> 资料最后核验于 2026-09-03；会变化的项目状态收录在下面的一手资料复核中。

- [本批章节一手资料复核](../research/01-05-chapter-promotion-sources.md)
- [Anthropic：Building Effective AI Agents](https://www.anthropic.com/research/building-effective-agents)
- [Anthropic：How tool use works](https://platform.claude.com/docs/en/agents-and-tools/tool-use/how-tool-use-works)
- [ReAct v3](https://arxiv.org/abs/2210.03629v3)
