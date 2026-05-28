# Provider Interface Inventory

## 范围

这份文档记录当前 pipeline 实际使用的 provider / interface 面，重点服务于当前产品方向：

- 优先覆盖 A 股和国内市场基金
- 港股仅记录当前已实现或已明确缺失的部分
- 只描述代码当前真实行为，不描述未来规划态

## 外部 Provider 层

| 数据层 | 当前默认 | 外部接口 | Provider 内部 fallback | Routing fallback | 适用市场 | 备注 |
| --- | --- | --- | --- | --- | --- | --- |
| `holdings` | `--provider-mode eastmoney` 时使用 `eastmoney-fundmobapi` | Eastmoney FundMNewApi：`https://fundmobapi.eastmoney.com/FundMNewApi/FundMNInverstPosition` | `EastmoneyFundHoldingProvider` 在抓取失败时回退到 `MockDataProvider` | `holdings` routing 支持 `eastmoney`、`mock`、`real`；当前 `real` 实际解析到 `mock` | 国内公募基金 | 当前主链路中唯一真实的持仓源。 |
| `market_quotes` | 默认 routing primary 是 `eastmoney` | Eastmoney K 线行情接口：`https://push2his.eastmoney.com/api/qt/stock/kline/get` | `EastmoneyMarketDataProvider` 内部会对单只失败的 A 股报价回退到 Yahoo Chart；港股报价直接走 Yahoo | 可选 routing，目前设计为 `akshare -> eastmoney`；Eastmoney 内部仍可能继续回退到 Yahoo | 以 A 股为主；港股通过 Yahoo symbol 归一化支持 | 最终 payload provider 可能是 `eastmoney-market-quote`、`yahoo-chart` 或 `mixed-market-quote`。 |
| `valuation_snapshots` | CLI 默认走本地衍生的 `quote-derived`；当 `--valuation-source provider` 时走 `eastmoney` | Eastmoney 估值接口：`https://push2.eastmoney.com/api/qt/stock/get` | `EastmoneyValuationProvider` 内部没有额外 provider fallback | 可选 routing，目前是 `tushare -> eastmoney` | provider 模式仅支持 A 股 | `quote-derived` 不是外部接口，而是从 `market_quotes` 本地衍生。 |
| `financial_metrics` | 启用后默认 routing primary 是 `eastmoney` | Eastmoney 财务指标接口：`https://datacenter.eastmoney.com/securities/api/data/get` | `EastmoneyFinancialMetricsProvider` 内部没有额外 provider fallback | 可选 routing，目前是 `tushare -> eastmoney` | 仅支持 A 股 | 这是当前不充值条件下的结构化基本面主路径。 |
| `announcements` | 默认 routing primary 是 `cninfo` | CNINFO 公告查询 POST 接口：`https://www.cninfo.com.cn/new/hisAnnouncement/query`；CNINFO 静态文件基址：`https://static.cninfo.com.cn/` | `CNInfoAnnouncementProvider` 内部没有额外 provider fallback | routing 层已预留，但当前内建真实 provider 只有 `cninfo` | A 股 / 北交所这类 6 位国内证券代码 | 不覆盖港股公告。 |
| `news_evidence` | 默认 routing primary 是 `multi-source-news` | Google News RSS 搜索：`https://news.google.com/rss/search`；新浪财经滚动：`https://finance.sina.com.cn/roll/` | `MultiSourceNewsEvidenceProvider` 会容忍任一子 provider 失败，并保留其他来源结果 | routing 层支持 `multi-source-news`、`google-news-rss`、`sina-finance-roll`、`mock` | 混合；当前对国内叙事和部分港股新闻线索都可用 | 这是聚合 provider，不是简单的 primary/fallback 二选一。 |

## Routing 可选 Provider

这些是 routing 层当前内建识别的 provider 名称。

| 数据层 | 内建 provider 名称 | 当前推荐的国内路径 |
| --- | --- | --- |
| `holdings` | `eastmoney`、`mock`、`real` | `eastmoney` |
| `market_quotes` | `eastmoney`、`akshare`、`mock` | 默认 `eastmoney`；`akshare -> eastmoney` 仅作为可选实验路径 |
| `valuation_snapshots` | `eastmoney`、`tushare`、`mock` | 当前国内不充值场景推荐 `eastmoney` |
| `financial_metrics` | `eastmoney`、`tushare` | 当前国内不充值场景推荐 `eastmoney` |
| `announcements` | `cninfo`、`mock` | `cninfo` |
| `news_evidence` | `multi-source-news`、`google-news-rss`、`sina-finance-roll`、`mock` | `multi-source-news` |

## 本地衍生层

这些层属于端到端 pipeline 的一部分，但不是直接从外部 provider 抓回来的。

| 数据层 | 来源 | fallback 行为 | 备注 |
| --- | --- | --- | --- |
| `valuation_snapshots` 的 `quote-derived` 模式 | 由 `quote-derived-valuation` 从 `market_quotes` 构建 | 没有独立 fallback；质量跟随 `market_quotes` | 这是当前 CLI 默认估值模式，不依赖付费基本面。 |
| `announcement_evidence` | 从 `announcements` 元数据衍生 | 没有独立外部 fallback | V1 只分类公告元数据，不解析 PDF 正文。 |
| `derived_signals` | 从 market quotes、valuation snapshots、financial metrics、announcement evidence、news evidence 衍生 | 没有独立外部 fallback | provider layer 会披露输入是 mixed、fresh、partial 还是 mock。 |
| `provider-derived-evidence` / `provider-derived-signals` | 当 `base_intelligence_mode=provider-derived` 时，由 provider-backed 的 evidence / signal 层聚合生成 | 取决于上游 provider 层 | 这是 orchestration 行为，不是独立外部接口。 |

## 国内优先方案总结

在当前“国内股票优先、且不充值”的前提下，最实用的主栈是：

1. `holdings`：Eastmoney
2. `market_quotes`：Eastmoney，必要时内部回退到 Yahoo
3. `valuation_snapshots`：默认 `quote-derived`，如果显式要求 provider 模式则走 Eastmoney
4. `financial_metrics`：Eastmoney
5. `announcements`：CNINFO
6. `news_evidence`：`multi-source-news`，即 Google News RSS + 新浪财经滚动

当前已经准备好、但不是必须启用的“付费/实验型”路径是：

1. `market_quotes`：`akshare -> eastmoney`
2. `valuation_snapshots`：`tushare -> eastmoney`
3. `financial_metrics`：`tushare -> eastmoney`

## 信息源策略与扩展原则

当前项目后续的国内优先方向，不是单纯“再多接几个 provider”，而是优先增加真正独立的信息源。

1. 优先新增独立源，而不是同一上游的不同封装
2. 优先补新闻、公告、evidence 这类信息密度高的层，再补更多数值接口
3. 对不确定、冲突或覆盖不完整的真实信息，优先输出 `partial`、`conflicting`、`low-confidence`
4. 大模型如果引入，应该放在语义判断层，不应该放在原始取数层
5. `mock` 仍然保留，但目标是“最后兜底”，不是默认偏好的 fallback

这里要特别区分两类“多源”：

- 真正多源：来自不同新闻站、不同公告源、不同监管披露面
- 伪多源：只是不同 wrapper，但底层仍然都依赖 Eastmoney、Sina 或同一网页源

因此后续评估一个新 provider 时，应该先回答两个问题：

1. 它有没有带来新的独立信息？
2. 它是提升了 evidence 密度，还是只是换了一层抓取壳？

## 重要边界

- 目前只有 `market_quotes` 这一层存在重要的 provider 内部 fallback：Eastmoney 单只股票行情失败时可以按股票级别回退到 Yahoo。
- `news_evidence` 默认行为是聚合，不是简单 fallback。
- `valuation_snapshots` 目前有两种完全不同的模式：
  - `quote-derived`：从 quote context 本地衍生
  - `provider`：走 routing 外部 provider 路径
- 当前代码中，`holdings` 和部分基础 intelligence 层仍然可能出现 mock 或 fixture-backed 路径；这反映的是现状，不代表后续优先方向。
- 后续国内 source-expansion 切片的目标，是让更多真实源以 `partial` 或 `conflicting` 方式留在结果里，而不是一遇到不确定就回落成 mock 解释。
- 港股的公告、估值、财务指标覆盖仍然不完整，不属于当前国内优先方案的重点。
