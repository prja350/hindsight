# Hindsight v2 — 台股交易回測系統設計文件（升級版）

**日期：** 2026-05-13
**狀態：** 已批准，待實作
**前一版：** [`2026-05-12-taiwan-stock-backtest-design.md`](2026-05-12-taiwan-stock-backtest-design.md)

---

## 1. 概覽

Hindsight v2 在 v1 之上做增量升級，主要新增：
- 每檔股票指派獨立策略 + 獨立參數（取代 v1 的單策略全套用）
- 共享資金池（一個 backtest run 跨所有 ticker 共用現金）
- 新策略「無限攤平_V0」：賣完後可自動再進場
- 缺漏資料自動偵測 + yfinance fallback + forward-fill
- 可設定執行價（close / open / vwap）
- 主頁三線圖（cash / position_value / total）
- 策略類別頁的標準化股價疊加圖
- K 線頁的累計投入折線疊圖 + 不同色買賣標註
- 未實現損益估算扣除手續費 + 稅

v1 的策略比較（多策略並排）概念**取消**，改為每 ticker 一列的混合策略結果視圖。

---

## 2. 變更需求對照表

| # | 需求                                | 章節                    |
| - | ---------------------------------- | ----------------------- |
| 1 | 日期 default 2026-01-01 → today    | §7.1 UI 全域            |
| 2 | 可設定本金（共享資金池）             | §7.1、§6.2              |
| 3 | 每檔股票指派一個策略 + 獨立參數        | §6、§7.2 Step 3         |
| 4 | 總資產三線圖（cash / pos / total）   | §7.3 主頁               |
| 5 | K 線買賣標註與 candle 顏色區分        | §7.5 Stock 頁            |
| 6 | 執行價可設定(close / open / vwap)    | §5、§6.4、§7.1          |
| 7 | K 線疊加累計投入折線                  | §7.5 Stock 頁            |
| 8 | 缺漏資料偵測 + 修復                   | §5.2                    |
| 9 | FinMind 優先 + cache                | §5.4 TTL                |
| 10 | 策略類別頁的所有 ticker 疊加股價圖    | §7.4 Strategy Class 頁   |
| 11 | 未實現損益扣除費用                    | §6.5、§4.3 helper        |
| 12 | 無限攤平_V0 策略                     | §4.4                    |

---

## 3. 架構決策 — 為什麼 Option A

評估三方案後選 **Option A：微改 v1 engine**：

- v1 `BacktestEngine.run()` 內部 `cash` 已是跨所有 ticker 共享的 local float — 共享資金池其實 v1 就有
- 真正差異在：per-ticker strategy assignment、snapshot 拆 cash/pos、`last_sell_price` 狀態給再進場、執行價可選
- v1 主迴圈骨架保留 ≥70%
- 拒絕 Option B（Portfolio 抽象）= YAGNI；拒絕 Option C（MetaStrategy 包裝）= 隱藏 per-ticker 語意

---

## 4. Strategy Layer

### 4.1 BaseStrategy ABC（更新）

```python
@dataclass
class Action:
    type: Literal["BUY", "SELL", "HOLD"]
    amount: float = 0.0  # BUY: 買入金額(元); SELL: 0 = 全賣

@dataclass
class PriceContext:
    date: date
    open: float
    close: float
    vwap: float
    price: float                     # = open/close/vwap，依 execution_price 選擇
    quality_flag: Literal["clean", "yfinance", "forward_filled"]

@dataclass
class TickerState:
    position: Position | None
    last_sell_price: float | None

class BaseStrategy(ABC):
    @abstractmethod
    def on_price_update(self, ctx: PriceContext, state: TickerState) -> Action: ...

    def on_session_end(self, state: TickerState) -> Action:
        return Action(type="HOLD")
```

### 4.2 Helper — strategy/pnl.py

```python
BUY_FEE_RATE  = 0.001425
SELL_FEE_RATE = 0.001425
SELL_TAX_RATE = 0.003

def net_unrealized_pct(state: TickerState, price: float) -> float:
    """若今天以 price 賣出，淨損益率 (扣手續費+稅)。無持倉回傳 0。"""
    pos = state.position
    if pos is None or pos.total_invested <= 0:
        return 0.0
    gross = pos.shares * price * (1 - SELL_FEE_RATE - SELL_TAX_RATE)
    return (gross - pos.total_invested) / pos.total_invested
```

### 4.3 DipAndTakeProfitStrategy（升級）

參數：`dip_pct`、`take_profit_pct`、`add_amount`、`max_position`、`max_hold_days`

決策表：

| 狀態                                                                                | Action          |
| ----------------------------------------------------------------------------------- | --------------- |
| `state.position is None`                                                            | BUY `add_amount` |
| `net_pnl_pct < -dip_pct` 且 `total_invested + add_amount ≤ max_position`             | BUY `add_amount` |
| `net_pnl_pct ≥ take_profit_pct`                                                     | SELL all        |
| `(ctx.date - position.entry_date).days ≥ max_hold_days`                              | SELL all        |
| 其他                                                                                 | HOLD            |

對 v1 差：止盈門檻改用 `net_unrealized_pct`（含費用估算）；價格欄位來自 `ctx.price`。

### 4.4 InfiniteAverageV0Strategy（新）

`strategy/infinite_average_v0.py`

參數：

| 名稱               | Default | 說明                              |
| ------------------ | ------- | -------------------------------- |
| `dip_pct`          | 0.05    | 加碼門檻 + 再進場跌幅門檻         |
| `take_profit_pct`  | 0.05    | 止盈門檻（net pnl）               |
| `add_amount`       | 10000   | 單次加碼金額（元）                 |
| `max_position`     | 100000  | 單股 total_invested 上限          |

決策表：

| 狀態                                                                                                          | Action            |
| ------------------------------------------------------------------------------------------------------------ | ----------------- |
| `position is None` 且 `last_sell_price is None`（首次進場）                                                   | BUY `add_amount`  |
| `position is None` 且 `ctx.price ≤ last_sell_price × (1 - dip_pct)`                                          | BUY `add_amount`（avg_cost 重置）|
| `position` 存在 且 `net_pnl_pct < -dip_pct` 且 `total_invested + add_amount ≤ max_position`                    | BUY `add_amount`  |
| `position` 存在 且 `total_invested + add_amount > max_position`                                                | HOLD              |
| `position` 存在 且 `net_pnl_pct ≥ take_profit_pct`                                                            | SELL all          |
| `on_session_end`                                                                                              | HOLD（不強平）     |

與 DipAndTakeProfit 差異：
1. 無 `max_hold_days`
2. 賣完不停 — 跌 `dip_pct` 自動再進場
3. 再進場時 `avg_cost = 新進場價`（不繼承上一輪）

---

## 5. Data Layer

### 5.1 介面（不變）

```python
class DataProvider:
    def get_ohlcv(self, ticker: str, start: date, end: date) -> pd.DataFrame
    def get_fundamentals(self, ticker: str, start: date, end: date) -> pd.DataFrame
    def get_ticker_list(self) -> pd.DataFrame
```

`get_ohlcv` 回傳欄位：`[date, open, high, low, close, volume, quality_flag]`

### 5.2 缺漏偵測 + 修復流程（item 8）

```
1. expected_days ← trading_calendar(start, end)
2. cached_df ← cache.get_ohlcv(ticker, start, end)
3. missing ← expected_days − cached_df.dates
4. if missing == ∅: return cached_df
5. for each contiguous gap [s, e] in missing:
   a. finmind.fetch_ohlcv(s, e) → 命中日子 quality_flag='clean'
   b. 仍缺日子 yfinance.fetch_ohlcv(s, e) → 命中 quality_flag='yfinance'
   c. 仍缺日子 forward-fill 前一個 clean/yfinance 的 close，volume=0，quality_flag='forward_filled'
6. cache.upsert(完整 df)，return
```

### 5.3 Trading calendar

主：`pandas_market_calendars` 之 `XTAI`。
備：`data/calendar_fallback.py` weekday + 台股例假日 hardcode list（若主套件 import 失敗）。

新模組 `data/quality.py`：
```python
def detect_gaps(df: pd.DataFrame, expected: list[date]) -> list[tuple[date, date]]:
    """純函式，可單測。"""
```

### 5.4 Cache 設計

SQLite schema：

```sql
ALTER TABLE ohlcv ADD COLUMN quality_flag TEXT NOT NULL DEFAULT 'clean';
ALTER TABLE cache_meta ADD COLUMN has_gaps INTEGER DEFAULT 0;
```

TTL：

| 資料                  | TTL                                             |
| -------------------- | ----------------------------------------------- |
| OHLCV clean（>5 日前） | 永久                                            |
| OHLCV 近 5 日         | 每日重拉                                        |
| OHLCV yfinance       | 7 日後重試 finmind（升級成 clean 就 update）     |
| OHLCV forward_filled | 每次取資料都重試（拿到真值就 update）             |
| Fundamentals          | 7 日                                            |
| Ticker list           | 30 日                                           |

### 5.5 Token 管理（不變）

FinMind token 從 `FINMIND_TOKEN` 環境變數讀；缺則降級純 yfinance；rate-limit 指數退避（v1 機制保留）。

---

## 6. Backtest Engine

### 6.1 介面變更

```python
class BacktestEngine:
    def __init__(self, provider: DataProvider) -> None: ...

    def run(self,
            assignments: list[TickerAssignment],
            start: date, end: date,
            initial_capital: float,
            execution_price: Literal["close", "open", "vwap"] = "close",
            ) -> BacktestResult: ...
```

`TickerAssignment` 定義見 §8.2。

### 6.2 主迴圈（pseudo）

```
cash = initial_capital
ticker_states = {a.ticker: TickerState(None, None) for a in assignments}
strategies   = {a.ticker: build_strategy(a.strategy_class, a.params) for a in assignments}
ohlcv_map    = {a.ticker: provider.get_ohlcv(a.ticker, start, end) for a in assignments}

for dt in sorted_trading_days(ohlcv_map):
    for ticker, df in ohlcv_map.items():
        row = df.row(dt)                       # 缺則 continue
        ctx = PriceContext(dt, row.open, row.close, row.vwap,
                           price=row[execution_price], quality_flag=row.quality_flag)
        state = ticker_states[ticker]
        action = strategies[ticker].on_price_update(ctx, state)

        if action.type == "BUY" and action.amount > 0:
            shares = floor(action.amount / ctx.price)
            cost = shares * ctx.price
            fee = round(cost * BUY_FEE_RATE)
            if cost + fee > cash: continue
            cash -= cost + fee
            if state.position is None:
                state.position = Position(ticker, shares, ctx.price, dt, cost + fee)
            else:
                # 同 v1：加權平均 avg_cost
                ...
            state.last_sell_price = None       # 新一輪買進後清除
            record Trade

        elif action.type == "SELL" and state.position is not None:
            proceeds = state.position.shares * ctx.price
            fee = round(proceeds * SELL_FEE_RATE)
            tax = round(proceeds * SELL_TAX_RATE)
            cash += proceeds - fee - tax
            realized = (proceeds - fee - tax) - state.position.total_invested
            state.last_sell_price = ctx.price  # 給再進場判斷
            state.position = None
            record Trade

    # daily snapshot
    pos_value = Σ shares × today_price for all states
    daily_snapshots.append(DailySnapshot(dt, cash, pos_value))

# session end
for ticker, state in ticker_states.items():
    strategies[ticker].on_session_end(state)   # 預設 HOLD
```

### 6.3 Per-ticker 指標
`MetricsCalculator` 介面不變。Engine 跑完後對每 ticker 子集呼叫一次，得到 `TickerResult.metrics`；全 portfolio 不另外計算，因為主視圖是 per-ticker。

### 6.4 執行價
`execution_price` 一旦設定，全 run 套用所有 ticker、所有交易、所有未實現估算。

### 6.5 未實現估算精度（item 11）
策略內判斷止盈/止損都呼叫 `pnl.net_unrealized_pct()`（扣手續費 + 稅）；
UI 顯示「未實現損益」欄位也用同一公式。
Engine 在 trade 落地時用實際 fee/tax 計算 `realized_pnl`，與估算分離。

---

## 7. UI

### 7.1 全域變更

- 日期 default：`start='2026-01-01'`、`end=date.today().isoformat()`
- Step 2 新增欄位：
  - `initial_capital`（number，default 500000）
  - `execution_price` dropdown（close / open / vwap，default close）

### 7.2 Step 3 — 動態 per-ticker 指派（item 3）

行為依 Step 1 模式：

| 模式      | Step 3                                                                                       |
| -------- | -------------------------------------------------------------------------------------------- |
| Manual   | 解析 Step 2 ticker list 後動態渲染：每 ticker 一行 `[ticker] [strategy dropdown] [params]`     |
| Random   | 抽中 ticker 未知 → 單一策略表單（default `infinite_average_v0`），所有抽中 ticker 共用同一策略 |
| Semi     | 同 Random                                                                                    |

Dash 元件：
- 容器 `html.Div(id='strategy-assignments')`
- Callback `Output('strategy-assignments', 'children')` ← `Input('tickers-input', 'value'), Input('mode-radio', 'value')`
- Manual：迭代 ticker list 生成 row（用 pattern-matching id `{'type': 'strat-select', 'idx': i}`）
- Random/Semi：單一 row（idx=0）

Strategy dropdown：
```
[
  {'label': '逢跌加碼止盈', 'value': 'dip_and_take_profit'},
  {'label': '無限攤平_V0',  'value': 'infinite_average_v0'},
]
```

Params 區塊用第二個 callback 依 strategy_class 切換欄位集合。

Run callback 蒐集 `State({'type': 'strat-select', 'idx': ALL}, 'value')` + 對應 params，組成 `list[TickerAssignment]` 傳給 engine。

### 7.3 主頁結果區（item 4）

**Chart**：`portfolio_3line_chart(snapshots)`
- 三條 Plotly trace：cash（綠）/ position_value（藍）/ total（粗黑）
- hover：日期 + 三值
- secondary y-axis 不用，三者同單位

**DataTable** — 每 ticker 一列：

| 欄位 | id            | 內容                                                          |
| --- | -------------- | ------------------------------------------------------------- |
| 標的 | `ticker`       | markdown `[<ticker>](/stock/<class>/<ticker>)`                |
| 策略 | `strategy`     | markdown `[<中文 label>](/strategy/<class>)`                  |
| 已實現損益 | `realized_pnl` | `${m.realized_pnl:+,.0f}`                                 |
| 未實現損益 | `unrealized_pnl` | `${m.unrealized_pnl:+,.0f}`（net of fees）              |
| MDD       | `mdd`        | `{m.max_drawdown:.1%}`                                       |
| Sharpe    | `sharpe`     | `{m.sharpe_ratio:.2f}`                                       |
| Win Rate  | `win_rate`   | `{m.win_rate:.0%}`                                           |
| Profit Factor | `profit_factor` | `{m.profit_factor:.2f}`                                |
| Avg Hold (days) | `avg_hold_days` | `{m.avg_hold_days:.0f}d`                              |

### 7.4 Strategy Class 頁 — `/strategy/<class>` (item 10)

`<class>` 是英文 strategy_class（避免中文 URL encode 問題）。

組件：
- 回首頁連結
- H2 顯示中文 label（用英文 class lookup mapping）
- **疊加股價折線圖** `normalized_price_chart(ohlcv_map)`：
  - 對每 ticker 第一個交易日 close = 1.0 為基準作 normalize
  - 多色線同圖，hover 顯示日期 + 各 ticker 標準化值
- **DataTable** — 每 ticker 一列：標的（markdown link 到 stock 頁）/ 交易次數 / 已實現損益 / Win Rate

### 7.5 Stock 頁 — `/stock/<class>/<ticker>` (item 5、7)

**K 線圖**：
- Candle：紅漲綠跌（台股慣例，與 v1 同）
- 買入標註：藍色 ▲（與漲綠 distinct）
- 加碼標註：淺藍 ▲（虛邊框）
- 賣出標註：橘色 ▼（與跌紅 distinct）
- forward_filled 區段：背景淡灰陰影（vrect annotation）

**Position size 折線圖**：
- 與 K 線同圖 subplot 或 secondary_y（兩種都可，採 subplot 較清晰）
- 內容：`total_invested` 累計值
- SELL 完成 → drop 回 0；新一輪買入後重新累計

**Trades table**：欄位同 v1（日期/動作/股數/成交價/成交金額/手續費+稅/已實現損益），加 hold_days 欄位顯示持倉天數。

### 7.6 URL 路徑

```
/                                主頁
/strategy/<class>                 策略類別頁
/stock/<class>/<ticker>           個股頁
```

`<class>` ∈ `{dip_and_take_profit, infinite_average_v0}`。

Dash 註冊：用 `path_template=` 不是 `path=`（v1 已修，繼續沿用）。
Layout 不需 `urllib.unquote()`，因為英文 class 與數字 ticker 不會 URL-encode。

---

## 8. Models / Dataclasses

### 8.1 既有更新

```python
@dataclass
class Position:
    ticker: str
    shares: int
    avg_cost: float
    entry_date: date
    total_invested: float  # 含買進手續費

@dataclass
class Trade:
    ticker: str
    action: Literal["BUY", "SELL"]
    date: date
    price: float          # 用 execution_price
    shares: int
    amount: float
    fee: float
    tax: float
    realized_pnl: float | None = None
    hold_days: int | None = None
```

### 8.2 新 dataclasses

```python
@dataclass
class TickerAssignment:
    ticker: str
    strategy_class: str           # "dip_and_take_profit" | "infinite_average_v0"
    params: dict[str, float]

@dataclass
class TickerState:
    position: Position | None
    last_sell_price: float | None

@dataclass
class PriceContext:
    date: date
    open: float
    close: float
    vwap: float
    price: float                   # 結算用，依 execution_price
    quality_flag: Literal["clean", "yfinance", "forward_filled"]

@dataclass
class DailySnapshot:
    date: date
    cash: float
    position_value: float
    @property
    def total(self) -> float: return self.cash + self.position_value

@dataclass
class TickerResult:
    ticker: str
    strategy_class: str
    params: dict[str, float]
    trades: list[Trade]
    metrics: Metrics
    final_position: Position | None

@dataclass
class BacktestResult:
    initial_capital: float
    execution_price: str
    start: date
    end: date
    ticker_results: list[TickerResult]
    daily_snapshots: list[DailySnapshot]
    final_cash: float
```

### 8.3 移除
- v1 `BacktestResult.strategy_name`、`BacktestResult.trades`、`BacktestResult.daily_snapshots` (tuple 形式) — 改為 v2 結構

---

## 9. 測試策略

| 層           | 重點                                                                                     |
| ----------- | --------------------------------------------------------------------------------------- |
| Data        | trading calendar gap detection；finmind → yfinance → forward_fill 三段 fallback；TTL 重抓 |
| Strategy    | DipAndTakeProfit 各條件；InfiniteAverageV0 首次/再進場/上限/止盈各分支；`net_unrealized_pct` 公式 |
| Engine      | 共享資金池扣款不足；per-ticker state 隔離；execution_price 切換；新一輪 avg_cost 重置             |
| Metrics     | Per-ticker 指標獨立性                                                                    |
| UI         | Manual 模式 Step 3 動態生成 N 行；Run callback 收集 N 組 assignment；strategy class 路由        |

維持 v1 ≥80% 覆蓋率目標。

---

## 10. 不在 v2 範圍

- 多 backtest run 比較（v1 概念取消）
- 手續費折扣參數
- 進階指標（Sortino、Calmar、Beta vs 大盤）
- 雲端部署
- 即時行情 / paper trading

未來版本可加。

---

## 11. 遷移路徑

- v1 → v2 為 schema-breaking change（`BacktestResult` 結構不同、`ohlcv.quality_flag` 新欄）
- SQLite migration：手動 `ALTER TABLE` 加欄位，舊資料 `quality_flag='clean'` default
- 程式碼：engine.py、models.py、所有 ui/pages、所有 ui/components/charts 都需動
- v1 tests 部分會失效，依新 schema 改寫
