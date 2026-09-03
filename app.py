"""智能旅行 & 酒店比价助手 — Streamlit Web 界面。"""
import asyncio
import calendar
import json
import re
import urllib.parse
from datetime import date, timedelta

import streamlit as st
from pathlib import Path
from streamlit.components.v1 import declare_component

trip_calendar = declare_component(
    "trip_calendar",
    path=str(Path(__file__).parent / "components" / "trip_calendar"),
)

# ---- 页面配置 ----
st.set_page_config(
    page_title="智能旅行 & 酒店比价助手",
    page_icon="🧳",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---- CSS 样式与动效 ----
st.markdown("""
<style>
    /* ===== 动效 ===== */
    @keyframes fadeInUp {
        from { opacity: 0; transform: translateY(12px); }
        to   { opacity: 1; transform: translateY(0); }
    }
    @keyframes pulse {
        0%, 100% { transform: scale(1); }
        50%      { transform: scale(1.05); }
    }
    .fade-in { animation: fadeInUp .4s ease-out both; }
    .d1 { animation-delay: .05s; }
    .d2 { animation-delay: .1s; }
    .d3 { animation-delay: .15s; }
    .d4 { animation-delay: .2s; }
    .d5 { animation-delay: .25s; }
    .d6 { animation-delay: .3s; }

    /* ===== 标题 ===== */
    .main-header {
        font-size: 2rem; font-weight: 700; padding: 0.5rem 0;
        border-bottom: 3px solid #4A90D9; margin-bottom: 1rem;
        background: linear-gradient(90deg, #4A90D9, #26C6DA);
        -webkit-background-clip: text; background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .plan-title {
        font-size: 1.4rem; font-weight: 700; color: #2E7D32;
        text-align: center; margin: 1rem 0;
    }
    .day-header {
        font-size: 1.1rem; font-weight: 700; color: #1565C0;
        border-bottom: 2px solid #BBDEFB; padding: 0.5rem 0; margin: 1rem 0 0.5rem;
    }

    /* ===== 卡片 ===== */
    .weather-card {
        background: #E3F2FD; border-radius: 10px; padding: 1rem; margin: 0.5rem 0;
        color: #1a1a1a;
        transition: transform .2s ease, box-shadow .2s ease;
    }
    .weather-card b { color: #1565C0; }
    .weather-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 6px 16px rgba(21, 101, 192, .18);
    }
    .budget-card {
        background: #FFF8E1; border-radius: 10px; padding: 1rem; margin: 0.5rem 0;
        color: #1a1a1a;
    }
    .result-card {
        background: #FFFFFF; border-left: 4px solid #4A90D9; border-radius: 8px;
        padding: 1rem 1.2rem; margin: 0.6rem 0; color: #1a1a1a;
        box-shadow: 0 2px 8px rgba(0, 0, 0, .06);
        transition: transform .2s ease, box-shadow .2s ease;
    }
    .result-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 16px rgba(0, 0, 0, .1);
    }
    .hotel-card {
        background: #FFFFFF; border-left: 4px solid #2E7D32; border-radius: 8px;
        padding: 1rem 1.2rem; margin: 0.6rem 0; color: #1a1a1a;
        box-shadow: 0 2px 8px rgba(0, 0, 0, .06);
        transition: transform .2s ease, box-shadow .2s ease;
    }
    .hotel-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 16px rgba(46, 125, 50, .15);
    }

    /* ===== 比价信号徽章 ===== */
    .signal-badge {
        display: inline-block; padding: 0.25rem 0.8rem; border-radius: 999px;
        font-weight: 600; font-size: 0.9rem;
    }
    .signal-green {
        background: #E8F5E9; color: #2E7D32; border: 1px solid #A5D6A7;
        animation: pulse 1.6s ease-in-out infinite;
    }
    .signal-yellow { background: #FFF8E1; color: #F9A825; border: 1px solid #FFE082; }
    .signal-red { background: #FFEBEE; color: #C62828; border: 1px solid #EF9A9A; }

    /* ===== 按钮过渡 ===== */
    .stButton > button, .stDownloadButton > button, .stLinkButton > a {
        transition: all .2s ease;
    }
    .stButton > button:hover, .stDownloadButton > button:hover, .stLinkButton > a:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(74, 144, 217, .35);
    }

    /* ===== 行程日历 ===== */
    .trip-cal {
        width: 100%; border-collapse: separate; border-spacing: 6px;
        table-layout: fixed; margin: .25rem 0;
    }
    .trip-cal th {
        font-size: .9rem; color: #78909C; font-weight: 600;
        text-align: center; padding-bottom: 2px;
    }
    .cal-cell {
        height: 108px; vertical-align: top; border-radius: 10px;
        background: #FAFAFA; border: 1px solid #ECEFF1; padding: 6px 4px;
        text-align: center; overflow: hidden;
    }
    .cal-cell.weekend { background: #FFF8F0; border-color: #FFE8CC; }
    .cal-cell.outside { background: transparent; border-color: transparent; }
    .cal-num { margin: 2px 0 4px; }
    .cal-daynum {
        display: inline-flex; align-items: center; justify-content: center;
        min-width: 30px; height: 30px; border-radius: 50%;
        font-weight: 600; color: #455A64; font-size: .95rem;
    }
    .cal-daynum.dim { color: #CFD8DC; font-weight: 500; }
    .cal-cell.trip { background: #E3F2FD; border-color: #90CAF9; }
    .cal-cell.trip:hover .cal-daynum { background: #B3E5FC; }
    .cal-cell.trip.selected { border: 2px solid #29B6F6; background: #E1F5FE; }
    .cal-cell.trip.selected .cal-daynum {
        background: #29B6F6; color: #fff;
        box-shadow: 0 2px 8px rgba(41, 182, 246, .45);
    }
    .cal-link { display: block; text-decoration: none; color: inherit; height: 100%; }
    .cal-badge {
        display: inline-block; background: #1565C0; color: #fff;
        border-radius: 999px; font-size: .7rem; padding: 1px 8px;
        white-space: nowrap;
    }
    .cal-cell.trip.selected .cal-badge { background: #0288D1; }
    .cal-desc {
        font-size: .76rem; color: #263238; margin-top: 4px; line-height: 1.3;
        display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;
        overflow: hidden;
    }
    .cal-meta {
        font-size: .7rem; color: #607D8B; margin-top: 3px;
        white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    }
    .cal-month-label { font-size: 1.2rem; font-weight: 700; color: #1565C0; }
</style>
""", unsafe_allow_html=True)


# ==================== 通用辅助 ====================

def _signal_badge(signal: str) -> str:
    """根据信号文本生成彩色徽章 HTML。"""
    if "🟢" in signal:
        cls = "signal-green"
    elif "🟡" in signal:
        cls = "signal-yellow"
    else:
        cls = "signal-red"
    return f'<span class="signal-badge {cls}">{signal}</span>'


def _exception_leaves(exc: BaseException) -> list[str]:
    """展开 ExceptionGroup / TaskGroup，收集最内层真实错误信息。"""
    messages: list[str] = []
    seen: set[str] = set()

    def walk(e: BaseException) -> None:
        subs = getattr(e, "exceptions", None)
        if subs:
            for sub in subs:
                walk(sub)
        else:
            text = str(e).strip()
            if text and text not in seen:
                seen.add(text)
                messages.append(text)

    walk(exc)
    if not messages:
        messages.append(str(exc).strip() or type(exc).__name__)
    return messages[:3]


def _render_advice(advice: dict, delay: int = 1):
    """渲染订房决策建议卡片。"""
    if not advice:
        return
    reasons = "".join(f"<li>{r}</li>" for r in advice.get("reasons", []))
    st.markdown(
        f'<div class="result-card fade-in d{min(delay, 6)}">'
        f'<div style="margin-bottom:.4rem">{_signal_badge(advice.get("signal", ""))}'
        f'<span style="color:#888;font-size:.85rem;margin-left:.5rem">'
        f'决策评分 {advice.get("score", 0)}</span></div>'
        f'<ul style="margin:.2rem 0 0;padding-left:1.2rem;color:#333">{reasons}</ul>'
        f'</div>',
        unsafe_allow_html=True,
    )


def _run_hotel_tool(tool_name: str, args: dict, status_label: str) -> dict | None:
    """调用酒店 MCP 工具，返回解析后的 JSON；失败时展示错误。"""
    from hotel_compare import call_hotel_tool

    with st.status(status_label, expanded=True) as status:
        try:
            st.write("🔌 启动酒店比价服务...")
            st.write("📡 正在查询多平台实时价格...")

            async def _call():
                return await call_hotel_tool(tool_name, args)

            raw = asyncio.run(_call())
            data = json.loads(raw)
            status.update(label="✅ 查询完成！", state="complete", expanded=False)
            return data
        except Exception as e:
            status.update(label="❌ 查询失败", state="error")
            st.error("酒店比价服务调用失败：" + "；".join(_exception_leaves(e)))
            return None


# ==================== 酒店比价结果渲染 ====================

def _render_search_result(data: dict):
    st.markdown("#### 🔍 酒店比价结果")
    c1, c2, c3 = st.columns(3)
    lowest_price = data.get("lowest_price")
    with c1:
        st.metric("💰 最低价格", f"¥{lowest_price:g}" if isinstance(lowest_price, (int, float)) else "—")
    with c2:
        st.metric("🏨 最低价酒店", data.get("lowest_hotel") or "—")
    with c3:
        st.metric("📋 结果数量", data.get("count", 0))

    _render_advice(data.get("advice"))

    if data.get("foreign_demo"):
        st.caption("ℹ️ 含 Agoda / Booking 演示价格（HOTELRATE_DEMO=true，合成数据仅供跑通流程）；真实比价需关闭演示模式并配置爬虫浏览器。")

    hotels = data.get("hotels", [])
    if hotels:
        st.markdown("**📋 酒店列表（按价格排序）**")
        rows = []
        for h in hotels:
            price = h.get("price")
            source = h.get("source", "")
            if h.get("demo"):
                source = f"{source}·演示"
            rows.append({
                "酒店": h.get("name", ""),
                "平台": source,
                "价格": f"¥{price:g}" if isinstance(price, (int, float)) and price > 0 else "—",
                "星级": h.get("star", ""),
                "评分": h.get("score", ""),
            })
        st.dataframe(rows, width="stretch", hide_index=True)

    if data.get("lowest_url"):
        st.link_button("🔗 前往最低价预订页", data["lowest_url"])


def _render_calendar_result(data: dict):
    st.markdown("#### 📅 低价日历")
    c1, c2, c3 = st.columns(3)
    min_price = data.get("min_price")
    avg_price = data.get("avg_price")
    with c1:
        st.metric("📆 最便宜入住日", data.get("cheapest_date") or "—")
    with c2:
        st.metric("💰 最低价格", f"¥{min_price:g}" if isinstance(min_price, (int, float)) else "—")
    with c3:
        st.metric("📊 期间均价", f"¥{avg_price:g}" if isinstance(avg_price, (int, float)) else "—")

    _render_advice(data.get("advice"))

    cal = data.get("calendar", [])
    if cal:
        rows = [{
            "入住日期": d.get("date", ""),
            "星期": d.get("weekday", ""),
            "最低价": f"¥{d['lowest_price']:g}" if isinstance(d.get("lowest_price"), (int, float)) else "—",
            "最低价酒店": d.get("cheapest_hotel") or "—",
            "标签": d.get("tag", ""),
        } for d in cal]
        st.dataframe(rows, width="stretch", hide_index=True)


def _render_advisor_result(data: dict):
    title = data.get("_ui_title") or f"🧭 订房决策 — {data.get('hotel_name', '')}"
    st.markdown(f"#### {title}")
    c1, c2 = st.columns(2)
    lowest_price = data.get("lowest_price")
    with c1:
        st.metric("💰 全网最低价", f"¥{lowest_price:g}" if isinstance(lowest_price, (int, float)) else "—")
    with c2:
        st.metric("🏆 最低价平台", data.get("lowest_platform") or "—")

    platforms = data.get("platforms", [])
    if platforms:
        if data.get("foreign_demo"):
            st.caption("ℹ️ Agoda / Booking 为演示价格（HOTELRATE_DEMO=true，合成数据仅供跑通流程）；真实比价需关闭演示模式并配置爬虫浏览器。")
        st.markdown("**🏷️ 各平台价格对比**")
        cols = st.columns(len(platforms))
        for i, p in enumerate(platforms):
            price = p.get("price")
            matched = bool(p.get("matched")) and isinstance(price, (int, float)) and price > 0
            is_lowest = (
                matched and p.get("source") == data.get("lowest_platform")
                and price == lowest_price
            )
            with cols[i]:
                border = "#2E7D32" if is_lowest else "#4A90D9"
                if matched:
                    price_html = f'<div style="font-size:1.5rem;font-weight:700;color:#C62828">¥{price:g}</div>'
                else:
                    price_html = '<div style="color:#999">未匹配到价格</div>'
                crown = '<div style="color:#2E7D32;font-size:.8rem">✅ 全网最低</div>' if is_lowest else ""
                demo_tag = '<span style="color:#b0a05a;font-size:.75rem">· 演示数据</span>' if p.get("demo") else ""
                detail_bits = []
                room = (p.get("room_name") or "").strip()
                meal = (p.get("meal_plan") or "").strip()
                if room:
                    detail_bits.append(room)
                if meal and meal != room:
                    detail_bits.append(meal)
                pn = p.get("per_night")
                if isinstance(pn, (int, float)) and pn > 0:
                    detail_bits.append(f"每晚 ¥{pn:g}")
                detail_html = (
                    f'<div style="color:#666;font-size:.8rem;margin-top:2px">{" · ".join(detail_bits)}</div>'
                    if detail_bits else ""
                )
                st.markdown(
                    f'<div class="result-card fade-in d{min(i + 1, 6)}" '
                    f'style="border-left-color:{border};text-align:center">'
                    f'<b>{p.get("source", "?")}</b>{demo_tag}{price_html}{detail_html}{crown}</div>',
                    unsafe_allow_html=True,
                )
                if p.get("url"):
                    st.link_button(f"🔗 {p.get('source')}预订", p["url"], width="stretch")

    _render_advice(data.get("advice"))


# ==================== 酒店比价模式 ====================

def hotel_mode():
    with st.sidebar:
        st.markdown("### 🏨 比价参数")
        h_city = st.text_input("📍 城市", placeholder="例如: 上海、北京...")
        col1, col2 = st.columns(2)
        with col1:
            h_check_in = st.date_input("📅 入住日期", value=date.today())
        with col2:
            h_check_out = st.date_input("📅 离店日期", value=date.today())
        h_keyword = st.text_input("🔎 关键词/地标", placeholder="例如: 外滩、迪士尼（选填）")
        h_hotel = st.text_input("🏨 酒店名称", placeholder="订房决策必填，如: 上海外滩华尔道夫")
        h_days = st.slider("🗓️ 低价日历扫描天数", min_value=5, max_value=30, value=14)

        st.markdown("---")
        btn_search = st.button("🔍 比价搜索", width="stretch")
        btn_calendar = st.button("📅 低价日历", width="stretch")
        btn_advisor = st.button("🧭 订房决策", type="primary", width="stretch")
        btn_abt = st.button("🔀 Agoda·Booking·途牛 三方比价", width="stretch")

    # ---- 触发查询 ----
    ci = h_check_in.strftime("%Y-%m-%d")
    co = h_check_out.strftime("%Y-%m-%d")

    if btn_search:
        if not h_city.strip():
            st.error("请输入城市")
        elif h_check_out <= h_check_in:
            st.error("离店日期必须晚于入住日期")
        else:
            result = _run_hotel_tool("search", {
                "city": h_city.strip(), "check_in": ci, "check_out": co,
                "keyword": h_keyword.strip(),
            }, "🔍 正在搜索多平台酒店价格...")
            if result is not None:
                st.session_state.hotel_result = {"tool": "search", "data": result}

    if btn_calendar:
        if not h_city.strip():
            st.error("请输入城市")
        else:
            nights = max((h_check_out - h_check_in).days, 1)
            result = _run_hotel_tool("calendar", {
                "city": h_city.strip(), "keyword": h_keyword.strip(),
                "start_date": ci, "nights": nights, "days": h_days,
            }, "📅 正在扫描低价日历...")
            if result is not None:
                st.session_state.hotel_result = {"tool": "calendar", "data": result}

    if btn_advisor:
        if not h_city.strip():
            st.error("请输入城市")
        elif not h_hotel.strip():
            st.error("订房决策需要输入酒店名称")
        elif h_check_out <= h_check_in:
            st.error("离店日期必须晚于入住日期")
        else:
            result = _run_hotel_tool("advisor", {
                "hotel": h_hotel.strip(), "city": h_city.strip(),
                "check_in": ci, "check_out": co,
            }, "🧭 正在进行多平台订房决策分析...")
            if result is not None:
                st.session_state.hotel_result = {"tool": "advisor", "data": result}

    if btn_abt:
        if not h_city.strip():
            st.error("请输入城市")
        elif not h_hotel.strip():
            st.error("三方比价需要输入酒店名称")
        elif h_check_out <= h_check_in:
            st.error("离店日期必须晚于入住日期")
        else:
            result = _run_hotel_tool("compare_abt", {
                "hotel": h_hotel.strip(), "city": h_city.strip(),
                "check_in": ci, "check_out": co,
            }, "🔀 正在 Agoda·Booking·途牛 三方实时比价...")
            if result is not None:
                result["_ui_title"] = f"🔀 Agoda · Booking · 途牛 三方房价对比 — {h_hotel.strip()}"
                st.session_state.hotel_result = {"tool": "abt", "data": result}

    # ---- 结果展示 ----
    hotel_result = st.session_state.get("hotel_result")
    if hotel_result is None:
        st.info("👈 在左侧填写比价参数，然后选择查询方式")
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            st.markdown("##### 🔍 多平台实时比价")
            st.caption("飞猪/途牛/RG/同程 + Agoda/Booking（可选）多平台比价；另有 Agoda·Booking·途牛 三方比价入口")
        with col_b:
            st.markdown("##### 📅 低价日历")
            st.caption("一键扫描 7-30 天价格洼地，找到最便宜的入住日期")
        with col_c:
            st.markdown("##### 🧭 订房决策")
            st.caption("五维度综合判断，输出 🟢订 / 🟡等 / 🔴观望 信号")
        return

    tool, data = hotel_result["tool"], hotel_result["data"]
    if tool == "search":
        _render_search_result(data)
    elif tool == "calendar":
        _render_calendar_result(data)
    else:
        _render_advisor_result(data)


# ==================== 旅行规划模式 ====================

# ---- 初始化 ----
@st.cache_resource
def get_planner():
    from config import CONFIG
    from agents.planner import TripPlanner
    llm = CONFIG.create_llm()
    return TripPlanner(llm)


# ---- 辅助: 构建 prompt ----
def build_prompt(
    city: str,
    start_date: date,
    end_date: date,
    transport: list[str],
    hotel_type: str,
    preferences: list[str],
    extra: str,
) -> str:
    days = (end_date - start_date).days
    parts = [
        f"{city}{days}日游",
        f"{start_date.strftime('%Y年%m月%d日')}-{end_date.strftime('%Y年%m月%d日')}",
    ]
    if preferences:
        parts.append(f"喜欢{'、'.join(preferences)}")
    if hotel_type:
        parts.append(f"住宿偏好{hotel_type}")
    if transport:
        parts.append(f"交通方式偏好{'、'.join(transport)}")
    if extra.strip():
        parts.append(f"额外要求: {extra.strip()}")
    parts.append("中等预算")
    return "，".join(parts)


# 工具名 → 流式状态标签
_STREAM_LABELS = {
    "maps_weather":                     "🌤️ 查询天气中...",
    "maps_text_search":                 "🔍 搜索景点/酒店中...",
    "maps_around_search":               "📍 周边搜索中...",
    "maps_search_detail":               "📄 获取POI详情...",
    "maps_geo":                         "📍 地址转经纬度...",
    "maps_direction_walking":           "🚶 规划步行路线...",
    "maps_direction_walking_by_address": "🚶 规划步行路线...",
    "maps_direction_driving":           "🚗 规划驾车路线...",
    "maps_direction_driving_by_address": "🚗 规划驾车路线...",
    "maps_direction_transit_integrated": "🚌 规划公交路线...",
    "maps_direction_transit_integrated_by_address": "🚌 规划公交路线...",
    "maps_direction_bicycling":         "🚲 规划骑行路线...",
    "maps_bicycling":                   "🚲 规划骑行路线...",
    "search":   "🏨 酒店多平台比价中...",
    "calendar": "📅 扫描低价日历中...",
    "advisor":  "🧭 订房决策分析中...",
}

_STATUS_EMOJIS = ["🌤️", "🔍", "📍", "📄", "🚶", "🚗", "🚌", "🚲", "🏨", "📅", "🧭"]


# ==================== 行程日历 ====================

def _trip_calendar_data(year: int, month: int, day_by_date: dict, selected: int) -> dict:
    """构建月历数据：行程日带 Day 序号与概述，供可点击日历组件渲染。"""
    today = date.today()
    weeks = []
    for week in calendar.Calendar(firstweekday=0).monthdatescalendar(year, month):
        cells = []
        for d in week:
            if d.month != month:
                cells.append({"out": True})
                continue
            entry = day_by_date.get(d.isoformat())
            cell = {
                "day": d.day,
                "weekend": d.weekday() >= 5,
                "today": d == today,
            }
            if entry is not None:
                idx, day = entry
                cell.update({
                    "idx": idx,
                    "selected": idx == selected,
                    "desc": day.get("description") or "",
                    "n": len(day.get("attractions", [])),
                })
            cells.append(cell)
        weeks.append(cells)
    return {"weeks": weeks}


def _render_day_details(day: dict, idx: int, plan_city: str):
    """渲染选中日的详细行程（住宿 / 景点 / 餐饮）。"""
    from render import attraction_photo, attraction_map_image

    d = day.get("date", "")[-5:]
    st.markdown(
        f'<div class="day-header fade-in">📅 {d}  Day {idx} · {day.get("description", "")}</div>',
        unsafe_allow_html=True,
    )

    # 住宿
    hotel = day.get("hotel", {})
    if hotel.get("name"):
        st.markdown(
            f"🏨 **{hotel['name']}**  ★{hotel.get('rating', '-')}  "
            f"¥{hotel.get('estimated_cost', 0)}/晚  |  {hotel.get('address', '')}"
        )
    st.caption(f"🚌 {day.get('transportation', '')}")

    # 景点
    attractions = day.get("attractions", [])
    if attractions:
        st.markdown("**🏛️ 景点**")
        for a in attractions:
            ticket = a.get("ticket_price", 0)
            ts = "🆓 免费" if ticket == 0 else f"🎫 ¥{ticket}"
            with st.container(border=True):
                name = a.get("name", "景点")
                img_url = a.get("image_url") or ""
                if not img_url:
                    img_url = attraction_photo(name, plan_city) or ""
                is_map = False
                if not img_url:
                    img_url = attraction_map_image(a.get("location") or {}) or ""
                    is_map = True
                if img_url:
                    if is_map:
                        st.markdown(
                            f"""
                            <div style="position:relative;border-radius:8px;overflow:hidden;margin-bottom:.5rem">
                              <img src="{img_url}" style="width:100%;display:block;border-radius:8px" />
                              <div style="position:absolute;top:50%;left:50%;transform:translate(-50%,-100%)">
                                <div style="width:14px;height:14px;background:#FF4444;border:3px solid #fff;border-radius:50%;box-shadow:0 2px 6px rgba(0,0,0,.4);animation:pulse 2s infinite"></div>
                                <div style="width:2px;height:14px;background:#FF4444;margin:-1px auto 0"></div>
                              </div>
                              <div style="position:absolute;top:12px;left:12px;background:rgba(255,255,255,.95);color:#c0392b;font-weight:600;padding:3px 10px;border-radius:14px;font-size:.85rem;box-shadow:0 1px 4px rgba(0,0,0,.15)">📍 {name}</div>
                            </div>
                            <style>@keyframes pulse{{0%,100%{{opacity:1}}50%{{opacity:.4}}}}</style>
                            """,
                            unsafe_allow_html=True,
                        )
                    else:
                        st.image(img_url, use_container_width=True)
                st.markdown(
                    f"**{name}**  |  {a.get('category', '')}  |  "
                    f"⏱️ {a.get('visit_duration', 0)}分钟  |  {ts}"
                )
                if a.get("address"):
                    st.caption(f"📍 {a['address']}")
                a_desc = a.get("description")
                if a_desc:
                    st.markdown(f"<div style='color:#555;font-size:.9rem;margin-top:.3rem'>{a_desc}</div>",
                                unsafe_allow_html=True)

    # 餐饮
    meals = day.get("meals", [])
    if meals:
        st.markdown("**🍽️ 餐饮推荐**")
        mt = {"breakfast": "🌅 早餐", "lunch": "☀️ 午餐", "dinner": "🌙 晚餐"}
        meal_cols = st.columns(len(meals))
        for j, m in enumerate(meals):
            label = mt.get(m.get("type", ""), "餐")
            with meal_cols[j]:
                st.markdown(
                    f"*{label}*\n\n**{m.get('name', '?')}**  \n"
                    f"¥{m.get('estimated_cost', 0)}"
                )


def travel_mode():
    # ============ 侧边栏: 参数输入 ============
    with st.sidebar:
        st.markdown("### 📋 旅行参数")

        city = st.text_input("📍 目的地城市", placeholder="例如: 杭州、成都、三亚...")

        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("📅 开始日期", value=date.today())
        with col2:
            end_date = st.date_input("📅 结束日期", value=date.today())

        if start_date and end_date and end_date >= start_date:
            trip_days = (end_date - start_date).days
            st.info(f"📌 共计 **{trip_days}** 天")
        elif end_date < start_date:
            st.error("结束日期不能早于开始日期")

        st.markdown("---")
        st.markdown("### 🚗 交通方式")
        transport_options = ["公共交通", "自驾", "打车/网约车", "骑行", "步行"]
        transport_selected = []
        for opt in transport_options:
            if st.checkbox(opt, key=f"trans_{opt}"):
                transport_selected.append(opt)

        st.markdown("---")
        st.markdown("### 🏨 住宿偏好")
        hotel_type = st.selectbox(
            "住宿类型",
            ["不限", "经济型酒店", "中档型酒店", "豪华型酒店", "民宿/客栈", "青年旅舍"],
            index=2,
            label_visibility="collapsed",
        )
        if hotel_type == "不限":
            hotel_type = ""

        st.markdown("---")
        st.markdown("### 🎯 旅行偏好")
        pref_options = ["自然风光", "历史文化", "美食探店", "休闲度假", "艺术展览", "购物逛街", "亲子乐园"]
        pref_selected = []
        for opt in pref_options:
            if st.checkbox(opt, key=f"pref_{opt}"):
                pref_selected.append(opt)

        st.markdown("---")
        st.markdown("### 💬 额外要求")
        extra_requirements = st.text_area(
            "补充说明",
            placeholder="例如: 带老人出行需要轻松行程、想在市中心活动...",
            label_visibility="collapsed",
        )

        st.markdown("---")
        submit_btn = st.button("🚀 开始规划", type="primary", width="stretch")

    # ============ 主区域: 结果展示 ============
    if "plan_data" not in st.session_state:
        st.session_state.plan_data = None
    if "plan_raw" not in st.session_state:
        st.session_state.plan_raw = ""

    # 未开始时的引导页
    if not submit_btn and st.session_state.plan_data is None:
        st.info("👈 在左侧填写旅行参数，然后点击 **开始规划** 按钮")
        col_a, col_b, col_c, col_d = st.columns(4)
        with col_a:
            st.markdown("##### 🌤️ 实时天气查询")
            st.caption("接入高德地图 MCP，获取目的地准确天气预报")
        with col_b:
            st.markdown("##### 🏛️ 智能景点推荐")
            st.caption("根据你的偏好，AI 精准匹配最适合的景点和路线")
        with col_c:
            st.markdown("##### 🏨 酒店多平台比价")
            st.caption("飞猪/途牛/RG/同程 + Agoda/Booking（可选）实时比价，给出订房时机建议")
        with col_d:
            st.markdown("##### 📊 预算自动汇总")
            st.caption("景点门票、餐饮、住宿、交通费用一目了然")

    # 点击按钮后执行
    if submit_btn:
        if not city.strip():
            st.error("请输入目的地城市")
        elif end_date < start_date:
            st.error("结束日期不能早于开始日期")
        else:
            with st.status("🤖 AI 正在为您规划旅行方案...", expanded=True) as status:
                try:
                    planner = get_planner()
                    prompt = build_prompt(
                        city, start_date, end_date,
                        transport_selected, hotel_type, pref_selected, extra_requirements,
                    )
                    from render import parse_plan

                    async def _collect():
                        results = []
                        async for token in planner.stream(prompt):
                            results.append(token)
                        return results

                    tokens = asyncio.run(_collect())

                    # 分离状态行和内容
                    full_text = ""
                    status_lines = []
                    for token in tokens:
                        full_text += token
                        stripped = token.strip()
                        if any(stripped.startswith(emoji) for emoji in _STATUS_EMOJIS):
                            status_lines.append(stripped)

                    # 展示规划过程
                    for line in status_lines:
                        st.write(line)

                    # 解析并存储
                    plan = parse_plan(full_text)
                    if plan is None:
                        snippet = full_text.strip()
                        if len(snippet) > 300:
                            snippet = snippet[:300] + "…"
                        raise RuntimeError(
                            "模型未返回可解析的旅行计划 JSON"
                            + (f"，输出片段：{snippet}" if snippet else "（输出为空）")
                        )
                    st.session_state.plan_data = plan
                    st.session_state.plan_raw = full_text
                    st.session_state.status_lines = status_lines
                    st.session_state.selected_day = 1
                    st.session_state.pop("trip_calendar", None)

                    status.update(label="✅ 旅行计划生成完成！", state="complete", expanded=False)
                except Exception as e:
                    status.update(label="❌ 旅行规划失败", state="error", expanded=True)
                    st.error("生成旅行计划时出错：" + "；".join(_exception_leaves(e)))
                    st.info(
                        "可能原因：\n"
                        "1. 地图服务已切换为高德开放平台官方 MCP，请在 `travel-agent/.env` 配置 `AMAP_MAPS_API_KEY`（Web 服务类型 Key）；\n"
                        "2. `DASHSCOPE_API_KEY` 缺失、过期或无效（LLM 生成 401/InvalidApiKey）——请同时确认它已配置；\n"
                        "3. 高德 MCP 端点 `mcp.amap.com` 网络不可达；\n"
                        "4. 本地酒店比价服务未初始化（报错中如含 `.hotel-mcp`，请执行 `python -m venv .hotel-mcp` 并 `pip install fastmcp`）。"
                    )
                else:
                    st.rerun()

    # ============ 结果展示 ============
    plan = st.session_state.plan_data
    if plan is None:
        return

    # 显示状态
    if "status_lines" in st.session_state and st.session_state.status_lines:
        with st.expander("🔍 规划过程", expanded=False):
            st.markdown("\n".join(st.session_state.status_lines))

    # ---- 标题 ----
    plan_city = plan.get("city", "")
    sd = plan.get("start_date", "")
    ed = plan.get("end_date", "")
    st.markdown(
        f'<div class="plan-title fade-in">🌴 {plan_city}旅行计划 ｜ {sd} ~ {ed}</div>',
        unsafe_allow_html=True,
    )

    # ---- 天气卡片 ----
    weather = plan.get("weather_info", [])
    if weather:
        st.markdown("##### 🌤️ 天气预报")
        if plan_city:
            msn_city = urllib.parse.quote(plan_city)
            st.markdown(
                f"<a href='https://www.msn.cn/zh-cn/weather/forecast/in-{msn_city}' "
                "target='_blank' rel='noopener' "
                "style='display:inline-block;margin-bottom:.5rem;color:#1565C0;"
                "text-decoration:none;border:1px solid #90CAF9;border-radius:999px;"
                "padding:.15rem .7rem;font-size:.85rem'>"
                "🌐 点击查看 msn.cn 天气 ›</a>",
                unsafe_allow_html=True,
            )
        cols = st.columns(len(weather))
        weather_icon_map = {
            "晴": "☀️", "多云": "⛅", "阴": "☁️",
            "小雨": "🌧️", "中雨": "🌧️", "大雨": "⛈️", "暴雨": "⛈️",
        }

        for i, w in enumerate(weather):
            d = w.get("date", "")[-5:]
            di = weather_icon_map.get(w.get("day_weather", ""), "🌡️")
            with cols[i]:
                st.markdown(
                    f"""<div class="weather-card fade-in d{min(i + 1, 6)}" style="text-align:center">
                    <b>{d}</b><br>
                    {di} {w.get('day_weather', '?')}<br>
                    🌡️ {w.get('day_temp', '?')}°C / {w.get('night_temp', '?')}°C<br>
                    💨 {w.get('wind_direction', '')}{w.get('wind_power', '')}
                    </div>""",
                    unsafe_allow_html=True,
                )

    # ---- 每日行程（月历视图） ----
    st.markdown("---")
    st.markdown("##### 📅 每日行程")

    days = plan.get("days", [])
    if days:
        day_by_date = {}
        idx_to_day = {}
        for i, day in enumerate(days):
            idx_to_day[i + 1] = day
            dstr = day.get("date", "")
            if dstr:
                day_by_date[dstr] = (i + 1, day)

        trip_dates = sorted(day_by_date)
        try:
            cal_start = date.fromisoformat(trip_dates[0])
        except ValueError:
            cal_start = date.today()

        selected = st.session_state.get("selected_day", 1)
        picked = st.session_state.get("trip_calendar")
        if picked is not None and picked in idx_to_day:
            selected = picked
            st.session_state.selected_day = picked
        if selected not in idx_to_day:
            selected = 1

        st.markdown(
            f'<div class="cal-month-label fade-in">{cal_start.year}年{cal_start.month}月</div>',
            unsafe_allow_html=True,
        )
        trip_calendar(
            data=_trip_calendar_data(cal_start.year, cal_start.month, day_by_date, selected),
            key="trip_calendar",
        )
        st.caption("💡 点击日历中的行程日期，可在下方查看当天详细行程")

        _render_day_details(idx_to_day[selected], selected, plan_city)

    # ---- 预算 ----
    budget = plan.get("budget", {})
    if budget:
        st.markdown("---")
        st.markdown("##### 💰 预算汇总")
        bc1, bc2, bc3, bc4, bc5 = st.columns(5)
        with bc1:
            st.metric("景点门票", f"¥{budget.get('total_attractions', 0):,}")
        with bc2:
            st.metric("酒店住宿", f"¥{budget.get('total_hotels', 0):,}")
        with bc3:
            st.metric("餐饮美食", f"¥{budget.get('total_meals', 0):,}")
        with bc4:
            st.metric("交通出行", f"¥{budget.get('total_transportation', 0):,}")
        with bc5:
            st.metric("📊 总计", f"¥{budget.get('total', 0):,}",
                      delta=None, delta_color="off")

    # ---- 酒店比价 ----
    comparison = plan.get("hotel_comparison", [])
    if comparison:
        st.markdown("---")
        st.markdown("##### 🏨 酒店比价")
        for i, h in enumerate(comparison):
            lowest = h.get("lowest_price")
            price_html = f"¥{lowest}" if isinstance(lowest, (int, float)) else "—"
            st.markdown(
                f'<div class="hotel-card fade-in d{min(i + 1, 6)}">'
                f'<div style="margin-bottom:.3rem"><b>{h.get("name", "")}</b> '
                f'{_signal_badge(h.get("signal", ""))}</div>'
                f'💰 最低 <b style="color:#C62828">{price_html}</b>'
                f'（{h.get("best_platform", "—")}）'
                f'<div style="color:#555;margin-top:.2rem">{h.get("advice", "")}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    # ---- 建议 ----
    suggestions = plan.get("overall_suggestions", "")
    if suggestions:
        st.markdown("---")
        st.markdown("##### 💡 旅行建议")
        for tip in suggestions.replace("；", ";").split(";"):
            tip = tip.strip()
            if tip:
                st.markdown(f"- {tip}")

    # ============ 导出 ============
    st.markdown("---")
    st.markdown("##### 📥 导出计划")

    from render import build_pdf
    pdf_bytes = build_pdf(plan)
    if pdf_bytes:
        st.download_button(
            label="📄 下载 PDF 旅行计划",
            data=pdf_bytes,
            file_name=f"{plan.get('city', '旅行')}_旅行计划.pdf",
            mime="application/pdf",
            width="stretch",
        )
    else:
        st.warning("PDF 生成失败，请确认已安装 reportlab 库")


# ==================== 主入口 ====================

st.markdown('<div class="main-header">🧳 智能旅行 & 酒店比价助手</div>', unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### ✨ 功能模式")
    mode = st.radio(
        "功能模式",
        ["🧳 智能旅行规划", "🏨 酒店比价"],
        label_visibility="collapsed",
    )
    st.markdown("---")

if mode == "🧳 智能旅行规划":
    travel_mode()
else:
    hotel_mode()
