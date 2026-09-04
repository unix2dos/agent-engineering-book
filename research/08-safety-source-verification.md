# 第 8 课一手资料复核：审批、权限与沙盒边界

> 核验时间：2026-09-04（Asia/Shanghai）。
>
> 核验方式：使用 GitHub CLI 读取当前仓库 HEAD、官方安全文档和实际执行后端源码；正文链接固定到本次 Commit，避免未来代码变化后张冠李戴。

## 本次结论

第 8 课的主线成立，但不能再把这些控制画成一条简单流水线：

```text
应用先决定：Tool 是否可见 -> 本次是否批准 -> 选择 Host 或 Sandbox Backend
操作系统再强制：当前用户 Permission + Sandbox 文件/网络/进程规则
执行后再记录：Result + Ledger
```

`Approval` 是应用对某次请求的决定，`Permission` 是进程真正拥有的系统能力。`Elevated` 只可能改变一条已经获准命令的执行 Backend；它不能让被 Tool Policy 隐藏的工具重新出现，也不能获得超过 Host 进程本身的权限。

## 当前源码快照

| 项目 | 固定 Commit | 本章核验到的实现 |
| --- | --- | --- |
| Pi | [`6aedd10`](https://github.com/earendil-works/pi/commit/6aedd1066e540642165aa30fa7b4a1b863778aa7) | 官方安全文档明确写明没有内置 Sandbox，Project Trust 也不是 Sandbox；审批和 OS Sandbox 由扩展加入，或者把整个 Pi 放进容器、VM、microVM 或 OpenShell。 |
| OpenClaw | [`aa627d2`](https://github.com/openclaw/openclaw/commit/aa627d2e94164e6bb730a027880a7adda651e118) | Tool Policy、Sandbox 与 Elevated 是三个控制面。`deny` 优先；Elevated 只影响 `exec`，不能越过 Tool Policy，也不能绕过由上层角色强制要求的 Sandbox。 |
| Codex | [`ea2046f`](https://github.com/openai/codex/commit/ea2046f36d5ee12d39c8e168fc3e5129301afa2b) | Approval 与 Permission Profile 共同决定执行要求，再由平台 Backend 落地。macOS 使用 Seatbelt；Linux 当前默认 Bubblewrap，旧 Landlock 路径仅作显式兼容；Windows 使用受限 Token 等机制。网络域名配置不会单独启动受管代理。 |
| Hermes Agent | [`6327930`](https://github.com/NousResearch/hermes-agent/commit/63279301bcbdc185c1b07b98a9312eb0c862f26d) | 官方安全策略把 OS 隔离称为对抗恶意 LLM 的唯一承重边界。Terminal Backend 只覆盖 Shell 和建立在同一契约上的文件工具；要覆盖代码执行、MCP、插件和 Hook，必须包住整个 Agent 进程。 |
| E2B Infra | [`baab220`](https://github.com/e2b-dev/infra/commit/baab2207ee67bc09bab42b94819d3bce7a198e8f) | API 负责鉴权、生命周期和节点选择，Orchestrator 在节点上启动 Firecracker microVM，命令由 VM 内的 `envd` 执行。它提供隔离执行位置，不替 Harness 决定 Tool Policy、Approval 或业务 Ledger。 |
| OpenSandbox | [`a8ad18f`](https://github.com/opensandbox-group/OpenSandbox/commit/a8ad18fa741f9c50a552116c16d09ba4be385468) | 通过统一 SDK、CLI、MCP 和生命周期 API 管理 Docker 或 Kubernetes Sandbox；`execd` 在 Sandbox 内执行命令和文件操作。gVisor、Kata 和 Firecracker 是需要管理员额外选择的安全 Runtime，不是本地快速开始自动获得的保证。 |

## 相比旧稿需要收紧的地方

1. Pi 的 GitHub 主地址现在是 `earendil-works/pi`。旧地址会重定向，但正式章节统一使用新地址。
2. “Elevated 获批就回到 Host”只适用于没有更高层强制 Sandbox 的情况。OpenClaw 的 creator/operator required sandbox 会拒绝越界，并在 Sandbox 无法创建时关闭执行。
3. Codex 当前 Linux 主路径是 Bubblewrap。源码中的枚举名仍可能出现 `LinuxSeccomp`，不能据此把整个实现简单写成“只靠 Seccomp”。
4. 域名 Allowlist 只是规则数据。只有命令流量真的被隔离网络或受管 Proxy 接管，规则才成为机器边界。
5. Hermes 已在官方安全策略中明确区分 Terminal Backend 隔离与 Whole-process wrapping；正文应直接使用这条边界，而不是只从代码结构推测。
6. OpenSandbox 是可自部署的 Sandbox 平台，不是新的 Agent Harness。它适合说明“统一 API 与真实隔离 Backend 是两层”，但不应被加入本书长期逐章对比的核心参考集合。

## 固定源码

- [Pi Security](https://github.com/earendil-works/pi/blob/6aedd1066e540642165aa30fa7b4a1b863778aa7/packages/coding-agent/docs/security.md)
- [Pi Permission Gate Extension](https://github.com/earendil-works/pi/blob/6aedd1066e540642165aa30fa7b4a1b863778aa7/packages/coding-agent/examples/extensions/permission-gate.ts)
- [Pi Sandbox Extension](https://github.com/earendil-works/pi/blob/6aedd1066e540642165aa30fa7b4a1b863778aa7/packages/coding-agent/examples/extensions/sandbox/index.ts)
- [Pi Containerization](https://github.com/earendil-works/pi/blob/6aedd1066e540642165aa30fa7b4a1b863778aa7/packages/coding-agent/docs/containerization.md)
- [OpenClaw Sandbox vs Tool Policy vs Elevated](https://github.com/openclaw/openclaw/blob/aa627d2e94164e6bb730a027880a7adda651e118/docs/gateway/sandbox-vs-tool-policy-vs-elevated.md)
- [OpenClaw Exec Approvals](https://github.com/openclaw/openclaw/blob/aa627d2e94164e6bb730a027880a7adda651e118/docs/tools/exec-approvals.md)
- [Codex Approval and Sandboxing Runtime](https://github.com/openai/codex/blob/ea2046f36d5ee12d39c8e168fc3e5129301afa2b/codex-rs/core/src/tools/sandboxing.rs)
- [Codex Permission Profiles](https://github.com/openai/codex/blob/ea2046f36d5ee12d39c8e168fc3e5129301afa2b/codex-rs/core/src/config/permissions.rs)
- [Codex Sandbox Manager](https://github.com/openai/codex/blob/ea2046f36d5ee12d39c8e168fc3e5129301afa2b/codex-rs/sandboxing/src/manager.rs)
- [Codex Linux Sandbox](https://github.com/openai/codex/blob/ea2046f36d5ee12d39c8e168fc3e5129301afa2b/codex-rs/linux-sandbox/README.md)
- [Hermes Security](https://github.com/NousResearch/hermes-agent/blob/63279301bcbdc185c1b07b98a9312eb0c862f26d/SECURITY.md)
- [Hermes Terminal Environment Provider](https://github.com/NousResearch/hermes-agent/blob/63279301bcbdc185c1b07b98a9312eb0c862f26d/agent/terminal_env_provider.py)
- [Hermes Environment Base](https://github.com/NousResearch/hermes-agent/blob/63279301bcbdc185c1b07b98a9312eb0c862f26d/tools/environments/base.py)
- [E2B Infrastructure Architecture](https://github.com/e2b-dev/infra/blob/baab2207ee67bc09bab42b94819d3bce7a198e8f/docs/ARCHITECTURE.md)
- [OpenSandbox Architecture](https://github.com/opensandbox-group/OpenSandbox/blob/a8ad18fa741f9c50a552116c16d09ba4be385468/docs/architecture/index.md)
- [OpenSandbox Secure Container Runtime](https://github.com/opensandbox-group/OpenSandbox/blob/a8ad18fa741f9c50a552116c16d09ba4be385468/docs/guides/secure-container.md)
- [OpenSandbox MCP Server](https://github.com/opensandbox-group/OpenSandbox/blob/a8ad18fa741f9c50a552116c16d09ba4be385468/sdks/mcp/sandbox/python/README.md)

## 不能从这些源码推出什么

- 用户批准一次执行，不等于命令已经安全。
- 某个产品有 Sandbox 配置，不等于本次命令真的进入了 Sandbox Backend。
- Tool 名被禁用，不等于通用 Shell 内部的同类副作用也被系统阻止。
- 命令在容器或 microVM 中运行，不等于凭据注入、网络出口、租户隔离和业务审批已经正确配置。
- Ledger 记录了执行，不等于它能阻止越界；它只能帮助审计和恢复。
