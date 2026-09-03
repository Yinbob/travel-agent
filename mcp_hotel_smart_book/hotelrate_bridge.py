# -*- coding: utf-8 -*-
"""hotelrate-mcp 桥接子进程 —— 在 .hotelrate-mcp 环境内以 MCP stdio 客户端调用
Agoda / Booking.com 比价服务（hotelrate-mcp）的 hotel_quote 工具，并把结果整理成
一行紧凑 JSON 打到 stdout，供「酒店聪明订」服务进程消费。

为什么需要这个桥：
  - mcp_hotel_smart_book/server.py 运行在 .hotel-mcp（fastmcp4 / mcp 2.x）；
  - hotelrate-mcp 依赖 mcp>=1.20（mcp 1.x），装进独立 .hotelrate-mcp 环境；
  - 跨版本库直接嵌套客户端有协议握手风险，因此用「同版本配对」的子进程桥：
    桥进程在 .hotelrate-mcp 内用 mcp 1.x client 连接 mcp 1.x server（安全），
    父进程只跟桥做 JSON 行通信。

用法:
  python hotelrate_bridge.py '<json>'
  json: {
    "hotel_name": str, "city": str, "checkin": "YYYY-MM-DD", "checkout": "YYYY-MM-DD",
    "adults": int, "children": int, "currency": "CNY", "locale": "zh-CN",
    "platforms": ["booking", "agoda"], "demo": bool, "firecrawl": bool,
    "timeout": float (秒)
  }
输出（stdout 最后一行，JSON）:
  {"ok": true, "demo": bool, "platforms": {"booking": {...} | null, "agoda": {...} | null}}
  {"ok": false, "error": "..."}
"""
import asyncio
import json
import os
import sys
import time
from datetime import date, timedelta

import anyio
import mcp
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# ---- 每个平台的最低报价 —— 从 hotel_quote 原始返回里抽出一行可比数据 ----
PLATFORM_SOURCES = {"booking": "Booking", "agoda": "Agoda"}


def _as_number(value):
    """把 pydantic JSON 里的价格（可能是 str / int / float / Decimal 字符串）转 float。"""
    if value is None:
        return None
    try:
        return float(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def _pick_lowest_offer(platform_result: dict) -> dict | None:
    """从 LivePlatformResult 的 offers 里挑 final_price 最低的一档，返回可展示字段。"""
    offers = platform_result.get("offers") or []
    priced = []
    for offer in offers:
        price = _as_number(offer.get("final_price"))
        if price is not None and price > 0:
            priced.append((price, offer))
    if not priced:
        return None
    priced.sort(key=lambda x: x[0])
    price, offer = priced[0]
    return {
        "price": price,
        "original_currency": offer.get("currency") or "CNY",
        "room_name": offer.get("room_name") or "",
        "cancel_policy": offer.get("cancellation_policy") or "",
        "url": (platform_result.get("selected_url") or offer.get("source_url")) or "",
        "n_offers": len(offers),
    }


async def _quote(args: dict) -> dict:
    """启动 hotelrate-mcp stdio 服务并调用 hotel_quote 工具。"""
    timeout = float(args.get("timeout", 90))
    currency = args.get("currency", "CNY")
    locale = args.get("locale", "zh-CN")

    # 子服务环境：demo 与 firecrawl 用显式参数覆盖（env 优先级高于 .env 文件）
    env = dict(os.environ)
    env["DEMO_MODE"] = "true" if args.get("demo", True) else "false"
    env["FIRECRAWL_ENABLED"] = "true" if args.get("firecrawl", False) else "false"
    env.setdefault("GOOGLE_SKIP", "true")
    env.setdefault("HEADLESS", "true")
    # 不把 cache / 会话目录污染到项目里
    env["URL_MAPPING_CACHE_PATH"] = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".hotelrate-cache", "url_mapping_cache.json"
    )

    cmd = [sys.executable, "-m", "hotelrate.apps.mcp.server"]
    params = StdioServerParameters(command=cmd[0], args=cmd[1:], env=env)

    payload = {
        "hotel_name": args["hotel_name"],
        "city": args.get("city", ""),
        "checkin": args["checkin"],
        "checkout": args["checkout"],
        "adults": int(args.get("adults", 2)),
        "children": int(args.get("children", 0)),
        "currency": currency,
        "locale": locale,
        "platforms": args.get("platforms") or ["booking", "agoda"],
    }

    with anyio.move_on_after(timeout):
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tool_result = await session.call_tool("hotel_quote", payload)
                text_parts = []
                for content in tool_result.content or []:
                    if getattr(content, "type", "") == "text":
                        text_parts.append(content.text)
                raw = "\n".join(text_parts)
                try:
                    return json.loads(raw)
                except Exception:
                    # 有些实现返回的不是单块 JSON，尝试直接整体解析一次
                    return {"_raw": raw}
    return {"_timeout": True, "error": f"hotel_quote 超过 {timeout}s"}


def _normalize(response: dict, demo: bool) -> dict:
    """把 LiveQuoteResponse 收敛成桥输出结构。"""
    result: dict = {"ok": True, "demo": demo, "platforms": {}}
    if "_timeout" in response:
        result["ok"] = False
        result["error"] = response.get("error", "timeout")
        return result
    if "_raw" in response:
        result["ok"] = False
        result["error"] = "hotel_quote 返回无法解析: " + (response["_raw"] or "")[:200]
        return result

    raw_results = {r.get("platform"): r for r in response.get("results") or [] if r.get("platform")}
    for platform_key, source in PLATFORM_SOURCES.items():
        pr = raw_results.get(platform_key)
        entry: dict = {"source": source, "matched": False, "error": ""}
        if pr is None:
            entry["error"] = "该平台未返回结果"
        else:
            diag = pr.get("diagnosis") or ""
            lowest = _pick_lowest_offer(pr)
            if lowest is None:
                entry["error"] = diag or "未解析到有效房价"
            else:
                entry.update({
                    "matched": True,
                    "name": pr.get("platform") or source,
                    "price": lowest["price"],
                    "original_currency": lowest["original_currency"],
                    "room_name": lowest["room_name"],
                    "cancel_policy": lowest["cancel_policy"],
                    "url": lowest["url"],
                    "n_offers": lowest["n_offers"],
                    "diagnosis": diag,
                })
        result["platforms"][platform_key] = entry
    return result


def main() -> int:
    if len(sys.argv) < 2:
        print(json.dumps({"ok": False, "error": "缺少参数 JSON"}, ensure_ascii=False))
        return 1
    try:
        args = json.loads(sys.argv[1])
        # 日期缺省：入住 7 天后 1 晚
        if not args.get("checkin"):
            args["checkin"] = (date.today() + timedelta(days=7)).isoformat()
        if not args.get("checkout"):
            args["checkout"] = (date.fromisoformat(args["checkin"]) + timedelta(days=1)).isoformat()
        demo = bool(args.get("demo", True))
        t0 = time.monotonic()
        response = asyncio.run(_quote(args))
        out = _normalize(response, demo)
        out["elapsed_s"] = round(time.monotonic() - t0, 1)
        print(json.dumps(out, ensure_ascii=False))
        return 0
    except Exception as exc:  # noqa: BLE001 —— 桥进程任何异常都要以 JSON 形式汇报
        print(json.dumps({"ok": False, "error": f"{type(exc).__name__}: {exc}"}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    sys.exit(main())
