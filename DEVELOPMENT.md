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
- **UI**：Dash 2.x + Plotly
- **資料來源**：FinMind → yfinance（後備）
- **快取**：SQLite（本機或 Docker volume）
- **測試**：pytest，覆蓋率 92%（58 個測試）

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
│   ├── engine.py        # 每日循環、費用計算、部位快照
│   ├── metrics.py       # MDD、Sharpe、勝率、獲利因子
│   └── models.py        # Action、Position、Trade、Metrics、BacktestResult
├── data/
│   ├── cache.py         # SQLite CacheManager，TTL 分型別設定
│   ├── finmind.py       # FinMind SDK wrapper，欄位正規化
│   ├── provider.py      # cache-first → FinMind → yfinance 回退
│   └── yfinance_src.py  # yfinance adapter，自動補 .TW 後綴
├── selection/
│   ├── filters/         # BaseFilter ABC + PriceFilter、VolumeFilter、PERatioFilter、VolatilityFilter
│   ├── manual.py        # ManualSelector（指定 ticker 清單）
│   ├── random_mode.py   # RandomSelector（隨機抽 n 檔）
│   └── semi_random.py   # SemiRandomSelector（過濾鏈 + 隨機抽）
├── strategy/
│   ├── base.py          # BaseStrategy ABC
│   └── dip_and_take_profit.py  # 逢跌加碼 + 止盈 + 強制平倉策略
├── ui/
│   ├── app.py           # Dash 進入點，use_pages=True
│   ├── components/
│   │   ├── charts.py    # portfolio_line_chart、candlestick_chart、stock_overlay_chart
│   │   └── tables.py    # strategy_metrics_rows、trades_table_rows
│   └── pages/
│       ├── home.py      # 路由 /，投資組合走勢 + 策略績效表
│       ├── strategy.py  # 路由 /strategy/<id>，各 ticker 績效
│       └── stock.py     # 路由 /stock/<id>/<ticker>，K 線 + 交易紀錄
├── tests/               # pytest 測試，58 個
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
- **InfiniteAverageV0**：無 max_hold_days、無 session-end 強制平倉；清空部位後依 `last_sell_price * (1 - dip_pct)` 判斷再進場，`avg_cost` 完全重設。

---

## 3. 開發流程

採用 **測試驅動開發（TDD）+ Subagent-Driven** 逐 task 實作，共 18 個 task。

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
58 passed in ~6s
整體覆蓋率：92%

backtest/engine.py     93%
backtest/metrics.py    96%
backtest/models.py    100%
data/cache.py          96%
data/finmind.py        73%   （FinMind SDK 本身無法 unit test 完整覆蓋）
data/provider.py       72%   （同上，部分路徑需真實 API）
data/yfinance_src.py   89%
selection/filters/*   62-100%
selection/manual.py   100%
selection/random_mode.py  100%
selection/semi_random.py   92%
strategy/*            100%
```

### 測試檔案對應

| 測試檔案 | 測試項目 | 數量 |
|---------|---------|------|
| `tests/backtest/test_models.py` | Action、Position、Trade、Metrics dataclass 欄位 | 5 |
| `tests/backtest/test_metrics.py` | 勝率、獲利因子、MDD、Sharpe、平均持有天數 | 6 |
| `tests/backtest/test_engine.py` | 買入記錄、手續費計算、日快照、metrics 產出 | 5 |
| `tests/data/test_cache.py` | OHLCV / fundamentals / ticker_list CRUD + TTL | 8 |
| `tests/data/test_finmind.py` | 欄位正規化、空資料回傳 | 4 |
| `tests/data/test_yfinance.py` | 欄位正規化、.TW 後綴、空資料 | 3 |
| `tests/data/test_provider.py` | cache hit、FinMind→yfinance fallback、cache miss | 5 |
| `tests/selection/test_filters.py` | PriceFilter、VolumeFilter、PERatioFilter、VolatilityFilter、鏈式過濾 | 6 |
| `tests/selection/test_modes.py` | ManualSelector、RandomSelector（n 上限）、SemiRandomSelector | 6 |
| `tests/strategy/test_base.py` | BaseStrategy 繼承、`on_session_end` 預設回 HOLD | 2 |
| `tests/strategy/test_dip_and_take_profit.py` | 初始買入、持倉穩定 HOLD、逢跌加碼、達上限不加碼、止盈、強制平倉 | 7 |
| `tests/test_smoke.py` | 所有層可正常 import | 1 |

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

- **UI 無資料注入介面**：`ui/pages/home.py` 的 `set_results()` 需在程式碼層呼叫，尚未有 web 表單觸發回測。
- **FinMind 覆蓋率較低**（73%）：SDK 本身的網路呼叫路徑不易在 unit test 完整覆蓋，需整合測試。
- **yfinance 備援無 fundamentals**：yfinance adapter 只實作 OHLCV；PE/PB 資料目前僅 FinMind 提供。
- **無認證機制**：服務直接暴露，不適合直接部署在公開網路。
