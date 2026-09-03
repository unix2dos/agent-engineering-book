# 第 6 课一手资料复核：JSONL、SQLite 与数据库

> 核验时间：2026-09-03（Asia/Shanghai）。
>
> 规则：项目行为只采用官方 GitHub 仓库和官方文档；变化中的项目固定到本次核验 Commit。

## 本次结论

第 6 课的主线仍然成立：JSONL 与 SQLite 不是高低级之分，选择取决于写者数量、查询方式、事务、约束和恢复需求。

两处旧材料已经失效，正式章节不能照搬：

1. OpenClaw 的旧 `docs/refactor/database-first.md` 已从当前仓库删除。当前依据改为 Session 文档和 Database Schemas 文档。
2. Pi 当前 SQLite Session Backend 明确不导出 Search Service 或 FTS Index；搜索属于单独的 S3 Projection。旧材料中“该 SQLite Backend 提供可选 FTS”的说法已经过时。

## 当前项目快照

| 项目 | 固定 Commit | 与本章有关的当前实现 |
| --- | --- | --- |
| Pi | [`007c0be`](https://github.com/earendil-works/pi/commit/007c0be640789b8971db6ecacdc96e61107d849f) | Coding Agent Session 默认保存为 JSONL，并用 `id/parentId` 形成树；Agent Core 另有 SQLite Session Backend。该 Backend 支持事务与 WAL 快照，但不提供 FTS/Search Service。 |
| OpenClaw | [`8544aed`](https://github.com/openclaw/openclaw/commit/8544aed05a5dbffb871483be781f71351203319e) | 全局控制面和每 Agent 数据面使用不同 SQLite；普通 Session 与 Transcript 在每 Agent 数据库中，旧 JSON/JSONL 作为迁移输入，Incognito Session 留在内存。 |
| Hermes Agent | [`561b053`](https://github.com/NousResearch/hermes-agent/commit/561b053f794a1781868bb032029d589c67708119) | `~/.hermes/state.db` 保存 Session、Message 与模型配置；使用 WAL、索引和 FTS5，并维护 Schema Migration。 |
| LangGraph | [`11738d8`](https://github.com/langchain-ai/langgraph/commit/11738d83db4320bb191804342b5c76ae7eca54a0) | Checkpointer 是可替换的持久层；一个 `thread_id` 对应一系列 Checkpoint，可使用内存、SQLite、PostgreSQL 等实现。 |
| OpenAI Agents SDK Python | [`89c02c8`](https://github.com/openai/openai-agents-python/commit/89c02c828ee8510fe9a84ee6675608193aa13b02) | Session Backend 包括 SQLite、Redis、SQLAlchemy、MongoDB、Dapr 和 OpenAI Conversations；同一 Run 不能把 SDK Session 与服务端续接选项叠加。 |

## 固定文件

- [Pi Session Format](https://github.com/earendil-works/pi/blob/007c0be640789b8971db6ecacdc96e61107d849f/packages/coding-agent/docs/session-format.md)
- [Pi SQLite Session Backend](https://github.com/earendil-works/pi/blob/007c0be640789b8971db6ecacdc96e61107d849f/packages/session-backends/sqlite-node/README.md)
- [OpenClaw Session](https://github.com/openclaw/openclaw/blob/8544aed05a5dbffb871483be781f71351203319e/docs/concepts/session.md)
- [OpenClaw Database Schemas](https://github.com/openclaw/openclaw/blob/8544aed05a5dbffb871483be781f71351203319e/docs/reference/database-schemas.md)
- [Hermes Session Storage](https://github.com/NousResearch/hermes-agent/blob/561b053f794a1781868bb032029d589c67708119/website/docs/developer-guide/session-storage.md)
- [LangGraph Checkpoint](https://github.com/langchain-ai/langgraph/blob/11738d83db4320bb191804342b5c76ae7eca54a0/libs/checkpoint/README.md)
- [OpenAI Agents SDK Sessions](https://github.com/openai/openai-agents-python/blob/89c02c828ee8510fe9a84ee6675608193aa13b02/docs/sessions/index.md)

## 不应写成通用结论的实现细节

- Pi 的 JSONL 是 Coding Agent CLI 当前选择，不是所有 Pi 包的唯一 Backend。
- OpenClaw 当前使用 SQLite，不代表 JSONL 不再适合本地单 Writer Agent。
- Hermes 使用 WAL 和 FTS，是由多入口访问、检索和迁移需求推动，不是“Agent 必须使用 SQLite”的证据。
- Provider 保存 Conversation 只能替应用管理部分模型历史，不能证明本地 Tool 副作用执行了几次。
