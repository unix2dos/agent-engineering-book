# MCP 最小实验：直接调用与跨进程调用

这次只观察一件事：同一个 `get_plan` 函数，直接在当前程序中调用，与通过 MCP 交给另一个进程执行，有什么区别。

资料固定为教学数据：family 支持 6 个账号，personal 支持 3 个。实验不调用模型、不需要密钥、不连接业务数据库，也不提供修改套餐的工具。函数返回的 `process_id` 只用于辨认执行进程，不是套餐业务字段。

当前验证状态：初始化、工具发现和 family 查询已实际发生，Server 返回账号上限 6、`isError=false`。但本版 SDK 将裸 `dict` 返回值编码为 `content` 中的 JSON 文本，脚本却要求存在 `structuredContent`，因此结果检查失败。按作者“遇到问题先讨论”的约定暂停；无效参数与未知写工具两个后续检查尚未执行，暂不把本实验标为通过。

## 1. 运行

本实验核验环境为 Python 3.13.5、`mcp==1.26.0`。当前本机已安装依赖；其他环境若没有，可以在独立虚拟环境中安装该版本，不需要升级全局环境。

从仓库根目录运行：

```bash
python -B practice/optional/mcp/demo.py
```

然后只改套餐参数，再运行一次：

```bash
python -B practice/optional/mcp/demo.py --plan personal
```

需要从空环境开始时：

```bash
python -m venv practice/optional/mcp/.venv
practice/optional/mcp/.venv/bin/python -m pip install 'mcp==1.26.0'
practice/optional/mcp/.venv/bin/python -B practice/optional/mcp/demo.py
```

## 2. 看哪些结果

程序会打印直接调用结果、MCP 工具定义、实际参数和返回结果。观察账号上限是否一致，以及两次执行的 `process_id` 是否不同。进程编号每次可能变化，不要求与某个固定数字相同。

```text
直接调用：当前进程执行 get_plan("family")，返回 6 个账号

MCP 调用：
当前程序启动同一脚本的 Server 子进程
-> Client 初始化连接
-> tools/list 取得工具名、说明和 inputSchema
-> tools/call 发送 get_plan 和 {"plan": "family"}
-> Server 子进程执行同一个函数
-> Client 收到结果，账号上限仍为 6
```

调用顺序在本实验中由 Python 代码固定，不是模型自主选择。`tools/list` 不会执行套餐查询；`tools/call` 才请求执行。Server 通过装饰器注册函数，SDK 根据类型标注生成参数 Schema，并负责 MCP 消息和进程通信。

最后两个检查分别使用无效套餐和不存在的 `write_plan` 工具，确认返回 `isError=true`。这验证参数错误与未注册工具的处理，不等于已经实现用户身份认证、远端授权或操作系统沙盒。只读来自本工具的实际实现，不是因为用了 MCP 就自动安全。

## 3. 完成标准

合上代码，用自己的话解释：工具名和参数格式从哪里来、哪个动作真正执行函数、为什么两次结果相同但进程编号不同。

若账号数不一致、错误请求返回成功，或协议版本不符，先停止并检查，不继续拼接新的能力。程序每个请求最多等待 10 秒；退出时 SDK 关闭通信并回收子进程。

本实验只验证 Host/Client/Server 的工具调用路径。若接入模型，还需要宿主把工具定义转换为模型接口的格式，接住模型的调用申请，并将结果加入下一次模型请求。Function Calling 与 MCP 的适配留到这条路径解释清楚以后。

## 4. 版本边界与来源

固定 SDK 使用 **2025-11-25** 协议及其初始化握手。这是与本机已安装版本一致的可复现实验，不是最新协议教程；不能把这里的 `initialize()` 套进 **2026-07-28** 的新版发现流程。两版的 `tools/list` 和 `tools/call` 基本职责仍可用于当前对照，完整消息格式要按各自版本理解。

- [Python SDK v1.26.0：Client 与 stdio 示例](https://github.com/modelcontextprotocol/python-sdk/tree/v1.26.0#writing-mcp-clients)
- [MCP 2025-11-25：Tools](https://modelcontextprotocol.io/specification/2025-11-25/server/tools)
- [MCP 2026-07-28：架构与发现流程](https://modelcontextprotocol.io/docs/2026-07-28/learn/architecture)

本目录是[第 13 课](../../../chapters/13-MCP与Skills.md)的选做实验，不加入全书默认离线检查；默认检查仍只依赖标准库，这里需要 MCP SDK。当前未通过的检查见文首说明。
