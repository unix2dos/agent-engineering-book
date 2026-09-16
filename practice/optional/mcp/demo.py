"""直接调用与本地 MCP 调用对照；无模型、无网络请求，只有给定套餐资料。"""

import argparse
import asyncio
from datetime import timedelta
from importlib.metadata import version
import json
import os
from pathlib import Path
import sys
from typing import Literal

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.server.fastmcp import FastMCP


server = FastMCP("plan-rules", log_level="CRITICAL")


@server.tool()
def get_plan(plan: Literal["family", "personal"]) -> dict[str, str | int]:
    """查询给定教学套餐的账号上限；只读，不提供修改功能。"""
    limits = {"family": 6, "personal": 3}
    if not isinstance(plan, str) or plan not in limits:
        raise ValueError("只支持 family 或 personal")
    return {
        "plan": plan,
        "max_accounts": limits[plan],
        "process_id": os.getpid(),
    }


async def compare(plan: str):
    direct = get_plan(plan)
    expected = 6 if plan == "family" else 3
    assert direct["max_accounts"] == expected
    print("1. 直接调用：", json.dumps(direct, ensure_ascii=False))

    parameters = StdioServerParameters(
        command=sys.executable,
        args=["-B", str(Path(__file__).resolve()), "--server"],
    )
    # 不传入当前进程的 API Key；SDK 只继承其默认环境变量清单。
    async with stdio_client(parameters) as (read, write):
        async with ClientSession(read, write, read_timeout_seconds=timedelta(seconds=10)) as session:
            initialized = await session.initialize()
            assert initialized.protocolVersion == "2025-11-25"
            print("2. MCP 初始化：协议", initialized.protocolVersion)

            listed = await session.list_tools()
            assert len(listed.tools) == 1 and listed.tools[0].name == "get_plan"
            tool = listed.tools[0]
            assert tool.outputSchema is not None, "本实验约定返回结构化结果"
            assert tool.inputSchema["required"] == ["plan"]
            assert set(tool.inputSchema["properties"]["plan"]["enum"]) == {"family", "personal"}
            print("3. tools/list：", tool.name)
            print("   inputSchema：", json.dumps(tool.inputSchema, ensure_ascii=False))

            print("4. tools/call：", json.dumps({"name": tool.name, "arguments": {"plan": plan}}))
            result = await session.call_tool(tool.name, arguments={"plan": plan})
            assert not result.isError and isinstance(result.structuredContent, dict)
            remote = result.structuredContent
            assert remote["plan"] == plan and remote["max_accounts"] == expected
            assert remote["process_id"] != direct["process_id"], "MCP 函数应在子进程执行"
            print("5. MCP 返回：", json.dumps(remote, ensure_ascii=False))
            print("   业务结果一致；process_id 不同，函数在另一个进程执行。")

            invalid = await session.call_tool(tool.name, arguments={"plan": "unknown"})
            assert invalid.isError
            print("6. 无效套餐：isError=true，没有伪造成功结果。")

            absent = await session.call_tool("write_plan", arguments={"plan": plan})
            assert absent.isError
            print("7. 未提供的 write_plan：isError=true，没有可调用的写工具。")
    print("检查通过；MCP 连接与子进程已由 SDK 上下文管理器关闭。")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--server", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--plan", choices=["family", "personal"], default="family")
    args = parser.parse_args()
    if version("mcp") != "1.26.0":
        parser.error("本实验固定使用 mcp==1.26.0，请按 README 在独立环境安装")
    if args.server:
        # stdio 的 stdout 用于协议消息，不能在 Server 侧随意 print。
        server.run(transport="stdio")
    else:
        asyncio.run(compare(args.plan))


if __name__ == "__main__":
    main()
