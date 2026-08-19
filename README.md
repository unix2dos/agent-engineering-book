我学习的目录

## Learning Notes

今天学到的 DeepSeek Harness 基础知识：

1. **DSH 是什么**：DeepSeek Harness 是一个让 AI 代理运行的工作平台，代理通过工具（bash 命令、文件读写、网络搜索等）与环境交互，而不是直接执行代码。
2. **沙箱与审批**：DSH 有文件沙箱（如 workspace-write 只允许修改工作区内的文件）和审批策略（ask / never），用来控制代理能改哪些文件、哪些操作需要用户确认。
3. **后台任务与子代理**：耗时的命令可以放到后台运行（background job），独立的任务可以委托给子代理（subagent）；两者都有 ID，可随时查询输出或终止。
