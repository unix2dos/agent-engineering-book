# 第 2 课：Agent Runtime——Model、Harness、Tool 与 Environment

你让 Agent“读取 `config.json`，再告诉我里面使用什么主题”。屏幕上很快出现：“我来读取。”

这句话来自 Model。真正打开文件的却是另一个对象。要判断一次读取到底卡在哪里，必须先把“提出动作”和“执行动作”的角色分开。

## 1. 同一次读取，实际有四个参与者

先不看 API 字段，只看一次读取发生了什么：

```text
用户要求读取 config.json
-> Model 提出 read_file("config.json")
-> Harness 判断这次申请能否执行
-> Tool 打开文件
-> Environment 返回文件内容或系统错误
-> Harness 把真实结果交还 Model
```

这里的四个名字分别指向四种职责：

| 核心组件 | 在读取案例中做什么 | 不负责什么 |
| --- | --- | --- |
| Model | 根据目标和已有结果选择下一步 | 不直接拥有本地文件权限 |
| Harness | 组织输入、检查申请、调用工具并控制运行 | 不替 Model 决定开放任务的解法 |
| Tool | 完成一个具体动作，例如读取文件 | 不决定自己何时出场 |
| Environment | 文件系统、Shell、网页和 API 所在的真实世界 | 不保证返回内容正确或安全 |

由这四部分组成的可运行整体，就是 **Agent Runtime**。Runtime 不是 Model 的另一个名字，也不是某个 SDK；它是这套系统真正运行起来后的整体。

## 2. Harness 为什么不是一根转发线？

假设 Model 提出 `read_file("../../secret.txt")`。如果 Harness 只负责转发，这条申请会直接碰到宿主文件系统。

真正的 Harness 至少要在几个时刻作出判断：

```text
发给 Model 之前   选择指令、历史和可见工具
收到申请之后      检查工具是否存在、参数是否可用
执行之前          检查策略、审批和运行边界
执行之后          保存结果，并决定继续还是停止
异常发生之后      决定报错、恢复还是等待人工处理
```

这些工作必须由能执行确定性代码的程序完成。Model 可以建议下一步，却不能同时负责批准自己的建议、声明执行成功并修改运行规则。

后面的课程会逐一展开这些判断。第 3 课先处理调用协议；第 4～6 课处理保存、Context 和故障恢复；第 7 课再处理审批、权限与 Sandbox。

## 3. Tool 与 Environment 为什么要分开？

`read_file` 是 Tool，磁盘上的真实文件系统是 Environment。

这一区分在失败时很有用。Tool 代码可能把路径解析错，也可能正确调用操作系统后收到 `Permission denied`。前者是工具实现问题，后者是当前进程在真实环境中没有权限。

同一个 Tool 换一个 Environment，结果也可能不同：

```text
同一个 read_file
-> 在开发机上读到文件
-> 在容器里找不到挂载
-> 在 Sandbox 里被系统拒绝
```

Tool 定义“准备做什么”，Environment 决定现实世界实际返回什么。Harness 必须保存真实结果，不能把 Model 预期的结果当成执行结果。

## 4. 出错时，先判断是哪一层

还是读取 `config.json`：

| 可见现象 | 优先检查的层 | 原因 |
| --- | --- | --- |
| Model 一直选择错误工具 | Model 或当前 Context | 决策本身不合适 |
| `read_file` 根本没有注册 | Harness | 找不到对应工具实现 |
| 路径参数结构不合法 | Harness / Tool 边界 | 申请不能安全地交给函数 |
| 文件解码代码报错 | Tool | 具体实现失败 |
| 操作系统返回无权限 | Environment / 进程权限 | 工具已经碰到真实边界 |
| 工具成功后仍继续死循环 | Harness | 停止和预算没有生效 |

这张表不是说一类故障永远只有一个原因，而是给排查提供第一站。没有角色边界时，所有失败最后都会被含糊地叫成“Model 不行”。

## 5. 开源项目里，这些职责不一定放在同一个文件

OpenCode 没有创建一个叫 `Harness` 的大类，再把所有代码塞进去。它把职责拆在不同模块中：[Session Processor](https://github.com/anomalyco/opencode/blob/50efc055de282e0e54a87ccebb8e2054cc45efd2/packages/opencode/src/session/processor.ts)处理会话运行，[Tool Registry](https://github.com/anomalyco/opencode/blob/50efc055de282e0e54a87ccebb8e2054cc45efd2/packages/opencode/src/tool/registry.ts)寻找工具实现，[Permission Evaluation](https://github.com/anomalyco/opencode/blob/50efc055de282e0e54a87ccebb8e2054cc45efd2/packages/opencode/src/permission/evaluate.ts)判断是否允许。

所以，Harness 描述的是一组运行职责，不要求源码中存在同名文件或对象。读其他项目时，应寻找“谁在完成这些工作”，而不是只搜索 `harness` 这个单词。

## 6. 自己给一次运行标责任

画出下面这条最小链路，再给每一步标上负责人：

```text
用户要求读取文件
-> 选择 read_file
-> 检查路径和权限
-> 打开文件
-> 收到文件内容或错误
-> 决定下一步
```

正确的标法是：Model 负责两端的选择，Harness 负责检查和推进，Tool 负责打开文件，Environment 提供真实文件与系统结果。

这一课只建立职责地图，还没有规定 Tool Call 在 API 中长什么样。下一课会把申请、执行、回执和停止条件写成可运行的[Tool Calling Loop](03-工具调用循环.md)。

## 主动回忆

1. Model、Harness、Tool 与 Environment 分别负责什么？
2. 为什么 Agent Runtime 不能等同于 Model？
3. Harness 为什么不能只转发消息？
4. `read_file` 与文件系统为什么不是同一个东西？
5. 操作系统返回 `Permission denied` 时，应该先检查哪一层？
6. 为什么源码中搜不到 `Harness`，仍可能存在完整的 Harness 职责？

<details>
<summary>检查简答</summary>

1. Model 选择动作；Harness 组织并控制运行；Tool 执行具体动作；Environment 返回真实状态。
2. Model 只负责推理和生成，Runtime 还包含控制程序、工具与真实环境。
3. 它还要组装输入、校验申请、执行策略、控制循环并处理异常。
4. `read_file` 是执行读取动作的代码；文件系统是它接触的真实环境。
5. 先确认进程身份、文件权限、挂载或 Sandbox 等 Environment 边界。
6. Harness 是职责集合，项目可以把这些职责拆进会话、工具注册、权限和执行模块。

</details>

## 参考资料

> 资料最后核验于 2026-09-03；会变化的源码锚点收录在下面的复核记录中。

- [本批章节一手资料复核](../research/01-05-chapter-promotion-sources.md)
- [OpenCode Session Processor](https://github.com/anomalyco/opencode/blob/50efc055de282e0e54a87ccebb8e2054cc45efd2/packages/opencode/src/session/processor.ts)
- [OpenCode Tool Registry](https://github.com/anomalyco/opencode/blob/50efc055de282e0e54a87ccebb8e2054cc45efd2/packages/opencode/src/tool/registry.ts)
- [OpenCode Permission Evaluation](https://github.com/anomalyco/opencode/blob/50efc055de282e0e54a87ccebb8e2054cc45efd2/packages/opencode/src/permission/evaluate.ts)
