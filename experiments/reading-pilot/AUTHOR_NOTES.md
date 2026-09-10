# 独立样章：作者验收记录

本目录用于试读，不是新增课次。正文入口是 README.md，不加入 SUMMARY.md，也不替换既有章节。

## 本次验证的问题

读者能否沿着一次具体排查，理解 Tool Call、Tool Result 和 Harness 的分工，并通过改变一个输入解释执行路径的变化。目标读者有基本编程知识，但不假设熟悉 Python 或 Agent。

先试读，再判断是否沿用。程序自检通过、图片生成成功，都不能证明读者已经学会。建议作者记录读者第一次想跳过或需要重读的段落；不连续打分，不要求从空白文件开始写代码。

## 实现与边界

- 业务代码在 order_service.py，保留一个故意设置的缺陷。demo.py 负责 HTTP 包装和演示，读者无需先读完它。
- 复用综合实践 starter.py 中的 run_agent_loop、read_file、会话记录和假响应构造，没有新增 Agent 框架或第三方依赖。
- 服务、HTTP 请求、异常和文件读取真实运行；订单及业务场景虚构。模型侧是固定规则，最终文字由预设分支产生。它只识别这一类故障，不是通用诊断器。
- 每次运行使用新临时目录和本机随机端口，结束后关闭服务。只读工具仅开放两份材料；输入文件前后按字节比较。此演示不等于操作系统沙盒，不能直接用于不可信生产数据。
- 不调用真实模型，不读取 Key，不自动修复源码。验证真实模型能否自主排查，需另行确认实验范围和费用。

## 已运行的检查（2026-09-10）

```bash
python -B experiments/reading-pilot/demo.py --self-check
python -B experiments/reading-pilot/demo.py
python -B experiments/reading-pilot/demo.py --order-id order_001
```

结果：缺失订单返回 HTTP 500，实际日志含 TypeError；排查读取日志和源码两份材料。已有订单返回 HTTP 200、金额 128，只读取日志。两次 Tool Result 均按对应调用编号回传，输入文件未改动。自检还检查了写工具、Shell、越界路径和非法参数被拒绝，以及读取出错时不下结论。

这些结果只验证这个固定样例的执行行为。尚未验证真实模型诊断能力，也尚未获得本篇试读反馈。

## 配图记录

使用内置 image_gen，按 ian-xiaohei-illustrations 的白底、少字、动作主体规则生成一张正文配图：500 报警，小黑取出日志和代码查证据。原始生成文件保留在：

`/Users/liuwei/.codex/generated_images/01a03705-7158-7c93-9e82-03b467e7dc98/exec-0eaf6661-7ffc-4d43-a224-3d71e886123e.png`

项目使用副本：`assets/tool-calling-loop-illustrations/01-evidence.png`。

视觉检查：中文标注可读，小黑实际拉开抽屉并检查材料；横向构图、留白和单一隐喻符合本次意图。图片只辅助记忆，正文中的调用流程仍独立成立。

### 生成提示词

```text
Generate ONE standalone 16:9 horizontal illustration, 1536x864 or equivalent 16:9, for a Chinese technical book reading pilot about diagnosing an HTTP 500 error using logs and source code.
Pure white background (#FFFFFF), minimalist black hand-drawn fine pen lines with slight irregularity, lots of clean empty white space, sparse handwritten Chinese annotations. A quietly absurd product-sketch feeling. No gradients, shading, shadows, paper texture, background scenery, polished vector art, PPT layout, boxes-and-arrows diagram or title.
Core idea: an error alarm tells you something failed, but you must retrieve and examine the evidence to find why.
One solid-black, slightly irregular bean-shaped creature 小黑 with small white-dot eyes, thin arms and legs, blank serious expression is actively pulling open a small low-tech evidence drawer. The creature braces with its legs and with its other hand extracts two paper sheets visibly labelled "日志" and "代码", holding the sheets close to its eyes to inspect them. This pulling-and-inspecting action is the center of the composition, not a decorative mascot. Beside the drawer, a comically oversized thin-outline alarm bell is ringing, marked with red "500". It is loud but contains no diagnosis. Draw only the bell, the drawer, the two papers, and this one working creature. No other props or characters.
Main scene occupies roughly 50% of the canvas, preserve at least 40% pure white negative space. Labels are few, handwritten and legible: exactly "500" (red on the bell), "日志" and "代码" (black on the two sheets), "先查证据" (small blue handwritten annotation near the action). No other words, no top-left heading, no English title. Black pen is the main color; red and blue only as specified. Deadpan engineering humor, not cute, no costume, no emoji, no children's cartoon or commercial illustration. Invent a fresh original composition for this evidence-drawer metaphor.
```
