# Computer Use 资料核验

初次核验：2026-09-16；后续补充日期见各节。课程正文已于 2026-09-18 整理为[第 15 课 Computer Use](../chapters/15-ComputerUse.md)。本文件保留资料版本与核验范围。

## OpenAI：当前接入方式与责任边界

资料通过本机 OpenAI Docs 的搜索、正文抓取核验。以下记录的是核验当日文档内容，不把核验日期当成发布日期；这些页面未提供明确的最后更新日期。

| 一手资料 | 核验结论 |
| --- | --- |
| [Computer use API guide](https://developers.openai.com/api/docs/guides/tools-computer-use) | 能力覆盖浏览器与桌面图形界面；模型依据截图和其他工具结果选择下一步，应用提供环境并执行请求。 |
| [Integration recipes：迁移说明](https://developers.openai.com/api/docs/guides/tools-computer-use-integration#migration-from-computer-use-preview) | `computer-use-preview` 与 `computer_use_preview` 属于旧接入；当前 GA 示例使用 `gpt-5.6-sol`、`computer` 和有序 `actions[]`。 |
| [GPT-6 Astra 模型页](https://developers.openai.com/api/docs/models/gpt-6-astra) | 当前模型页列出 computer use 能力；主指南针对 GPT-6 Astra 推荐代码执行方式，结构化 `computer` 工具仍然支持。 |
| [Computer Use 资料入口](https://developers.openai.com/learn/cua) | 官方提供 CUA 示例应用与前端测试示例入口；此轮未运行这些示例。 |
| [ChatGPT 桌面产品说明](https://learn.chatgpt.com/docs/computer-use) | 产品通过插件、操作系统权限和应用授权连接桌面。此页描述现成产品，不等于 API 自动附赠桌面环境，也不能据此推断某个账号可用。 |

### 已确认的实现事实

1. **有两条接入路径。** 代码执行路径让模型生成调用 Playwright 或 PyAutoGUI 的脚本，由应用在隔离环境执行；结构化工具路径让模型返回点击、输入、滚动等动作，由应用的 action handler 转成输入。现有 function calling 或远程 MCP 界面工具也可以保留。依据：[主指南](https://developers.openai.com/api/docs/guides/tools-computer-use)。
2. **应用必须真正执行动作。** `computer_call` 的 `status: "completed"` 表示模型已生成调用，不表示界面操作已经完成。应用按顺序执行允许的 `actions[]`，截图后用原 `call_id` 返回 `computer_call_output`，继续模型对话。依据：[动作执行与截图返回](https://developers.openai.com/api/docs/guides/tools-computer-use#execute-the-requested-actions)。
3. **对话状态和执行环境状态分开。** `previous_response_id` 延续对话，不会恢复浏览器会话、登录状态或运行时变量。应用需要保持或重建对应环境，并核对真实结果。依据：[状态与观察](https://developers.openai.com/api/docs/guides/tools-computer-use#preserve-state-and-return-observations)。
4. **新示例不能直接套用旧 preview 协议。** 旧协议每个调用一个 `action`，新结构化路径是 `actions[]`；迁移说明明确 preview 只用于维护旧集成。依据：[迁移表](https://developers.openai.com/api/docs/guides/tools-computer-use-integration#migration-from-computer-use-preview)。
5. **程序负责边界和验收。** 官方要求隔离环境、限制允许的网站与动作、把屏幕内容当作不可信输入、为重要操作保留用户控制，以及设置步数、时间或成本限制并验证实际结果。依据：[Run safely](https://developers.openai.com/api/docs/guides/tools-computer-use#run-safely)。

### 教学归位建议（基于资料的课程设计判断）

Computer Use 主要属于 Agent 的“观察与行动接口”：把原来调用业务函数的路径，扩展为读取界面状态、操作界面并再次观察。它继续复用模型—工具循环、状态、权限、预算与验收，不是一套独立于这些机制的新架构。MCP 是接入协议，可以承载界面工具；浏览器自动化是其中一种环境与执行手段，两者均不与 Computer Use 等同。

建议从隔离浏览器内的本地测试页面开始：读取当前界面 → 修改一个可逆设置 → 重新观察并核对结果。把错误点击、页面变化、预算耗尽列为异常案例。源码或官方示例、执行轨迹和最终状态分别留证；模型声称“完成”不能代替验收。

### 本轮未验证

- 未调用付费 API、未申请账号权限、未安装或操作桌面插件。
- 未确认当前账号的模型、地区、套餐或 API 可用性。
- 未把产品文档中的桌面能力视为 API 自动托管环境的证明。
- 当前官方页面更新较快，正式编写可运行练习时仍需核对接口与示例版本。

## Anthropic：桌面工具集与实际 Agent Loop

[当前 Computer use 文档](https://platform.claude.com/docs/en/agents-and-tools/tool-use/computer-use-tool)定义的是客户端工具集：模型生成操作请求，应用在自己的桌面环境执行，并把截图或结果交回模型。当前接口为 `computer_toolset_20260801`，包含截图、点击、输入等 17 个成员；该版本不需要 beta header。旧 `computer_20251124` 仍保留为兼容路线，不能把版本标识当作网页发布日期。

该文档要求一批界面动作按顺序执行；某个动作失败后，后续动作跳过但仍逐项返回结果。点击改变焦点以后再输入，正是不能把这类动作当作普通并行请求的例子。文档同时明确：屏幕内容可能夹带与用户意图冲突的指令，环境隔离和动作边界仍由应用负责。依据同上文档的 Batch actions、Security considerations 与 Computing environment 部分。

实际源码已读：[官方示例 sampling_loop](https://github.com/anthropics/claude-quickstarts/blob/8826387af1d23280996f0a0892e0cfd764becb57/computer-use-demo/computer_use_demo/loop.py#L168-L241)。它保存模型回复，依次执行 toolset 成员，遇失败后为剩余成员生成未执行结果，再将结果放入下一次请求。本轮固定到提交 `8826387af1d23280996f0a0892e0cfd764becb57`（提交时间 2026-09-15T23:32:41Z）；这里只读了相应执行路径，没有安装或运行整个示例。

## Google：当前 Gemini Computer Use

[官方指南](https://ai.google.dev/gemini-api/docs/computer-use)标注最后更新为 **2026-09-04 UTC**。当前页面推荐 `gemini-3.8-flash`，列出 browser、mobile、desktop 三种环境；`gemini-2.5-computer-use-preview-10-2025` 位于 legacy 分支，Computer Use 能力仍标为 Preview。它同样要求应用实现动作执行和观察结果回传，不能把返回 function call 当作点击已经发生。

此轮只核验指南与版本表，没有验证账户访问、模型调用、设备接入或各环境表现。示例、动作字段和坐标约定应按同一版本阅读，不能拼接不同厂商或 legacy 文档的代码。

## 开源与评测入口

| 一手入口 | 当前核验与适合阅读的内容 | 边界 |
| --- | --- | --- |
| [Browser Use](https://github.com/browser-use/browser-use) | 浏览器 Agent 框架；README 提供 Python、CLI 等入口。[GitHub 最新 release](https://github.com/browser-use/browser-use/releases/tag/0.13.10)为 0.13.10，发布于 2026-09-04T03:28:53Z；当前主分支固定点为 [d8110c5](https://github.com/browser-use/browser-use/tree/d8110c5ff87ccba887aaa726cdb780f2f84bef8d)。 | 面向浏览器，不能据此宣称能直接操作所有桌面软件；同名项目不等于厂商内置 browser use 工具。 |
| [OSWorld](https://github.com/xlang-ai/OSWorld) | 桌面 Agent 环境与评测项目，当前核对的提交为 [b138d34](https://github.com/xlang-ai/OSWorld/tree/b138d348256078fa634fc3b73567a7337c793e6b)。README 指向 OSWorld-Verified，并要求比较对应版本的结果。 | 是评测资源，不是初学者必须先部署的 SDK；本轮没有跑分，也没有引用厂商间的性能排名。 |

以上提交日期反映源码快照，不是整个项目的首次发布日期。依赖版本、平台可用性和模型能力不能由一次源码读取推断为已实测。

## 在本书中的位置与学习起点（课程建议）

Computer Use 属于 Agent 的观察与行动接口扩展：Model 根据界面状态选择动作，Harness 管理执行顺序、权限、预算与停止，Tool 实现截图和输入，Environment 是浏览器、桌面或移动界面。MCP 是接入协议，可以承载界面工具；Computer Use 描述 Agent 通过什么界面行动，两者不处于同一个分类维度。

建议将其作为下一项交互能力专题，而不是重新扩写第 10 或第 14 课。前置为第 3 课的工具循环、第 7 课的权限边界、第 9 课的程序验收和第 14 课的运行控制；RAG 不是必需前置。

建议只选一个可逆的本地任务：在测试网页中将主题改为 dark，保留端口 3000。先看当前页面，执行点击或输入，再观察保存后的页面，由程序独立核验最终状态。沿用既有任务验收条件，改变的是界面交互方式。

一轮学习只交付三项：

1. 能说明截图或页面状态怎样进入模型，动作怎样到达执行器，结果怎样回到下一次请求。
2. 完成一次界面任务，保留实际动作轨迹和最终状态；不能用模型说“完成”代替验收。
3. 加入一个可控失败：按钮位置变化、弹窗或页面加载延迟，观察如何重新获取状态或按预算停止。

这会自然带入输入安全：网页和截图中的文字不能自行变成用户授权。先读官方 loop 和动作处理代码，再准备小实验；本次调研没有操作用户桌面、安装插件或消费模型 API，也没有为新专题分配正式课次。

## 三个项目的分层对照（2026-09-17）

本次核对 Tencent/BrowserSkill、herdrdev/herdr、trycua/cua 的 README 与关键文档/入口。下述定位是按项目职责作出的分类；广义的计算机操作能力，不等于某一家厂商专用的截图动作 API。没有安装这些项目，也没有验证它们之间现成可互通。

### BrowserSkill：把已有 Agent 接到真实浏览器

固定提交：`75e2c64abaf4b7cc75682d94b0c1fd5db0cbd5e5`（2026-09-16T12:20:39Z）。[README 与架构](https://github.com/Tencent/BrowserSkill/blob/75e2c64abaf4b7cc75682d94b0c1fd5db0cbd5e5/README.md)说明本地链路为 Agent → bsk CLI → daemon → 浏览器扩展 → Agent Window。项目支持复用已登录的浏览器；操作已有用户标签页有显式借用与归还流程。

它不提供一个新的决策模型。项目同时包含可执行程序、后台服务、浏览器扩展和使用指引；Skill 教现有 Agent 怎样调用这些工具。

[随项目提供的 Skill](https://github.com/Tencent/BrowserSkill/blob/75e2c64abaf4b7cc75682d94b0c1fd5db0cbd5e5/skill/SKILL.md)优先使用 observe 取得文字、控件与 @eN 元素引用，再执行 click、fill、select 等操作；页面导航或明显变化后重新观察。截图用于视觉内容或证据，Canvas 才使用关联 capture_id 的图像坐标路径。因此它属于浏览器操作能力的接入与执行层，可归入广义 Computer Use，不等于只靠截图点击的视觉模型。

### Herdr：编码 Agent 的终端工作区与运行管理

固定提交：`e7e3dfa60e359404def46503dd105c165d02a561`（2026-09-17T01:14:57Z）。[概念文档](https://github.com/herdrdev/herdr/blob/e7e3dfa60e359404def46503dd105c165d02a561/docs/next/website/src/content/docs/concepts.mdx)描述 workspace、tab、pane 的组织；pane 内是实际终端与进程。它承载现有编码 Agent，管理并行工作区、状态和协作，不替代这些 Agent 的模型与工具循环。

[后台 server](https://github.com/herdrdev/herdr/blob/e7e3dfa60e359404def46503dd105c165d02a561/src/server/headless.rs#L1-L15)持有 PTY、进程与事件循环，前台 client 显示内容并转发输入。[多机文档](https://github.com/herdrdev/herdr/blob/e7e3dfa60e359404def46503dd105c165d02a561/docs/next/website/src/content/docs/connecting-machines.mdx)说明本机和 SSH 机器各自有 server/session/进程，可统一查看与重连。

[README 的恢复边界](https://github.com/herdrdev/herdr/blob/e7e3dfa60e359404def46503dd105c165d02a561/README.md)区分 client 退出/SSH 断开与 server/机器重启。后者不能保留原进程存活，只能恢复保存布局或续接支持的 Agent 会话。文档中的鼠标操作主要指人操作终端界面，不能据此把 Herdr 归为模型点击桌面的 Computer Use 执行器。

### Cua：界面操作驱动、电脑环境与评测配套

固定提交：`592f6ee39e1d65101b00af756cb52b6181fdbfc8`（2026-09-17T02:13:30Z）。[README](https://github.com/trycua/cua/blob/592f6ee39e1d65101b00af756cb52b6181fdbfc8/README.md)将入口分为四部分：Driver 操作应用，Fleets 提供隔离云桌面池，Lume 管理 Apple Silicon 上的本地虚拟机，Bench 定义任务并评测 Agent。项目明确由使用者提供 Agent 与模型。

[Driver 文档](https://github.com/trycua/cua/blob/592f6ee39e1d65101b00af756cb52b6181fdbfc8/libs/cua-driver/README.md)给出 MCP、CLI、Python/TypeScript SDK 接入路径。它可用于桌面应用和浏览器，具体动作、后台输入与平台支持仍应核对对应文档，不能把所有平台的能力当成一致。

这套项目更接近 Computer Use 的工具与环境基础设施，而非一个必须自带决策模型的聊天产品。其 Computer-Use 2.0 是项目描述代码、API 与图形界面混合操作的说法，不作为全行业统一协议名称使用。

### 对学习顺序的修正

先理解用户目标如何变成模型决策、工具动作和可核对结果，再看项目负责接入、执行、环境还是运行管理。BrowserSkill 适合先观察已有 Agent 怎样取得浏览器能力；Cua Driver 与环境部分适合接着理解桌面操作；Herdr 更适合回到编排与执行环境课程研究。

坐标换算、截图缩放、底层输入注入是视觉路径的实现与排错知识。它们有用，但不应成为理解 Computer Use 的第一道门槛，也不能代表 Computer Use 的全部实现。

## 浏览器接入、登录状态与桌面范围的补充依据

2026-09-17 核验的正文素材已并入第 15 课，2026-09-18 补入桌面范围与页面授权边界。来源与结论如下；这是文档／源码核验，没有安装运行这些项目的整套示例。

| 来源 | 核验结论 |
| --- | --- |
| [Playwright 认证状态](https://playwright.dev/docs/auth) | 可以保存并加载认证状态；新建干净环境不会自动取得日常浏览器的登录。状态复用不等于实时同步。 |
| [Playwright BrowserType](https://playwright.dev/docs/api/class-browsertype) | 支持专用持久化目录及 Chromium 的 `connectOverCDP()`；不支持直接自动化日常 Chrome 默认 profile，也不能多实例共用同一数据目录。 |
| [Chrome 调试入口限制](https://developer.chrome.com/blog/remote-debugging-port) | 从 Chrome 136 起，远程调试参数用于默认数据目录时不再生效，需要非默认目录。 |
| [Playwright MCP，`e73d72e`](https://github.com/microsoft/playwright-mcp/blob/e73d72e01f162054a3d0a6b0fe8d4affffb095ee/README.md#user-profile) | 扩展模式连接已有标签页并复用登录；Playwright 与扩展可以组合。 |
| [BrowserSkill 点击实现，`75e2c64`](https://github.com/Tencent/BrowserSkill/blob/75e2c64abaf4b7cc75682d94b0c1fd5db0cbd5e5/apps/extension/src/tools/interaction.ts#L475-L627) | 解析目标节点、取得几何位置，再用 `Input.dispatchMouseEvent` 执行点击。 |
| [BrowserSkill 扩展驱动](https://github.com/Tencent/BrowserSkill/blob/75e2c64abaf4b7cc75682d94b0c1fd5db0cbd5e5/apps/extension/src/browser-driver/chromium-cdp.ts#L70-L77)与 [Chrome API](https://developer.chrome.com/docs/extensions/reference/api/debugger) | `chrome.debugger.sendCommand` 是扩展发送 CDP 命令的入口。 |
| [Chrome 可访问性说明](https://developer.chrome.com/docs/devtools/accessibility/reference) | 浏览器提供可访问性树与计算属性，不能把 AX 描述成模型看图生成的文字。 |
| [Playwright 上传接口](https://playwright.dev/docs/input#upload-files) | 可以给文件输入控件设置文件，或处理 filechooser 事件，无需逐层点击系统文件窗口。 |
| [Microsoft UI Automation](https://learn.microsoft.com/en-us/dotnet/framework/ui-automation/ui-automation-overview) | 桌面控件也可提供结构化属性和操作；桌面自动化不限于截图坐标。 |
| [Anthropic Computer Use 安全说明](https://platform.claude.com/docs/en/agents-and-tools/tool-use/computer-use-tool#security-considerations) | 页面和图片可能携带提示注入，建议限制环境权限和网络范围，保留必要的人工控制；这些措施不等于消除全部风险。 |

2026-09-17 会话中用现有 Chrome 工具完成了 GitHub 搜索、进入腾讯仓库、打开 Releases、滚动与截图。该演示没有安装或使用 BrowserSkill 执行操作。会话中读回发布页和截图属于该次操作证据，不能据此宣称整套项目、桌面隔离或提示注入防护已经验收。
