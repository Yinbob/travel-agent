"""
配置中心 —— 统一管理环境变量、LLM 实例、MCP 连接参数。
"""
import os
from dataclasses import dataclass, field
from dotenv import load_dotenv
from langchain_community.chat_models.tongyi import ChatTongyi
from langchain_community.chat_models import tongyi as _tongyi_module
from langchain_core.messages import AIMessage

load_dotenv()

# ========== 修复 langchain_community ChatTongyi 流式 tool_calls 的 KeyError ==========
# 上游 bug: subtract_client_response 访问 prev_function["name"] / ["arguments"]
# 前没有检查 key 是否存在。流式首个 tool_call chunk 可能不含这些 key。


def _patched_subtract(self, resp, prev_resp):
    import json

    resp_copy = json.loads(json.dumps(resp))
    message = resp_copy["output"]["choices"][0]["message"]
    prev_message = json.loads(json.dumps(prev_resp))["output"]["choices"][0]["message"]

    message["content"] = message["content"].replace(
        prev_message.get("content", "") or "", ""
    )

    if message.get("tool_calls") and prev_message.get("tool_calls"):
        for index, tool_call in enumerate(message["tool_calls"]):
            function = tool_call["function"]
            prev_function = prev_message["tool_calls"][index]["function"]

            if "name" in function and "name" in prev_function:
                function["name"] = function["name"].replace(prev_function["name"], "")
            if "arguments" in function and "arguments" in prev_function:
                function["arguments"] = function["arguments"].replace(
                    prev_function["arguments"], ""
                )

    return resp_copy


ChatTongyi.subtract_client_response = _patched_subtract
# ========== 修复结束 ==========

# ========== 修复 ChatTongyi 回传历史时 tool_calls 参数非 JSON ==========
# 上游 bug: 流式 chunk 把未拼完整的原始 tool_call 塞进 additional_kwargs，
# 下次请求时原样回传给 DashScope，触发
# "The function.arguments parameter ... must be in JSON format" (400)。
# 修复：回传时用 langchain 已解析好的 message.tool_calls 重建干净的
# tool_calls（arguments 转 JSON 字符串），丢弃残缺原始片段。
_ORIG_CONVERT_MESSAGE_TO_DICT = _tongyi_module.convert_message_to_dict


def _patched_convert_message_to_dict(message):
    import json

    message_dict = _ORIG_CONVERT_MESSAGE_TO_DICT(message)
    if isinstance(message, AIMessage):
        tool_calls = getattr(message, "tool_calls", None)
        if tool_calls:
            clean_tool_calls = []
            for call in tool_calls:
                args = call.get("args")
                if isinstance(args, (dict, list)):
                    args = json.dumps(args, ensure_ascii=False)
                clean_tool_calls.append({
                    "type": "function",
                    "id": call.get("id") or "",
                    "function": {
                        "name": call.get("name") or "",
                        "arguments": args if isinstance(args, str) else json.dumps(args),
                    },
                })
            message_dict["tool_calls"] = clean_tool_calls
        else:
            message_dict.pop("tool_calls", None)
    return message_dict


_tongyi_module.convert_message_to_dict = _patched_convert_message_to_dict
# ========== 修复结束 ==========


@dataclass
class Config:
    """全局配置，单例语义 —— 模块级 CONFIG 实例"""

    # API 密钥
    api_key: str = field(
        default_factory=lambda: os.getenv("DASHSCOPE_API_KEY", "")
    )

    # LLM —— qwen-plus 比 qwen3-max 快 2-3 倍，质量差别小
    model_name: str = "qwen-plus"
    temperature: float = 0.5

    # 地图 MCP 连接（高德开放平台官方 MCP，原阿里百炼 amap-maps 已下线）
    mcp_transport: str = "http"
    mcp_url: str = field(
        default_factory=lambda: os.getenv("AMAP_MCP_URL", "https://mcp.amap.com/mcp")
    )
    amap_api_key: str = field(
        default_factory=lambda: os.getenv("AMAP_MAPS_API_KEY")
        or os.getenv("AMAP_API_KEY", "")
    )

    # 工具领域映射
    tool_domains: dict = field(default_factory=lambda: {
        "poi":     ["maps_text_search", "maps_search_detail", "maps_around_search"],
        "weather": ["maps_weather"],
        "route":   [
            "maps_direction_walking",
            "maps_direction_walking_by_address",
            "maps_direction_driving",
            "maps_direction_driving_by_address",
            "maps_direction_transit_integrated",
            "maps_direction_transit_integrated_by_address",
            "maps_direction_bicycling",
            "maps_bicycling",
            "maps_geo",
        ],
        "hotel":   ["search", "calendar", "advisor"],
    })

    # 自动检查初始化
    def __post_init__(self):
        if not self.api_key:
            raise ValueError("请配置 DASHSCOPE_API_KEY")

    # 生成带高德 Key 的 MCP 地址
    def map_mcp_url(self) -> str:
        url = self.mcp_url
        if "key=" not in url:
            if not self.amap_api_key:
                raise RuntimeError(
                    "未配置高德地图 Key：请在 travel-agent 目录的 .env 中设置 "
                    "AMAP_MAPS_API_KEY=你的高德Web服务Key（前往 https://lbs.amap.com 申请）"
                )
            sep = "&" if "?" in url else "?"
            url = f"{url}{sep}key={self.amap_api_key}"
        return url

    # 创建模型实例对象
    def create_llm(self) -> ChatTongyi:
        return ChatTongyi(
            model=self.model_name,
            api_key=self.api_key,
            temperature=self.temperature,
            streaming=False,         # 关闭流式：qwen3-max 流式下最终消息内容会丢失
            model_kwargs={"max_tokens": 8192},  # 行程 JSON 较长，避免输出被截断
        )


CONFIG = Config()