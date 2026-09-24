# 02 生成记录

方式：`codex exec -m gpt-5.6-sol` 调用内置 image_gen；未使用 API/CLI 备用方案。

原始生成文件：`/Users/liuwei/.codex/generated_images/01a0d454-c63d-7da0-adea-7e31e1f69d87/exec-43102584-0f3d-48ef-aee6-9e11cfe925a0.png`，保留未覆盖。

工作区图片：`02-four-prerequisites.png`。

目视检查：五处标注正确，`Skill` 拼写无误；小黑读说明书并拉杆，说明书不直接连机器；橙色传动经齿轮与机械手到空锁孔为止，锁孔红圈、“系统权限”为红字；机械手下垂，屏幕通电但按钮未被按下；白底、无左上角标题。图只表达“缺一样就点不动”，不代表真实程序的连接顺序。

## 提示词

```text
Generate one standalone 16:9 horizontal Chinese technical-book body illustration, not a cover, in the Ian Xiaohei minimalist absurd hand-drawn style.

Visual DNA: pure white background, thin slightly wobbly black pen line art, at least 40% empty white space. Sparse handwritten annotations: orange for the transmission path, blue for secondary notes, red only for the missing part. No shadows, gradients, paper texture, polished vector graphics, PPT boxes, realistic UI, title, legend, numbered steps, cute cartoon or mascot poster.

Recurring character: Xiaohei, a small solid-black slightly irregular bean-shaped creature with two tiny white dot eyes, thin limbs, blank serious deadpan expression. Xiaohei performs the core action and is not cute.

Theme: an instruction manual alone cannot press a button; the executing program, system permission, and running target environment must all be present.

Composition: a strange hand-drawn "button pressing machine" spans the canvas from left to right. On the left, Xiaohei holds an open instruction booklet in one hand, reading it seriously, and pulls a lever with the other hand exactly as the booklet's small arrow shows. The lever drives an orange transmission line through three linked parts in a row: first a gear-driven mechanical hand; then a lock with an EMPTY keyhole, no key anywhere; then a plugged-in, switched-on simple computer screen showing one plain button. Because the keyhole is empty, the transmission is broken at the lock: the orange line stops there, and the mechanical hand hangs limp, far from the screen button. Xiaohei is completely unaware of the empty keyhole and keeps pulling the lever. The booklet does not connect to the machine directly; only Xiaohei's hand touches the lever.

Use ONLY these five short labels exactly:
"Skill 说明" on the booklet;
"执行程序" near the mechanical hand;
"系统权限" in red next to the empty keyhole, with a small red circle around the keyhole;
"目标环境" near the computer screen;
"缺一样就点不动" in blue handwriting under the machine.

Keep the English word spelled exactly Skill. Constraints: one core structure only, main subject 40%-60% of canvas, no top-left title, all Chinese correct and legible, no extra text. Invent this composition afresh; no conveyor belt, no stamp toolbox, no standard flowchart.
```
