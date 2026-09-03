"""
行程规划总控 Agent —— 直接持有所有 MCP 工具，并行收集信息后流式输出最终行程。

架构（优化后，无嵌套）:
  Planner (LangGraph Agent)
    ├── 高德地图 MCP 工具：weather / POI search / direction / geo
    └── 酒店比价 MCP 工具：search / calendar / advisor

速度对比：
  原方案：Planner → 子Agent(LLM+MCP+LLM) → MCP     每次搜索 3 次 LLM
  本方案：Planner → MCP → Planner                    每次搜索 1 次 LLM + 支持并行
"""
import re
from typing import AsyncIterator
from langchain.agents import create_agent
from langchain_core.language_models import BaseChatModel

from mcp_client import McpClientManager
from prompts import PLANNER_AGENT_PROMPT

TOOL_LABELS = {
    "maps_weather":                     ("🌤️", "查询天气"),
    "maps_text_search":                 ("🔍", "搜索POI"),
    "maps_around_search":               ("📍", "周边搜索"),
    "maps_search_detail":               ("📄", "POI详情"),
    "maps_direction_walking":           ("🚶", "规划步行路线"),
    "maps_direction_walking_by_address": ("🚶", "规划步行路线"),
    "maps_direction_driving":           ("🚗", "规划驾车路线"),
    "maps_direction_driving_by_address": ("🚗", "规划驾车路线"),
    "maps_direction_transit_integrated": ("🚌", "规划公交路线"),
    "maps_direction_transit_integrated_by_address": ("🚌", "规划公交路线"),
    "maps_direction_bicycling":         ("🚲", "规划骑行路线"),
    "maps_bicycling":                   ("🚲", "规划骑行路线"),
    "maps_geo":                         ("📍", "地址转经纬度"),
    "search":                           ("🏨", "酒店多平台比价"),
    "calendar":                         ("📅", "扫描低价日历"),
    "advisor":                          ("🧭", "订房决策分析"),
}

_TOOL_CALL_PATTERN = re.compile(r"\[TOOL_CALL:[^\]]*\]")


class TripPlanner:
    """
    旅行规划总控智能体 —— 直接持有所有 MCP 工具。
    """

    def __init__(self, llm: BaseChatModel):
        self.llm = llm
        self.mcp = McpClientManager()
        self._agent = None

    async def build(self):
        """一次性加载所有 MCP 工具，组装 Planner Agent"""
        if self._agent is not None:
            return

        poi_tools = await self.mcp.get_tools_for("poi")
        weather_tools = await self.mcp.get_tools_for("weather")
        route_tools = await self.mcp.get_tools_for("route")
        hotel_price_tools = await self.mcp.get_tools_for("hotel")

        all_tools = [*poi_tools, *weather_tools, *route_tools, *hotel_price_tools]

        self._agent = create_agent(
            model=self.llm,
            tools=all_tools,
            system_prompt=PLANNER_AGENT_PROMPT,
        )

    async def invoke(self, user_input: str) -> str:
        """非流式调用"""
        await self.build()
        result = await self._agent.ainvoke({
            "messages": [{"role": "user", "content": user_input}]
        })
        return result["messages"][-1].content

    async def stream(self, user_input: str) -> AsyncIterator[str]:
        """流式输出 + 工具调用状态标记"""
        await self.build()

        streamed_any = False
        final_content = ""

        async for event in self._agent.astream_events(
            {"messages": [{"role": "user", "content": user_input}]},
            version="v2",
        ):
            kind = event.get("event", "")

            if kind == "on_chat_model_stream":
                content = event["data"]["chunk"].content
                if content:
                    content = _TOOL_CALL_PATTERN.sub("", content)
                    if content.strip():
                        streamed_any = True
                        yield content

            elif kind == "on_chat_model_end":
                output = event["data"].get("output")
                content = getattr(output, "content", "") if output is not None else ""
                if isinstance(content, list):
                    content = "".join(
                        item.get("text", "") if isinstance(item, dict) else str(item)
                        for item in content
                    )
                if content:
                    final_content = content

            elif kind == "on_tool_start":
                name = event.get("name", "unknown")
                emoji, label = TOOL_LABELS.get(name, ("🔧", name))
                yield f"\n{emoji} {label}...\n"

            elif kind == "on_tool_end":
                pass

        if not streamed_any and final_content:
            final_content = _TOOL_CALL_PATTERN.sub("", final_content)
            if final_content.strip():
                yield final_content