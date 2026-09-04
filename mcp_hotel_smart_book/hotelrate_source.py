# -*- coding: utf-8 -*-
"""Agoda / Booking.com 外部数据源适配器（「酒店聪明订」服务进程侧）。

运行在 .hotel-mcp（fastmcp4 / mcp2）内的 server.py 通过本模块把查询「外包」给
.hotelrate-mcp 环境里的 hotelrate_bridge.py —— 桥进程在 hotelrate 自己的环境内
**直接调用 hotelrate-crawl 的取价方法**（LiveQuoteService.quote → AgodaCollector /
BookingCollector.fetch_rates，Playwright 抓包 + 多级兜底解析；demo 模式即
build_demo_offer 合成价），父进程只消费一行 JSON。

设计要点：
  - 全部逻辑可选：.hotelrate-mcp 未安装或未启用时返回 None，既有国内四平台
    （飞猪/途牛/RG/同程）链路完全不受影响；
  - 任何异常/超时都收敛成 per-platform 的 error 行，不影响主比价结果；
  - 非 CNY 报价按内置近似汇率折算（仅供比价排序参考，演示/实验用途）。
"""
import json
import os
import subprocess
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_HOTELRATE_RUNTIME = _ROOT / ".hotelrate-mcp"
_HOTELRATE_PYTHON = _HOTELRATE_RUNTIME / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
_BRIDGE = Path(__file__).resolve().parent / "hotelrate_bridge.py"

# 环境变量（可写进 travel-agent/.env）
ENV_ENABLED = "HOTELRATE_MCP_ENABLED"     # true / false
ENV_DEMO = "HOTELRATE_DEMO"               # true=演示合成价（无需浏览器） false=真实爬取
ENV_CURRENCY = "HOTELRATE_CURRENCY"       # 请求币种，默认 CNY
ENV_LOCALE = "HOTELRATE_LOCALE"           # 请求 locale，默认 zh-CN
ENV_SPOT_CHECK = "HOTELRATE_SPOT_CHECK"   # search 中对最便宜前 N 家做 Agoda/Booking 抽查
ENV_TIMEOUT = "HOTELRATE_QUOTE_TIMEOUT"   # 单次 hotel_quote 超时（秒）
ENV_FIRECRAWL = "HOTELRATE_FIRECRAWL"     # 是否允许 firecrawl 兜底（默认 false）

DEFAULT_CURRENCY = "CNY"
DEFAULT_LOCALE = "zh-CN"
DEFAULT_SPOT_CHECK = 2
DEFAULT_TIMEOUT = 90

# 非 CNY 报价的近似汇率（1 外币 ≈ N 人民币），仅用于比价排序参考
FX_TO_CNY = {
    "USD": 7.20, "EUR": 7.80, "GBP": 9.20, "JPY": 0.048, "KRW": 0.0051,
    "HKD": 0.92, "TWD": 0.22, "SGD": 5.40, "MYR": 1.62, "THB": 0.21,
    "AUD": 4.70, "CAD": 5.25, "CHF": 8.10, "SEK": 0.70, "NOK": 0.68,
    "DKK": 1.05, "INR": 0.086, "VND": 0.00028, "IDR": 0.00045, "PHP": 0.13,
    "AED": 1.96, "SAR": 1.92, "ILS": 2.00, "TRY": 0.20, "RUB": 0.078,
    "PLN": 1.80, "CZK": 0.30, "HUF": 0.019, "RON": 1.55, "MXN": 0.39,
    "BRL": 1.30, "ZAR": 0.39,
}


def _env_flag(name: str, default: str) -> bool:
    return os.getenv(name, default).strip().lower() in ("1", "true", "yes", "on")


def enabled() -> bool:
    """外部 MCP 数据源是否启用（默认：检测到 .hotelrate-mcp 即启用）。"""
    raw = os.getenv(ENV_ENABLED, "").strip().lower()
    if raw in ("1", "true", "yes", "on"):
        return True
    if raw in ("0", "false", "no", "off"):
        return False
    return _HOTELRATE_PYTHON.exists()  # 未显式配置时看环境是否就绪


def demo_mode() -> bool:
    return _env_flag(ENV_DEMO, "true")


def spot_check_count() -> int:
    """search 中对最便宜的前 N 家酒店做 Agoda/Booking 抽查比价。"""
    try:
        return max(0, int(os.getenv(ENV_SPOT_CHECK, str(DEFAULT_SPOT_CHECK))))
    except (TypeError, ValueError):
        return DEFAULT_SPOT_CHECK


def installed() -> bool:
    return _HOTELRATE_PYTHON.exists()


def runtime_hint() -> str:
    """未安装时给用户的中文修复提示。"""
    return (
        "未找到 Agoda/Booking 数据源运行环境 .hotelrate-mcp。"
        "如需启用请执行：python -m venv .hotelrate-mcp && "
        ".hotelrate-mcp/bin/pip install git+https://github.com/seanbabalala/hotelrate-crawl.git "
        "（真实比价还需 .hotelrate-mcp/bin/pip install playwright && "
        ".hotelrate-mcp/bin/playwright install chromium，并设 HOTELRATE_DEMO=false）"
    )


def _to_cny(price: float, currency: str) -> float | None:
    """把 foreign 报价折算成人民币；已知币种用近似汇率，未知返回 None。"""
    if not currency or currency.upper() == "CNY":
        return round(price, 2)
    rate = FX_TO_CNY.get(currency.upper())
    if rate is None:
        return None
    return round(price * rate, 2)


def quote(hotel_name: str, city: str, check_in: str, check_out: str,
          adults: int = 2, timeout: float | None = None) -> dict:
    """通过桥子进程直接调用 hotelrate-crawl 的取价方法（Agoda + Booking）。

    返回归一化结构：
      {"ok": bool, "demo": bool, "error": str, "platforms": {"booking": {...}|None, "agoda": {...}|None}}
    其中每个平台条目字段与 server.py 内其他 compare_* 对齐：
      source/matched/name/price(¥)/original_currency/original_price/url/cancel_policy/error
    """
    if not enabled():
        return {"ok": False, "demo": demo_mode(), "error": "hotelrate 数据源未启用",
                "platforms": {"booking": None, "agoda": None}}
    if not installed():
        return {"ok": False, "demo": demo_mode(), "error": runtime_hint(),
                "platforms": {"booking": None, "agoda": None}}

    currency = os.getenv(ENV_CURRENCY, DEFAULT_CURRENCY) or DEFAULT_CURRENCY
    locale = os.getenv(ENV_LOCALE, DEFAULT_LOCALE) or DEFAULT_LOCALE
    try:
        cfg_timeout = float(os.getenv(ENV_TIMEOUT, str(DEFAULT_TIMEOUT)) or DEFAULT_TIMEOUT)
    except (TypeError, ValueError):
        cfg_timeout = DEFAULT_TIMEOUT  # 配置写错时回退默认，避免整个工具崩溃
    t = max(5.0, float(timeout or cfg_timeout))
    firecrawl = _env_flag(ENV_FIRECRAWL, "false")
    demo = demo_mode()

    payload = {
        "hotel_name": hotel_name,
        "city": city,
        "checkin": check_in,
        "checkout": check_out,
        "adults": int(adults),
        "children": 0,
        "currency": currency,
        "locale": locale,
        "platforms": ["booking", "agoda"],
        "demo": demo,
        "firecrawl": firecrawl,
        "timeout": t,
    }
    try:
        proc = subprocess.run(
            [str(_HOTELRATE_PYTHON), str(_BRIDGE), json.dumps(payload, ensure_ascii=False)],
            capture_output=True,
            text=True,
            encoding="utf-8",       # 固定 UTF-8，避免 Windows GBK 控制台乱码
            errors="replace",
            timeout=t + 30,
            cwd=str(_ROOT),
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "demo": demo, "error": f"hotelrate 桥进程超时(>{t}s)",
                "platforms": {"booking": None, "agoda": None}}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "demo": demo, "error": f"hotelrate 桥进程启动失败: {exc}",
                "platforms": {"booking": None, "agoda": None}}

    try:
        data = json.loads(proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else "{}")
    except Exception:
        return {"ok": False, "demo": demo,
                "error": f"hotelrate 桥输出解析失败: {(proc.stderr or '')[-300:]}",
                "platforms": {"booking": None, "agoda": None}}

    demo = bool(data.get("demo", demo))
    platforms: dict = {}
    raw_platforms = data.get("platforms") or {}
    for key in ("booking", "agoda"):
        entry = raw_platforms.get(key)
        if not entry or not entry.get("matched"):
            platforms[key] = {
                "source": "Booking" if key == "booking" else "Agoda",
                "matched": False,
                "name": hotel_name,
                "price": None,
                "url": "",
                "error": (entry or {}).get("error") or data.get("error") or "未匹配到该平台价格",
            }
            continue
        original_price = entry.get("price")
        original_currency = entry.get("original_currency") or currency
        cny = _to_cny(original_price, original_currency) if original_price is not None else None
        if cny is None:
            platforms[key] = {
                "source": "Booking" if key == "booking" else "Agoda",
                "matched": False, "name": hotel_name, "price": None, "url": entry.get("url", ""),
                "error": f"报价币种 {original_currency} 无汇率映射，无法折算人民币",
            }
            continue
        platforms[key] = {
            "source": "Booking" if key == "booking" else "Agoda",
            "matched": True,
            "name": hotel_name,
            "price": cny,
            "original_currency": original_currency,
            "original_price": original_price,
            "per_night": _to_cny(entry.get("per_night"), original_currency),  # 每晚均价（¥）
            "room_name": entry.get("room_name", ""),
            "meal_plan": entry.get("meal_plan", ""),   # 餐标：含早/仅房间/全食宿...
            "cancel_policy": entry.get("cancel_policy", ""),
            "mode": entry.get("mode", "parsed"),       # demo / parsed / api / dom...
            "n_offers": entry.get("n_offers", 0),
            "url": entry.get("url", ""),
            "n_offers": entry.get("n_offers", 0),
            "error": "",
        }
    return {"ok": True, "demo": demo, "error": data.get("error", ""), "platforms": platforms}
