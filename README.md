# 🧳 智能旅行 & 酒店比价助手

> 一个界面整合「智能旅行规划」与「多平台酒店比价」的 Streamlit 应用。
> 旅行规划由 Multi-Agent 驱动，接入**高德开放平台官方 MCP**（天气 / POI / 路线）与**通义千问（DashScope）**；
> 酒店比价内置「酒店聪明订」FastMCP 服务，聚合飞猪 / 途牛 / RG / 同程四平台实时价格，提供订房时机建议。

---

## ✨ 功能总览

Web 界面在侧边栏顶部切换两个功能模式。

### 🧳 智能旅行规划

| 能力              | 说明                                                                                |
| ----------------- | ----------------------------------------------------------------------------------- |
| 🌤️ 实时天气     | 通过高德 MCP`maps_weather` 获取目的地天气，标题下带 msn.cn 天气链接               |
| 🏛️ 智能景点推荐 | Planner Agent 直接调用高德 POI 搜索，按用户偏好匹配景点，附带真实风景照片与详细介绍 |
| 🏨 酒店推荐       | 结合区域 / 地标 / 预算推荐酒店，规划完成后附带多平台比价结论                        |
| 🗺️ 路线规划     | 高德步行 / 驾车 / 公交路线，先地理编码再规划                                        |
| 🖼️ 景点配图     | 优先使用高德 POI 自带的真实风景照片 URL，无则兜底静态地图底图                       |
| 📊 预算汇总       | 自动汇总门票、酒店、餐饮、交通与总预算                                              |
| 📥 PDF 导出       | 一键下载精美排版 PDF（封面、天气表格、每日行程、预算高亮、酒店比价、页码）          |
| ✍️ 一句话生成     | 主界面像 Gemini 一样输入一段文字描述，AI 先理解需求（自动推断日期/预算/偏好）再生成完整计划；原有左侧表单规划保留 |
| 🏨 酒店比价       | 行程中的`hotel_comparison` 板块展示最低平台 / 最低价 / 订/等/观望信号             |

### 🏨 酒店比价（独立模式，无需任何 API Key）

| 操作        | 对应 MCP 工具 | 说明                                                 |
| ----------- | ------------- | ---------------------------------------------------- |
| 🔍 比价搜索 | `search`    | 飞猪 + 途牛合并去重，按价格排序并给出订房建议        |
| 📅 低价日历 | `calendar`  | 扫描 5-30 天入住价格洼地，标注低价 / 适中 / 偏贵     |
| 🧭 订房决策 | `advisor`   | 指定酒店四平台精确比价，输出 🟢 订 / 🟡 等 / 🔴 观望 |

> 酒店价格实时变动，查询结果仅供参考，实际价格以预订页面为准。

![示例1](示例1.png)

![示例2](示例2.png)

![示例3](示例3.png)

---

## 🚀 快速开始（Windows PowerShell）

### 1. 环境要求

- Python 3.10+（本仓库在 Python 3.14 验证通过）
- 两个 API Key：DashScope（通义千问）、高德 Web 服务 Key

### 2. 创建主环境并安装依赖

```powershell
cd D:\Code\Python\hotel_hunter\smart_travel_mcp\travel-agent

python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 3. 安装酒店比价运行环境（独立 venv）

酒店比价服务在主进程外的独立 venv 中运行（内部 fastmcp 4 + mcp 2，与主环境 mcp 1.x 隔离）：

```powershell
python -m venv .hotel-mcp
.hotel-mcp\Scripts\python -m pip install fastmcp
```

> `.hotel-mcp` 已加入 `.gitignore`；应用会按 `travel-agent/.hotel-mcp/Scripts/python.exe` 自动找到它。

### 4. 配置 API Key

在 `travel-agent` 目录创建 `.env`：

```env
# 通义千问 LLM（阿里百炼），智能旅行规划必需
DASHSCOPE_API_KEY=sk-xxxx

# 高德地图 MCP（高德开放平台 Web 服务 Key），智能旅行规划必需
AMAP_MAPS_API_KEY=xxxxxxxx
```

- DashScope Key：https://dashscope.console.aliyun.com/
- 高德 Web 服务 Key：https://lbs.amap.com/ → 控制台创建应用，Key 类型选 **Web服务**

### 5. 启动

```powershell
# 激活主项目环境
.\.venv\Scripts\Activate.ps1

# 然后启动
streamlit run app.py
```

浏览器访问 `http://localhost:8501`。

```powershell
# 命令行模式（仅旅行规划演示）
python Agent.py
```

---

## 📁 项目结构

```
travel-agent/
├── app.py                   # Streamlit 双模式界面（旅行规划 / 酒店比价）+ 动效 + PDF 导出
├── Agent.py                 # CLI 演示入口（流式收集 + 格式化输出）
├── config.py                # 配置中心：Key、模型(qwen-plus)、MCP 领域映射
├── mcp_client.py            # MCP 客户端管理器：高德(HTTP) + 酒店(stdio) 双服务单例
├── hotel_compare.py         # 酒店比价独立调用器（无需 DashScope Key）
├── prompts.py               # Planner Agent 系统提示词（含 image_url 提取要求）
├── render.py                # JSON 容错解析 + CLI/Web 渲染 + 景点图片获取 + PDF 生成
├── requirements.txt         # 主环境依赖（含 reportlab）
├── .env                     # 本地密钥（不入库）
├── .hotel-mcp/              # 酒店比价运行环境 venv（不入库）
├── agents/
│   └── planner.py           # Planner Agent：直接持有 MCP 工具（无嵌套子 Agent）
└── mcp_hotel_smart_book/    # 内置酒店比价 FastMCP 服务（search/calendar/advisor）
    ├── server.py
    ├── __init__.py / __main__.py
    └── README.md            # 原「酒店聪明订」服务文档
```

---

## 🏗️ 系统架构

```
┌──────────────────────────────────────────────────────────────┐
│                    Streamlit UI (app.py)                     │
│   功能模式：🧳 智能旅行规划  /  🏨 酒店比价                   │
│   渲染：天气卡片 / 每日行程 / 景点配图(真实照片) / PDF 导出    │
└───────────────┬──────────────────────────┬───────────────────┘
                │                          │
     ┌──────────▼──────────┐    ┌──────────▼──────────────────┐
     │ TripPlanner (直连)   │    │ hotel_compare.call_hotel_tool│
     │ create_agent        │    │ (独立比价，按次启动)          │
     │ Planner 直接持有    │    └──────────┬───────────────────┘
     │ 高德 MCP + 酒店工具  │               │ stdio (fastmcp)
     └──────────┬──────────┘    ┌──────────▼──────────────────┐
                │                │  .hotel-mcp 里的酒店比价服务
                │                │  mcp_hotel_smart_book/server.py
                │                └────────────────────────────────┘
  并行调用 MCP（LangGraph 自动并行多工具调用）
┌───────────────▼─────────────────────────────────────────┐
│            MultiServerMCPClient (langchain)              │
│  amap-server: https://mcp.amap.com/mcp?key=… (HTTP)     │
│  hotel-server: stdio → .hotel-mcp 子进程                  │
└──────────────────────────────────────────────────────────┘
```

**关键设计**

- 高德 MCP 走**高德开放平台官方服务** `https://mcp.amap.com/mcp?key=<高德Key>`（原阿里百炼 amap-maps 已下线）。认证方式为 URL 上的 `key`，不是 Bearer。
- 高德官方工具命名：`maps_weather`、`maps_text_search`、`maps_around_search`、`maps_search_detail`、`maps_geo`、`maps_direction_walking/driving/transit_integrated/bicycling` 等。路线工具为**坐标版**，规划前用 `maps_geo` 或 POI 返回的 `location` 转经纬度。
- 主环境 mcp SDK 固定为 **1.x**（`langchain-mcp-adapters` 依赖其 API），酒店服务用独立 `.hotel-mcp` 跑 fastmcp 4 + mcp 2，避免版本冲突。
- 领域工具过滤：先精确/前缀匹配，再关键字兜底，能兼容不同版本高德服务的工具命名差异。

---

## 🧩 核心模块

### config.py

- `DASHSCOPE_API_KEY`（LLM）与 `AMAP_MAPS_API_KEY`（高德 MCP）从 `.env` / 环境变量读取；仅 LLM Key 在导入时强校验。
- `tool_domains` 将工具分为 `poi / weather / route / hotel` 四组，`maps_geo` 归入 route 组供总控做地理编码。
- `map_mcp_url()`：自动为 `mcp.amap.com/mcp` 拼接 `?key=`，未配置高德 Key 时抛出明确中文提示。
- `create_llm()`：通义千问 `qwen-plus`（速度比 qwen3-max 快 2-3 倍，质量差距小），**`streaming=False`** 且 `max_tokens=8192`——实测流式下最终消息内容会丢失，非流式才能稳定拿到完整 JSON 行程。
- 内置两处 ChatTongyi 补丁：`subtract_client_response`（流式 tool_calls 缺 key 的 KeyError）与 `convert_message_to_dict`（回传历史时用已解析 `tool_calls` 重建 JSON 参数，避免 `function.arguments must be in JSON format` 400）。

### mcp_client.py

- 单例 `McpClientManager`，`MultiServerMCPClient` 同时挂载 `amap-server`（HTTP）与 `hotel-server`（stdio 子进程）。
- `_hotel_command()` 校验 `.hotel-mcp` 是否存在，缺失时提示重建命令。
- `get_tools_for(domain)` 前缀匹配 + 关键字兜底过滤。

### hotel_compare.py

- 独立于规划链路：不 import config，因此**酒店比价模式不要求任何 API Key**。
- 每次查询按需启动一次酒店 MCP stdio 子进程并返回结果文本。

### agents / prompts

- **单 Planner Agent**，去掉子 Agent 嵌套。Planner 直接持有全部高德 MCP 工具 + 酒店比价 `search/calendar/advisor` 工具，每步只有 1 次 LLM 往返（原架构 3 层嵌套约 3 次往返）。
- `prompts.py` 只有一个 `PLANNER_AGENT_PROMPT`，精简后约 1500 字（原 3000 字），明确要求：景点 `description` 写 2-3 句详细介绍、从 POI photos 数组提取 `image_url`、优先并行调用天气/景点/酒店。
- LangGraph `ToolNode` 自动并行执行多个并发工具调用。

### render.py / app.py

- `parse_plan()`：去掉代码块包裹 → 首尾大括号解析 → JSONDecoder 容错扫描，多级兜底。
- `attraction_photo(name, city)`：直接调高德 POI 搜索 REST API（不走 MCP），从返回的 photos 数组拿真实风景照片 URL。
- `attraction_map_image(location)`：高德静态地图底图 URL（无 markers，纯底图），用于景点照片兜底。
- `build_pdf(plan)`：reportlab 生成中文 PDF — 自动跨平台找中文字体（Windows 默认 simhei.ttf），封面页 + 天气表格 + 每日行程 + 预算高亮 + 酒店比价 + 页码页脚。
- 行程页面：天气卡片（带 msn.cn 链接）、每日行程 Tabs、景点卡片（真实风景照 → 兜底地图底图 + CSS 红点标记 → 纯文字）、餐饮、预算 Metrics、酒店比价、PDF 下载按钮。
- 出错时展开 `ExceptionGroup` 叶子错误并给出中文修复提示。

---

## 📡 数据流（旅行规划一次执行）

1. 用户点击「🚀 开始规划」，`TripPlanner.stream()` 初始化：加载全部高德工具 + 启动酒店比价子服务并缓存。
2. Planner Agent 直接调用 MCP 工具：
   - 首次回复并行发出 `maps_weather` + `maps_text_search(景点)` + `maps_text_search(酒店)` — LangGraph ToolNode 并行执行
   - `maps_geo` → 地址转经纬度 → `maps_direction_*` 规划 Day 首尾景点路线
   - 酒店比价 `search / calendar / advisor`（可选步骤）
3. 全部工具完成后模型输出**单个 JSON 计划**（含 `image_url` 从 POI photos 提取）。
4. `parse_plan` 解析 → 存入 `session_state` → `st.rerun()` → 渲染行程（景点真实照片）与 PDF 导出按钮。

---

## 🛠️ 常见问题排查

| 现象                                              | 原因与处理                                                                                          |
| ------------------------------------------------- | --------------------------------------------------------------------------------------------------- |
| 报错`请配置 DASHSCOPE_API_KEY`                  | `.env` 缺 LLM Key；补上后重启                                                                     |
| 报错`未配置高德地图 Key ... AMAP_MAPS_API_KEY`  | `.env` 缺高德 Web 服务 Key；补上后重启                                                            |
| `ExceptionGroup ... 401 Unauthorized`           | 旧版阿里百炼 MCP 已下线；已切换高德官方 MCP，请确认`.env` 使用 `AMAP_MAPS_API_KEY` 并重启       |
| `function.arguments ... must be in JSON format` | ChatTongyi 回传残缺 tool_call 片段；已内置补丁修复                                                  |
| 规划结束只剩引导语 / 结果为空                     | qwen3-max 流式丢内容或 JSON 解析失败；已切非流式 + 容错解析；仍失败时红框会显示真实原因             |
| 提示找不到`.hotel-mcp`                          | 未建酒店运行环境：`python -m venv .hotel-mcp && .hotel-mcp\Scripts\python -m pip install fastmcp` |
| pip 安装后被装上 mcp 2.x                          | `requirements.txt` 已固定 `mcp>=1.24,<2`；卸载后重装                                            |
| 端口被占用                                        | Streamlit 会自动换端口，或先`Ctrl+C` 旧实例                                                       |

> 每次修改 `.env` 或依赖后都需重启 `streamlit run app.py` 才能生效。

---

## 🔧 关键修复记录

1. 阿里百炼高德 MCP 下线 → 切换高德开放平台官方 MCP（`mcp.amap.com` + `?key=`），并补 `maps_geo`、坐标版路线提示词。
2. 子 Agent 提示词误教模型输出 `[TOOL_CALL:...]` 占位文本 → 重写为真实调用工具。
3. qwen3-max 流式最终内容丢失 → `streaming=False` + `max_tokens=8192`，`stream()` 补发最终消息。
4. ChatTongyi 历史回传 `function.arguments` 非 JSON → monkey-patch `convert_message_to_dict` 重建干净 tool_calls。
5. `langchain-mcp-adapters` 与 mcp 2.x 不兼容 → 主环境固定 mcp 1.x；酒店服务跑在独立 `.hotel-mcp` venv（fastmcp 4 + mcp 2）。
6. UI 原始 `ExceptionGroup` 堆栈不可读 → 展开叶子错误并显示中文修复提示。
7. 速度优化：去掉子 Agent 嵌套，Planner 直接持有 MCP 工具（每步从 3 次 LLM 往返降到 1 次）；换 `qwen-plus`（比 qwen3-max 快 2-3 倍）；精简 prompt 从 3000 字到 1500 字，引导首次回复并行发出天气+景点+酒店工具调用。
8. 景点真实配图：`render.attraction_photo()` 直接调高德 POI REST API 拿 photos[0].url；Prompt 要求 LLM 从 MCP 结果提取 `image_url`；UI 三级降级（真实照片 → 兜底高德查询 → 地图底图）。
9. PDF 导出：Markdown 下载改为 reportlab PDF（封面页 + 天气表格 + 每日行程 + 预算高亮 + 酒店比价 + 页码），自动跨平台发现中文字体。
10. Windows Streamlit 热加载缓存问题 → 推荐用 `--server.fileWatcherType poll` 启动。

---

## 📋 依赖说明

`requirements.txt`（主环境）：

```text
langchain
langchain-community
langchain-mcp-adapters
mcp>=1.24,<2
streamlit
python-dotenv
dashscope
reportlab
```

> `reportlab`（v5.0.1）用于 PDF 生成，自动跨平台发现系统中文字体（Windows 默认 simhei.ttf / 黑体）。

`.hotel-mcp` venv 内：`fastmcp`（自动携带 mcp 2.x）。
