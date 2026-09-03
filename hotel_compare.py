"""酒店比价调用器 —— 独立调用酒店 MCP 工具。

与 McpClientManager 分离：不导入 config，因此不需要 DASHSCOPE_API_KEY，
比价功能可以独立运行。
"""
import os
from pathlib import Path

from langchain_mcp_adapters.client import MultiServerMCPClient

# 酒店比价服务独立运行环境（fastmcp4 + mcp2），与主进程的 mcp1 客户端隔离
_HOTEL_RUNTIME = Path(__file__).parent / ".hotel-mcp"
HOTEL_PYTHON = _HOTEL_RUNTIME / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
HOTEL_SERVER_PATH = Path(__file__).parent / "mcp_hotel_smart_book" / "server.py"


async def call_hotel_tool(tool_name: str, args: dict) -> str:
    """通过 stdio 启动酒店 MCP 服务并调用指定工具，返回文本结果。"""
    if not HOTEL_PYTHON.exists():
        raise RuntimeError(
            f"未找到酒店比价运行环境: {HOTEL_PYTHON}。"
            "请先在 travel-agent 目录执行: "
            "python -m venv .hotel-mcp && .hotel-mcp/Scripts/python -m pip install fastmcp"
        )
    client = MultiServerMCPClient({
        "hotel-server": {
            "transport": "stdio",
            "command": str(HOTEL_PYTHON),
            "args": [str(HOTEL_SERVER_PATH)],
        }
    })
    tools = await client.get_tools()
    tool = next((t for t in tools if t.name == tool_name), None)
    if tool is None:
        raise ValueError(f"未找到酒店工具: {tool_name}")

    result = await tool.ainvoke(args)
    if isinstance(result, list):
        parts = []
        for item in result:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(item.get("text", ""))
            else:
                parts.append(str(item))
        return "\n".join(parts)
    return result if isinstance(result, str) else str(result)
