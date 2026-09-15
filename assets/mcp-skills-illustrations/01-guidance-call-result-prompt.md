# 主图生成记录

方式：内置 image_gen；未使用 API/CLI 备用方案。

原始生成文件：`/Users/liuwei/.codex/generated_images/01a03705-7158-7c93-9e82-03b467e7dc98/exec-e109e26c-f190-4fa2-9d4f-b74b0920c4ae.png`，保留未覆盖。

工作区图片：`01-guidance-call-result.png`。

目视检查：中文及英文标注正确；小黑读手册、提交申请并接回执；Harness 检查机构独立；橙色请求向右、蓝色结果向左；MCP 标在通信管道上；无左上角类型标题，白底且留白充足。图片表达概念关系，不代表实际进程部署；Host 与 MCP Client 细节留给正文。

## 提示词

```text
Generate one standalone 16:9 horizontal Chinese technical-book body illustration, not a cover, with an Ian Xiaohei minimalist absurd hand-drawn style.

Pure white background, thin slightly wobbly black pen line art, huge clean margins and at least 40% blank white space. Very sparse orange and blue handwritten annotations. No shadows, gradients, texture, polished vector graphics, PPT boxes, UI panels, title, legend, numbered steps, cute cartoon or decorative mascot.

A single strange but understandable pneumatic-message query workstation occupies the middle of the canvas. On the left, Xiaohei is a solid black, slightly irregular bean-shaped serious creature with two tiny white dot eyes and thin limbs, blank expression. Xiaohei actively consults an open little instruction booklet with one hand while submitting a paper query with the other hand. Xiaohei represents the MODEL, not the operator of the approval mechanism.

The paper goes into a small mechanically controlled inspection slot in the central workstation, representing HARNESS. This is a distinct mechanism; Xiaohei can submit a paper but cannot operate or bypass its gate. From the inspection mechanism, two simple thin outlined pneumatic tubes connect to a small tool-service filing cabinet on the right. The tubes are the MCP communication link, NOT an additional decision-maker, NOT a robot. One orange forward arrow carries the query from inspection to the tool cabinet. One blue return arrow carries a result from the cabinet back through the workstation to Xiaohei. Make the result handoff back to Xiaohei visible. The returned slip reads "6 个账号". The tool cabinet provides the result, not the pipe. No cloud icon: this is a conceptual metaphor, not a deployment map.

Use ONLY these seven short readable labels exactly, with their positions attached unambiguously:
"Skill 方法" on the open booklet;
"模型" near Xiaohei;
"查询申请" on or near the submitted paper;
"Harness 检查" beside the inspection mechanism;
"MCP 通信" above the paired tubes, indicating both directions;
"工具服务" beside the right cabinet;
"6 个账号" on the returned slip near Xiaohei.

Keep English words spelled exactly Skill, Harness, MCP. All Chinese correct and legible. Main forms black, forward direction orange, returning result blue; at most one small red detail on the inspection gate. Seven labels maximum, no extra instructional text. The illustration explains one round trip: read guidance -> propose query -> controlled execution via MCP -> receive tool evidence. Skill is guidance, not permission. No line from the book to the gate controls. Xiaohei must be essential to the action, serious and slightly bizarre, not childish. Invent this composition afresh; no conveyor belt, no stamp toolbox, no standard flowchart.
```
