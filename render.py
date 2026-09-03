"""渲染工具 —— JSON 解析、CLI 格式化、Streamlit 组件、PDF 导出。"""
import io
import json
import os
import platform
import urllib.parse
import urllib.request

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

_AMAP_KEY = os.getenv("AMAP_MAPS_API_KEY") or os.getenv("AMAP_API_KEY", "")


# ==================== 景点图片 ====================

def attraction_photo(name: str, city: str = "") -> str | None:
    """根据景点名从高德 POI 接口获取真实风景照片 URL。"""
    if not name or not _AMAP_KEY:
        return None
    try:
        params = urllib.parse.urlencode({
            "keywords": name,
            "city": city or "",
            "key": _AMAP_KEY,
            "output": "json",
            "offset": 1,
        })
        req = urllib.request.Request(
            "https://restapi.amap.com/v3/place/text?" + params,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read().decode())
        if data.get("status") != "1":
            return None
        for poi in data.get("pois", []):
            photos = poi.get("photos") or []
            if photos:
                url = photos[0].get("url", "")
                if url:
                    return url
    except Exception:
        return None
    return None


def attraction_map_image(location: dict, width: int = 400, height: int = 260) -> str | None:
    """根据景点经纬度生成高德静态地图底图 URL。"""
    if not location:
        return None
    lng = location.get("longitude") or location.get("lng")
    lat = location.get("latitude") or location.get("lat")
    if not lng or not lat:
        return None
    if not _AMAP_KEY:
        return None
    params = {
        "location": f"{lng},{lat}",
        "zoom": 15,
        "size": f"{width}*{height}",
        "scale": 2,
        "key": _AMAP_KEY,
    }
    return f"https://restapi.amap.com/v3/staticmap?{urllib.parse.urlencode(params)}"


# ==================== JSON 解析 ====================

def parse_plan(text: str) -> dict | None:
    """从混合文本中提取并解析旅行计划 JSON。"""
    if not text or not text.strip():
        return None
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        cleaned = cleaned.removeprefix("json").strip()
    try:
        start = cleaned.find("{")
        end = cleaned.rfind("}") + 1
        if start == -1 or end == 0:
            return None
        return json.loads(cleaned[start:end])
    except (json.JSONDecodeError, KeyError):
        pass
    try:
        decoder = json.JSONDecoder()
        pos = 0
        while pos < len(cleaned):
            while pos < len(cleaned) and cleaned[pos] != "{":
                pos += 1
            if pos >= len(cleaned):
                break
            try:
                obj, _ = decoder.raw_decode(cleaned[pos:])
                if isinstance(obj, dict):
                    return obj
            except json.JSONDecodeError:
                pos += 1
    except Exception:
        return None
    return None


# ==================== CLI 格式化 ====================

def _weather_icon(weather: str) -> str:
    mapping = {
        "晴": "☀️", "多云": "⛅", "阴": "☁️",
        "小雨": "🌧️", "中雨": "🌧️", "大雨": "⛈️", "暴雨": "⛈️",
        "雪": "❄️", "雾": "🌫️", "霾": "🌫️",
    }
    for key, icon in mapping.items():
        if key in weather:
            return icon
    return "🌡️"


def format_plan_cli(json_text: str) -> str | None:
    """将 Planner JSON 渲染为 CLI 可读的中文旅行计划。"""
    data = parse_plan(json_text)
    if data is None:
        return None

    lines = []
    city = data.get("city", "未知")
    start_date = data.get("start_date", "")
    end_date = data.get("end_date", "")

    lines.append("")
    lines.append("╔" + "═" * 58 + "╗")
    title = f"  {city} {start_date} ~ {end_date} 旅行计划"
    lines.append(f"║{title:<56}║")
    lines.append("╚" + "═" * 58 + "╝")

    weather_info = data.get("weather_info", [])
    if weather_info:
        lines.append("")
        lines.append("  天气预报")
        for w in weather_info:
            d = w.get("date", "")[-5:]
            di = _weather_icon(w.get("day_weather", ""))
            ni = _weather_icon(w.get("night_weather", ""))
            lines.append(
                f"     {d}  {di} {w.get('day_weather', '?')} -> "
                f"{ni} {w.get('night_weather', '?')}  "
                f"{w.get('day_temp', '?')}C / {w.get('night_temp', '?')}C  "
                f"{w.get('wind_direction', '')}{w.get('wind_power', '')}"
            )

    for day in data.get("days", []):
        idx = day.get("day_index", 0) + 1
        d = day.get("date", "")[-5:]
        desc = day.get("description", "")
        lines.append("")
        lines.append("━" * 60)
        lines.append(f"  Day {idx}  {d}  {desc}")
        lines.append("━" * 60)

        hotel = day.get("hotel", {})
        if hotel.get("name"):
            lines.append(
                f"     住宿: {hotel['name']}  *{hotel.get('rating', '')}  "
                f"Y{hotel.get('estimated_cost', 0)}/晚  |  {hotel.get('address', '')}"
            )
        lines.append(f"     交通: {day.get('transportation', '')}")

        attractions = day.get("attractions", [])
        if attractions:
            lines.append(f"     景点 ({len(attractions)}个):")
            for a in attractions:
                ticket = a.get("ticket_price", 0)
                ts = "免费" if ticket == 0 else f"Y{ticket}"
                lines.append(f"       - {a.get('name', '?')}")
                lines.append(
                    f"         {a.get('address', '')}  |  {a.get('category', '')}  |  "
                    f"游玩约{a.get('visit_duration', 0)}分钟  |  {ts}"
                )

        meals = day.get("meals", [])
        if meals:
            lines.append("     餐饮:")
            for m in meals:
                mt = {"breakfast": "早", "lunch": "午", "dinner": "晚"}
                label = mt.get(m.get("type", ""), "餐")
                lines.append(f"       {label} {m.get('name', '?')}  Y{m.get('estimated_cost', 0)}")

    budget = data.get("budget", {})
    if budget:
        lines.append("")
        lines.append("━" * 60)
        lines.append("  预算汇总")
        lines.append(
            f"     景点: Y{budget.get('total_attractions', 0):>6}  |  "
            f"酒店: Y{budget.get('total_hotels', 0):>6}  |  "
            f"餐饮: Y{budget.get('total_meals', 0):>6}  |  "
            f"交通: Y{budget.get('total_transportation', 0):>6}"
        )
        lines.append(f"     总计: Y{budget.get('total', 0):,}")

    suggestions = data.get("overall_suggestions", "")
    if suggestions:
        lines.append("")
        lines.append("  旅行建议")
        for tip in suggestions.replace("；", ";").split(";"):
            tip = tip.strip()
            if tip:
                lines.append(f"     - {tip}")

    lines.append("")
    return "\n".join(lines)


# ==================== PDF 生成 ====================

def _find_cn_font() -> str | None:
    """在常见系统路径中查找可用的中文 TTF 字体文件。"""
    system = platform.system()
    candidates = []
    if system == "Windows":
        windir = os.environ.get("WINDIR", r"C:\Windows")
        font_dir = os.path.join(windir, "Fonts")
        candidates = [
            os.path.join(font_dir, "simhei.ttf"),
            os.path.join(font_dir, "simfang.ttf"),
            os.path.join(font_dir, "simsun.ttc"),
            os.path.join(font_dir, "msyh.ttc"),
            os.path.join(font_dir, "Deng.ttf"),
        ]
    elif system == "Darwin":
        candidates = [
            "/System/Library/Fonts/PingFang.ttc",
            "/System/Library/Fonts/STHeiti Medium.ttc",
        ]
    else:
        candidates = [
            "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
            "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        ]
    for p in candidates:
        if os.path.isfile(p):
            return p
    return None


def _register_cn_font() -> str | None:
    """注册中文字体并返回字体名。"""
    try:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
    except ImportError:
        return None
    font_path = _find_cn_font()
    if not font_path:
        return None
    name = "CN"
    try:
        pdfmetrics.registerFont(TTFont(name, font_path))
        pdfmetrics.registerFont(TTFont(name + "Bold", font_path))
        return name
    except Exception:
        try:
            pdfmetrics.registerFont(TTFont(name, font_path, subfontIndex=0))
            pdfmetrics.registerFont(TTFont(name + "Bold", font_path, subfontIndex=0))
            return name
        except Exception:
            return None


def build_pdf(plan: dict) -> bytes | None:
    """将旅行计划 dict 渲染为美观的 PDF，返回 bytes；失败返回 None。"""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import cm
        from reportlab.lib import colors
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Table, TableStyle,
            Spacer, PageBreak,
        )
        from reportlab.lib.enums import TA_CENTER
    except ImportError:
        return None

    cn_font = _register_cn_font()
    if not cn_font:
        return None

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="CoverTitle", fontName="CNBold", fontSize=28, leading=38,
        alignment=TA_CENTER, textColor=colors.HexColor("#1a5276"), spaceAfter=10,
    ))
    styles.add(ParagraphStyle(
        name="CoverSub", fontName="CN", fontSize=14, leading=20,
        alignment=TA_CENTER, textColor=colors.HexColor("#7d3c98"), spaceAfter=20,
    ))
    styles.add(ParagraphStyle(
        name="CNH1", fontName="CNBold", fontSize=17, leading=25,
        spaceBefore=18, spaceAfter=10, textColor=colors.HexColor("#c0392b"),
    ))
    styles.add(ParagraphStyle(
        name="CNH2", fontName="CNBold", fontSize=14, leading=20,
        spaceBefore=14, spaceAfter=8, textColor=colors.HexColor("#2874a6"),
    ))
    styles.add(ParagraphStyle(
        name="CNBody", fontName="CN", fontSize=10, leading=16, spaceAfter=4,
    ))
    styles.add(ParagraphStyle(
        name="CNMeta", fontName="CN", fontSize=9, leading=14,
        textColor=colors.grey, spaceAfter=3,
    ))
    styles.add(ParagraphStyle(
        name="CNDesc", fontName="CN", fontSize=9, leading=14,
        textColor=colors.HexColor("#566573"), spaceAfter=6,
    ))

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=2 * cm, bottomMargin=2 * cm,
        title=f"{plan.get('city', '')}旅行计划",
        author="AI Travel Planner",
    )

    def _table(rows: list, col_widths: list | None = None, header=True) -> Table:
        t = Table(rows, colWidths=col_widths, hAlign="LEFT")
        style = [
            ("FONT", (0, 0), (-1, -1), "CN", 10),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d5dbdb")),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ]
        if header and len(rows) > 1:
            style += [
                ("FONT", (0, 0), (-1, 0), "CNBold", 10),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2874a6")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1),
                 [colors.white, colors.HexColor("#ebf5fb")]),
            ]
        t.setStyle(TableStyle(style))
        return t

    story: list = []

    # === 封面 ===
    city = plan.get("city", "")
    sd = plan.get("start_date", "")
    ed = plan.get("end_date", "")
    story.append(Spacer(1, 2 * cm))
    story.append(Paragraph(f"  {city} 旅行计划", styles["CoverTitle"]))
    story.append(Paragraph(f"{sd}  ~  {ed}", styles["CoverSub"]))
    story.append(Spacer(1, 0.5 * cm))
    story.append(Paragraph("-- AI Travel Planner --", styles["CNMeta"]))
    story.append(PageBreak())

    # === 天气 ===
    weather = plan.get("weather_info", [])
    if weather:
        story.append(Paragraph("  天气预报", styles["CNH1"]))
        rows = [["日期", "白天", "夜间", "温度", "风向/风力"]]
        for w in weather:
            rows.append([
                str(w.get("date", ""))[-5:],
                str(w.get("day_weather", "")),
                str(w.get("night_weather", "")),
                f"{w.get('day_temp', '?')} / {w.get('night_temp', '?')}",
                f"{w.get('wind_direction', '')} {w.get('wind_power', '')}",
            ])
        story.append(_table(rows, col_widths=[2.0*cm, 2.6*cm, 2.6*cm, 2.6*cm, 3.2*cm]))

    # === 每日行程 ===
    for day in plan.get("days", []):
        idx = day.get("day_index", 0) + 1
        d = str(day.get("date", ""))[-5:]
        story.append(Paragraph(
            f"  Day {idx} -- {d}  {day.get('description', '')}", styles["CNH1"]
        ))

        hotel = day.get("hotel", {})
        if hotel.get("name"):
            story.append(Paragraph(
                f"<b>住宿:</b> {hotel['name']}  "
                f"*{hotel.get('rating', '')}  "
                f"Y{hotel.get('estimated_cost', 0)}/night",
                styles["CNBody"],
            ))
            if hotel.get("address"):
                story.append(Paragraph(f"  {hotel['address']}", styles["CNMeta"]))
        story.append(Paragraph(f"<b>交通:</b> {day.get('transportation', '')}", styles["CNBody"]))

        attractions = day.get("attractions", [])
        if attractions:
            story.append(Paragraph("  景点", styles["CNH2"]))
            for a in attractions:
                ticket = a.get("ticket_price", 0)
                ts = "Free" if ticket == 0 else f"Y{ticket}"
                story.append(Paragraph(
                    f"<b>{a.get('name', '')}</b>"
                    f"  <font color='#7d3c98'>{a.get('category', '')}</font>"
                    f"  {a.get('visit_duration', 0)}min"
                    f"  {ts}",
                    styles["CNBody"],
                ))
                if a.get("address"):
                    story.append(Paragraph(f"  {a['address']}", styles["CNMeta"]))
                desc = a.get("description", "")
                if desc:
                    story.append(Paragraph(desc, styles["CNDesc"]))

        meals = day.get("meals", [])
        if meals:
            story.append(Paragraph("  餐饮推荐", styles["CNH2"]))
            mt_map = {"breakfast": "早餐", "lunch": "午餐", "dinner": "晚餐"}
            rows = [["类型", "餐厅", "预估费用"]]
            for m in meals:
                rows.append([
                    mt_map.get(m.get("type", ""), "餐"),
                    str(m.get("name", "")),
                    f"Y{m.get('estimated_cost', 0)}",
                ])
            story.append(_table(rows, col_widths=[2.2*cm, 7*cm, 3*cm]))

    # === 预算 ===
    budget = plan.get("budget", {})
    if budget:
        story.append(PageBreak())
        story.append(Paragraph("  预算汇总", styles["CNH1"]))
        rows = [["项目", "金额"]]
        rows.append(["景点门票", f"Y{budget.get('total_attractions', 0):,}"])
        rows.append(["酒店住宿", f"Y{budget.get('total_hotels', 0):,}"])
        rows.append(["餐饮美食", f"Y{budget.get('total_meals', 0):,}"])
        rows.append(["交通出行", f"Y{budget.get('total_transportation', 0):,}"])
        rows.append(["合计", f"Y{budget.get('total', 0):,}"])
        t = _table(rows, col_widths=[7*cm, 5*cm])
        t.setStyle(TableStyle([
            ("FONT", (0, 5), (-1, 5), "CNBold", 11),
            ("BACKGROUND", (0, 5), (-1, 5), colors.HexColor("#fcf3cf")),
        ]))
        story.append(t)

    # === 酒店比价 ===
    hc = plan.get("hotel_comparison", [])
    if hc:
        story.append(Paragraph("  酒店比价", styles["CNH1"]))
        rows = [["酒店", "最低平台", "最低价", "信号", "建议"]]
        for h in hc:
            price = h.get("lowest_price")
            price_s = f"Y{price}" if isinstance(price, (int, float)) else "-"
            rows.append([
                str(h.get("name", "")),
                str(h.get("best_platform", "-")),
                price_s,
                str(h.get("signal", "")),
                str(h.get("advice", "")),
            ])
        story.append(_table(rows))

    # === 建议 ===
    sug = plan.get("overall_suggestions", "")
    if sug:
        story.append(Paragraph("  旅行建议", styles["CNH1"]))
        for tip in sug.replace("；", ";").split(";"):
            tip = tip.strip()
            if tip:
                story.append(Paragraph(f"- {tip}", styles["CNBody"]))

    # === 页脚 ===
    def _page_number(canvas, doc):
        canvas.saveState()
        canvas.setFont("CN", 8)
        canvas.setFillColor(colors.grey)
        canvas.drawRightString(
            19 * cm, 1.2 * cm,
            f"第 {doc.page} 页 / 共 {doc.page} 页",
        )
        canvas.restoreState()

    doc.build(story, onFirstPage=_page_number, onLaterPages=_page_number)
    return buf.getvalue()