"""
MCP 客户端管理器 —— 单例模式，全局共享高德地图 MCP 连接。
"""
import os
from pathlib import Path

from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_core.tools import BaseTool
from config import CONFIG

# 酒店比价服务独立运行环境（fastmcp4 + mcp2），与主进程的 mcp1 客户端隔离
_HOTEL_RUNTIME = Path(__file__).parent / ".hotel-mcp"
HOTEL_PYTHON = _HOTEL_RUNTIME / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
HOTEL_SERVER_PATH = Path(__file__).parent / "mcp_hotel_smart_book" / "server.py"


def _hotel_command() -> list[str]:
    if not HOTEL_PYTHON.exists():
        raise RuntimeError(
            f"未找到酒店比价运行环境: {HOTEL_PYTHON}。"
            "请先在 travel-agent 目录执行: "
            "python -m venv .hotel-mcp && .hotel-mcp/Scripts/python -m pip install fastmcp"
        )
    return [str(HOTEL_PYTHON), str(HOTEL_SERVER_PATH)]


class McpClientManager:
    """
    高德地图 MCP 客户端单例。
    这是单例模式
    保证整个程序永远只有一个 McpClientManager
    保证缓存只创建一次，不重复请求
    保证客户端不重复初始化

    职责：
      1. 管理与高德开放平台 MCP 服务器的连接
      2. 按领域（poi/weather/route）分发工具子集
      3. 缓存已加载工具，避免重复请求

    用法：
      manager = McpClientManager()
      poi_tools = await manager.get_tools_for("poi")
      route_tools = await manager.get_tools_for("route")
    """

    _instance: "McpClientManager | None" = None

    def __new__(cls) -> "McpClientManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._client: MultiServerMCPClient | None = None
        self._tools_cache: dict[str, list[BaseTool]] = {}
        self._initialized = True

    # ==================== 连接管理 ====================

    async def _get_client(self) -> MultiServerMCPClient:
        """懒加载 MCP 客户端"""
        if self._client is None:
            hotel_cmd = _hotel_command()
            self._client = MultiServerMCPClient({
                "amap-server": {
                    "transport": CONFIG.mcp_transport,
                    "url": CONFIG.map_mcp_url(),
                },
                "hotel-server": {
                    "transport": "stdio",
                    "command": hotel_cmd[0],
                    "args": hotel_cmd[1:],
                }
            })
        return self._client

    # ==================== 工具获取 ====================

    async def get_all_tools(self) -> list[BaseTool]:
        """获取 MCP 服务器暴露的全部工具"""
        if "all" not in self._tools_cache:
            client = await self._get_client()
            self._tools_cache["all"] = await client.get_tools()
            # for t in self._tools_cache["all"]:
            #     print(f"  ✓ {t.name}: {t.description[:60]}...")
        return self._tools_cache["all"]

    async def get_tools_for(self, domain: str) -> list[BaseTool]:
        """按领域获取工具子集"""
        all_tools = await self.get_all_tools()
        target_names = set(CONFIG.tool_domains.get(domain, []))

        def prefix_match(name: str) -> bool:
            return any(name == target or name.startswith(target) or target.startswith(name)
                       for target in target_names)

        # 高德官方/旧百炼工具名可能略有差异：先精确/前缀匹配，未命中再按关键字兜底
        matched = [t for t in all_tools if prefix_match(t.name)]
        if not matched:
            fallback_keywords = {
                "poi":     ("search",),
                "weather": ("weather",),
                "route":   ("direction", "bicycling", "cycling"),
                "hotel":   ("search", "calendar", "advisor"),
            }.get(domain, ())
            matched = [t for t in all_tools if any(k in t.name for k in fallback_keywords)]
        return matched

    # ==================== 生命周期 ====================

    async def close(self):
        """关闭 MCP 连接（如有需要）"""
        self._client = None
        self._tools_cache.clear()

    @classmethod
    def reset(cls):
        """重置单例（测试用）"""
        cls._instance = None
