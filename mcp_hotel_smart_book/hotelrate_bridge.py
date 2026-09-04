# -*- coding: utf-8 -*-
"""hotelrate 取价子进程 —— 直接调用 hotelrate-crawl 的取价方法获取
Agoda / Booking.com 的实时酒店房价，并把两家各自的最低报价归一化成
一行 JSON 打到 stdout，供「酒店聪明订」服务进程（.hotel-mcp）消费。

与旧版（MCP 工具转发）的区别：
  这里不再经过 hotelrate-mcp 的 `hotel_quote` MCP 工具与 stdio 握手，
  而是直接在 .hotelrate-mcp 环境里实例化 hotelrate-crawl 的核心类：
    - hotelrate.config.Settings / get_settings()
    - hotelrate.schemas.LiveQuoteRequest / Platform
    - hotelrate.services.LiveQuoteService.quote()
  其内部即为该项目获取实时房价的真实方法链：
    UrlDiscoveryService.discover（酒店页 URL 发现）
      → AgodaCollector / BookingCollector.fetch_rates（Playwright 抓取
        Agoda room-grid API / Booking availability 等接口，LD+JSON / DOM /
        URL / 文本价格多级解析兜底）
    demo 模式（DEMO_MODE=true）下两个 collector 直接返回 build_demo_offer()
    的确定性合成价，便于无浏览器跑通整条管线。

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

# 直接使用 hotelrate-crawl 的取价方法（.hotelrate-mcp 环境已安装该包）
from hotelrate.config import get_settings
from hotelrate.schemas import LiveQuoteRequest, Platform
from hotelrate.services import LiveQuoteService

PLATFORM_SOURCES = {"booking": "Booking", "agoda": "Agoda"}


def _as_number(value):
    """把 pydantic JSON 里的价格（可能是 str / int / float / Decimal 字符串）转 float。"""
    if value is None:
        return None
    try:
        return float(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def _pick_lowest_offer(platform_result: dict, nights: int) -> dict | None:
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
    nights = max(1, nights)
    return {
        "price": price,
        "original_currency": offer.get("currency") or "CNY",
        "room_name": offer.get("room_name") or "",
        "meal_plan": offer.get("meal_plan") or "",
        "cancel_policy": offer.get("cancellation_policy") or "",
        "base_price": _as_number(offer.get("base_price")),
        "tax_fee": _as_number(offer.get("tax_fee")),
        "per_night": round(price / nights, 2),   # 每晚均价（原币种）
        "mode": offer.get("mode") or "parsed",    # demo / parsed / api / dom ... 数据来源标识
        "url": (platform_result.get("selected_url") or offer.get("source_url")) or "",
        "n_offers": len(offers),
    }


async def _quote(args: dict) -> dict:
    """直接调用 hotelrate-crawl 的 LiveQuoteService.quote() 取 Agoda + Booking 房价。"""
    timeout = float(args.get("timeout", 90))
    currency = args.get("currency", "CNY")
    locale = args.get("locale", "zh-CN")

    # 在构造 Settings 之前设定环境变量（pydantic-settings 优先级：init > env > .env 文件）
    demo = bool(args.get("demo", True))
    os.environ["DEMO_MODE"] = "true" if demo else "false"
    os.environ["FIRECRAWL_ENABLED"] = "true" if args.get("firecrawl", False) else "false"
    os.environ.setdefault("GOOGLE_SKIP", "true")
    os.environ.setdefault("HEADLESS", "true")
    # 不让缓存文件落在项目根目录
    os.environ["URL_MAPPING_CACHE_PATH"] = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        ".hotelrate-cache", "url_mapping_cache.json",
    )

    settings = get_settings()
    service = LiveQuoteService(settings)

    checkin = date.fromisoformat(args["checkin"])
    checkout = date.fromisoformat(args["checkout"])

    try:
        platform_values = [p for p in (args.get("platforms") or ["booking", "agoda"])
                           if p in PLATFORM_SOURCES]
        platforms = [Platform(p) for p in (platform_values or ["booking", "agoda"])]
    except ValueError:
        platforms = [Platform.BOOKING, Platform.AGODA]

    request = LiveQuoteRequest(
        hotel_name=args["hotel_name"],
        city=args.get("city", ""),
        checkin=checkin,
        checkout=checkout,
        adults=int(args.get("adults", 2)),
        children=int(args.get("children", 0)),
        currency=currency,
        locale=locale,
        platforms=platforms,
        # 只盯用户给的入住日期，不做额外多日期探测，控制实时爬取耗时
        probe_days_ahead=0,
        probe_step_days=3,
    )

    try:
        response = await asyncio.wait_for(service.quote(request), timeout=timeout)
    except asyncio.TimeoutError:
        return {"_timeout": True, "error": f"hotelrate 取价超过 {timeout}s"}
    except Exception as exc:  # noqa: BLE001 —— 任何异常都要以 JSON 汇报
        return {"_error": True, "error": f"{type(exc).__name__}: {exc}"}
    return response.model_dump(mode="json")


def _normalize(response: dict, demo: bool) -> dict:
    """把 LiveQuoteResponse（model_dump）收敛成桥输出结构。"""
    result: dict = {"ok": True, "demo": demo, "platforms": {}}
    if "_timeout" in response or "_error" in response:
        result["ok"] = False
        result["error"] = response.get("error", "timeout")
        return result

    raw_results = {r.get("platform"): r for r in response.get("results") or [] if r.get("platform")}
    req = response.get("request") or {}
    try:
        nights = max(1, (date.fromisoformat(req.get("checkout")) - date.fromisoformat(req.get("checkin"))).days)
    except (TypeError, ValueError):
        nights = 1
    for platform_key, source in PLATFORM_SOURCES.items():
        pr = raw_results.get(platform_key)
        entry: dict = {"source": source, "matched": False, "error": ""}
        if pr is None:
            entry["error"] = "该平台未返回结果"
        else:
            diag = pr.get("diagnosis") or ""
            lowest = _pick_lowest_offer(pr, nights)
            if lowest is None:
                entry["error"] = diag or "未解析到有效房价"
            else:
                entry.update({
                    "matched": True,
                    "name": pr.get("platform") or source,
                    "price": lowest["price"],
                    "original_currency": lowest["original_currency"],
                    "room_name": lowest["room_name"],
                    "meal_plan": lowest["meal_plan"],
                    "cancel_policy": lowest["cancel_policy"],
                    "base_price": lowest["base_price"],
                    "tax_fee": lowest["tax_fee"],
                    "per_night": lowest["per_night"],
                    "mode": lowest["mode"],
                    "demo": lowest["mode"] == "demo" or demo,
                    "url": lowest["url"],
                    "n_offers": lowest["n_offers"],
                    "diagnosis": diag,
                })
        result["platforms"][platform_key] = entry
    return result


def main() -> int:
    # 固定 UTF-8 输出，避免 Windows GBK 控制台下中文 JSON 乱码（父进程也按 UTF-8 读取）
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
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