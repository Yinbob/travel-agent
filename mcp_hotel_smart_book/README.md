# 🏨 酒店聪明订

多旅游平台数据直连的酒店比价与订房决策助手，帮你找到最便宜的酒店并告诉你该订还是再等等。

## ✨ 核心特性

▸ 多平台实时比价 — 飞猪+途牛+RG+同程4源实时对比，找到最低价
▸ 国际平台扩展（可选）— 检测到 `.hotelrate-mcp` 环境后，`search` / `advisor` 自动并入 **Agoda + Booking.com** 报价，全网最低可能落在国际平台
▸ 订房决策引擎 — 5维度综合判断（时机/性价比/平台价差/房型价值/临近降价），输出🟢订/🟡等/🔴观望信号
▸ 低价日历 — 一键扫描7-30天价格洼地，找到最便宜的入住日期
▸ 零配置即用 — 无需申请API Key，无需登录Cookie，配置即接入

> ⚠️ Agoda/Booking 演示模式（默认）返回**合成价**并带"演示数据"标记；真实比价需
> 安装 Playwright 浏览器并设 `HOTELRATE_DEMO=false`（详见仓库根 README「步骤 4」）。

## 🛠 工具

### search
搜索城市酒店列表，合并飞猪和途牛结果并去重，附带订房建议。

▸ `city`（字符串，✅必填）：城市名，如"上海"、"北京"
▸ `check_in`（字符串，✅必填）：入住日期，格式YYYY-MM-DD
▸ `check_out`（字符串，✅必填）：离店日期，格式YYYY-MM-DD
▸ `keyword`（字符串，选填）：搜索关键词/地标，如"外滩"、"迪士尼"

### calendar
酒店低价日历，扫描多入住日期的酒店价格，找到价格洼地。

▸ `city`（字符串，✅必填）：城市名
▸ `keyword`（字符串，选填）：搜索关键词/地标
▸ `start_date`（字符串，✅必填）：起始入住日期，格式YYYY-MM-DD
▸ `nights`（整数，选填）：住几晚，默认1
▸ `days`（整数，选填）：扫描天数，最多30，默认14

### advisor
指定酒店多平台精确比价+订房决策建议，输出各平台价格对比（国内 4 源 + 可选 Agoda/Booking）和订/等信号。

▸ `hotel`（字符串，✅必填）：酒店名称，如"上海外滩华尔道夫"
▸ `city`（字符串，✅必填）：城市名
▸ `check_in`（字符串，✅必填）：入住日期，格式YYYY-MM-DD
▸ `check_out`（字符串，✅必填）：离店日期，格式YYYY-MM-DD

## 🌐 Agoda / Booking 扩展（可选，hotelrate-mcp）

`search` / `advisor` 返回前会探测 `.hotelrate-mcp` 运行环境：

- `advisor`：对查询的酒店补一次 `hotel_quote`（platforms=booking+agoda），把 **Booking / Agoda** 作为两个平台并进比价与"全网最低"判定。
- `search`：对价格最便宜的前 `HOTELRATE_SPOT_CHECK`（默认 2）家国内结果再做 Agoda/Booking 抽查，更便宜就以新行并入列表。
- `calendar`：不变（仍扫描国内飞猪源）。

相关文件：`hotelrate_source.py`（开关与降级）、`hotelrate_bridge.py`（子进程桥）。
配置（`travel-agent/.env`）：`HOTELRATE_MCP_ENABLED` / `HOTELRATE_DEMO`（默认 true=合成价）
/ `HOTELRATE_CURRENCY`（默认 CNY，非 CNY 按内置近似汇率折算）
/ `HOTELRATE_SPOT_CHECK` / `HOTELRATE_QUOTE_TIMEOUT`（默认 90s）。
环境不存在、未启用或查询失败时自动降级为纯国内平台结果。

## 📝 使用示例

▸ "上海7月1号到3号住哪便宜" → search
▸ "下周哪天住外滩最便宜" → calendar
▸ "华尔道夫现在订还是再等等" → advisor
▸ "北京五一酒店比价" → search
▸ "广州下周哪天住最划算" → calendar

## Server Config

```json
{
  "mcpServers": {
    "hotel-smart-book": {
      "command": "uvx",
      "args": ["mcp-hotel-smart-book"],
      "env": {
        "PROXY_TOKEN": ""
      }
    }
  }
}
```

## 环境变量

▸ `PROXY_TOKEN`（选填）：代理服务认证Token，不填使用内置默认值

## 说明

酒店价格实时变动，查询结果仅供参考，实际价格以预订页面为准。多源比价取实时数据，不同平台酒店信息可能存在延迟。订房建议基于行业通用规律和当前数据，不构成消费承诺。
