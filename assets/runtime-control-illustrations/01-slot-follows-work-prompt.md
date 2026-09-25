# 01 生成记录

方式：`codex exec -m gpt-5.6-sol` 调用内置 image_gen；未使用 API/CLI 备用方案。

原始生成文件：`/Users/liuwei/.codex/generated_images/01a0d635-61aa-7201-8095-7a86f61d1cc9/exec-268523d3-2825-4a6d-ac18-04bc5a1a18d4.png`，保留未覆盖。

工作区图片：`01-slot-follows-work.png`。

目视检查：五处中文与 A～D 字母正确；房间内恰好三个工作位；A 贴着红色“已发取消”仍在冒汗工作，后面连着三个子进程；小黑站在门口握住名额牌，D 在门外等待。白底、无左上角标题。

- 插入位置：第 14 课第 5 节“名额要跟着它代表的实际工作走”之后。
- 核心意思：发出取消不等于工作结束；并发名额要在确认工作真正结束后才交给下一个任务。
- 技术检查：A 身上有取消标记但仍在工作，且拖着子进程；小黑握住名额牌不给 D；房间里只有三个工作位。

## 提示词

```text
Generate one standalone 16:9 horizontal Chinese technical-book body illustration, not a cover, in the Ian Xiaohei minimalist absurd hand-drawn style.

Visual DNA: pure white background, thin slightly wobbly black pen line art, at least 40% empty white space. Sparse handwritten annotations: orange for the slot, red only for the cancelled-but-still-running problem, blue for the waiting task and the rule. No shadows, gradients, paper texture, polished vector graphics, PPT boxes, realistic UI, title, legend, numbered steps, cute cartoon or mascot poster.

Recurring character: Xiaohei, a small solid-black slightly irregular bean-shaped creature with two tiny white dot eyes, thin limbs, blank serious deadpan expression. Xiaohei performs the core action and is not cute.

Theme: sending a cancel signal is not the same as the work ending; a concurrency slot is handed over only after the work really stops.

Composition: a simple small room outline with exactly three workbenches inside. At the benches are three plain box-shaped little machines with legs, labeled with big letters A, B, C on their bodies (they are NOT Xiaohei; they are simple white boxes). Machine A has a red paper sticker slapped on it but is still busily working, sweat lines, and a thin string of three tiny smaller boxes (its child processes) still running behind it. Machines B and C work normally. Outside the room door, a fourth box machine D waits on a bench. At the door stands Xiaohei, the gatekeeper, holding one wooden slot tag firmly against its chest with both hands, deadpan, watching A's tiny child boxes; it clearly refuses to hand the tag to D yet.

Use ONLY these five short labels exactly:
"名额 3" in orange on the room's door frame;
"已发取消" in red on A's sticker;
"子进程还在" in red near the tiny boxes behind A;
"D 等待" in blue near D;
"确认结束才还名额" in blue handwriting under Xiaohei.
Plus the single letters A, B, C, D on the machines.

Constraints: all Chinese correct and legible, no extra text. Invent this composition afresh; no conveyor belt, no stamp toolbox, no standard flowchart.
```
