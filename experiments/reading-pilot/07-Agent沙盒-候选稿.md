# 第 7 课：Agent Sandbox——审批、权限与执行边界

上一课让排查助手把报告写进工作区的 `diagnosis.txt`，并处理回执丢失。现在再加一条要求：只能处理项目材料，不能读取项目外的文件。

把工作目录设为项目目录，再让用户点一次“允许”，够了吗？先做一次读取就知道了。下面的秘密文件只有 `demo-secret` 这几个示例字符，不接触真实凭据。

## 1. Workspace 与 Tool Policy：入口限制

准备这样的临时目录：

```text
demo/
|-- workspace/
|   |-- diagnosis.txt
|-- outside-secret.txt    内容：demo-secret
```

从 `workspace/` 启动 Shell，执行：

```bash
cat ../outside-secret.txt
```

只要进程有读取权限，就能得到 `demo-secret`。`cwd=workspace` 只决定相对路径从哪里计算，`../` 仍能走到上级。告诉 Agent 在哪儿上班，不等于收走它整栋楼的钥匙。

之前的文件工具会解析路径，再检查目标是否位于工作区。这能保护经过该函数的访问，却不会自动管住另一个 Shell 进程。

工具名单也有这个问题。假设应用隐藏了 `write_file`，却保留 `run_bash`，Shell 仍能执行：

```bash
printf demo > diagnosis.txt
```

文件照样被写入。**Tool Policy（工具策略）** 决定哪些工具入口可用，不能仅凭工具名字判断其全部能力。允许任意 Shell 命令，就不能把这套工具集称为“只读”。

工具策略要在真正的执行入口检查，不能只从给模型的说明中删掉名字。模型仍可能申请一个没开放的工具；这时执行器应拒绝，而不是寻找同名函数运行。

## 2. Approval 与 Permission：意愿和能力

**Approval（审批）** 回答“是否同意这一次操作”。允许写 `diagnosis.txt`，不等于同意读取另一个文件，更不等于允许修改系统设置。批准记录要关联具体请求，参数变了，应重新判断是否仍在授权范围内。

下面假设这些请求都需要审批，只演示执行前的决策顺序。`approved` 来自应用核验过的审批记录，不能取自模型声称的“用户已批准”：

```python
def check_request(tool, allowed_tools, approved):
    if tool not in allowed_tools:
        return "denied_by_policy"
    if not approved:
        return "rejected"
    return "ready"

print(check_request("run_bash", {"read_file"}, True))
print(check_request("read_file", {"read_file"}, False))
print(check_request("read_file", {"read_file"}, True))
```

输出为：

```text
denied_by_policy
rejected
ready
```

策略禁止的工具，不能靠一个批准绕过去；通过策略检查后，才看本次审批。这个函数没有实现审批记录的认证，也不意味着所有读取都要弹窗。实际应用可以按可信策略预先允许低风险操作。

`ready` 只表示通过了这两项应用检查。**Permission（权限）** 指进程实际拥有的访问能力：如果操作系统不允许它读文件，界面上点“允许”仍然读不开。审批按钮不会把进程变成 root。

| 当前情况 | 应当发生什么 |
| --- | --- |
| 系统能读，用户拒绝本次读取 | 应用停止，不调用工具 |
| 用户批准，系统禁止读取 | 执行时被系统拒绝，返回错误 |
| 工具策略禁止，带着批准结果 | 执行入口直接拒绝 |

应用应返回实际拒绝原因，不能把权限错误改写成成功，也不能为完成任务自动提权。

## 3. Sandbox Backend：验证系统强制边界

当前用户通常能读很多与任务无关的文件。只继承这些权限，排查助手就可能看得太多。**Sandbox（沙盒）** 给执行进程增加系统强制的限制，例如只允许访问指定文件或网络。模型忘记规则时，限制仍要生效。

执行后端（Backend）决定命令在哪里运行：

```text
Host：在宿主环境中，受宿主用户及已有系统限制约束
Sandbox：在额外限制过的环境中执行
```

下面用 macOS 的 `sandbox-exec` 观察文件拒读。它是系统命令，但本机手册已标为 **DEPRECATED（弃用）**，这里只做机制实验，不建议把这段配置当成新项目的部署方案。其他系统无需照抄命令。

实验不能只看“秘密文件没读出来”。如果沙盒根本没启动，也会读失败。因此要加一个**正对照**：同一规则下，允许的文件必须能读。

```python
import json
import subprocess
import sys
import tempfile
from pathlib import Path

sandbox_exec = Path("/usr/bin/sandbox-exec")
if sys.platform != "darwin" or not sandbox_exec.is_file():
    raise RuntimeError("本机不支持此实验，尚未验证系统拒读")

with tempfile.TemporaryDirectory() as folder:
    root = Path(folder).resolve()
    workspace = root / "workspace"
    workspace.mkdir()
    (workspace / "allowed.txt").write_text("inside-demo", encoding="utf-8")
    secret = root / "outside-secret.txt"
    secret.write_text("demo-secret", encoding="utf-8")

    quoted_path = json.dumps(str(secret), ensure_ascii=False)
    profile = "(version 1)(allow default)"
    profile += f"(deny file-read-data (literal {quoted_path}))"
    sandbox = [str(sandbox_exec), "-p", profile]

    def read_with(prefix, path):
        return subprocess.run(
            prefix + ["/bin/cat", path], cwd=workspace,
            capture_output=True, text=True, timeout=5,
        )

    host = read_with([], "../outside-secret.txt")
    allowed = read_with(sandbox, "allowed.txt")
    denied = read_with(sandbox, "../outside-secret.txt")

    assert host.returncode == 0 and host.stdout == "demo-secret"
    assert allowed.returncode == 0 and allowed.stdout == "inside-demo", "正对照失败"
    assert denied.returncode != 0 and denied.stdout == "", "禁止的文件仍能读取"
    print("host_read =", host.returncode == 0)
    print("sandbox_allowed_read =", allowed.returncode == 0)
    print("sandbox_secret_read =", denied.returncode == 0)
```

通过检查时输出：

```text
host_read = True
sandbox_allowed_read = True
sandbox_secret_read = False
```

`-p` 后面是本次进程使用的规则。`allow default` 允许默认操作，后面的 `deny file-read-data` 禁止读取那个具体路径的数据。拒绝发生在系统执行期间，不是 Python 先看文件名、再假装读取失败。

这里的断言只负责验证结果，不承担安全限制。规则仍允许其他文件和网络操作；它证明了本例的拒读行为，**不是完整的工作区隔离策略**。不能换一个真实秘密文件，就把这份默认放行配置投入使用。

## 4. Elevated 与 Fail-closed：后端选择

有些 Agent 允许某次命令离开平常的沙盒，改到 Host 执行，称为 **Elevated**。这里说的是执行环境变化，不等于获得管理员权限，也不是所有产品统一使用的名称。

下面只展示默认启用 Sandbox、且工具策略与审批已经通过后的选择：

```python
def choose_backend(elevated_requested, allow_elevated):
    if not elevated_requested:
        return "sandbox"
    if not allow_elevated:
        return "elevation_denied"
    return "host"

print(choose_backend(False, False))
print(choose_backend(True, False))
print(choose_backend(True, True))
```

输出为：

```text
sandbox
elevation_denied
host
```

`allow_elevated` 来自可信策略。更高层要求必须隔离时，它就不能为真，模型无法自己开通权限。允许一次命令在 Host 运行，也不应让后续命令永久离开沙盒。

后端选好后，还可能创建失败。如果本次操作要求强制隔离，创建失败就必须停止，不能偷偷改到 Host 重跑。这种“保护条件不成立就拒绝执行”的规则叫 **Fail-closed**。安全设施坏了，不能用“先裸跑一下”提高可用性。

上面的函数只返回选择，没有实现创建后端或失败处理。把这些关系放回一次请求中：

```text
应用决策：工具策略 -> 本次审批 -> 选择并准备执行后端
执行期间：系统权限与 Sandbox 规则共同限制进程
执行之后：保存实际 Tool Result 与 Ledger
```

系统权限与 Sandbox 规则不是两个顺次运行的普通 if；它们在执行环境里约束真实访问。上一课的 Ledger 可以记录拒绝或失败，却没有隔离能力。越界读完后再记一笔，材料已经看到了。

## 5. 执行路径覆盖：别漏掉另一个出口

假设终端已经放进容器，某个插件却仍在宿主机上执行 `open(...)`。终端的文件限制管不到它。“支持 Sandbox”这几个字，还没回答到底保护了哪些进程。

| 实际入口 | 需要核对的边界 |
| --- | --- |
| 文件工具、Shell | 在哪里执行，能够访问哪些路径 |
| 插件、Hook、MCP 子进程 | 是否也进入隔离，还是留在 Host |
| 网络请求 | 是否必须经过执行规则的网络或代理，有没有直连旁路 |

例如，配置写着“只允许访问指定域名”，命令却能绕过代理直连公网，这条名单就没形成限制。规则必须覆盖真实流量，不能只写在工具说明里。

本书核验的 Hermes 安全文档也区分终端后端与更广的进程隔离：终端受限，不意味着插件和整个 Agent 进程树都受限。[1] 对未覆盖的执行入口，要么补上相应隔离，要么收回能力；不能因为其中一条路径安全，就把整个系统判为安全。

远程服务可以代为创建和管理执行环境。核验版本的 **OpenSandbox** 提供统一接口，将命令送到受管理的容器或集群环境中运行。实际隔离能力取决于所选后端、挂载与网络配置；审批、交给环境的凭据和执行记账仍由应用负责。[2][3]

回到诊断报告任务：想允许助手写工作区文件，就应验证允许的写入能完成，也验证项目外访问确实被拒绝。我会先查实际执行路径及拒绝结果，而不是先数配置里出现了几次 sandbox。

下一课看执行之后的另一个问题：多个模型请求、工具调用与等待，怎样接成一条能排查的运行路径。

## 资料与配套实验

1. [Hermes：已核验版本的进程与工具隔离边界](https://github.com/NousResearch/hermes-agent/blob/63279301bcbdc185c1b07b98a9312eb0c862f26d/SECURITY.md)
2. [OpenSandbox：已核验版本的架构](https://github.com/opensandbox-group/OpenSandbox/blob/a8ad18fa741f9c50a552116c16d09ba4be385468/docs/architecture/index.md)
3. [OpenSandbox：隔离后端配置](https://github.com/opensandbox-group/OpenSandbox/blob/a8ad18fa741f9c50a552116c16d09ba4be385468/docs/guides/secure-container.md)
4. [配套实验与完整运行说明](../../exercises/lesson-07-safety/README.md)
5. [项目对照、固定源码与核验记录](../../research/07-safety-source-verification.md)
6. [候选代码检查](check_lesson_07.py)：`python -B experiments/reading-pilot/check_lesson_07.py`，本机系统拒读部分需要支持 sandbox-exec 的 macOS。所有文件为临时假材料，不调用模型。
7. 本机命令手册：`man sandbox-exec`。本轮核验了 `-p` 用法与弃用标记；该实验不替代生产沙盒的选型和安全验证。
