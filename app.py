"""智能旅行 & 酒店比价助手 — Streamlit Web 界面。"""
import asyncio
import calendar
import html
import json
import re
import traceback
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

# ---------------------------------------------------------------------------
# 旧版多层主题样式保留在源码中仅供追溯，已不再注入页面。
# 当前全部生效样式统一维护在 assets/travel_style.css。
# ---------------------------------------------------------------------------
_LEGACY_CSS = """
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

    /* ===== 月历标题 ===== */
    .cal-month-label { font-size: 1.2rem; font-weight: 700; color: #1565C0; }

    /* ===== 景点图墙：多图并排，悬停横向展开并显示详情 ===== */
    .spot-strip {
        display: flex; flex-wrap: wrap; gap: 10px; align-items: stretch;
        margin: .6rem 0 .25rem;
    }
    .spot-tile {
        position: relative; flex: 1 1 0; min-width: 150px; height: 230px;
        border-radius: 12px; overflow: hidden; cursor: pointer;
        background: linear-gradient(135deg, #546E7A, #78909C);
        box-shadow: 0 2px 6px rgba(0, 0, 0, .10);
        transition: flex-grow .35s ease, box-shadow .3s ease;
    }
    .spot-tile:hover, .spot-tile:focus-visible {
        flex-grow: 5; z-index: 2; outline: none;
        box-shadow: 0 10px 24px rgba(0, 0, 0, .28);
    }
    .spot-tile > img {
        position: absolute; inset: 0; width: 100%; height: 100%;
        object-fit: cover; display: block;
    }
    .spot-tile.noimg .spot-place {
        position: absolute; inset: 0;
        display: flex; flex-direction: column; align-items: center;
        justify-content: center; gap: 6px; text-align: center;
        color: #ECEFF1; font-size: .9rem; padding: 10px;
    }
    .spot-cap {
        position: absolute; left: 0; right: 0; bottom: 0; z-index: 3;
        padding: 22px 10px 8px; text-align: left; pointer-events: none;
        color: #fff; font-size: .9rem; font-weight: 600;
        background: linear-gradient(transparent, rgba(0, 0, 0, .62));
        white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
        transition: opacity .2s ease;
    }
    .spot-tile:hover .spot-cap, .spot-tile:focus-visible .spot-cap { opacity: 0; }
    .spot-pin {
        position: absolute; left: 50%; top: 44%; z-index: 2;
        width: 12px; height: 12px; transform: translateX(-50%);
        background: #f44336; border: 3px solid #fff; border-radius: 50%;
        box-shadow: 0 2px 6px rgba(0, 0, 0, .4);
        transition: opacity .2s ease;
    }
    .spot-pin::after {
        content: ""; position: absolute; left: 50%; top: 100%;
        width: 2px; height: 10px; margin-left: -1px; background: #f44336;
    }
    .spot-tile:hover .spot-pin, .spot-tile:focus-visible .spot-pin { opacity: 0; }
    .spot-detail {
        position: absolute; inset: 0; z-index: 1;
        display: flex; flex-direction: column; justify-content: flex-end;
        padding: 12px 12px 10px; color: #fff; pointer-events: none;
        background: linear-gradient(to top,
            rgba(0, 0, 0, .90) 0%, rgba(0, 0, 0, .66) 58%,
            rgba(0, 0, 0, .28) 100%);
        opacity: 0; transition: opacity .25s ease .1s;
    }
    .spot-tile:hover .spot-detail, .spot-tile:focus-visible .spot-detail {
        opacity: 1;
    }
    .spot-detail h5 {
        margin: 0 0 3px; padding: 0; font-size: 1rem; line-height: 1.3;
        white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    }
    .spot-meta {
        font-size: .78rem; color: #E1F5FE; margin-bottom: 3px;
        white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    }
    .spot-addr {
        font-size: .75rem; color: #B0BEC5; margin-bottom: 5px;
        white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    }
    .spot-desc {
        font-size: .8rem; line-height: 1.45; color: #ECEFF1;
        max-height: 6.2em; overflow: auto;
        scrollbar-width: thin;
    }

    /* ===== 简约苹果风格（全局覆写） ===== */
    :root {
        --apple-bg: #f5f5f7;
        --apple-card: rgba(255, 255, 255, .82);
        --apple-text: #1d1d1f;
        --apple-sub: #6e6e73;
        --apple-blue: #0071e3;
        --apple-blue-soft: #e8f2ff;
        --apple-border: rgba(0, 0, 0, .08);
        --apple-shadow: 0 1px 2px rgba(0, 0, 0, .04), 0 12px 32px rgba(0, 0, 0, .06);
    }
    html, body, section.main, [class*="css"] {
        font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text",
                     "SF Pro Display", "PingFang SC", "Helvetica Neue",
                     "Microsoft YaHei", "Segoe UI", sans-serif !important;
    }
    [data-testid="stAppViewContainer"] {
        background:
            radial-gradient(1200px 600px at 15% -10%, rgba(0, 113, 227, .08), transparent 60%),
            radial-gradient(1000px 500px at 110% 10%, rgba(90, 200, 250, .10), transparent 55%),
            var(--apple-bg);
    }
    [data-testid="stHeader"] { background: transparent; }
    [data-testid="stSidebar"] { display: none; }
    section.main > div.block-container {
        max-width: 1180px;
        padding-top: 2.2rem;
        padding-bottom: 4rem;
    }
    section.main h1, section.main h2, section.main h3,
    section.main h4, section.main h5 {
        color: var(--apple-text);
        letter-spacing: -.01em;
        font-weight: 650;
    }
    section.main p, section.main span, section.main div, section.main label {
        color: var(--apple-text);
    }

    .main-header {
        border-bottom: none;
        text-align: center;
        font-size: 2.15rem;
        font-weight: 700;
        letter-spacing: -.02em;
        color: var(--apple-text);
        margin: .2rem auto 1.5rem;
        padding: 0 0 .3rem;
        background: none;
        -webkit-text-fill-color: initial;
    }
    .plan-title {
        color: var(--apple-text);
        font-weight: 700;
        font-size: 1.5rem;
        letter-spacing: -.015em;
    }
    .day-header { color: #111; border-bottom-color: rgba(0, 0, 0, .08); }
    .cal-month-label { color: var(--apple-blue); }

    .weather-card, .result-card, .hotel-card, .budget-card {
        background: var(--apple-card);
        backdrop-filter: blur(14px);
        -webkit-backdrop-filter: blur(14px);
        border: 1px solid var(--apple-border);
        border-radius: 18px;
        color: var(--apple-text);
        box-shadow: var(--apple-shadow);
    }
    .weather-card b { color: var(--apple-blue); }
    .result-card { border-left: none; }
    .hotel-card { border-left: none; }

    .stButton > button, .stDownloadButton > button, .stLinkButton > a {
        border-radius: 980px;
        font-weight: 600;
        transition: transform .18s ease, box-shadow .18s ease, opacity .18s ease;
    }
    .stButton > button[kind="primary"],
    .stDownloadButton > button {
        background: var(--apple-blue);
        border: none;
        color: #fff;
        box-shadow: 0 4px 14px rgba(0, 113, 227, .28);
    }
    .stButton > button[kind="primary"]:hover,
    .stDownloadButton > button:hover {
        background: #0077ed;
        transform: translateY(-1px);
        box-shadow: 0 6px 20px rgba(0, 113, 227, .34);
    }
    .stButton > button:active, .stDownloadButton > button:active {
        transform: scale(.97);
    }

    [data-testid="stTextInput"] input,
    [data-testid="stTextArea"] textarea,
    [data-testid="stDateInput"] input,
    [data-testid="stNumberInput"] input,
    [data-testid="stSelectbox"] > div > div {
        background: rgba(255, 255, 255, .92);
        border: 1px solid rgba(0, 0, 0, .10) !important;
        border-radius: 12px;
        color: var(--apple-text);
    }
    [data-testid="stCheckbox"] label {
        background: rgba(255, 255, 255, .8);
        border: 1px solid rgba(0, 0, 0, .06);
        border-radius: 12px;
        padding: .35rem .7rem;
        transition: transform .15s ease, box-shadow .15s ease;
    }
    [data-testid="stCheckbox"] label:hover {
        transform: translateY(-1px);
        box-shadow: 0 3px 10px rgba(0, 0, 0, .06);
    }

    [data-testid="stExpander"] {
        background: var(--apple-card);
        border: 1px solid var(--apple-border);
        border-radius: 20px;
        box-shadow: var(--apple-shadow);
        backdrop-filter: blur(14px);
        -webkit-backdrop-filter: blur(14px);
        overflow: hidden;
        margin-bottom: .8rem;
    }
    [data-testid="stExpander"] summary {
        font-weight: 650;
        padding: .2rem .2rem;
    }

    [data-testid="stSegmentedControl"] {
        background: rgba(255, 255, 255, .78);
        border: 1px solid var(--apple-border);
        border-radius: 999px;
        padding: 4px;
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        width: fit-content;
        margin: 0 auto;
    }
    [data-testid="stSegmentedControl"] button {
        border: none;
        border-radius: 999px;
        color: var(--apple-sub);
        font-weight: 600;
        transition: all .2s ease;
    }
    [data-testid="stSegmentedControl"] button[aria-checked="true"] {
        background: #fff;
        color: var(--apple-text);
        box-shadow: 0 2px 8px rgba(0, 0, 0, .10);
    }

    [data-testid="stProgress"] > div > div {
        background: rgba(0, 0, 0, .07);
        border-radius: 999px;
        overflow: hidden;
    }
    [data-testid="stProgress"] > div > div > div {
        background: linear-gradient(90deg, var(--apple-blue), #5ac8fa);
        border-radius: 999px;
        transition: width .4s ease;
    }
    [data-testid="stStatusWidget"] {
        border-radius: 18px;
        overflow: hidden;
        background: var(--apple-card);
        border: 1px solid var(--apple-border);
    }

    .fade-in { animation: fadeInUp .5s cubic-bezier(.22, .61, .36, 1) both; }

    /* ===== 单张景点图：点击开关，向下展开完整图片并显示详情 ===== */
    .spot-toggle {
        display: block;
        cursor: pointer;
    }
    .spot-toggle-input {
        position: absolute;
        opacity: 0;
        width: 1px;
        height: 1px;
        pointer-events: none;
    }
    .spot-tile.reveal {
        flex: 1 1 auto;
        align-self: flex-start;
        min-width: 0;
        width: 100%;
        interpolate-size: allow-keywords;
        height: 230px;
        max-height: none;
        transition: height .6s cubic-bezier(.22, .61, .36, 1),
                    box-shadow .3s ease;
    }
    .spot-tile.reveal > img {
        position: relative;
        width: 100%;
        height: auto;
        object-fit: initial;
    }
    /* 勾选（点击图片）后：完整展开、隐藏名称条、显示详情层 */
    .spot-toggle-input:checked + .spot-tile.reveal {
        height: auto;
    }
    .spot-toggle-input:checked + .spot-tile.reveal .spot-cap { opacity: 0; }
    .spot-toggle-input:checked + .spot-tile.reveal .spot-detail { opacity: 1; }
    .spot-toggle-input:not(:checked) + .spot-tile.reveal:hover .spot-cap {
        opacity: 1;
    }
    .spot-toggle-input:not(:checked) + .spot-tile.reveal:hover .spot-detail {
        opacity: 0;
    }
    .spot-toggle-input:focus-visible + .spot-tile.reveal {
        outline: 2px solid rgba(184, 148, 90, .85);
        outline-offset: 2px;
    }
    @supports not (interpolate-size: allow-keywords) {
        .spot-tile.reveal {
            height: auto;
            max-height: 230px;
            transition: max-height .6s cubic-bezier(.22, .61, .36, 1),
                        box-shadow .3s ease;
        }
        .spot-toggle-input:checked + .spot-tile.reveal {
            max-height: 1200px;
        }
    }
    .spot-strip.single { display: block; }
    .spot-strip.single .spot-toggle { width: 100%; }

    /* ===== 高级典雅主题（墨绿 × 暖金 × 象牙白） ===== */
    :root {
        --lux-bg: #f7f3ea;
        --lux-bg-soft: #fdfbf5;
        --lux-card: rgba(255, 253, 248, .92);
        --lux-ink: #22302a;
        --lux-ink-soft: #5c685f;
        --lux-green: #1d4a3d;
        --lux-green-deep: #12342c;
        --lux-gold: #b8945a;
        --lux-gold-soft: #e7d8b8;
        --lux-line: rgba(29, 74, 61, .13);
        --lux-shadow: 0 2px 6px rgba(46, 53, 44, .04),
                       0 18px 44px rgba(46, 53, 44, .08);
    }
    [data-testid="stAppViewContainer"] {
        background:
            radial-gradient(1100px 520px at 88% -10%, rgba(184, 148, 90, .12), transparent 62%),
            radial-gradient(900px 600px at -8% 8%, rgba(29, 74, 61, .10), transparent 58%),
            var(--lux-bg);
    }
    html, body, section.main, [class*="css"] {
        font-family: "Inter", -apple-system, BlinkMacSystemFont, "SF Pro Text",
                     "PingFang SC", "Microsoft YaHei", "Segoe UI", sans-serif !important;
    }
    .main-header {
        font-family: "Playfair Display", "Songti SC", "STSong", "Noto Serif SC",
                     Georgia, serif;
        text-align: center;
        font-size: 2.35rem;
        letter-spacing: .04em;
        margin: .2rem auto .35rem;
        background: linear-gradient(92deg, var(--lux-green-deep), var(--lux-green),
                                    var(--lux-gold));
        -webkit-background-clip: text;
        background-clip: text;
        -webkit-text-fill-color: transparent;
        -webkit-text-stroke: .4px rgba(29, 74, 61, .06);
    }
    .plan-title {
        color: var(--lux-green-deep);
        font-weight: 600;
        letter-spacing: .01em;
        font-size: 1.55rem;
    }
    .day-header {
        color: var(--lux-green);
        border-bottom: 1px solid rgba(184, 148, 90, .45);
        font-weight: 650;
    }
    .cal-month-label { color: var(--lux-green); font-weight: 650; }

    .weather-card, .result-card, .hotel-card, .budget-card {
        background: var(--lux-card);
        border: 1px solid var(--lux-line);
        border-radius: 16px;
        color: var(--lux-ink);
        box-shadow: var(--lux-shadow);
        backdrop-filter: blur(8px);
        -webkit-backdrop-filter: blur(8px);
    }
    .weather-card b, .weather-card b { color: var(--lux-green); }
    .result-card { border-left: 3px solid var(--lux-gold); }
    .hotel-card { border-left: 3px solid var(--lux-green); }

    /* 左侧栏 —— 深色雅致面板 */
    [data-testid="stSidebar"] {
        display: block;
        background:
            radial-gradient(600px 400px at 20% -10%, rgba(184, 148, 90, .16), transparent 60%),
            linear-gradient(180deg, #152a23, #0f1f1a);
        border-right: 1px solid rgba(184, 148, 90, .25);
    }
    [data-testid="stSidebar"] > div {
        background: transparent;
    }
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] h4,
    [data-testid="stSidebar"] h5 {
        color: var(--lux-gold-soft);
        letter-spacing: .05em;
        font-weight: 600;
    }
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] div,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] small,
    [data-testid="stSidebar"] .stCaption,
    [data-testid="stSidebar"] [data-testid="stCaptionContainer"] p {
        color: #e7e0cf;
    }
    [data-testid="stSidebar"] hr {
        border-color: rgba(231, 224, 207, .18);
    }
    .sidebar-brand {
        font-family: "Playfair Display", "Songti SC", "STSong", Georgia, serif;
        font-size: 1.08rem;
        font-weight: 600;
        letter-spacing: .05em;
        color: #f3ead2;
        padding: .35rem 0 .25rem;
        border-bottom: 1px solid rgba(184, 148, 90, .35);
        margin-bottom: .8rem;
    }
    [data-testid="stSidebar"] .stRadio > label,
    [data-testid="stSidebar"] [role="radiogroup"] label {
        color: #e7e0cf;
        background: rgba(255, 255, 255, .06);
        border: 1px solid rgba(231, 224, 207, .12);
        border-radius: 12px;
        padding: .45rem .75rem;
        margin-bottom: .35rem;
        transition: all .18s ease;
    }
    [data-testid="stSidebar"] [role="radiogroup"] label:hover {
        background: rgba(255, 255, 255, .12);
        transform: translateX(2px);
    }
    [data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {
        background: rgba(184, 148, 90, .18);
        border-color: rgba(184, 148, 90, .55);
    }
    [data-testid="stSidebar"] input,
    [data-testid="stSidebar"] textarea,
    [data-testid="stSidebar"] [data-testid="stSelectbox"] > div > div,
    [data-testid="stSidebar"] [data-testid="stNumberInput"] input,
    [data-testid="stSidebar"] [data-testid="stDateInput"] input {
        background: rgba(255, 255, 255, .08) !important;
        border: 1px solid rgba(231, 224, 207, .18) !important;
        color: #f6f1e3 !important;
        border-radius: 10px !important;
    }
    [data-testid="stSidebar"] input::placeholder,
    [data-testid="stSidebar"] textarea::placeholder {
        color: rgba(231, 224, 207, .55) !important;
    }
    [data-testid="stSidebar"] [data-testid="stDateInput"] svg,
    [data-testid="stSidebar"] [data-testid="stNumberInput"] svg,
    [data-testid="stSidebar"] [data-testid="stSelectbox"] svg {
        color: #d9cba8 !important;
    }
    [data-testid="stSidebar"] .stCheckbox label {
        background: transparent;
        border: none;
        color: #e7e0cf;
        padding: .2rem .1rem;
    }
    [data-testid="stSidebar"] .stCheckbox label:hover {
        background: transparent;
        transform: none;
    }
    [data-testid="stSidebar"] .stSlider [data-testid="stSliderThumbValue"] {
        color: #f6f1e3;
    }

    .stButton > button[kind="primary"],
    .stDownloadButton > button {
        background: linear-gradient(135deg, var(--lux-green), #2c5f4c);
        border: none;
        color: #faf6ea;
        box-shadow: 0 6px 18px rgba(29, 74, 61, .24);
    }
    .stButton > button[kind="primary"]:hover,
    .stDownloadButton > button:hover {
        background: linear-gradient(135deg, #1f5948, #38715c);
        box-shadow: 0 8px 24px rgba(29, 74, 61, .30);
    }
    [data-testid="stProgress"] > div > div > div {
        background: linear-gradient(90deg, var(--lux-green), var(--lux-gold));
    }

    /* ===== 恢复经典配色（原蓝色系，覆盖深绿色主题） ===== */
    :root {
        --lux-bg: #f2f7fb;
        --lux-bg-soft: #ffffff;
        --lux-card: #ffffff;
        --lux-ink: #263238;
        --lux-ink-soft: #607D8B;
        --lux-green: #1565C0;
        --lux-green-deep: #0D47A1;
        --lux-gold: #26C6DA;
        --lux-gold-soft: #E1F5FE;
        --lux-line: rgba(21, 101, 192, .16);
        --lux-shadow: 0 2px 8px rgba(13, 71, 161, .06);
    }
    [data-testid="stAppViewContainer"] {
        background:
            radial-gradient(1100px 520px at 88% -10%, rgba(38, 198, 218, .10), transparent 62%),
            radial-gradient(900px 600px at -8% 8%, rgba(21, 101, 192, .08), transparent 58%),
            #f2f7fb;
    }
    .main-header {
        background: linear-gradient(90deg, #4A90D9, #26C6DA);
        -webkit-background-clip: text;
        background-clip: text;
        -webkit-text-fill-color: transparent;
        -webkit-text-stroke: 0;
    }
    .plan-title { color: #2E7D32; }
    .day-header { color: #1565C0; border-bottom-color: #BBDEFB; }
    .cal-month-label { color: #1565C0; }

    .weather-card {
        background: #E3F2FD;
        border-color: #BBDEFB;
        color: #263238;
        box-shadow: 0 2px 10px rgba(21, 101, 192, .10);
    }
    .weather-card b { color: #1565C0; }
    .budget-card {
        background: #FFF8E1;
        border-color: #FFE082;
        color: #4e342e;
    }
    .result-card {
        background: #ffffff;
        border-left: 4px solid #4A90D9;
        color: #1a1a1a;
        box-shadow: 0 2px 8px rgba(0, 0, 0, .06);
    }
    .hotel-card {
        background: #ffffff;
        border-left: 4px solid #2E7D32;
        color: #1a1a1a;
        box-shadow: 0 2px 8px rgba(0, 0, 0, .06);
    }

    /* 左侧栏恢复为浅色经典样式 */
    [data-testid="stSidebar"] {
        display: block;
        background: linear-gradient(180deg, #ffffff, #eef5fb);
        border-right: 1px solid rgba(21, 101, 192, .16);
    }
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] h4,
    [data-testid="stSidebar"] h5 {
        color: #1565C0;
    }
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] div,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] small,
    [data-testid="stSidebar"] [data-testid="stCaptionContainer"] p {
        color: #263238;
    }
    .sidebar-brand {
        color: #1565C0;
        border-bottom-color: #90CAF9;
    }
    [data-testid="stSidebar"] [role="radiogroup"] label {
        color: #263238;
        background: #ffffff;
        border-color: #d0d9e4;
    }
    [data-testid="stSidebar"] [role="radiogroup"] label:hover {
        background: #f4f9fd;
        transform: none;
    }
    [data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {
        background: #E3F2FD;
        border-color: #90CAF9;
    }
    [data-testid="stSidebar"] input,
    [data-testid="stSidebar"] textarea,
    [data-testid="stSidebar"] [data-testid="stSelectbox"] > div > div,
    [data-testid="stSidebar"] [data-testid="stNumberInput"] input,
    [data-testid="stSidebar"] [data-testid="stDateInput"] input {
        background: #ffffff !important;
        border-color: #d0d9e4 !important;
        color: #263238 !important;
    }
    [data-testid="stSidebar"] input::placeholder,
    [data-testid="stSidebar"] textarea::placeholder {
        color: #90a4ae !important;
    }
    [data-testid="stSidebar"] [data-testid="stDateInput"] svg,
    [data-testid="stSidebar"] [data-testid="stNumberInput"] svg,
    [data-testid="stSidebar"] [data-testid="stSelectbox"] svg {
        color: #1565C0 !important;
    }
    [data-testid="stSidebar"] .stCheckbox label { color: #263238; }

    .stButton > button[kind="primary"],
    .stDownloadButton > button {
        background: linear-gradient(135deg, #1976D2, #4A90D9);
        color: #fff;
        box-shadow: 0 6px 18px rgba(25, 118, 210, .24);
    }
    .stButton > button[kind="primary"]:hover,
    .stDownloadButton > button:hover {
        background: linear-gradient(135deg, #1565C0, #42A5F5);
    }
    [data-testid="stProgress"] > div > div > div {
        background: linear-gradient(90deg, #1976D2, #26C6DA);
    }
</style>
"""

_APP_STYLE_FILE = Path(__file__).parent / "assets" / "travel_style.css"
st.markdown(
    f"<style>\n{_APP_STYLE_FILE.read_text(encoding='utf-8')}</style>",
    unsafe_allow_html=True,
)


_AMBIENT_GLOW_HTML = """
<div id="ambient-glow" aria-hidden="true" style="position:fixed;inset:0;z-index:999980;pointer-events:none">
  <canvas id="ambient-glow-canvas" style="position:fixed;inset:0;width:100vw;height:100vh"></canvas>
</div>
<script>
(function () {
  var root = document.getElementById("ambient-glow");
  if (!root) return;
  if (typeof root._agCleanup === "function") {
    try { root._agCleanup(); } catch (e) {}
  }
  var canvas = document.getElementById("ambient-glow-canvas");
  if (!canvas) return;
  var ctx = canvas.getContext("2d");
  if (!ctx) return;

  var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  var dpr = 1;
  var vw = window.innerWidth, vh = window.innerHeight, left = 0;
  var homeCX = 0, homeCY = 0;
  var sbBottom = 0, sbCenterX = 0;

  function measure() {
    vw = window.innerWidth;
    vh = window.innerHeight;
    var sb = document.querySelector('[data-testid="stSidebar"]');
    left = sb ? sb.getBoundingClientRect().right : 0;
    var paneW = Math.max(vw - left, 320);
    homeCX = left + paneW * 0.7;
    homeCY = vh * 0.34;
    if (sb) {
      var sbRect = sb.getBoundingClientRect();
      sbBottom = sbRect.bottom;
      sbCenterX = sbRect.left + sbRect.width / 2;
    } else {
      sbBottom = vh;
      sbCenterX = 0;
    }
    dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = Math.round(vw * dpr);
    canvas.height = Math.round(vh * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }
  measure();

  var rnd = function (a, b) { return a + Math.random() * (b - a); };
  var gauss = function () { return (Math.random() + Math.random() + Math.random() - 1.5) / 1.5; };

  // ============ 中心模式粒子 ============
  var N = 46;
  var spreadR = 400;
  var centerParts = [];
  for (var i = 0; i < N; i++) {
    var angle = Math.random() * 6.2832;
    var radius = (i < 8) ? (Math.random() * 60) : (Math.sqrt(Math.random()) * spreadR);
    centerParts.push({
      offX: Math.cos(angle) * radius,
      offY: Math.sin(angle) * radius,
      jx: rnd(-1, 1),
      jy: rnd(-1, 1),
      x: homeCX, y: homeCY,
      sizeS: rnd(120, 220),
      sizeG: rnd(50, 90),
      aS: (i < 8) ? rnd(0.05, 0.08) : rnd(0.025, 0.045),
      aG: rnd(0.05, 0.075),
      hueOff: rnd(-15, 15),
      edgeTX: 0, edgeTY: 0,
      edgeSize: 0, edgeAlpha: 0
    });
  }

  // ============ 边缘模式粒子（全屏四周 + 四角） ============
  var edgeN = 64; // 每条边 15 个 + 4 个角落
  var edgeParts = [];
  var edgeDepth = 25;
  // 四条边各 15 个粒子
  for (var i = 0; i < 60; i++) {
    var side = Math.floor(i / 15);
    var pos = ((i % 15) + Math.random() * 0.7) / 15;
    var ex = 0, ey = 0;
    var d = Math.abs(gauss()) * edgeDepth + 10;
    switch (side) {
      case 0: ex = pos * vw; ey = d; break;
      case 1: ex = vw - d; ey = pos * vh; break;
      case 2: ex = pos * vw; ey = vh - d; break;
      case 3: ex = d; ey = pos * vh; break;
    }
    edgeParts.push({ x: ex, y: ey, size: rnd(140, 220), alpha: rnd(0.05, 0.09), hueOff: rnd(-20, 20) });
  }
  // 8 个角落粒子（每个角 2 个，大尺寸高亮度，确保四角全覆盖）
  var cornerPos = [
    [0, 0], [vw, 0], [vw, vh], [0, vh]
  ];
  for (var i = 0; i < 4; i++) {
    var cx2 = cornerPos[i][0], cy2 = cornerPos[i][1];
    var angle = Math.atan2(cy2 - vh/2, cx2 - vw/2);
    // 主角落粒子：大尺寸，覆盖角本身
    edgeParts.push({
      x: cx2 + Math.cos(angle) * 8,
      y: cy2 + Math.sin(angle) * 8,
      size: rnd(320, 420),
      alpha: rnd(0.10, 0.16),
      hueOff: rnd(-10, 10)
    });
    // 副角落粒子：略偏向边内侧，覆盖角附近的边缘区域
    edgeParts.push({
      x: cx2 + Math.cos(angle) * 25,
      y: cy2 + Math.sin(angle) * 25,
      size: rnd(240, 320),
      alpha: rnd(0.07, 0.12),
      hueOff: rnd(-15, 15)
    });
  }
  // 额外 4 个粒子覆盖顶部侧边栏上方区域（中心在边缘，向屏幕内渐淡）
  for (var i = 0; i < 4; i++) {
    var px = left * (i + 0.5) / 4;
    edgeParts.push({
      x: px, y: 0,
      size: rnd(300, 400),
      alpha: rnd(0.12, 0.18),
      hueOff: rnd(-10, 10)
    });
  }

  // ============ 状态变量 ============
  var active = false;
  var blend = 0;
  var mx = homeCX, my = homeCY;
  var focusX = homeCX, focusY = homeCY;
  var t0 = performance.now();

  var driftX = 0, driftY = 0;
  var driftTargetX = 0, driftTargetY = 0;
  var lastExitX = homeCX, lastExitY = homeCY;

  var planningMode = false;
  var modeBlend = 0;
  var edgeTargetsReady = false;

  var HUE_PALETTE = [216, 268, 322, 196, 216];
  function slowHue(now) {
    var segMs = 9000;
    var spanMs = segMs * (HUE_PALETTE.length - 1);
    var elapsed = Math.max(0, (now || 0) - t0);
    var t = (elapsed % spanMs) / spanMs;
    var pos = t * (HUE_PALETTE.length - 1);
    var idx = Math.min(HUE_PALETTE.length - 2, Math.floor(pos));
    var f = pos - idx;
    var e = f * f * (3 - 2 * f);
    return HUE_PALETTE[idx] + (HUE_PALETTE[idx + 1] - HUE_PALETTE[idx]) * e;
  }

  // ============ 计算中心粒子到边缘的目标位置 ============
  function assignEdgeTargets() {
    for (var i = 0; i < centerParts.length; i++) {
      var p = centerParts[i];
      var angle = Math.atan2(p.offY, p.offX);
      var cosA = Math.cos(angle), sinA = Math.sin(angle);
      var t = Infinity;
      if (sinA < 0) { var tt = -homeCY / sinA; if (tt > 0 && tt < t) t = tt; }
      if (sinA > 0) { var tt = (vh - homeCY) / sinA; if (tt > 0 && tt < t) t = tt; }
      if (cosA < 0) { var tt = (0 - homeCX) / cosA; if (tt > 0 && tt < t) t = tt; }
      if (cosA > 0) { var tt = (vw - homeCX) / cosA; if (tt > 0 && tt < t) t = tt; }
      var margin = 20;
      p.edgeTX = homeCX + cosA * (t - margin);
      p.edgeTY = homeCY + sinA * (t - margin);
      p.edgeSize = rnd(80, 150);
      p.edgeAlpha = rnd(0.04, 0.07);
    }
    edgeTargetsReady = true;
  }

  // ============ 进度条检测 ============
  function checkProgressBar() {
    var el = document.querySelector('[data-testid="stProgress"]');
    var found = el !== null && el.isConnected;
    if (found !== planningMode) {
      planningMode = found;
      if (planningMode) {
        assignEdgeTargets();
      } else {
        edgeTargetsReady = false;
      }
    }
  }

  var observer = null;
  function startObserver() {
    if (observer) return;
    observer = new MutationObserver(function () { checkProgressBar(); });
    observer.observe(document.body, { childList: true, subtree: true });
  }
  startObserver();
  checkProgressBar();

  // ============ 鼠标事件 ============
  function onMove(e) {
    if (!root.isConnected) {
      document.removeEventListener("mousemove", onMove);
      return;
    }
    mx = e.clientX;
    my = e.clientY;
    active = mx >= 0 && mx <= vw && my >= 0 && my <= vh;
    if (active) {
      lastExitX = mx;
      lastExitY = my;
    }
  }
  function onLeave() {
    active = false;
    var dx = lastExitX - homeCX;
    var dy = lastExitY - homeCY;
    var len = Math.sqrt(dx * dx + dy * dy) || 1;
    var dist = 150 + Math.random() * 100;
    driftTargetX = (dx / len) * dist;
    driftTargetY = (dy / len) * dist;
  }
  function onResize() {
    measure();
    // 重新计算边缘粒子位置
    for (var i = 0; i < 60; i++) {
      var side = Math.floor(i / 15);
      var pos = ((i % 15) + Math.random() * 0.7) / 15;
      var d = Math.abs(gauss()) * edgeDepth + 10;
      switch (side) {
        case 0: edgeParts[i].x = pos * vw; edgeParts[i].y = d; break;
        case 1: edgeParts[i].x = vw - d; edgeParts[i].y = pos * vh; break;
        case 2: edgeParts[i].x = pos * vw; edgeParts[i].y = vh - d; break;
        case 3: edgeParts[i].x = d; edgeParts[i].y = pos * vh; break;
      }
    }
    // 角落粒子（每个角 2 个）
    var cPos = [
      [0, 0], [vw, 0], [vw, vh], [0, vh]
    ];
    for (var i = 0; i < 4; i++) {
      var cx2 = cPos[i][0], cy2 = cPos[i][1];
      var angle = Math.atan2(cy2 - vh/2, cx2 - vw/2);
      edgeParts[60 + i * 2].x = cx2 + Math.cos(angle) * 8;
      edgeParts[60 + i * 2].y = cy2 + Math.sin(angle) * 8;
      edgeParts[60 + i * 2 + 1].x = cx2 + Math.cos(angle) * 25;
      edgeParts[60 + i * 2 + 1].y = cy2 + Math.sin(angle) * 25;
    }
    // 顶部侧边栏上方区域额外粒子（中心在边缘）
    for (var i = 0; i < 4; i++) {
      var px = left * (i + 0.5) / 4;
      edgeParts[68 + i].x = px;
      edgeParts[68 + i].y = 0;
    }
    for (var i = 0; i < centerParts.length; i++) {
      centerParts[i].x = homeCX + centerParts[i].offX + driftX;
      centerParts[i].y = homeCY + centerParts[i].offY + driftY;
    }
  }

  // ============ 绘制 ============
  function draw(now) {
    var hue = slowHue(now);
    var gatheredSpread = 50;
    var cx = homeCX + driftX;
    var cy = homeCY + driftY;
    ctx.clearRect(0, 0, vw, vh);
    ctx.globalCompositeOperation = "lighter";

    // ---- 中心模式层 ----
    var centerAlpha = Math.max(0, 1 - modeBlend * 1.2);
    if (centerAlpha > 0.001) {
      var idleCore = 1 - blend;
      var hh = hue;
      var outerCol = "hsla(" + hh.toFixed(1) + ", 88%, 70%, " + (0.035 * idleCore * centerAlpha).toFixed(4) + ")";
      var outerGrad = ctx.createRadialGradient(cx, cy, 0, cx, cy, spreadR + 60);
      outerGrad.addColorStop(0, outerCol);
      outerGrad.addColorStop(0.5, outerCol);
      outerGrad.addColorStop(1, "hsla(" + hh.toFixed(1) + ", 88%, 70%, 0)");
      ctx.fillStyle = outerGrad;
      ctx.beginPath(); ctx.arc(cx, cy, spreadR + 60, 0, 6.2832); ctx.fill();

      var coreCol = "hsla(" + hh.toFixed(1) + ", 92%, 65%, " + (0.18 * idleCore * centerAlpha).toFixed(4) + ")";
      var coreGrad = ctx.createRadialGradient(cx, cy, 0, cx, cy, 280);
      coreGrad.addColorStop(0, coreCol);
      coreGrad.addColorStop(0.3, coreCol);
      coreGrad.addColorStop(0.6, "hsla(" + hh.toFixed(1) + ", 92%, 65%, " + (0.08 * idleCore * centerAlpha).toFixed(4) + ")");
      coreGrad.addColorStop(1, "hsla(" + hh.toFixed(1) + ", 92%, 65%, 0)");
      ctx.fillStyle = coreGrad;
      ctx.beginPath(); ctx.arc(cx, cy, 280, 0, 6.2832); ctx.fill();
    }

    // ---- 中心粒子层（过渡中移动到边缘） ----
    for (var i = 0; i < centerParts.length; i++) {
      var p = centerParts[i];
      var hx, hy;
      if (edgeTargetsReady && modeBlend > 0.01) {
        var baseX = cx + p.offX;
        var baseY = cy + p.offY;
        var eLerp = Math.min(1, modeBlend * 1.5);
        hx = baseX + (p.edgeTX - baseX) * eLerp;
        hy = baseY + (p.edgeTY - baseY) * eLerp;
      } else {
        hx = cx + p.offX;
        hy = cy + p.offY;
      }
      var tx = hx + (focusX + p.jx * gatheredSpread - hx) * blend;
      var ty = hy + (focusY + p.jy * gatheredSpread - hy) * blend;
      p.x += (tx - p.x) * 0.07;
      p.y += (ty - p.y) * 0.07;

      var size, alpha;
      if (edgeTargetsReady && modeBlend > 0.01) {
        var eLerp = Math.min(1, modeBlend * 1.5);
        var s1 = p.sizeS + (p.sizeG - p.sizeS) * blend;
        size = s1 + (p.edgeSize - s1) * eLerp;
        var a1 = (p.aS + (p.aG - p.aS) * blend);
        alpha = (a1 + (p.edgeAlpha - a1) * eLerp) * Math.max(0, 1 - modeBlend * 0.5);
      } else {
        size = p.sizeS + (p.sizeG - p.sizeS) * blend;
        alpha = (p.aS + (p.aG - p.aS) * blend) * centerAlpha;
      }
      var hh = hue + p.hueOff;
      var col = "hsla(" + hh.toFixed(1) + ", 88%, 72%, " + alpha.toFixed(4) + ")";
      var grad = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, size);
      grad.addColorStop(0, col);
      grad.addColorStop(1, "hsla(" + hh.toFixed(1) + ", 88%, 72%, 0)");
      ctx.fillStyle = grad;
      ctx.beginPath(); ctx.arc(p.x, p.y, size, 0, 6.2832); ctx.fill();
    }

    // ---- 边缘模式层 ----
    var edgeAlpha = modeBlend;
    if (edgeAlpha > 0.001) {
      var hh = hue;
      // 边缘泛光呼吸动效：整体 alpha 缓慢脉动
      var breathe = 0.85 + 0.15 * Math.sin(performance.now() * 0.0008 + t0 * 0.001);
      for (var i = 0; i < edgeParts.length; i++) {
        var p = edgeParts[i];
        var a = p.alpha * edgeAlpha * breathe;
        var hh2 = hh + p.hueOff;
        var col = "hsla(" + hh2.toFixed(1) + ", 88%, 72%, " + a.toFixed(4) + ")";
        var grad = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, p.size);
        grad.addColorStop(0, col);
        grad.addColorStop(1, "hsla(" + hh2.toFixed(1) + ", 88%, 72%, 0)");
        ctx.fillStyle = grad;
        ctx.beginPath(); ctx.arc(p.x, p.y, p.size, 0, 6.2832); ctx.fill();
      }
    }

    // 鼠标聚焦光束已整合到粒子层中（粒子随惯性向光标收束）

    ctx.globalCompositeOperation = "source-over";
  }

  // ============ 动画循环 ============
  var raf = null;
  function tick(now) {
    if (!root.isConnected) { cleanup(); return; }

    checkProgressBar();

    var modeTarget = planningMode ? 1 : 0;
    modeBlend += (modeTarget - modeBlend) * 0.03;
    if (modeTarget === 0 && modeBlend < 0.001) modeBlend = 0;
    if (modeTarget === 1 && modeBlend > 0.999) modeBlend = 1;

    var target = active ? 1 : 0;
    blend += (target - blend) * 0.05;
    if (target === 0 && blend < 0.001) blend = 0;
    if (target === 1 && blend > 0.999) blend = 1;

    if (!active) {
      driftX += (driftTargetX - driftX) * 0.006;
      driftY += (driftTargetY - driftY) * 0.006;
    } else {
      driftX += (0 - driftX) * 0.01;
      driftY += (0 - driftY) * 0.01;
    }

    var fxk = active ? 0.03 : 0.02;
    var fxt = active ? mx : homeCX;
    var fyt = active ? my : homeCY;
    focusX += (fxt - focusX) * fxk;
    focusY += (fyt - focusY) * fxk;

    draw(now);
    raf = requestAnimationFrame(tick);
  }

  function cleanup() {
    if (raf) cancelAnimationFrame(raf);
    raf = null;
    if (observer) { observer.disconnect(); observer = null; }
    document.removeEventListener("mousemove", onMove);
    document.removeEventListener("mouseleave", onLeave);
    window.removeEventListener("resize", onResize);
  }
  root._agCleanup = cleanup;
  document.addEventListener("mousemove", onMove, { passive: true });
  document.addEventListener("mouseleave", onLeave, { passive: true });
  window.addEventListener("resize", onResize);
  draw(performance.now());
  if (!reduce) { raf = requestAnimationFrame(tick); }
})();
</script>
"""


def _inject_ambient_glow():
    """规划结果生成前，在主内容区注入「一团随鼠标收束 / 散开的多彩泛光」。

    通过 st.html(unsafe_allow_javascript=True) 注入固定于视口的 Canvas 泛光层：
    - 仅在使用旅行规划模式且尚未产出规划结果时调用；
    - 无鼠标时：右侧内容区呈一团更大、缓慢变色的弥散泛光，以极慢速度漂移；
    - 鼠标进入右侧内容区：光点向鼠标处收束聚合、更发散；鼠标移出后重新散开；
    - 泛光层 pointer-events: none，不拦截任何交互；
    - 遵循 prefers-reduced-motion，仅渲染一帧静态泛光。
    """
    st.html(_AMBIENT_GLOW_HTML, unsafe_allow_javascript=True)


_SIDEBAR_HARNESS_HTML = """
<style>
  /* 侧边栏自动隐藏 - 热区 + 把手样式 */
  #hh-sidebar-strip {
    position: fixed; left: 0; top: 0; bottom: 0; width: 16px;
    z-index: 999990; cursor: default;
  }
  #hh-sidebar-tab {
    position: fixed; left: 0; top: 50%; transform: translateY(-50%);
    z-index: 999991;
    background: rgba(255,255,255,.85); backdrop-filter: blur(8px);
    border: 1px solid rgba(0,0,0,.08); border-left: none;
    border-radius: 0 10px 10px 0;
    padding: 10px 8px 10px 4px;
    font-size: 13px; color: #555; cursor: pointer;
    box-shadow: 2px 0 8px rgba(0,0,0,.06);
    transition: opacity .15s ease;
    user-select: none; white-space: nowrap; writing-mode: vertical-lr;
    letter-spacing: 2px;
  }
  #hh-sidebar-tab:hover { background: rgba(255,255,255,.95); color: #222; }
  /* 侧边栏展开/收起动画速度 */
  section[data-testid="stSidebar"] {
    transition: width 0.6s ease, min-width 0.6s ease, max-width 0.6s ease !important;
  }
  section[data-testid="stSidebar"] > div {
    transition: width 0.6s ease !important;
  }
  section[data-testid="stSidebar"] .stSidebarCollapseButton {
    transition: all 0.6s ease !important;
  }
  /* 主内容区域移动动画 */
  .stAppHeader, .stMain, .st-emotion-cache-1y4p8pa, .st-emotion-cache-1wrcr25 {
    transition: margin-left 0.6s ease, padding-left 0.6s ease !important;
  }
  .stApp > section:not([data-testid="stSidebar"]) {
    transition: margin-left 0.6s ease !important;
  }
</style>
<div id="hh-ui" aria-hidden="true" data-hh-mode="__HH_MODE__" data-hh-ready="__HH_READY__"
     style="display:none"></div>
<script>
(function () {
  var ui = document.getElementById("hh-ui");
  if (!ui) return;

  var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var finePointer = window.matchMedia && window.matchMedia("(pointer: fine)").matches;
  var mode = ui.getAttribute("data-hh-mode") || "";
  var ready = ui.getAttribute("data-hh-ready") === "1";
  var travel = mode === "travel";

  var HIDE_KEY = "hh_sb_auto_hide";
  function getFlag() {
    try { return sessionStorage.getItem(HIDE_KEY) === "1"; } catch (e) { return false; }
  }
  function setFlag(v) {
    try { sessionStorage.setItem(HIDE_KEY, v ? "1" : "0"); } catch (e) {}
  }

  function sidebarEl() { return document.querySelector('[data-testid="stSidebar"]'); }
  function collapseBtn() { return document.querySelector('[data-testid="stSidebarCollapseButton"]'); }
  function isOpen() {
    var s = sidebarEl();
    if (!s) return true;
    return s.getBoundingClientRect().width > 120;
  }
  function toggleCollapse() {
    // Streamlit 1.63: data-testid 元素是外层容器，真正可点击的是内部 button
    var b = collapseBtn();
    if (!b) return;
    var inner = b.querySelector('button');
    (inner || b).click();
  }
  function syncHidden() {
    var hidden = travel && ready && finePointer && !isOpen();
    document.body.classList.toggle("hh-sb-hidden", hidden);
  }

  // 清理上次脚本追加到 body 的 UI（st.html 的 innerHTML 重置不会清理它们）
  function removeById(id) {
    var el = document.getElementById(id);
    if (el) el.remove();
  }
  removeById("hh-sidebar-strip");
  removeById("hh-sidebar-tab");

  // ---------- ✈️ 开始规划按钮点击动画 ----------
  if (!window.__hhFlyBound) {
    window.__hhFlyBound = true;
    document.addEventListener("click", function (ev) {
      var btn = ev.target && ev.target.closest
        ? ev.target.closest('[data-testid="stButton"] button')
        : null;
      if (!btn) return;
      if ((btn.innerText || "").trim().indexOf("开始规划") === -1) return;
      if (reduce || document.querySelector(".hh-plane")) return;
      var r = btn.getBoundingClientRect();
      if (!r.width || !r.height) return;
      var plane = document.createElement("div");
      plane.className = "hh-plane";
      plane.textContent = "✈️";
      plane.style.left = Math.round(r.left + 6) + "px";
      plane.style.top = Math.round(r.top + r.height / 2) + "px";
      plane.style.setProperty("--hh-fly-dist", Math.round(r.width + 20) + "px");
      document.body.appendChild(plane);
      btn.classList.add("hh-flying");
      var done = function () {
        plane.remove();
        btn.classList.remove("hh-flying");
      };
      plane.addEventListener("animationend", done, { once: true });
      window.setTimeout(done, 1100);
    });
  }

  // ---------- 侧边栏自动隐藏（仅旅行规划 + 精细指针） ----------
  var timers = window.__hhTimers || (window.__hhTimers = {});
  var clearTimer = function (key) {
    if (timers[key]) { clearTimeout(timers[key]); timers[key] = null; }
  };

  if (travel && finePointer) {
    if (ready) {
      // 结果就绪：约 1 秒后自动收起
      clearTimer("hide");
      timers.hide = window.setTimeout(function () {
        timers.hide = null;
        if (isOpen()) {
          toggleCollapse();
          setFlag(true);
        }
      }, 2000);

      // 左缘热区 + 「⚙ 参数」小把手
      var strip = document.createElement("div");
      strip.id = "hh-sidebar-strip";
      document.body.appendChild(strip);
      var tab = document.createElement("div");
      tab.id = "hh-sidebar-tab";
      tab.textContent = "⚙ 参数";
      document.body.appendChild(tab);

      function openSidebar() {
        if (!isOpen()) {
          toggleCollapse();
          setFlag(true);
        }
      }
      strip.addEventListener("mouseenter", openSidebar);
      tab.addEventListener("click", openSidebar);
      var sb = sidebarEl();
      if (sb) {
        sb.addEventListener("mouseleave", function () {
          clearTimer("leave");
          timers.leave = window.setTimeout(function () {
            timers.leave = null;
            if (isOpen() &&
                !document.querySelector("#hh-sidebar-strip:hover, #hh-sidebar-tab:hover")) {
              toggleCollapse();
              setFlag(true);
            }
          }, 500);
        });
      }
    } else if (getFlag() && !isOpen()) {
      // 结果清空后恢复展开（仅当是本功能收起的）
      toggleCollapse();
      setFlag(false);
    }
  } else if (!travel && getFlag() && !isOpen()) {
    // 离开旅行模式：恢复侧边栏
    toggleCollapse();
    setFlag(false);
  }

  // 周期同步 body.hh-sb-hidden（覆盖用户用原生按钮开合侧边栏等场景）
  if (!window.__hhSyncTimer) {
    window.__hhSyncTimer = window.setInterval(function () {
      var st = window.__hhUiState;
      if (!st) return;
      var s = sidebarEl();
      var hidden = st.travel && st.ready && st.fine && (!s || s.getBoundingClientRect().width <= 120);
      var has = document.body.classList.contains("hh-sb-hidden");
      if (hidden !== has) document.body.classList.toggle("hh-sb-hidden", hidden);
    }, 700);
  }
  window.__hhUiState = { travel: travel, ready: ready, fine: finePointer };
  syncHidden();
})();
</script>
"""


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


def _weather_class(text: str) -> str:
    """把 AMAP 天气文本归为 wx-* 卡片背景类（晴/多云/阴/雨/雪/雾，兜底 unknown）。"""
    t = text or ""
    for kw, cls in (
        ("雨", "wx-rain"), ("雷", "wx-rain"), ("冰雹", "wx-rain"),
        ("雪", "wx-snow"),
        ("雾", "wx-fog"), ("霾", "wx-fog"), ("浮尘", "wx-fog"), ("扬沙", "wx-fog"), ("沙尘", "wx-fog"),
        ("阴", "wx-overcast"),
        ("多云", "wx-cloudy"),
        ("晴", "wx-sunny"),
    ):
        if kw in t:
            return cls
    return "wx-unknown"


def _weather_icon(text: str) -> str:
    """按天气文本返回语义化天气 emoji。"""
    t = text or ""
    if "雷" in t:
        return "⛈️"
    if "阵雨" in t:
        return "🌦️"
    if "雨" in t:
        return "🌧️"
    if "雪" in t:
        return "❄️"
    if "雾" in t or "霾" in t:
        return "🌫️"
    if "多云" in t:
        return "⛅"
    if "阴" in t:
        return "☁️"
    if "晴" in t:
        return "☀️"
    return "🌡️"


def _esc(value) -> str:
    """HTML 转义，用于拼接 unsafe_allow_html 文本与属性。"""
    return html.escape("" if value is None else str(value), quote=True)


def _short_name(name: str, limit: int = 5) -> str:
    """将单个景点名截断为约 limit 个字符，超长时补省略号。"""
    name = (name or "").strip()
    if len(name) <= limit:
        return name
    return name[:limit] + "…"


def _spots_summary(day: dict) -> str:
    """生成日历格子的紧凑景点名摘要：最多 2 个景点，每个约 5 字。"""
    names = [a.get("name", "") for a in day.get("attractions", [])
             if str(a.get("name", "") or "").strip()]
    if not names:
        return ""
    parts = [_short_name(n) for n in names[:2]]
    text = " · ".join(parts)
    if len(names) > 2:
        text = text.rstrip("…") + "…"
    return text


def _progress_chip_html(value: float, message: str, collected: int = 0, state: str = "running") -> str:
    """生成进度提示芯片：左侧呼吸圆点 + 当前模块文字，右侧模块计数与百分比。"""
    pct = max(0, min(100, int(round(value * 100))))
    state_cls = state if state in {"done", "error"} else "running"
    if state == "done":
        text = f"✅ {_esc(message)}"
        meta = "规划完成"
    elif state == "error":
        text = f"❌ {_esc(message)}"
        meta = "生成已停止"
    else:
        text = f"{_esc(message)}"
        prefix = f"模块 {collected} · " if collected else "初始化 · "
        meta = f"{prefix}{pct}%"
    return (
        f'<div class="gen-chip {state_cls}">'
        f'<span class="gen-chip-main"><span class="gen-orb"></span>'
        f'<span class="gen-chip-text">{text}</span></span>'
        f'<span class="gen-chip-meta">{meta}</span></div>'
    )


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


def _is_broken_resource_exc(exc: BaseException) -> bool:
    """判断是否为可自动重连恢复的 MCP 连接中断类错误。"""
    subs = getattr(exc, "exceptions", None)
    if subs:
        return any(_is_broken_resource_exc(sub) for sub in subs)
    name = type(exc).__name__
    return name in {"BrokenResourceError", "ClosedResourceError"} or isinstance(
        exc, (ConnectionResetError, BrokenPipeError)
    )


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

    hotels = data.get("hotels", [])
    if hotels:
        st.markdown("**📋 酒店列表（按价格排序）**")
        rows = []
        for h in hotels:
            price = h.get("price")
            rows.append({
                "酒店": h.get("name", ""),
                "平台": h.get("source", ""),
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
    st.markdown(f"#### 🧭 订房决策 — {data.get('hotel_name', '')}")
    c1, c2 = st.columns(2)
    lowest_price = data.get("lowest_price")
    with c1:
        st.metric("💰 全网最低价", f"¥{lowest_price:g}" if isinstance(lowest_price, (int, float)) else "—")
    with c2:
        st.metric("🏆 最低价平台", data.get("lowest_platform") or "—")

    platforms = data.get("platforms", [])
    if platforms:
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
                st.markdown(
                    f'<div class="result-card fade-in d{min(i + 1, 6)}" '
                    f'style="border-left-color:{border};text-align:center">'
                    f'<b>{p.get("source", "?")}</b>{price_html}{crown}</div>',
                    unsafe_allow_html=True,
                )
                if p.get("url"):
                    st.link_button(f"🔗 {p.get('source')}预订", p["url"], width="stretch")

    _render_advice(data.get("advice"))


def _feature_card_grid(features: list[tuple[str, str, str]]) -> None:
    """把功能简介渲染成一排毛玻璃特性卡片。"""
    cols = st.columns(len(features))
    for i, (icon, title, desc) in enumerate(features):
        with cols[i]:
            st.markdown(
                f'<div class="feature-card fade-in d{min(i + 1, 6)}">'
                f'<div class="feature-icon">{icon}</div>'
                f'<div class="feature-title">{title}</div>'
                f'<div class="feature-desc">{desc}</div>'
                f"</div>",
                unsafe_allow_html=True,
            )


# ==================== 酒店比价模式 ====================

def hotel_mode():
    # ============ 左侧参数面板 ============
    with st.sidebar:
        st.markdown("##### ✦ 比价参数")

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

    # ---- 结果展示 ----
    hotel_result = st.session_state.get("hotel_result")
    if hotel_result is None:
        st.caption("✨ 聚合飞猪、途牛、RG、同程四源价格，支持比价 / 低价日历 / 订房决策")
        _feature_card_grid([
            ("🔍", "多平台实时比价",
             "飞猪 + 途牛 + RG + 同程四源实时对比，找到最低价"),
            ("📅", "低价日历",
             "一键扫描 7-30 天价格洼地，找到最便宜的入住日期"),
            ("🧭", "订房决策",
             "五维度综合判断，输出 🟢订 / 🟡等 / 🔴观望 信号"),
        ])
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
@st.cache_resource(show_spinner=False)
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
    """构建月历数据：行程日带 Day 序号与紧凑景点名，并裁掉首尾无行程的空周。"""
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
                    "spots": _spots_summary(day),
                    "n": len(day.get("attractions", [])),
                })
            cells.append(cell)
        weeks.append(cells)

    # 裁剪首尾不含行程日的整周；裁剪为空时回退完整月，保证月历始终可渲染。
    non_empty = [i for i, week in enumerate(weeks)
                 if any(c.get("idx") for c in week)]
    if non_empty:
        weeks = weeks[non_empty[0]:non_empty[-1] + 1]
    return {"weeks": weeks}


def _attraction_strip(attractions: list, plan_city: str) -> str:
    """把当天景点渲染成一行并排图墙；悬停/聚焦时该图横向展开并显示详情。"""
    from render import attraction_photo, attraction_map_image

    tiles = []
    single = len(attractions) == 1
    for a in attractions:
        raw_name = str(a.get("name") or "").strip() or "景点"
        img_url = (a.get("image_url") or "").strip()
        if not img_url:
            img_url = (attraction_photo(raw_name, plan_city) or "").strip()
        is_map = False
        if not img_url:
            img_url = (attraction_map_image(a.get("location") or {}) or "").strip()
            is_map = bool(img_url)

        # 元信息：分类 / 游玩时长 / 门票
        meta_parts = []
        if str(a.get("category") or "").strip():
            meta_parts.append(str(a["category"]).strip())
        visit_duration = a.get("visit_duration")
        if isinstance(visit_duration, (int, float)) and visit_duration > 0:
            meta_parts.append(f"⏱️ {visit_duration:g} 分钟")
        ticket = a.get("ticket_price")
        if ticket == 0:
            meta_parts.append("🆓 免费")
        elif isinstance(ticket, (int, float)) and ticket > 0:
            meta_parts.append(f"🎫 ¥{ticket:g}")
        meta = " · ".join(meta_parts)

        addr = str(a.get("address") or "").strip()
        desc = str(a.get("description") or "").strip()
        addr_html = f'<div class="spot-addr">📍 {_esc(addr)}</div>' if addr else ""
        desc_html = f'<div class="spot-desc">{_esc(desc)}</div>' if desc else ""

        if img_url:
            media_html = f'<img src="{_esc(img_url)}" alt="{_esc(raw_name)}" loading="lazy">'
            if is_map:
                media_html += '<span class="spot-pin"></span>'
            tile_cls = "spot-tile reveal" if single else "spot-tile"
        else:
            media_html = (
                '<div class="spot-place"><div style="font-size:2.2rem">🏛️</div>'
                "<div>暂无图片</div></div>"
            )
            tile_cls = "spot-tile noimg" + (" single" if single else "")

        hint = "查看介绍与详情" if not img_url else (
            "点击展开查看完整图片与介绍" if single else "悬停查看完整图片与详情"
        )
        keyboard_attrs = "" if single else ' tabindex="0" role="button"'
        tile_html = (
            f'<div class="{tile_cls}"{keyboard_attrs} '
            f'title="{_esc(raw_name)}：{hint}">'
            f"{media_html}"
            f'<div class="spot-cap">{_esc(raw_name)}</div>'
            f'<div class="spot-detail">'
            f'<h5>{_esc(raw_name)}</h5>'
            f'<div class="spot-meta">{_esc(meta)}</div>'
            f"{addr_html}{desc_html}"
            f"</div></div>"
        )
        if single and img_url:
            tile_html = (
                '<label class="spot-toggle">'
                '<input type="checkbox" class="spot-toggle-input" '
                f'aria-label="{_esc(raw_name)}：点击展开/收起完整图片与介绍">'
                f"{tile_html}</label>"
            )
        tiles.append(tile_html)
    return f'<div class="spot-strip{" single" if single else ""}">{"".join(tiles)}</div>'


def _render_day_details(day: dict, idx: int, plan_city: str):
    """渲染选中日的详细行程（住宿 / 景点 / 餐饮）。"""
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
        st.markdown(_attraction_strip(attractions, plan_city), unsafe_allow_html=True)

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
    # ============ 会话初始化 ============
    if "plan_data" not in st.session_state:
        st.session_state.plan_data = None
    if "plan_raw" not in st.session_state:
        st.session_state.plan_raw = ""

    # 规划结果生成前：主内容区显示多彩泛光背景（Gemini 风格，随鼠标流动）
    if st.session_state.plan_data is None:
        _inject_ambient_glow()

    # ============ 左侧参数面板 ============
    with st.sidebar:
        st.markdown("##### ✦ 旅行参数")

        city = st.text_input("📍 目的地城市", placeholder="例如: 杭州、成都、三亚...")

        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("📅 开始日期", value=date.today())
        with col2:
            end_date = st.date_input("📅 结束日期", value=date.today())

        if start_date and end_date and end_date >= start_date:
            trip_days = (end_date - start_date).days
            st.caption(f"📌 共计 **{trip_days}** 天")
        elif end_date < start_date:
            st.error("结束日期不能早于开始日期")

        st.markdown("---")
        st.markdown("##### ✦ 交通方式")
        transport_options = ["公共交通", "自驾", "打车/网约车", "骑行", "步行"]
        transport_selected = []
        for opt in transport_options:
            if st.checkbox(opt, key=f"trans_{opt}"):
                transport_selected.append(opt)

        st.markdown("---")
        st.markdown("##### ✦ 住宿偏好")
        hotel_type = st.selectbox(
            "住宿类型",
            ["不限", "经济型酒店", "中档型酒店", "豪华型酒店", "民宿/客栈", "青年旅舍"],
            index=2,
            label_visibility="collapsed",
        )
        if hotel_type == "不限":
            hotel_type = ""

        st.markdown("---")
        st.markdown("##### ✦ 旅行偏好")
        pref_options = ["自然风光", "历史文化", "美食探店", "休闲度假", "艺术展览", "购物逛街", "亲子乐园"]
        pref_selected = []
        for opt in pref_options:
            if st.checkbox(opt, key=f"pref_{opt}"):
                pref_selected.append(opt)

        st.markdown("---")
        st.markdown("##### ✦ 额外要求")
        extra_requirements = st.text_area(
            "补充说明",
            placeholder="例如: 带老人出行需要轻松行程、想在市中心活动...",
            label_visibility="collapsed",
        )

        st.markdown("---")
        submit_btn = st.button("🚀 开始规划", type="primary", width="stretch")

    # 未开始时的引导页
    if not submit_btn and st.session_state.plan_data is None:
        st.caption("✨ 一站式智能出行：天气、景点、路线、酒店比价与预算自动生成")
        _feature_card_grid([
            ("🌤️", "实时天气查询",
             "接入高德地图 MCP，获取目的地准确天气预报"),
            ("🏛️", "智能景点推荐",
             "根据你的偏好，AI 精准匹配最适合的景点和路线"),
            ("🏨", "酒店多平台比价",
             "飞猪 / 途牛 / RG / 同程实时比价，给出订房时机建议"),
            ("📊", "预算自动汇总",
             "景点门票、餐饮、住宿、交通费用一目了然"),
        ])

    # 点击按钮后执行
    if submit_btn:
        if not city.strip():
            st.error("请输入目的地城市")
        elif end_date < start_date:
            st.error("结束日期不能早于开始日期")
        else:
            chip = None
            progress_bar = None
            try:
                planner = get_planner()
                prompt = build_prompt(
                    city, start_date, end_date,
                    transport_selected, hotel_type, pref_selected, extra_requirements,
                )
                from render import parse_plan

                def _update_progress(
                    value: float,
                    message: str,
                    collected: int = 0,
                    state: str = "running",
                ) -> None:
                    """同步更新模块提示芯片与纤细进度条。"""
                    chip.markdown(
                        _progress_chip_html(value, message, collected, state),
                        unsafe_allow_html=True,
                    )
                    progress_bar.progress(min(max(float(value), 0.0), 1.0))

                chip = st.empty()
                progress_bar = st.progress(0.02)
                _update_progress(0.02, "正在初始化生成引擎…", 0)

                tokens: list[str] = []
                status_lines: list[str] = []
                module_seen: list[str] = []
                for attempt in range(2):
                    async def _collect():
                        results = []
                        module_seen.clear()
                        status_lines.clear()
                        async for token in planner.stream(prompt):
                            stripped = token.strip()
                            if any(
                                stripped.startswith(emoji)
                                for emoji in _STATUS_EMOJIS
                            ):
                                status_lines.append(stripped)
                                if stripped not in module_seen:
                                    module_seen.append(stripped)
                                    _update_progress(
                                        min(0.08 + len(module_seen) * 0.065, 0.90),
                                        stripped,
                                        len(module_seen),
                                    )
                            results.append(token)
                        return results

                    try:
                        tokens = asyncio.run(_collect())
                        break
                    except Exception as exc:
                        # MCP 连接/会话被服务端或旧事件循环中断时，重建
                        # 全新的 Planner + MCP 客户端后自动重试一次。
                        if attempt == 0 and _is_broken_resource_exc(exc):
                            traceback.print_exc()
                            st.warning(
                                "检测到地图/酒店 MCP 连接中断（BrokenResourceError），"
                                "正在重建连接并自动重试，请稍候…"
                            )
                            _update_progress(
                                0.03,
                                "MCP 连接中断，正在重建连接并自动重试…",
                                len(module_seen),
                            )
                            from mcp_client import McpClientManager

                            McpClientManager.reset()
                            get_planner.cache_clear()
                            planner = get_planner()
                            continue
                        raise

                _update_progress(
                    0.95, "数据已就绪，正在整理最终行程…", len(module_seen)
                )

                # 汇总生成内容
                full_text = "".join(tokens)

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
                for state_key in list(st.session_state.keys()):
                    if state_key.startswith("trip_calendar"):
                        st.session_state.pop(state_key, None)

                _update_progress(
                    1.0, "旅行计划生成完成", len(module_seen), state="done"
                )
            except Exception as e:
                traceback.print_exc()
                if progress_bar is not None:
                    _update_progress(1.0, "行程生成失败", 0, state="error")
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

        for i, w in enumerate(weather):
            day_wx = w.get("day_weather", "")
            d = w.get("date", "")[-5:]
            di = _weather_icon(day_wx)
            wx_cls = _weather_class(day_wx)
            with cols[i]:
                st.markdown(
                    f"""<div class="weather-card {wx_cls} fade-in d{min(i + 1, 6)}" style="text-align:center">
                    <b>{_esc(d)}</b><br>
                    {di} {_esc(day_wx or '?')}<br>
                    🌡️ {_esc(w.get('day_temp', '?'))}°C / {_esc(w.get('night_temp', '?'))}°C<br>
                    💨 {_esc(w.get('wind_direction', ''))}{_esc(w.get('wind_power', ''))}
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
        months = []
        for dstr in trip_dates:
            try:
                key = (int(dstr[:4]), int(dstr[5:7]))
            except (IndexError, ValueError):
                continue
            if key not in months:
                months.append(key)
        if not months:
            today = date.today()
            months = [(today.year, today.month)]

        selected = st.session_state.get("selected_day", 1)
        if selected not in idx_to_day:
            selected = 1

        # 比较各月组件返回值与上次渲染的差异，只采用确实发生变化的点击，
        # 避免旧月份残留值干扰；无变化则沿用当前选中日。
        prev_returns = st.session_state.get("trip_calendar_prev") or {}
        picked = None
        for y, m in months:
            key_name = f"trip_calendar_{y}_{m}"
            value = st.session_state.get(key_name)
            if value is not None and value in idx_to_day and value != prev_returns.get(key_name):
                if picked is None:
                    picked = value
                elif picked != value:
                    picked = None
                    break
        if picked is not None:
            selected = picked
            st.session_state.selected_day = picked

        for y, m in months:
            key_name = f"trip_calendar_{y}_{m}"
            st.markdown(
                f'<div class="cal-month-label fade-in">{y}年{m}月</div>',
                unsafe_allow_html=True,
            )
            trip_calendar(
                data=_trip_calendar_data(y, m, day_by_date, selected),
                key=key_name,
            )
        st.caption("💡 点击日历中的行程日期，可在下方查看当天详细行程")

        _render_day_details(idx_to_day[selected], selected, plan_city)
        st.session_state.trip_calendar_prev = {
            f"trip_calendar_{y}_{m}": st.session_state.get(f"trip_calendar_{y}_{m}")
            for y, m in months
        }

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

st.markdown('<div class="main-header">🧳 智能旅行助手</div>', unsafe_allow_html=True)

with st.sidebar:
    st.markdown('<div class="sidebar-brand">🧳 智能旅行 & 酒店比价</div>',
                unsafe_allow_html=True)
    st.markdown("##### ✦ 功能模式")
    mode = st.radio(
        "功能模式",
        ["🧳 智能旅行规划", "🏨 酒店比价"],
        label_visibility="collapsed",
        key="app_mode",
    )
    st.markdown("---")

# ---- UI 增强：侧边栏自动隐藏（旅行模式）+ 「开始规划」飞行动画 ----
st.html(
    _SIDEBAR_HARNESS_HTML
    .replace("__HH_MODE__", "travel" if mode == "🧳 智能旅行规划" else "hotel")
    .replace("__HH_READY__", "1" if st.session_state.get("plan_data") is not None else "0"),
    unsafe_allow_javascript=True,
)

if mode == "🧳 智能旅行规划":
    travel_mode()
else:
    hotel_mode()
