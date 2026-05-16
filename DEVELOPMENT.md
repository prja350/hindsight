# Hindsight — 開發文件

## 目錄

1. [專案簡介](#1-專案簡介)
2. [系統架構](#2-系統架構)
3. [開發流程](#3-開發流程)
4. [測試說明](#4-測試說明)
5. [啟動服務](#5-啟動服務)
6. [環境變數](#6-環境變數)
7. [已知限制](#7-已知限制)

---

## 1. 專案簡介

Hindsight 是台灣股票回測系統，支援自訂策略、多來源資料、SQLite 快取，以及 Dash 視覺化 UI。

- **語言**：Python 3.11+
- **UI**：Dash 4.x + Plotly
- **資料來源**：FinMind → yfinance（後備）+ 拆股回溯調整
- **快取**：SQLite（本機或 Docker volume），含 `quality_flag` 欄位
- **測試**：pytest，105 個測試

---

## 2. 系統架構

### 五層單體架構（依賴單向向下）

```
┌─────────────────────────────┐
│  ui/               第 5 層  │  Dash multi-page app（/, /strategy, /stock）
├─────────────────────────────┤
│  backtest/         第 4 層  │  BacktestEngine、MetricsCalculator
├─────────────────────────────┤
│  strategy/         第 3 層  │  BaseStrategy ABC、DipAndTakeProfitStrategy
├─────────────────────────────┤
│  selection/        第 2 層  │  Filter 鏈、Manual / Random / SemiRandom 選股
├─────────────────────────────┤
│  data/             第 1 層  │  CacheManager、FinMind adapter、yfinance adapter
└─────────────────────────────┘
```

### 目錄結構

```
hindsight/
├── backtest/
│   ├── engine.py        # 每日循環、TickerAssignment、PriceContext、splits_applied
│   ├── metrics.py       # MDD、Sharpe、勝率、獲利因子
│   └── models.py        # Action、Position、Trade、Metrics、TickerAssignment、
│                        # TickerState、PriceContext、DailySnapshot、TickerResult、
│                        # BacktestResult
├── data/
│   ├── cache.py         # SQLite CacheManager，含 quality_flag 欄位 + 向後相容 ALTER TABLE
│   ├── calendar.py      # XTAI 交易日 (pandas_market_calendars + fallback)
│   ├── calendar_fallback.py # 硬編 2024-2026 台灣假日
│   ├── finmind.py       # FinMind SDK wrapper，欄位正規化
│   ├── provider.py      # gap-fill: FinMind → yfinance → forward-fill；讀取時套用拆股
│   ├── quality.py       # detect_gaps() — 純函式，以 trading-day 序判斷缺漏
│   ├── splits.py        # 拆股表 (manual JSON + heuristic) + apply_splits()
│   ├── splits_manual.json # ticker → [{date, ratio, note}] 表
│   └── yfinance_src.py  # yfinance adapter，自動補 .TW 後綴
├── selection/
│   ├── filters/         # BaseFilter ABC + PriceFilter、VolumeFilter、PERatioFilter、VolatilityFilter
│   ├── manual.py        # ManualSelector（指定 ticker 清單）
│   ├── random_mode.py   # RandomSelector（隨機抽 n 檔）
│   └── semi_random.py   # SemiRandomSelector（過濾鏈 + 隨機抽）
├── strategy/
│   ├── base.py          # BaseStrategy ABC (PriceContext + TickerState)
│   ├── pnl.py           # net_unrealized_pct/value (sell fee + tax aware)
│   ├── dip_and_take_profit.py  # 逢跌加碼 + 止盈 + 強制平倉策略
│   └── infinite_average_v0.py  # 無限攤平：last_sell_price 再進場、avg_cost 重設
├── ui/
│   ├── app.py           # Dash 進入點，use_pages=True
│   ├── components/
│   │   ├── charts.py    # portfolio_3line_chart、normalized_price_chart、candlestick_chart
│   │   └── tables.py    # per_ticker_rows (含 split_adj 欄)、trades_table_rows、STRATEGY_LABEL
│   └── pages/
│       ├── home.py      # 路由 /，wizard + 3-line 總資產 + per-ticker 表 (含拆股調整欄)
│       ├── strategy.py  # 路由 /strategy/<class>，normalized overlay + 該策略各 ticker 績效
│       └── stock.py     # 路由 /stock/<class>/<ticker>，K 線 + 累計投入 + 拆股⚠ banner + 交易紀錄
├── tests/               # pytest 測試，105 個
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

### 關鍵設計決策

| 主題 | 決策 |
|------|------|
| 快取 TTL | ohlcv = 永久；fundamentals = 7 天；ticker_list = 30 天 |
| SQLite upsert | DELETE 日期範圍 + `to_sql(if_exists='append')` |
| 台灣手續費 | 買 0.1425%、賣 0.1425% + 證交稅 0.3% |
| Sharpe 計算 | 日報酬率，樣本變異數（ddof=1），×√252 年化 |
| 初始買入信號 | `position=None` 時策略回傳 BUY；engine 計算 `shares = floor(amount / price)` |
| 加碼均價 | `avg_cost = total_invested / total_shares` |

### v2 設計重點

- **每檔指派**：`BacktestEngine.run(assignments: list[TickerAssignment])` — 每檔 ticker 各自設定 strategy class + params。
- **共用資金池**：整個回測共享單一 cash float，跨 ticker 競爭資金。
- **執行價**：`close | open | vwap`，整輪回測統一設定一次。
- **淨未實現損益**：`(shares × price × (1-sell_fee-tax)) − total_invested`。策略觸發與 UI 顯示皆採此公式。
- **資料品質**：`quality_flag ∈ {clean, yfinance, forward_filled}`；forward_filled 列每次讀取都重試。
- **路由**：`/`、`/strategy/<class>`、`/stock/<class>/<ticker>`；`<class>` 採英文識別碼避免 URL encode 問題。
- **InfiniteAverageV0**：無 max_hold_days、無 session-end 強制平倉；**出場後隔天無條件再進場** (移除原 `last_sell_price * (1 - dip_pct)` 價格 gate)，`avg_cost` 完全重設。`TickerState.last_sell_price` 仍由 engine 記錄但策略不再讀取。
- **拆股回溯調整**：`data/splits.py` 混合 manual JSON (`data/splits_manual.json`) + heuristic (consecutive close ratio outside `[1/1.5, 1.5]`)。manual 優先，heuristic ±3 天內被吃掉。`DataProvider.get_ohlcv()` 每次讀取套用 (cache 仍存 raw，新增 split 條目不需 invalidate)。`TickerResult.splits_applied` 帶 `[{date, ratio, source}]` 到 UI。
- **UI 拆股註記**：Home per-ticker 表「拆股調整」欄顯示 `⚠ N`；Stock 頁面頂部 ⚠ banner 列出每筆 split (date, ratio, source)。

### 已知資料品質限制

- FinMind 自身**不做**回溯調整 — 拆股前後資料價格不連續，需依賴 `splits.py` 修正。
- FinMind 拆股 API (`taiwan_stock_split_price`) 為付費版，免費 token 拿不到正規拆股表。
- yfinance Taiwan ETF 拆股資訊不完整 (`Ticker(...).splits` 對 00631L 等回傳空)。
- 故 v2 採 manual JSON 為主、heuristic 為輔；遇到新拆股事件需人工加進 `data/splits_manual.json`。
- yfinance 與 FinMind 對部分 ETF 的價格 feed 不一致 (例如 00631L)：填補 gap 時若兩源混用會殘留尺度差異，建議遇到此類 ticker 將 manual 表覆蓋對應日期。

---

## 3. 開發流程

採用 **測試驅動開發（TDD）+ Subagent-Driven** 逐 task 實作。
v1：18 個 task；v2：16 個 task + 拆股回溯調整 patch。

### 開發步驟（每個 task）

1. **寫失敗測試**（RED）
2. **執行測試確認失敗**
3. **最小化實作**（GREEN）
4. **執行測試確認通過**
5. **雙重審查**：spec reviewer（是否符合設計規格）+ code quality reviewer
6. **Commit**

### Git 提交歷程

```
6224cf6  chore: Dockerfile + docker-compose
60ffe0d  feat: stock page — candlestick chart + trades table; smoke test
f3afbe0  feat: strategy page — per-ticker metrics table
3796089  feat: home page — portfolio line chart + strategy metrics table
d3b6720  fix: resolve pages_folder as absolute path
44e653d  feat: Dash app entry + chart/table helper components
1ba8f67  feat: BacktestEngine — daily loop, fee/tax, portfolio snapshots
6f40e09  feat: MetricsCalculator (MDD, Sharpe, WinRate, ProfitFactor, AvgHoldDays)
2a97e0a  feat: DipAndTakeProfitStrategy
7c79d73  feat: BaseStrategy ABC
f9f2c06  feat: SemiRandomSelector with pluggable filter chain
87419e5  feat: ManualSelector + RandomSelector, SelectionResult dataclass
f25c415  feat: BaseFilter ABC + 4 concrete filters
c5bc3ec  feat: DataProvider with cache-first + FinMind→yfinance fallback
b0bd8e9  feat: yfinance adapter
677d998  feat: FinMind adapter with normalized output
693e19f  fix: guard save_* against empty DataFrame (cache poisoning)
5a1b2ee  feat: SQLite CacheManager with TTL
3336b81  feat: core dataclasses
```

### 開發中修復的 Bug

| Bug | 現象 | 修法 |
|-----|------|------|
| `save_*` 空 DataFrame | 空 DF 導致 `date.min()` = NaN → DELETE 不匹配任何列，但 metadata 仍標記為 fresh（靜默快取污染） | 所有 `save_*` 函式開頭加 `if df.empty: return` |
| FinMind fake token crash | 測試用假 token 導致建構 adapter 時丟例外 | `login_by_token` 包入 try/except |
| yfinance 無名稱 DatetimeIndex | mock 回傳無名 DatetimeIndex → `reset_index()` 產生欄位名 `'index'` 而非 `'Date'` | 在 `reset_index()` 前設 `raw.index.name = 'Date'` |
| DipAndTakeProfit 測試矛盾 | `open_position.total_invested=100_000` 等於 `max_position`，導致「應加碼」與「不應加碼」測試同時拿到相同 fixture | 把 fixture 的 `total_invested` 改為 `50_000`；max-position 測試自行建 100k position |
| Dash `pages_folder` 路徑 | Dash 從 `flask.helpers.get_root_path(__name__)` 解析相對路徑 → 在 `ui/` 下找，找不到 pages | 改成絕對路徑：`Path(__file__).parent.parent / "ui" / "pages"` |

---

## 4. 測試說明

### 執行測試

```bash
# 執行所有測試 + 覆蓋率報告
python3 -m pytest --cov=. --cov-report=term-missing -q
```

### 測試結果

```
105 passed
```

### 測試檔案對應

| 測試檔案 | 測試項目 |
|---------|---------|
| `tests/backtest/test_models.py` | v2 dataclasses：Action、Position、Trade、Metrics、TickerAssignment、TickerState、PriceContext、DailySnapshot、TickerResult、BacktestResult |
| `tests/backtest/test_metrics.py` | 勝率、獲利因子、MDD、Sharpe、平均持有天數 |
| `tests/backtest/test_engine_v2.py` | per-ticker assignments、execution_price、cash/pos snapshots、shared capital、InfiniteAverageV0 re-entry |
| `tests/data/test_calendar.py` | XTAI 交易日 + 硬編 fallback |
| `tests/data/test_quality.py` | detect_gaps 純函式 |
| `tests/data/test_cache.py` | OHLCV CRUD + TTL + `quality_flag` 欄位 + ALTER TABLE 向後相容 |
| `tests/data/test_finmind.py` | 欄位正規化、空資料 |
| `tests/data/test_yfinance.py` | 欄位正規化、.TW 後綴 |
| `tests/data/test_provider.py` | cache hit、gap-fill 鏈、forward_fill、UNIQUE PK regression |
| `tests/data/test_splits.py` | manual JSON + heuristic + apply_splits 計算、merged 優先序 |
| `tests/selection/test_filters.py` | PriceFilter、VolumeFilter、PERatioFilter、VolatilityFilter |
| `tests/selection/test_modes.py` | Manual / Random / Semi 選股 |
| `tests/strategy/test_base.py` | BaseStrategy ABC、`on_session_end` 預設 HOLD |
| `tests/strategy/test_pnl.py` | net_unrealized_pct/value (fee + tax aware) |
| `tests/strategy/test_dip_and_take_profit.py` | 初買、加碼、止盈、強制平倉、達部位上限 |
| `tests/strategy/test_infinite_average_v0.py` | 初買、無 last_sell 持有、再進場條件、加碼、止盈、session-end HOLD |
| `tests/ui/test_charts.py` | 3-line portfolio、normalized overlay、candlestick + invested overlay |
| `tests/ui/test_home_layout.py` | initial-capital / exec-price / 預設日期 |
| `tests/test_smoke.py` | 所有層可正常 import |
| `tests/test_smoke_v2.py` | 2 ticker × 2 strategy 端對端 |

### 只跑單一模組

```bash
python3 -m pytest tests/backtest/ -v
python3 -m pytest tests/data/ -v
python3 -m pytest tests/strategy/ -v
```

---

## 5. 啟動服務

### 方法一：本機直接啟動

```bash
# 安裝依賴
pip install -r requirements.txt

# 設定環境變數（選填，沒有就只用 yfinance）
export FINMIND_TOKEN=your_token_here
export CACHE_DIR=data/db

# 啟動
python3 -m ui.app
```

瀏覽器開啟 http://localhost:8050

---

### 方法二：Docker（建議用於部署）

```bash
# 建置 image
docker build -t hindsight .

# 啟動容器（SQLite 資料持久化到本機 ./data/db）
docker run -p 8050:8050 \
  -v $(pwd)/data/db:/app/data/db \
  -e FINMIND_TOKEN=your_token_here \
  hindsight
```

瀏覽器開啟 http://localhost:8050

---

### 方法三：Docker Compose

```bash
# 複製並填入 token
echo "FINMIND_TOKEN=your_token_here" > .env

# 啟動
docker compose up

# 背景執行
docker compose up -d

# 停止
docker compose down
```

---

### 容器煙霧測試（驗證 image 正確）

```bash
docker run --rm hindsight python3 -c "
from data.provider import DataProvider
from backtest.engine import BacktestEngine
print('container OK')
"
```

---

## 6. 環境變數

| 變數 | 說明 | 預設值 |
|------|------|--------|
| `FINMIND_TOKEN` | FinMind API token（無則退回 yfinance） | 空字串 |
| `CACHE_DIR` | SQLite 資料庫目錄 | `data/db` |
| `PORT` | Dash server 監聽埠 | `8050` |

---

## 7. 已知限制

- **FinMind 覆蓋率較低**：SDK 本身的網路呼叫路徑不易在 unit test 完整覆蓋，需整合測試。
- **yfinance 備援無 fundamentals**：yfinance adapter 只實作 OHLCV；PE/PB 資料目前僅 FinMind 提供。
- **無認證機制**：服務直接暴露，不適合直接部署在公開網路。
- **拆股表需人工維護**：FinMind 拆股 API 為付費版；yfinance 對 Taiwan ETF 拆股不完整。遇到新拆股事件需編輯 `data/splits_manual.json`。Heuristic 偵測 (close ratio 變化 ≥ 50%) 為輔，可能誤判真實大跌；建議將確認過的事件升級為 manual 條目。
- **多源價格 feed 不一致**：FinMind 與 yfinance 對部分 ETF (例如 00631L) 提供完全不同尺度的價格序列，gap-fill 時混用會產生不連續資料。建議該類 ticker 在 manual 表覆蓋對應日期。
- **快取無自動失效**：拆股調整在讀取時套用，cache 仍存 raw，所以新增 split 條目會自動生效；但 ticker 重新命名 / 下市等罕見事件目前無清理機制。
