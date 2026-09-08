# 第 7 课：Agent Sandbox——审批、权限与执行边界

假设你把 Agent 的工作目录设在项目里，让它修一个测试。它却绕到上级目录，把测试文件删了。报错没了，测试也没了。

问题不在于它有没有从指定目录启动，而在于启动后的进程还能碰到什么。用户点一次“允许”，也不会自动给命令套上保护。

这一课沿着一条文件读取请求，看清工具名单、审批、系统权限和沙盒分别管什么。

## 1. 工作目录是起点，不是边界

先看一个小目录，外面的文件只存放示例文字：

```text
demo/
|-- workspace/
|-- outside-secret.txt    内容：demo-secret
```

如果当前进程有读取权限，从 `workspace/` 启动的 Shell 仍能执行：

```bash
cat ../outside-secret.txt
```

结果是 `demo-secret`。`cwd=workspace` 只决定相对路径从哪里计算，`../` 仍然能走到上级。告诉 Agent 在哪儿上班，不等于收走它整栋楼的钥匙。

限制工具名单也有类似的边界。假设应用隐藏了 `write_file`，但仍允许 `run_bash`，Shell 可以写：

```bash
printf demo > result.txt
```

它通过重定向创建文件，没有调用名为 `write_file` 的工具。因此，**Tool Policy（工具策略）** 控制哪些工具入口可用；要限制入口内部能产生的影响，还需要执行层的保护。

工具名单不仅影响展示给模型的说明，执行入口也要检查。不能因为模型写出了一个工具名，就直接找到同名函数运行。

## 2. 同意执行，与真的有权限，是两回事

工具可用以后，应用可以再问用户是否批准这一次操作，这叫 **Approval（审批）**。

下面的代码只判断请求是否能进入执行阶段，尚未运行命令。工具名单和批准结果来自应用的可信记录，不能由模型自己填写：

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

顺序有意义：策略禁止的工具，即使带着“用户同意”，也不能执行；通过策略检查后，才看本次批准结果。

`ready` 还不等于文件一定读得开。进程在操作系统里实际拥有的能力，叫 **Permission（权限）**。如果系统不允许这个进程读目标文件，用户在 Agent 界面点“允许”，读取仍会失败。

审批不会把文件自动改成可读，不会把进程变成 root。反过来，系统允许读取，应用仍可以因为用户拒绝而停止。人的决定和进程的权限，两者都要满足。

## 3. 怎样让系统强制拒绝越界？

**Sandbox（沙盒）** 是由系统强制执行的隔离边界，可以限制进程接触的文件、网络和其他资源。模型就算忘了规则，或者读到恶意指令，边界仍应生效。

命令在哪里执行，由执行后端（Backend）决定：

```text
Host 后端：使用宿主进程拥有的权限
Sandbox 后端：在受限制的环境中执行
```

下面是在具备 `sandbox-exec` 的 macOS 上运行的完整小例子。它只创建临时演示文件，分别在普通进程和限制读取的进程中执行同一条 `cat`：

```python
import json
import subprocess
import tempfile
from pathlib import Path

with tempfile.TemporaryDirectory() as folder:
    target = Path(folder).resolve() / "outside-secret.txt"
    target.write_text("demo-secret", encoding="utf-8")
    command = ["/bin/cat", str(target)]

    quoted_path = json.dumps(str(target), ensure_ascii=False)
    profile = "(version 1)(allow default)"
    profile += f"(deny file-read-data (literal {quoted_path}))"

    host = subprocess.run(command, capture_output=True, timeout=5)
    sandboxed = ["/usr/bin/sandbox-exec", "-p", profile] + command
    sandbox = subprocess.run(sandboxed, capture_output=True, timeout=5)

    print("host_read =", host.returncode == 0)
    print("sandbox_read =", sandbox.returncode == 0)
```

在支持此机制的环境中，结果为：

```text
host_read = True
sandbox_read = False
```

`-p` 后面是本次进程的隔离规则：先允许默认操作，再拒绝读取指定文件。拒绝由操作系统执行，代码没有靠一个 `if` 假装文件打不开。

这只是证明拒读边界存在。规则仍允许其他文件和网络操作，不能当成完整安全策略。其他系统可以使用不同机制实现隔离，读懂这里的保护关系即可；无需记住每个平台的参数。

如果上层策略要求必须隔离，沙盒创建失败时应停止执行，不能偷偷退回 Host。否则“有保护”和“保护启动失败”最后都变成了无限制执行。

## 4. 临时离开沙盒，究竟改变了什么？

有些 Agent 允许某次命令离开平常的沙盒，改在 Host 执行，通常称为 **Elevated**。它只是执行位置和限制的变化，不等于获得管理员权限。

下面只展示“正常情况下已启用 Sandbox”时的选择。调用它之前，工具策略和审批都应已经通过：

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

`allow_elevated` 由可信策略决定。更高层要求必须隔离时，这个值就不能为真；模型不能自己把它改成真。命令即使最终进入 Host，也仍受宿主用户本身的权限限制，后续命令不会因此永久离开沙盒。

把本课各层放回一条请求中：

```text
应用决定：工具是否可用 → 本次是否批准 → 选择执行后端
执行时：系统权限与 Sandbox 规则共同限制进程
执行后：保存 Tool Result 和 Ledger
```

系统权限与沙盒规则并不是两个依次执行的普通 `if`。选好后端之后，它们共同约束进程。Ledger 记录执行结果，不能代替隔离；把越界行为记得再清楚，也没有阻止它发生。

## 5. 规则必须覆盖真正执行的路径

假设配置写着“只能访问指定域名”，命令却可以直接使用 Host 网络，绕过检查代理。这行配置就没有形成边界。

要限制网络，流量必须经过实际执行规则的隔离网络、代理或防火墙，并且不能另找一条路绕开。文件规则也一样：写入可能来自文件工具、Shell、插件或其他进程，必须检查所有实际入口。

只把终端放进容器，也可能漏掉仍在宿主运行的插件、Hook 和 MCP 子进程。对这些入口，要么提供相应隔离，要么把整个 Agent 进程树放进受限环境。开放能力越多，越要检查哪些操作还留在边界外。[1]

远程执行服务可以承担创建和管理隔离环境的工作。例如，核验版本的 OpenSandbox 提供统一接口，让 Harness 把命令送到受管理的容器或集群环境执行。实际隔离强度仍由后端、挂载和网络配置决定；接上 SDK 不会自动得到所有保护。审批谁来做、哪些凭据可以交给环境、执行后如何记账，仍由应用负责。[2]

以后看到一个 Agent 宣称“支持 Sandbox”，可以沿着一条命令追问：它在哪里执行，哪些资源被限制，规则由谁强制，失败后是否停止，是否还有其他入口能绕过。能把这些问题回答清楚，才知道本次操作受到了什么保护。

下一课继续追踪命令执行后的记录：多个模型请求、工具调用与重试，怎样接成一条可以排查的运行路径。

## 资料与配套实验

1. [Hermes：已核验版本的进程与工具隔离边界](https://github.com/NousResearch/hermes-agent/blob/63279301bcbdc185c1b07b98a9312eb0c862f26d/SECURITY.md)
2. [OpenSandbox：已核验版本的架构](https://github.com/opensandbox-group/OpenSandbox/blob/a8ad18fa741f9c50a552116c16d09ba4be385468/docs/architecture/index.md)
3. [OpenSandbox：隔离后端配置](https://github.com/opensandbox-group/OpenSandbox/blob/a8ad18fa741f9c50a552116c16d09ba4be385468/docs/guides/secure-container.md)
4. [配套实验与完整运行说明](../exercises/lesson-07-safety/README.md)
5. [全部项目对照、固定源码与核验记录](../research/07-safety-source-verification.md)
