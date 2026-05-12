# Hindsight — 台股交易回測系統設計文件

**日期：** 2026-05-12  
**專案：** Hindsight  
**狀態：** 已批准，待實作

---

## 1. 概覽

Hindsight 是一套台股交易回測系統，支援三種標的挑選模式、可插拔交易策略、多策略並行比較，以及三層式 Web UI。設計目標：模組化優先，新增策略或篩選條件只需加一個 Python 檔案，不修改核心引擎。

**技術棧**
- UI：Dash (Plotly)
- 語言：Python 3.11+
- 資料：FinMind API（主）+ yfinance（備援）
- 快取：SQLite
- 部署：Docker（單容器）

---

## 2. 架構總覽

五層分離，每層有明確介面，單向依賴（UI → Backtest → Strategy/Selection → Data）。

```
ui/                  Layer 5 — Dash 三層頁面
backtest/            Layer 4 — 回測引擎 + 指標計算
strategy/            Layer 3 — 可插拔策略（BaseStrategy ABC）
selection/           Layer 2 — 可插拔標的挑選（BaseFilter ABC）
data/                Layer 1 — DataProvider + SQLite 快取
```

**專案目錄結構**

```
hindsight/
├── data/
│   ├── provider.py          # 統一 DataProvider 介面
│   ├── finmind.py           # FinMind 適配器
│   ├── yfinance_src.py      # yfinance 適配器
│   ├── cache.py             # 快取管理（TTL 邏輯）
│   └── db/                  # SQLite 檔案（Docker volume 掛載）
├── selection/
│   ├── manual.py
│   ├── random_mode.py
│   ├── semi_random.py
│   └── filters/
│       ├── base.py          # BaseFilter ABC
│       ├── price.py
│       ├── volume.py
│       ├── pe_ratio.py
│       └── volatility.py
├── strategy/
│   ├── base.py              # BaseStrategy ABC
│   └── dip_and_take_profit.py
├── backtest/
│   ├── engine.py            # 主迴圈
│   ├── metrics.py           # MetricsCalculator
│   └── models.py            # Trade, Position, BacktestResult dataclasses
├── ui/
│   ├── app.py               # Dash app 入口
│   ├── pages/
│   │   ├── home.py          # 策略比較主頁
│   │   ├── strategy.py      # 策略詳情頁
│   │   └── stock.py         # 標的 K 線 + 交易記錄頁
│   └── components/          # 共用 Dash 元件
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

---

## 3. Data Layer

### 3.1 DataProvider 介面

所有呼叫端只與 `DataProvider` 互動，不直接碰 FinMind 或 yfinance。

```python
class DataProvider:
    def get_ohlcv(self, ticker: str, start: date, end: date) -> pd.DataFrame
    def get_fundamentals(self, ticker: str, start: date, end: date) -> pd.DataFrame
    def get_ticker_list(self) -> pd.DataFrame
```

### 3.2 Fallback 邏輯

1. 查 SQLite 快取（`cache_meta` 表確認有效期）
2. 命中且未過期 → 直接回傳
3. 未命中或過期 → 呼叫 FinMind
4. FinMind 失敗（rate limit / token 缺失）→ fallback 到 yfinance
5. 拉到資料後寫回 SQLite

### 3.3 SQLite Schema

```sql
CREATE TABLE ohlcv (
    ticker TEXT, date TEXT, open REAL, high REAL, low REAL,
    close REAL, volume INTEGER,
    PRIMARY KEY (ticker, date)
);

CREATE TABLE fundamentals (
    ticker TEXT, date TEXT, pe_ratio REAL, pb_ratio REAL, market_cap REAL,
    PRIMARY KEY (ticker, date)
);

CREATE TABLE cache_meta (
    ticker TEXT, data_type TEXT, last_updated TEXT, source TEXT,
    PRIMARY KEY (ticker, data_type)
);

CREATE TABLE ticker_list (
    ticker TEXT PRIMARY KEY, name TEXT, market TEXT, listed_date TEXT
);
```

### 3.4 快取有效期

| 資料類型                | TTL  |
| ------------------- | ---- |
| OHLCV 歷史（收盤後 5 日以前） | 永久   |
| OHLCV 近 5 日         | 每日重拉 |
| 財務指標（本益比等）          | 7 天  |
| 全股清單                | 30 天 |

### 3.5 Token 管理

- 從環境變數 `FINMIND_TOKEN` 讀取
- Token 缺失時自動降級為純 yfinance 模式（不崩潰）
- FinMind rate limit 觸發時指數退避重試（最多 3 次）

---

## 4. Selection Engine

### 4.1 三種模式

| 模式 | 說明 |
|------|------|
| **Manual** | 手動指定 ticker 清單 + 日期區間 |
| **全隨機** | 從 `ticker_list` 隨機抽 N 檔，日期區間也隨機 |
| **半隨機** | 指定日期區間，依 Filter 條件過濾後隨機抽 N 檔 |

### 4.2 BaseFilter ABC

```python
class BaseFilter(ABC):
    @abstractmethod
    def apply(self, df: pd.DataFrame) -> pd.DataFrame:
        """接收標的清單 DataFrame，回傳過濾後的 DataFrame"""
        ...
```

### 4.3 內建 Filter

- `PriceFilter(min_price, max_price)` — 股價區間
- `VolumeFilter(min_volume)` — 成交量下限
- `PERatioFilter(min_pe, max_pe)` — 本益比區間
- `VolatilityFilter(min_vol)` — 年化波動率下限

### 4.4 擴充方式

在 `selection/filters/` 新增繼承 `BaseFilter` 的 `.py` 檔，`semi_random.py` 自動掃描載入，不需修改其他程式碼。

---

## 5. Strategy Engine

### 5.1 BaseStrategy ABC

```python
@dataclass
class Action:
    type: Literal["BUY", "SELL", "HOLD"]
    amount: float = 0.0   # BUY 時為買入金額（元）；SELL 時為 0 代表全賣

class BaseStrategy(ABC):
    @abstractmethod
    def on_price_update(
        self, date: date, price: float, position: Position | None
    ) -> Action:
        """每個交易日收盤時呼叫，回傳 Action。
        position 為 None 代表尚未建倉（初始狀態）。
        策略自行決定是否在 position=None 時回傳 BUY 建倉。"""
        ...

    def on_session_end(self, position: Position | None) -> Action:
        """回測區間結束時呼叫，預設 HOLD（子類可 override 強平）"""
        return Action(type="HOLD")
```

**初始建倉規則：** 回測開始第一個交易日，position = None，策略收到 `on_price_update` 後若回傳 `BUY`，引擎以 `amount` 金額建倉（股數 = floor(amount / price)）。`DipAndTakeProfitStrategy` 預設第一日直接建倉（amount = `add_amount`）。

### 5.2 初始策略：DipAndTakeProfitStrategy

**邏輯：**
- 建倉後，若收盤價較平均成本跌超過 `dip_pct` → 加碼 `add_amount` 元（不超過 `max_position`）
- 未實現損益 > `take_profit_pct` → 全賣
- 持倉天數 ≥ `max_hold_days` → 強制平倉
- 買入與賣出均以當天收盤價計算

**可設定參數：**

| 參數 | 說明 | 範例 |
|------|------|------|
| `dip_pct` | 加碼跌幅門檻 | 7% |
| `add_amount` | 每次加碼金額（元） | 10,000 |
| `take_profit_pct` | 止盈門檻 | 3% |
| `max_position` | 單一標的持倉上限（元） | 100,000 |
| `entry_price` | 買入基準價格類型 | `close` |
| `max_hold_days` | 強制平倉天數 | 60 |

### 5.3 擴充方式

在 `strategy/` 新增繼承 `BaseStrategy` 的 `.py` 檔即可，回測引擎不需修改。

---

## 6. Backtest Engine

### 6.1 主迴圈（逐日模擬）

```
for each strategy in strategies:
    初始化各標的 Position（capital 獨立分配）
    for each date in date_range:
        for each ticker in selected_tickers:
            action = strategy.on_price_update(date, close[date], position)
            execute_action(action, position)  # 套用費用，記錄 Trade
            check_force_close(position)       # 強平 / 上限檢查
        snapshot_portfolio_value(date)        # 每日淨值快照
    strategy.on_session_end(all_positions)
calculate_metrics(all_trades, daily_snapshots)
```

### 6.2 台股費用

| 項目 | 費率 |
|------|------|
| 買入手續費 | 0.1425% |
| 賣出手續費 | 0.1425% |
| 證券交易稅（賣出） | 0.3% |
| **賣出單次總成本** | **≈ 0.4425%** |

手續費折扣（券商折數）預留為未來可設定參數。

### 6.3 多策略並行

最多五個策略同時執行，各策略持有獨立 capital 與 Position 物件，互不干擾。

### 6.4 核心 Dataclass

```python
@dataclass
class Trade:
    ticker: str
    action: Action          # BUY / SELL
    date: date
    price: float
    shares: int
    amount: float
    fee: float
    tax: float
    realized_pnl: float | None   # 僅賣出時有值

@dataclass
class Position:
    ticker: str
    shares: int
    avg_cost: float
    entry_date: date
    total_invested: float

@dataclass
class BacktestResult:
    strategy_name: str
    trades: list[Trade]
    daily_snapshots: list[tuple[date, float]]  # (date, portfolio_value)
    metrics: Metrics
```

---

## 7. 量化指標

五項指標由 `MetricsCalculator` 統一計算。

| 指標 | 公式 | 說明 |
|------|------|------|
| **Max Drawdown (MDD)** | (peak − trough) / peak | 峰值到谷底最大跌幅，越小越好 |
| **Sharpe Ratio** | (Rp − Rf) / σp（年化，Rf = 0） | 風險調整後報酬，>1 為佳 |
| **Win Rate** | 獲利交易數 / 總交易數 | 每筆交易獨立計算 |
| **Profit Factor** | 總獲利 / 總虧損 | >1 為正期望值策略 |
| **Avg Hold Days** | Σ(賣出日 − 買入日) / 交易數 | 平均持倉天數 |

進階指標（Sortino Ratio、Calmar Ratio、Beta vs 大盤）預留為未來擴充。

---

## 8. UI — 三層頁面

### 8.1 主頁（策略比較）

- 折線圖：各策略倉位總價值變動（不同顏色，hover 顯示日期/淨值/報酬率）
- 指標比較表：每策略一列，欄位包含已實現損益、未實現損益、最終淨值、MDD、Sharpe、Win Rate、Profit Factor、Avg Hold Days
- 點策略名稱 → 策略頁

### 8.2 策略頁（標的列表）

- 左欄：策略參數 + 選股設定（唯讀顯示）
- 右上：所有持有標的股價走勢疊加圖（標準化起始值 = 1.0）
- 右下：各標的指標比較表（交易次數、損益、MDD、Win Rate、Avg Hold）
- 點標的 → 標的頁

### 8.3 標的頁（K 線 + 交易記錄）

- K 線圖：日線，回測區間前後各延伸 10 個交易日；買入▲綠 / 加碼▲綠虛 / 賣出▼紅 / 強平▼橘箭頭標注
- 逐筆交易表：日期、動作、股數、成交價、成交金額、手續費+稅、已實現損益

### 8.4 Dash 路由

```
/                                   主頁
/strategy/<strategy_id>             策略頁
/stock/<strategy_id>/<ticker>       標的頁
```

---

## 9. 部署

### 9.1 Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8050
CMD ["python", "-m", "ui.app"]
```

- SQLite DB 掛載為 Docker volume（`/app/data/db/`），重啟不失資料
- `FINMIND_TOKEN` 透過環境變數注入
- `docker-compose.yml` 提供本機開發一鍵啟動

### 9.2 環境變數

| 變數 | 說明 | 必填 |
|------|------|------|
| `FINMIND_TOKEN` | FinMind API token | 否（缺失降級 yfinance） |
| `CACHE_DIR` | SQLite 檔案目錄 | 否（預設 `/app/data/db`） |
| `PORT` | Dash 監聽 port | 否（預設 `8050`） |

---

## 10. 測試策略

| 層 | 測試重點 |
|----|---------|
| Data Layer | 快取 hit/miss；fallback 觸發；TTL 過期 |
| Selection Engine | 各 Filter 過濾正確性；多 Filter 疊加 |
| Strategy Engine | DipAndTakeProfit 各條件觸發（跌幅/止盈/強平/上限） |
| Backtest Engine | 費用計算精度；多策略獨立性 |
| Metrics | MDD、Sharpe、Win Rate、Profit Factor、Avg Hold Days 計算正確性 |

---

## 11. 未來擴充（不在 v1 範圍）

- 手續費折扣參數
- 進階指標：Sortino Ratio、Calmar Ratio、Beta vs 大盤
- 更多策略（繼承 BaseStrategy）
- 更多篩選條件（繼承 BaseFilter）
- 雲端部署（Render / Fly.io / GCP Cloud Run）
