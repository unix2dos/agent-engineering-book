# LangChain 与 LangGraph：配图记录

用途：单张解释图，用“现成循环模块装在编排底座上”的动作，说明 LangChain Agent 建立在 LangGraph 之上。小黑承担装配动作，图不作为两者完整功能清单。图文经用户确认，已应用到[正式第 2 课](../../chapters/02-Agent运行时.md)第 5 节；[候选稿](../../experiments/reading-pilot/02-Agent运行时-候选稿.md)作为审阅记录保留。尚未提交或发布。

输出：`01-agent-loop-on-runtime.png`。生成方式：内置 image_gen，按 ian-xiaohei-illustrations 的白底手绘、少量标注和动作主体规则生成；保留工具保存的原始文件。

原始文件：`/Users/liuwei/.codex/generated_images/01a03705-7158-7c93-9e82-03b467e7dc98/exec-413c6448-ce2c-4850-97e5-7a8c48e3e1a7.png`。项目副本与原图 SHA-256 一致。视觉检查：两层名称与中文标注可读，模型／工具循环方向明确，小黑实际承担装配动作；横向留白构图。此图只说明软件层次，不代表真实 API 调用或硬件部署关系。

解释时配合具体任务：LangChain 可以组织“模型申请读取 → 调用读取工具 → 回传结果 → 再请求模型”；LangGraph 可以组织诊断、修复、测试与条件分支，并按配置保存运行状态。LangChain 也支持定制和持久化，不能把图解读成它只会固定循环、或者只有 LangGraph 才能恢复。

依据为本次对话已读取的官方说明：[LangChain overview](https://docs.langchain.com/oss/python/langchain/overview) 和 [LangGraph overview](https://docs.langchain.com/oss/python/langgraph/overview)。两者是框架代码，不是语言模型；LangChain Agent 使用 LangGraph，直接使用 LangGraph 不要求先使用 LangChain。

## 提示词

```text
Create ONE 16:9 horizontal Chinese technical-article illustration, preferably 1792x1008 or equivalent 16:9. Pure white #FFFFFF background. Sparse black hand-drawn fine pen lines, slightly irregular, large quiet white margins. Small accents of orange for movement and blue for secondary annotation. No shadows, shading, paper grain, beige, gradients or scenery. Deadpan surreal sketch, NOT a slide, infographic, flowchart, polished vector art, commercial poster, cute cartoon or children's illustration.

Single core idea: LangChain offers a ready-made model/tool agent loop built ON TOP OF LangGraph, a lower-level task-orchestration and progress-saving foundation. These are software libraries, not two AI models and not two competing independent machines. Depict their built-on relationship through ONE physical assembly scene.

Invent a low-tech modular contraption, like a small handmade tabletop mechanical toy. Its upper removable module, clearly labelled exactly "LangChain", is an already-assembled open wooden work station. Inside it are only TWO simple sockets/modules labelled "模型" and "工具", connected by two spare orange curved arrows: the model asks the tool to work, and the result returns to the model. A small handwritten annotation near this upper module says "现成循环". Keep it simple, no tiny gears or detailed machinery.

The upper LangChain module is being fitted into a visibly WIDER lower supporting plinth. This bottom plinth is clearly labelled exactly "LangGraph", with a small annotation "编排底座". Show a FEW chunky removable track/step pieces and a single fork as part of the plinth, implying that a developer can arrange task steps and branches directly. A tiny open drawer in the plinth labelled "进度" holds a single paper bookmark, implying saved execution state. Do not fill the plinth with an actual diagram or many nodes.

One required character 小黑: solid-black slightly uneven bean-shaped creature with white DOT eyes, thin limbs, blank serious expression. The creature is actively bracing its legs and using both thin arms to lift and fit the whole LangChain upper module onto the LangGraph base. This assembly is its core job; it must NOT be a decorative spectator. Slightly absurd effort, calm serious face, not smiling or cute. No extra characters or outfits.

Composition: a single clean three-quarter physical sketch, clear upper-module/lower-foundation relationship, not side-by-side comparison panels. Main scene roughly 50-60% of canvas, at least 35% clean blank white space. No heading anywhere in the upper-left. Exactly these seven labels only: "LangChain", "现成循环", "模型", "工具", "LangGraph", "编排底座", "进度". Names must be accurately spelled, Chinese crisp and legible, handwritten but not calligraphy. Labels belong on objects or as small nearby annotations, not text paragraphs. Do not add arrows suggesting LangGraph sends results to a separate LangChain service. Do not depict a workflow-only restriction: the foundation can support this loop or other arrangements. No prior example compositions, no conveyor-break motif, no drawer-of-evidence scene or large alarm bell.
```
