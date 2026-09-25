# 01 生成记录

方式：`codex exec -m gpt-5.6-sol` 调用内置 image_gen；未使用 API/CLI 备用方案。

原始生成文件：`/Users/liuwei/.codex/generated_images/01a0d635-6154-7441-ae23-2e1e1b7f9427/exec-0fc7d787-70ff-4de3-8047-70d2d61d8778.png`，保留未覆盖。

工作区图片：`01-three-failures.png`。

目视检查：六处标注正确；第一格窗帘拉上后小黑仍在工作；第二格空椅子有红叉，新小黑从桌外柜子取记录；第三格吊车吊走整张桌子，新小黑从机器外的保险柜取出文件箱，并带着另一件记录。白底、无左上角标题。已知不足：第三格的“记录”画得像木盒，不如第二格的本子直观。

- 插入位置：第 11 课第 3 节末尾。
- 核心意思：三种故障一种比一种丢得多；关网页靠远端继续，程序退出靠进程外的记录，机器回收还要靠机器外的工作区文件。
- 技术检查：第一格小黑仍在干活；第二格新小黑读的是柜子里的记录，不是旧小黑的脑子；第三格同时拿记录和文件箱，二者分开保管。

## 提示词

```text
Generate one standalone 16:9 horizontal Chinese technical-book body illustration, not a cover, in the Ian Xiaohei minimalist absurd hand-drawn style.

Visual DNA: pure white background, thin slightly wobbly black pen line art, at least 40% empty white space. Sparse handwritten annotations: orange for the main labels of each scene, blue for what saves the task, red only for what is lost. No shadows, gradients, paper texture, polished vector graphics, PPT boxes, realistic UI, title, legend, numbered steps, cute cartoon or mascot poster.

Recurring character: Xiaohei, a small solid-black slightly irregular bean-shaped creature with two tiny white dot eyes, thin limbs, blank serious deadpan expression. Xiaohei performs the core action and is not cute.

Theme: three failures, each losing more than the last, and what lets the work continue.

Composition: three loose side-by-side scenes on the same white paper, separated only by white space, no frames, getting progressively emptier from left to right.
Scene 1 (left): a small browser window drawn as a picture frame whose curtain has been pulled shut. Behind it, still visible, Xiaohei keeps working at a tiny desk with a computer, unbothered.
Scene 2 (middle): the same tiny desk, but the old worker's chair is empty with a small red "×" on it. A second Xiaohei has just arrived and is reading a thick logbook it took from a separate locker standing OUTSIDE the desk area, then sits down to continue.
Scene 3 (right): a crane hook is lifting the whole desk and computer away into the sky; the spot is empty. A third Xiaohei walks in carrying two separate things: the logbook from the outside locker, and a small file box it pulls out of a separate safe standing further away.

Use ONLY these six short labels exactly:
"关网页" above scene 1;
"程序退出" above scene 2;
"机器回收" above scene 3;
"远端照常干活" in blue near scene 1's working Xiaohei;
"进程外的记录" in blue near the outside locker in scene 2;
"记录 + 工作区快照" in blue near the logbook and file box in scene 3.

Constraints: all Chinese correct and legible, no extra text, no arrows between scenes other than white space. Invent this composition afresh; no conveyor belt, no stamp toolbox, no standard flowchart.
```
