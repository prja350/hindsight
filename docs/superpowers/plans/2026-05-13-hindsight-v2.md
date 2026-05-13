# Hindsight v2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade Hindsight from v1 (single-strategy backtest) to v2 (per-ticker strategy assignment, shared capital, new InfiniteAverageV0 strategy, data quality, refreshed UI).

**Architecture:** Microscopic refactor: v1 main loop kept (shared cash already there), inject per-ticker strategy map, enrich snapshots, add data quality layer, new strategy + new UI components. No greenfield.

**Tech Stack:** Python 3.11+, pandas, Dash 4.1, Plotly, SQLite, FinMind, yfinance, pandas_market_calendars, pytest.

**Spec:** `docs/superpowers/specs/2026-05-13-hindsight-v2-design.md`

---

## Phase 1 — Data Quality Layer

### Task 1: Trading Calendar Module

**Files:**
- Create: `data/calendar.py`
- Create: `data/calendar_fallback.py`
- Test: `tests/data/test_calendar.py`

- [ ] **Step 1: Add dependency**

Edit `requirements.txt` — add line:
```
pandas_market_calendars>=4.0.0
```
Run: `pip install pandas_market_calendars`
Expected: success.

- [ ] **Step 2: Write the failing test**

Create `tests/data/test_calendar.py`:
```python
from __future__ import annotations
from datetime import date
from data.calendar import trading_days


def test_excludes_weekends():
    days = trading_days(date(2025, 1, 1), date(2025, 1, 7))
    assert date(2025, 1, 4) not in days  # Sat
    assert date(2025, 1, 5) not in days  # Sun


def test_includes_weekdays():
    days = trading_days(date(2025, 1, 6), date(2025, 1, 6))  # Mon
    assert date(2025, 1, 6) in days


def test_returns_sorted_list():
    days = trading_days(date(2025, 1, 1), date(2025, 1, 10))
    assert days == sorted(days)
```

- [ ] **Step 3: Run test — fail**

Run: `pytest tests/data/test_calendar.py -v`
Expected: FAIL `ModuleNotFoundError: data.calendar`.

- [ ] **Step 4: Implement fallback module**

Create `data/calendar_fallback.py`:
```python
from __future__ import annotations
from datetime import date, timedelta

_HOLIDAYS_2024 = {
    date(2024, 1, 1), date(2024, 2, 8), date(2024, 2, 9), date(2024, 2, 12),
    date(2024, 2, 13), date(2024, 2, 14), date(2024, 2, 28), date(2024, 4, 4),
    date(2024, 4, 5), date(2024, 5, 1), date(2024, 6, 10), date(2024, 9, 17),
    date(2024, 10, 10),
}
_HOLIDAYS_2025 = {
    date(2025, 1, 1), date(2025, 1, 27), date(2025, 1, 28), date(2025, 1, 29),
    date(2025, 1, 30), date(2025, 1, 31), date(2025, 2, 28), date(2025, 4, 3),
    date(2025, 4, 4), date(2025, 5, 1), date(2025, 5, 30), date(2025, 10, 6),
    date(2025, 10, 10),
}
_HOLIDAYS_2026 = {
    date(2026, 1, 1), date(2026, 2, 16), date(2026, 2, 17), date(2026, 2, 18),
    date(2026, 2, 19), date(2026, 2, 20), date(2026, 2, 27), date(2026, 4, 3),
    date(2026, 4, 6), date(2026, 5, 1), date(2026, 6, 19), date(2026, 9, 25),
    date(2026, 10, 9),
}
_HOLIDAYS = _HOLIDAYS_2024 | _HOLIDAYS_2025 | _HOLIDAYS_2026


def trading_days_fallback(start: date, end: date) -> list[date]:
    days = []
    d = start
    while d <= end:
        if d.weekday() < 5 and d not in _HOLIDAYS:
            days.append(d)
        d += timedelta(days=1)
    return days
```

- [ ] **Step 5: Implement main module**

Create `data/calendar.py`:
```python
from __future__ import annotations
from datetime import date

try:
    import pandas_market_calendars as mcal
    _XTAI = mcal.get_calendar('XTAI')
    _HAS_MCAL = True
except Exception:
    _HAS_MCAL = False

from data.calendar_fallback import trading_days_fallback


def trading_days(start: date, end: date) -> list[date]:
    if _HAS_MCAL:
        sched = _XTAI.valid_days(start.isoformat(), end.isoformat())
        return [d.date() for d in sched]
    return trading_days_fallback(start, end)
```

- [ ] **Step 6: Run test — pass**

Run: `pytest tests/data/test_calendar.py -v`
Expected: 3 passed.

- [ ] **Step 7: Commit**

```bash
git add requirements.txt data/calendar.py data/calendar_fallback.py tests/data/test_calendar.py
git commit -m "feat(data): trading calendar with XTAI + hardcoded fallback"
```

---

### Task 2: Gap Detection

**Files:**
- Create: `data/quality.py`
- Test: `tests/data/test_quality.py`

- [ ] **Step 1: Write the failing test**

Create `tests/data/test_quality.py`:
```python
from __future__ import annotations
from datetime import date
import pandas as pd
from data.quality import detect_gaps


def test_no_gaps_returns_empty():
    df = pd.DataFrame({'date': ['2025-01-02', '2025-01-03', '2025-01-06']})
    expected = [date(2025, 1, 2), date(2025, 1, 3), date(2025, 1, 6)]
    assert detect_gaps(df, expected) == []


def test_single_day_gap():
    df = pd.DataFrame({'date': ['2025-01-02', '2025-01-06']})
    expected = [date(2025, 1, 2), date(2025, 1, 3), date(2025, 1, 6)]
    assert detect_gaps(df, expected) == [(date(2025, 1, 3), date(2025, 1, 3))]


def test_contiguous_gap_merged():
    df = pd.DataFrame({'date': ['2025-01-02', '2025-01-07']})
    expected = [date(2025,1,2), date(2025,1,3), date(2025,1,6), date(2025,1,7)]
    assert detect_gaps(df, expected) == [(date(2025,1,3), date(2025,1,6))]


def test_empty_df_returns_full_range():
    df = pd.DataFrame({'date': []})
    expected = [date(2025, 1, 2), date(2025, 1, 3)]
    assert detect_gaps(df, expected) == [(date(2025, 1, 2), date(2025, 1, 3))]
```

- [ ] **Step 2: Run test — fail**

Run: `pytest tests/data/test_quality.py -v`
Expected: FAIL `ModuleNotFoundError: data.quality`.

- [ ] **Step 3: Implement detect_gaps**

Create `data/quality.py`:
```python
from __future__ import annotations
from datetime import date
import pandas as pd


def detect_gaps(df: pd.DataFrame, expected: list[date]) -> list[tuple[date, date]]:
    """Return contiguous missing date ranges. Pure function, no I/O.
    Contiguity is measured in *trading-day* order (consecutive entries in `expected`).
    """
    have = set()
    if not df.empty and 'date' in df.columns:
        have = {date.fromisoformat(str(d)) for d in df['date'].tolist()}
    missing_set = {d for d in expected if d not in have}
    if not missing_set:
        return []
    # Walk expected list, group consecutive missing entries
    gaps: list[tuple[date, date]] = []
    run_start: date | None = None
    prev: date | None = None
    for d in expected:
        if d in missing_set:
            if run_start is None:
                run_start = d
            prev = d
        else:
            if run_start is not None and prev is not None:
                gaps.append((run_start, prev))
            run_start = None
            prev = None
    if run_start is not None and prev is not None:
        gaps.append((run_start, prev))
    return gaps
```

- [ ] **Step 4: Run test — pass**

Run: `pytest tests/data/test_quality.py -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add data/quality.py tests/data/test_quality.py
git commit -m "feat(data): detect_gaps() pure function for trading-day gaps"
```

---

### Task 3: SQLite Schema Migration

**Files:**
- Modify: `data/cache.py`
- Test: `tests/data/test_cache.py`

- [ ] **Step 1: Read current cache schema**

Run: `grep -n "CREATE TABLE\|ALTER\|quality" data/cache.py`
Expected: see existing `ohlcv`, `fundamentals`, `cache_meta`, `ticker_list` tables; no quality column.

- [ ] **Step 2: Write failing test**

Append to `tests/data/test_cache.py` (create if absent):
```python
def test_ohlcv_has_quality_flag_column(tmp_path):
    from data.cache import CacheManager
    c = CacheManager(db_path=str(tmp_path / "t.db"))
    cols = c._conn.execute("PRAGMA table_info(ohlcv)").fetchall()
    names = [r[1] for r in cols]
    assert 'quality_flag' in names


def test_save_with_quality_flag(tmp_path):
    import pandas as pd
    from datetime import date
    from data.cache import CacheManager
    c = CacheManager(db_path=str(tmp_path / "t.db"))
    df = pd.DataFrame([{
        'ticker': '2330', 'date': '2025-01-02',
        'open': 600, 'high': 610, 'low': 595, 'close': 605, 'volume': 1000,
        'quality_flag': 'forward_filled',
    }])
    c.save_ohlcv('2330', df, source='finmind')
    out = c.get_ohlcv('2330', date(2025,1,1), date(2025,1,3))
    assert out is not None
    assert out.iloc[0]['quality_flag'] == 'forward_filled'
```

- [ ] **Step 3: Run test — fail**

Run: `pytest tests/data/test_cache.py -v -k quality`
Expected: FAIL — column not present or save ignores it.

- [ ] **Step 4: Patch CacheManager**

In `data/cache.py`:

a) Replace `CREATE TABLE IF NOT EXISTS ohlcv` block with:
```python
self._conn.execute("""
    CREATE TABLE IF NOT EXISTS ohlcv (
        ticker TEXT, date TEXT,
        open REAL, high REAL, low REAL, close REAL, volume INTEGER,
        quality_flag TEXT NOT NULL DEFAULT 'clean',
        PRIMARY KEY (ticker, date)
    )
""")
try:
    self._conn.execute(
        "ALTER TABLE ohlcv ADD COLUMN quality_flag TEXT NOT NULL DEFAULT 'clean'"
    )
except Exception:
    pass  # already added
```

b) Inside `save_ohlcv`, before the insert, ensure column:
```python
if 'quality_flag' not in df.columns:
    df = df.assign(quality_flag='clean')
```
Include `quality_flag` in the INSERT column list and values tuple.

c) Inside `get_ohlcv`, change SELECT to include `quality_flag`:
```python
SELECT ticker, date, open, high, low, close, volume, quality_flag FROM ohlcv WHERE ...
```

- [ ] **Step 5: Run test — pass**

Run: `pytest tests/data/test_cache.py -v`
Expected: all passed.

- [ ] **Step 6: Commit**

```bash
git add data/cache.py tests/data/test_cache.py
git commit -m "feat(data): cache schema adds quality_flag column"
```

---

### Task 4: DataProvider Gap-Fill Flow

**Files:**
- Modify: `data/provider.py`
- Test: `tests/data/test_provider.py`

- [ ] **Step 1: Write failing test**

Append to `tests/data/test_provider.py`:
```python
def test_forward_fill_when_no_data_available(tmp_path, monkeypatch):
    from datetime import date
    import pandas as pd
    from data.provider import DataProvider

    monkeypatch.setattr('data.finmind.FinMindAdapter.fetch_ohlcv',
                        lambda self, t, s, e: pd.DataFrame())
    monkeypatch.setattr('data.yfinance_src.YFinanceAdapter.fetch_ohlcv',
                        lambda self, t, s, e: pd.DataFrame())

    provider = DataProvider(cache_dir=str(tmp_path))
    seed = pd.DataFrame([{
        'ticker': '2330', 'date': '2025-01-02',
        'open': 600, 'high': 605, 'low': 595, 'close': 600, 'volume': 1000,
        'quality_flag': 'clean',
    }])
    provider.cache.save_ohlcv('2330', seed, source='finmind')

    out = provider.get_ohlcv('2330', date(2025, 1, 2), date(2025, 1, 3))
    assert out is not None
    rows = out[out['date'] == '2025-01-03']
    assert not rows.empty
    assert rows.iloc[0]['quality_flag'] == 'forward_filled'
    assert rows.iloc[0]['close'] == 600
```

- [ ] **Step 2: Run test — fail**

Run: `pytest tests/data/test_provider.py::test_forward_fill_when_no_data_available -v`
Expected: FAIL.

- [ ] **Step 3: Rewrite DataProvider.get_ohlcv**

Replace `get_ohlcv` in `data/provider.py`:
```python
def get_ohlcv(self, ticker: str, start: date, end: date) -> Optional[pd.DataFrame]:
    from data.calendar import trading_days
    from data.quality import detect_gaps
    import pandas as pd

    expected = trading_days(start, end)
    if not expected:
        return None

    cached = self.cache.get_ohlcv(ticker, start, end)
    if cached is None:
        cached = pd.DataFrame(columns=['ticker','date','open','high','low','close','volume','quality_flag'])

    # Always retry forward_filled rows
    if 'quality_flag' in cached.columns:
        cached = cached[cached['quality_flag'] != 'forward_filled'].reset_index(drop=True)

    gaps = detect_gaps(cached, expected)
    new_rows: list[pd.DataFrame] = []

    for gap_start, gap_end in gaps:
        fm = self.finmind.fetch_ohlcv(ticker, gap_start, gap_end)
        covered: set[str] = set()
        if fm is not None and not fm.empty:
            fm = fm.assign(quality_flag='clean')
            new_rows.append(fm)
            covered = set(fm['date'].tolist())

        remaining = [d for d in expected
                     if gap_start <= d <= gap_end and d.isoformat() not in covered]
        if remaining:
            yf = self.yfinance.fetch_ohlcv(ticker, gap_start, gap_end)
            if yf is not None and not yf.empty:
                yf = yf.assign(quality_flag='yfinance')
                new_rows.append(yf)
                covered |= set(yf['date'].tolist())
            still_missing = [d for d in remaining if d.isoformat() not in covered]
            if still_missing:
                fill = self._forward_fill(ticker, cached, new_rows, still_missing)
                if not fill.empty:
                    new_rows.append(fill)

    if new_rows:
        merged = pd.concat([cached] + new_rows, ignore_index=True)
        self.cache.save_ohlcv(ticker, merged, source='multi')
        return self.cache.get_ohlcv(ticker, start, end)

    return cached if not cached.empty else None


def _forward_fill(self, ticker, cached_df, new_rows, missing_dates):
    import pandas as pd
    parts = [cached_df] + new_rows if new_rows else [cached_df]
    all_known = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()
    if all_known.empty:
        return pd.DataFrame()
    all_known = all_known.sort_values('date').reset_index(drop=True)
    rows = []
    for d in missing_dates:
        prior = all_known[all_known['date'] < d.isoformat()]
        if prior.empty:
            continue
        last_close = float(prior.iloc[-1]['close'])
        rows.append({
            'ticker': ticker, 'date': d.isoformat(),
            'open': last_close, 'high': last_close, 'low': last_close,
            'close': last_close, 'volume': 0, 'quality_flag': 'forward_filled',
        })
    return pd.DataFrame(rows)
```

- [ ] **Step 4: Run test — pass**

Run: `pytest tests/data/test_provider.py -v`
Expected: passed.

- [ ] **Step 5: Commit**

```bash
git add data/provider.py tests/data/test_provider.py
git commit -m "feat(data): provider gap detection + finmind/yfinance/forward-fill chain"
```

---

## Phase 2 — Models & Helpers

### Task 5: Models Update

**Files:**
- Modify: `backtest/models.py`
- Test: `tests/backtest/test_models.py`

- [ ] **Step 1: Write failing test**

Create or replace `tests/backtest/test_models.py`:
```python
from __future__ import annotations
from datetime import date
from backtest.models import (
    TickerAssignment, TickerState, PriceContext, DailySnapshot,
    TickerResult, BacktestResult, Position, Trade, Metrics, Action,
)


def test_ticker_assignment_holds_class_and_params():
    a = TickerAssignment(ticker='2330', strategy_class='infinite_average_v0',
                          params={'dip_pct': 0.05})
    assert a.ticker == '2330'
    assert a.params['dip_pct'] == 0.05


def test_ticker_state_initially_empty():
    s = TickerState()
    assert s.position is None
    assert s.last_sell_price is None


def test_price_context_holds_all_prices():
    ctx = PriceContext(date(2025,1,2), 100, 105, 102, 102, 'clean')
    assert ctx.price == 102
    assert ctx.quality_flag == 'clean'


def test_daily_snapshot_total_property():
    s = DailySnapshot(date(2025,1,2), cash=10000, position_value=5000)
    assert s.total == 15000


def test_backtest_result_v2_shape():
    r = BacktestResult(
        initial_capital=500_000, execution_price='close',
        start=date(2025,1,1), end=date(2025,12,31),
    )
    assert r.execution_price == 'close'
    assert r.ticker_results == []
```

- [ ] **Step 2: Run test — fail**

Run: `pytest tests/backtest/test_models.py -v`
Expected: FAIL.

- [ ] **Step 3: Replace models.py**

Replace `backtest/models.py`:
```python
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date
from typing import Literal


@dataclass
class Action:
    type: Literal["BUY", "SELL", "HOLD"]
    amount: float = 0.0


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
    price: float
    shares: int
    amount: float
    fee: float
    tax: float
    realized_pnl: float | None = None
    hold_days: int | None = None


@dataclass
class Metrics:
    realized_pnl: float
    realized_pnl_pct: float
    unrealized_pnl: float
    final_cost: float
    final_nav: float
    max_drawdown: float
    sharpe_ratio: float
    win_rate: float
    profit_factor: float
    avg_hold_days: float


@dataclass
class TickerAssignment:
    ticker: str
    strategy_class: str
    params: dict[str, float]


@dataclass
class TickerState:
    position: Position | None = None
    last_sell_price: float | None = None


@dataclass
class PriceContext:
    date: date
    open: float
    close: float
    vwap: float
    price: float
    quality_flag: Literal["clean", "yfinance", "forward_filled"]


@dataclass
class DailySnapshot:
    date: date
    cash: float
    position_value: float

    @property
    def total(self) -> float:
        return self.cash + self.position_value


@dataclass
class TickerResult:
    ticker: str
    strategy_class: str
    params: dict[str, float]
    trades: list[Trade] = field(default_factory=list)
    metrics: Metrics | None = None
    final_position: Position | None = None


@dataclass
class BacktestResult:
    initial_capital: float
    execution_price: str
    start: date
    end: date
    ticker_results: list[TickerResult] = field(default_factory=list)
    daily_snapshots: list[DailySnapshot] = field(default_factory=list)
    final_cash: float = 0.0
```

- [ ] **Step 4: Run test — pass**

Run: `pytest tests/backtest/test_models.py -v`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add backtest/models.py tests/backtest/test_models.py
git commit -m "refactor(models): v2 dataclasses for per-ticker assignment + cash/pos snapshots"
```

---

### Task 6: Strategy PnL Helper

**Files:**
- Create: `strategy/pnl.py`
- Test: `tests/strategy/test_pnl.py`

- [ ] **Step 1: Write failing test**

Create `tests/strategy/test_pnl.py`:
```python
from __future__ import annotations
from datetime import date
from backtest.models import Position, TickerState
from strategy.pnl import net_unrealized_pct


def test_no_position_returns_zero():
    s = TickerState(position=None)
    assert net_unrealized_pct(s, 100.0) == 0.0


def test_positive_pnl_net_of_fees():
    pos = Position('2330', shares=10, avg_cost=100, entry_date=date(2025,1,2),
                    total_invested=1000)
    s = TickerState(position=pos)
    pct = net_unrealized_pct(s, 110.0)
    # 10*110*(1-0.001425-0.003) = 1095.1325; (1095.1325 - 1000)/1000 = 0.0951325
    assert abs(pct - 0.0951325) < 1e-6


def test_negative_pnl():
    pos = Position('2330', shares=10, avg_cost=100, entry_date=date(2025,1,2),
                    total_invested=1000)
    s = TickerState(position=pos)
    assert net_unrealized_pct(s, 90.0) < -0.1


def test_zero_invested_returns_zero():
    pos = Position('2330', shares=0, avg_cost=0, entry_date=date(2025,1,2),
                    total_invested=0)
    s = TickerState(position=pos)
    assert net_unrealized_pct(s, 100.0) == 0.0
```

- [ ] **Step 2: Run test — fail**

Run: `pytest tests/strategy/test_pnl.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement strategy/pnl.py**

Create `strategy/pnl.py`:
```python
from __future__ import annotations
from backtest.models import TickerState

BUY_FEE_RATE = 0.001425
SELL_FEE_RATE = 0.001425
SELL_TAX_RATE = 0.003


def net_unrealized_pct(state: TickerState, price: float) -> float:
    pos = state.position
    if pos is None or pos.total_invested <= 0:
        return 0.0
    gross = pos.shares * price * (1 - SELL_FEE_RATE - SELL_TAX_RATE)
    return (gross - pos.total_invested) / pos.total_invested


def net_unrealized_value(state: TickerState, price: float) -> float:
    pos = state.position
    if pos is None:
        return 0.0
    gross = pos.shares * price * (1 - SELL_FEE_RATE - SELL_TAX_RATE)
    return gross - pos.total_invested
```

- [ ] **Step 4: Run test — pass**

Run: `pytest tests/strategy/test_pnl.py -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add strategy/pnl.py tests/strategy/test_pnl.py
git commit -m "feat(strategy): net_unrealized_pct helper (net of sell fees+tax)"
```

---

## Phase 3 — Strategy Layer

### Task 7: BaseStrategy ABC Update

**Files:**
- Modify: `strategy/base.py`
- Test: `tests/strategy/test_base.py`

- [ ] **Step 1: Write failing test**

Create `tests/strategy/test_base.py`:
```python
from __future__ import annotations
from datetime import date
from backtest.models import Action, PriceContext, TickerState
from strategy.base import BaseStrategy


class _HoldAlways(BaseStrategy):
    def on_price_update(self, ctx, state):
        return Action(type="HOLD")


def test_signature_takes_ctx_and_state():
    s = _HoldAlways()
    ctx = PriceContext(date(2025,1,2), 100, 100, 100, 100, 'clean')
    st = TickerState()
    assert s.on_price_update(ctx, st).type == "HOLD"


def test_session_end_default_hold():
    s = _HoldAlways()
    assert s.on_session_end(TickerState()).type == "HOLD"
```

- [ ] **Step 2: Run test — fail**

Run: `pytest tests/strategy/test_base.py -v`
Expected: FAIL.

- [ ] **Step 3: Replace base.py**

Replace `strategy/base.py`:
```python
from __future__ import annotations
from abc import ABC, abstractmethod
from backtest.models import Action, PriceContext, TickerState


class BaseStrategy(ABC):
    @abstractmethod
    def on_price_update(self, ctx: PriceContext, state: TickerState) -> Action:
        ...

    def on_session_end(self, state: TickerState) -> Action:
        return Action(type="HOLD")
```

- [ ] **Step 4: Run test — pass**

Run: `pytest tests/strategy/test_base.py -v`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add strategy/base.py tests/strategy/test_base.py
git commit -m "refactor(strategy): BaseStrategy ABC takes PriceContext + TickerState"
```

---

### Task 8: DipAndTakeProfit Refactor

**Files:**
- Modify: `strategy/dip_and_take_profit.py`
- Test: `tests/strategy/test_dip_and_take_profit.py`

- [ ] **Step 1: Write failing test**

Replace `tests/strategy/test_dip_and_take_profit.py`:
```python
from __future__ import annotations
from datetime import date
from backtest.models import Position, PriceContext, TickerState
from strategy.dip_and_take_profit import DipAndTakeProfitStrategy


def _ctx(d, price): return PriceContext(d, price, price, price, price, 'clean')


def test_first_entry_buys():
    s = DipAndTakeProfitStrategy(0.05, 0.05, 10_000, 100_000, 60)
    a = s.on_price_update(_ctx(date(2025,1,2), 100), TickerState())
    assert a.type == "BUY" and a.amount == 10_000


def test_adds_when_below_dip_threshold():
    pos = Position('2330', shares=10, avg_cost=100, entry_date=date(2025,1,2),
                    total_invested=1000)
    s = DipAndTakeProfitStrategy(0.05, 0.05, 10_000, 100_000, 60)
    a = s.on_price_update(_ctx(date(2025,1,10), 80), TickerState(position=pos))
    assert a.type == "BUY"


def test_sells_at_take_profit():
    pos = Position('2330', shares=10, avg_cost=100, entry_date=date(2025,1,2),
                    total_invested=1000)
    s = DipAndTakeProfitStrategy(0.05, 0.05, 10_000, 100_000, 60)
    a = s.on_price_update(_ctx(date(2025,1,10), 120), TickerState(position=pos))
    assert a.type == "SELL"


def test_max_hold_forces_sell():
    pos = Position('2330', shares=10, avg_cost=100,
                    entry_date=date(2025,1,2), total_invested=1000)
    s = DipAndTakeProfitStrategy(0.05, 0.05, 10_000, 100_000, 5)
    a = s.on_price_update(_ctx(date(2025,1,10), 100), TickerState(position=pos))
    assert a.type == "SELL"


def test_max_position_blocks_add():
    pos = Position('2330', shares=1000, avg_cost=100, entry_date=date(2025,1,2),
                    total_invested=100_000)
    s = DipAndTakeProfitStrategy(0.05, 0.05, 10_000, 100_000, 60)
    a = s.on_price_update(_ctx(date(2025,1,5), 80), TickerState(position=pos))
    assert a.type == "HOLD"
```

- [ ] **Step 2: Run test — fail**

Run: `pytest tests/strategy/test_dip_and_take_profit.py -v`
Expected: FAIL.

- [ ] **Step 3: Replace strategy module**

Replace `strategy/dip_and_take_profit.py`:
```python
from __future__ import annotations
from dataclasses import dataclass
from backtest.models import Action, PriceContext, TickerState
from strategy.base import BaseStrategy
from strategy.pnl import net_unrealized_pct


@dataclass
class DipAndTakeProfitStrategy(BaseStrategy):
    dip_pct: float
    take_profit_pct: float
    add_amount: float
    max_position: float
    max_hold_days: int

    def on_price_update(self, ctx: PriceContext, state: TickerState) -> Action:
        pos = state.position
        if pos is None:
            return Action(type="BUY", amount=self.add_amount)

        hold_days = (ctx.date - pos.entry_date).days
        if hold_days >= self.max_hold_days:
            return Action(type="SELL")

        pnl_pct = net_unrealized_pct(state, ctx.price)
        if pnl_pct >= self.take_profit_pct:
            return Action(type="SELL")
        if pnl_pct < -self.dip_pct:
            if pos.total_invested + self.add_amount <= self.max_position:
                return Action(type="BUY", amount=self.add_amount)
        return Action(type="HOLD")
```

- [ ] **Step 4: Run test — pass**

Run: `pytest tests/strategy/test_dip_and_take_profit.py -v`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add strategy/dip_and_take_profit.py tests/strategy/test_dip_and_take_profit.py
git commit -m "refactor(strategy): dip_and_take_profit uses net_unrealized_pct + ctx.price"
```

---

### Task 9: InfiniteAverageV0 Strategy

**Files:**
- Create: `strategy/infinite_average_v0.py`
- Test: `tests/strategy/test_infinite_average_v0.py`

- [ ] **Step 1: Write failing test**

Create `tests/strategy/test_infinite_average_v0.py`:
```python
from __future__ import annotations
from datetime import date
from backtest.models import Position, PriceContext, TickerState
from strategy.infinite_average_v0 import InfiniteAverageV0Strategy


def _ctx(d, p): return PriceContext(d, p, p, p, p, 'clean')


def test_first_entry_when_no_position_no_last_sell():
    s = InfiniteAverageV0Strategy(0.05, 0.05, 10_000, 100_000)
    a = s.on_price_update(_ctx(date(2025,1,2), 100), TickerState())
    assert a.type == "BUY" and a.amount == 10_000


def test_no_entry_when_last_sell_drop_below_threshold():
    s = InfiniteAverageV0Strategy(0.05, 0.05, 10_000, 100_000)
    st = TickerState(position=None, last_sell_price=100)
    a = s.on_price_update(_ctx(date(2025,1,5), 98), st)
    assert a.type == "HOLD"


def test_reentry_when_drop_meets_threshold():
    s = InfiniteAverageV0Strategy(0.05, 0.05, 10_000, 100_000)
    st = TickerState(position=None, last_sell_price=100)
    a = s.on_price_update(_ctx(date(2025,1,5), 95), st)
    assert a.type == "BUY"


def test_add_when_net_pnl_below_negative_dip():
    pos = Position('2330', shares=10, avg_cost=100, entry_date=date(2025,1,2),
                    total_invested=1000)
    s = InfiniteAverageV0Strategy(0.05, 0.05, 10_000, 100_000)
    a = s.on_price_update(_ctx(date(2025,1,10), 80), TickerState(position=pos))
    assert a.type == "BUY"


def test_max_position_blocks_add():
    pos = Position('2330', shares=1000, avg_cost=100, entry_date=date(2025,1,2),
                    total_invested=100_000)
    s = InfiniteAverageV0Strategy(0.05, 0.05, 10_000, 100_000)
    a = s.on_price_update(_ctx(date(2025,1,10), 80), TickerState(position=pos))
    assert a.type == "HOLD"


def test_sells_at_take_profit():
    pos = Position('2330', shares=10, avg_cost=100, entry_date=date(2025,1,2),
                    total_invested=1000)
    s = InfiniteAverageV0Strategy(0.05, 0.05, 10_000, 100_000)
    a = s.on_price_update(_ctx(date(2025,1,10), 120), TickerState(position=pos))
    assert a.type == "SELL"


def test_session_end_holds():
    s = InfiniteAverageV0Strategy(0.05, 0.05, 10_000, 100_000)
    a = s.on_session_end(TickerState())
    assert a.type == "HOLD"
```

- [ ] **Step 2: Run test — fail**

Run: `pytest tests/strategy/test_infinite_average_v0.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement strategy**

Create `strategy/infinite_average_v0.py`:
```python
from __future__ import annotations
from dataclasses import dataclass
from backtest.models import Action, PriceContext, TickerState
from strategy.base import BaseStrategy
from strategy.pnl import net_unrealized_pct


@dataclass
class InfiniteAverageV0Strategy(BaseStrategy):
    dip_pct: float
    take_profit_pct: float
    add_amount: float
    max_position: float

    def on_price_update(self, ctx: PriceContext, state: TickerState) -> Action:
        pos = state.position
        if pos is None:
            if state.last_sell_price is None:
                return Action(type="BUY", amount=self.add_amount)
            if ctx.price <= state.last_sell_price * (1 - self.dip_pct):
                return Action(type="BUY", amount=self.add_amount)
            return Action(type="HOLD")

        pnl_pct = net_unrealized_pct(state, ctx.price)
        if pnl_pct >= self.take_profit_pct:
            return Action(type="SELL")
        if pnl_pct < -self.dip_pct:
            if pos.total_invested + self.add_amount <= self.max_position:
                return Action(type="BUY", amount=self.add_amount)
        return Action(type="HOLD")
```

- [ ] **Step 4: Run test — pass**

Run: `pytest tests/strategy/test_infinite_average_v0.py -v`
Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add strategy/infinite_average_v0.py tests/strategy/test_infinite_average_v0.py
git commit -m "feat(strategy): InfiniteAverageV0 with re-entry after drop"
```

---

## Phase 4 — Backtest Engine

### Task 10: Engine Rewrite

**Files:**
- Modify: `backtest/engine.py`
- Test: `tests/backtest/test_engine_v2.py`

- [ ] **Step 1: Write failing test**

Create `tests/backtest/test_engine_v2.py`:
```python
from __future__ import annotations
from datetime import date
import pandas as pd
from unittest.mock import MagicMock
from backtest.engine import BacktestEngine
from backtest.models import TickerAssignment


def _provider(df_map):
    p = MagicMock()
    p.get_ohlcv.side_effect = lambda t, s, e: df_map.get(t)
    return p


def test_run_returns_v2_backtest_result_shape():
    df = pd.DataFrame([
        {'date':'2025-01-02','open':100,'high':100,'low':100,'close':100,'volume':1000,'quality_flag':'clean'},
        {'date':'2025-01-03','open':105,'high':105,'low':105,'close':105,'volume':1000,'quality_flag':'clean'},
    ])
    eng = BacktestEngine(_provider({'2330': df}))
    r = eng.run(
        assignments=[TickerAssignment('2330','dip_and_take_profit',
                                       {'dip_pct':0.05,'take_profit_pct':0.05,
                                        'add_amount':10000,'max_position':100000,
                                        'max_hold_days':60})],
        start=date(2025,1,1), end=date(2025,1,31),
        initial_capital=500_000, execution_price='close',
    )
    assert r.initial_capital == 500_000
    assert r.execution_price == 'close'
    assert len(r.ticker_results) == 1
    assert r.ticker_results[0].ticker == '2330'
    assert len(r.daily_snapshots) >= 1
    assert all(hasattr(s,'cash') and hasattr(s,'position_value') for s in r.daily_snapshots)


def test_shared_capital_blocks_overspending():
    df = pd.DataFrame([
        {'date':'2025-01-02','open':100,'high':100,'low':100,'close':100,'volume':1000,'quality_flag':'clean'},
    ])
    eng = BacktestEngine(_provider({'2330': df, '2317': df}))
    common = {'dip_pct':0.05,'take_profit_pct':0.05,'add_amount':6000,
              'max_position':100000,'max_hold_days':60}
    r = eng.run(
        assignments=[
            TickerAssignment('2330','dip_and_take_profit', common),
            TickerAssignment('2317','dip_and_take_profit', common),
        ],
        start=date(2025,1,1), end=date(2025,1,31),
        initial_capital=10_000, execution_price='close',
    )
    buys = [t for tr in r.ticker_results for t in tr.trades if t.action == 'BUY']
    assert len(buys) == 1


def test_execution_price_open_used_for_settlement():
    df = pd.DataFrame([
        {'date':'2025-01-02','open':90,'high':100,'low':85,'close':95,'volume':1000,'quality_flag':'clean'},
    ])
    eng = BacktestEngine(_provider({'2330': df}))
    r = eng.run(
        assignments=[TickerAssignment('2330','dip_and_take_profit',
                                       {'dip_pct':0.05,'take_profit_pct':0.05,
                                        'add_amount':9_000,'max_position':100_000,
                                        'max_hold_days':60})],
        start=date(2025,1,1), end=date(2025,1,31),
        initial_capital=500_000, execution_price='open',
    )
    assert r.ticker_results[0].trades[0].price == 90


def test_infinite_average_reentry():
    df = pd.DataFrame([
        {'date':'2025-01-02','open':100,'high':100,'low':100,'close':100,'volume':1000,'quality_flag':'clean'},
        {'date':'2025-01-03','open':200,'high':200,'low':200,'close':200,'volume':1000,'quality_flag':'clean'},
        {'date':'2025-01-06','open':95, 'high':95, 'low':95, 'close':95, 'volume':1000,'quality_flag':'clean'},
    ])
    eng = BacktestEngine(_provider({'2330': df}))
    r = eng.run(
        assignments=[TickerAssignment('2330','infinite_average_v0',
                                       {'dip_pct':0.05,'take_profit_pct':0.05,
                                        'add_amount':5_000,'max_position':100_000})],
        start=date(2025,1,1), end=date(2025,1,31),
        initial_capital=500_000, execution_price='close',
    )
    actions = [t.action for t in r.ticker_results[0].trades]
    assert actions[0] == 'BUY'
    assert 'SELL' in actions
    assert actions.count('BUY') >= 2  # re-entry happened
```

- [ ] **Step 2: Run test — fail**

Run: `pytest tests/backtest/test_engine_v2.py -v`
Expected: FAIL.

- [ ] **Step 3: Replace engine.py**

Replace `backtest/engine.py`:
```python
from __future__ import annotations
import math
from datetime import date
from typing import TYPE_CHECKING

from backtest.metrics import MetricsCalculator
from backtest.models import (
    BacktestResult, DailySnapshot, PriceContext, Position,
    TickerAssignment, TickerResult, TickerState, Trade,
)

if TYPE_CHECKING:
    from data.provider import DataProvider
    from strategy.base import BaseStrategy

BUY_FEE_RATE = 0.001425
SELL_FEE_RATE = 0.001425
SELL_TAX_RATE = 0.003


def _build_strategy(class_name: str, params: dict) -> "BaseStrategy":
    if class_name == 'dip_and_take_profit':
        from strategy.dip_and_take_profit import DipAndTakeProfitStrategy
        return DipAndTakeProfitStrategy(
            dip_pct=params['dip_pct'],
            take_profit_pct=params['take_profit_pct'],
            add_amount=params['add_amount'],
            max_position=params['max_position'],
            max_hold_days=int(params['max_hold_days']),
        )
    if class_name == 'infinite_average_v0':
        from strategy.infinite_average_v0 import InfiniteAverageV0Strategy
        return InfiniteAverageV0Strategy(
            dip_pct=params['dip_pct'],
            take_profit_pct=params['take_profit_pct'],
            add_amount=params['add_amount'],
            max_position=params['max_position'],
        )
    raise ValueError(f"Unknown strategy class: {class_name}")


def _ctx_from_row(dt: date, row, execution_price: str) -> PriceContext:
    o = float(row['open']); c = float(row['close'])
    h = float(row['high']); lo = float(row['low'])
    vwap = (h + lo + c) / 3
    if execution_price == 'open':
        price = o
    elif execution_price == 'vwap':
        price = vwap
    else:
        price = c
    qf = row['quality_flag'] if 'quality_flag' in row else 'clean'
    return PriceContext(date=dt, open=o, close=c, vwap=vwap, price=price, quality_flag=qf)


class BacktestEngine:
    def __init__(self, provider: "DataProvider") -> None:
        self.provider = provider

    def run(self, assignments: list[TickerAssignment], start: date, end: date,
            initial_capital: float, execution_price: str = "close") -> BacktestResult:

        cash = initial_capital
        states: dict[str, TickerState] = {a.ticker: TickerState() for a in assignments}
        strategies = {a.ticker: _build_strategy(a.strategy_class, a.params)
                       for a in assignments}

        ohlcv_map = {}
        for a in assignments:
            df = self.provider.get_ohlcv(a.ticker, start, end)
            if df is not None and not df.empty:
                ohlcv_map[a.ticker] = df

        all_dates = sorted({d for df in ohlcv_map.values() for d in df['date'].tolist()})

        per_ticker_trades: dict[str, list[Trade]] = {a.ticker: [] for a in assignments}
        daily_snapshots: list[DailySnapshot] = []

        for dt_str in all_dates:
            dt = date.fromisoformat(dt_str)
            if not (start <= dt <= end):
                continue

            for ticker, df in ohlcv_map.items():
                rdf = df[df['date'] == dt_str]
                if rdf.empty:
                    continue
                row = rdf.iloc[0]
                ctx = _ctx_from_row(dt, row, execution_price)
                state = states[ticker]
                action = strategies[ticker].on_price_update(ctx, state)

                if action.type == "BUY" and action.amount > 0:
                    shares = math.floor(action.amount / ctx.price)
                    if shares == 0:
                        continue
                    cost = shares * ctx.price
                    fee = round(cost * BUY_FEE_RATE)
                    if cost + fee > cash:
                        continue
                    cash -= cost + fee
                    if state.position is None:
                        state.position = Position(
                            ticker=ticker, shares=shares, avg_cost=ctx.price,
                            entry_date=dt, total_invested=cost + fee,
                        )
                    else:
                        total_shares = state.position.shares + shares
                        new_total = state.position.total_invested + cost + fee
                        state.position = Position(
                            ticker=ticker, shares=total_shares,
                            avg_cost=new_total / total_shares,
                            entry_date=state.position.entry_date,
                            total_invested=new_total,
                        )
                    state.last_sell_price = None
                    per_ticker_trades[ticker].append(Trade(
                        ticker=ticker, action='BUY', date=dt,
                        price=ctx.price, shares=shares, amount=cost,
                        fee=fee, tax=0.0,
                    ))

                elif action.type == "SELL" and state.position is not None:
                    pos = state.position
                    proceeds = pos.shares * ctx.price
                    fee = round(proceeds * SELL_FEE_RATE)
                    tax = round(proceeds * SELL_TAX_RATE)
                    net = proceeds - fee - tax
                    realized = net - pos.total_invested
                    hold_days = (dt - pos.entry_date).days
                    cash += net
                    per_ticker_trades[ticker].append(Trade(
                        ticker=ticker, action='SELL', date=dt,
                        price=ctx.price, shares=pos.shares, amount=proceeds,
                        fee=fee, tax=tax, realized_pnl=realized, hold_days=hold_days,
                    ))
                    state.last_sell_price = ctx.price
                    state.position = None

            pos_value = 0.0
            for ticker, state in states.items():
                if state.position is None or ticker not in ohlcv_map:
                    continue
                rdf = ohlcv_map[ticker][ohlcv_map[ticker]['date'] == dt_str]
                if rdf.empty:
                    continue
                ctx = _ctx_from_row(dt, rdf.iloc[0], execution_price)
                pos_value += state.position.shares * ctx.price
            daily_snapshots.append(DailySnapshot(date=dt, cash=cash, position_value=pos_value))

        ticker_results = []
        for a in assignments:
            trades = per_ticker_trades[a.ticker]
            metrics = MetricsCalculator(
                trades=trades,
                snapshots=[(s.date, s.total) for s in daily_snapshots],
                initial_capital=initial_capital,
            ).calculate()
            ticker_results.append(TickerResult(
                ticker=a.ticker, strategy_class=a.strategy_class, params=a.params,
                trades=trades, metrics=metrics, final_position=states[a.ticker].position,
            ))

        return BacktestResult(
            initial_capital=initial_capital, execution_price=execution_price,
            start=start, end=end,
            ticker_results=ticker_results, daily_snapshots=daily_snapshots,
            final_cash=cash,
        )
```

- [ ] **Step 4: Run test — pass**

Run: `pytest tests/backtest/test_engine_v2.py -v`
Expected: 4 passed.

- [ ] **Step 5: Remove obsolete v1 engine test**

Run: `git rm tests/backtest/test_engine.py 2>/dev/null || true`
If the file doesn't exist or has been adapted, skip. The new `test_engine_v2.py` is canonical.

- [ ] **Step 6: Run full pytest**

Run: `pytest --tb=short`
Expected: all Phase 1–4 tests pass. UI tests not yet written, no failures expected outside Phase 5–6 modules.

- [ ] **Step 7: Commit**

```bash
git add backtest/engine.py tests/backtest/test_engine_v2.py
git rm tests/backtest/test_engine.py 2>/dev/null || true
git commit -m "refactor(engine): per-ticker assignments + execution_price + cash/pos snapshots"
```

---

## Phase 5 — UI Components

### Task 11: Charts (3-line, normalized, K-line + overlay)

**Files:**
- Modify: `ui/components/charts.py`
- Test: `tests/ui/test_charts.py`

- [ ] **Step 1: Write failing test**

Create `tests/ui/__init__.py` (empty) and `tests/ui/test_charts.py`:
```python
from __future__ import annotations
from datetime import date
import pandas as pd
from backtest.models import DailySnapshot, Trade


def test_portfolio_3line_chart_has_three_traces():
    from ui.components.charts import portfolio_3line_chart
    snaps = [DailySnapshot(date(2025,1,2), 100, 50),
             DailySnapshot(date(2025,1,3), 90, 70)]
    fig = portfolio_3line_chart(snaps)
    assert len(fig.data) == 3
    names = [t.name for t in fig.data]
    assert '現金' in names and '部位市值' in names and '總資產' in names


def test_normalized_price_chart_starts_at_one():
    from ui.components.charts import normalized_price_chart
    df = pd.DataFrame([
        {'date':'2025-01-02','close':100},
        {'date':'2025-01-03','close':110},
    ])
    fig = normalized_price_chart({'2330': df})
    trace = fig.data[0]
    assert abs(trace.y[0] - 1.0) < 1e-9
    assert abs(trace.y[1] - 1.1) < 1e-9


def test_candlestick_chart_with_invested_overlay():
    from ui.components.charts import candlestick_chart
    ohlcv = pd.DataFrame([
        {'date':'2025-01-02','open':100,'high':105,'low':95,'close':100,'quality_flag':'clean'},
        {'date':'2025-01-03','open':100,'high':105,'low':95,'close':100,'quality_flag':'forward_filled'},
    ])
    trades = [Trade(ticker='2330', action='BUY', date=date(2025,1,2),
                     price=100, shares=10, amount=1000, fee=2, tax=0)]
    fig = candlestick_chart(ohlcv, trades)
    assert any(t.type == 'candlestick' for t in fig.data)
    assert any(getattr(t, 'mode', None) == 'lines' and t.name == '累計投入' for t in fig.data)
```

- [ ] **Step 2: Run test — fail**

Run: `pytest tests/ui/test_charts.py -v`
Expected: FAIL.

- [ ] **Step 3: Replace charts.py**

Replace `ui/components/charts.py`:
```python
from __future__ import annotations
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from backtest.models import DailySnapshot, Trade


def portfolio_3line_chart(snaps: list[DailySnapshot]) -> go.Figure:
    if not snaps:
        return go.Figure()
    dates = [s.date for s in snaps]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=dates, y=[s.cash for s in snaps],
                              mode='lines', name='現金',
                              line=dict(color='#2e7d32', width=1.5)))
    fig.add_trace(go.Scatter(x=dates, y=[s.position_value for s in snaps],
                              mode='lines', name='部位市值',
                              line=dict(color='#1976d2', width=1.5)))
    fig.add_trace(go.Scatter(x=dates, y=[s.total for s in snaps],
                              mode='lines', name='總資產',
                              line=dict(color='#212121', width=2.5)))
    fig.update_layout(
        height=380, margin=dict(t=20, b=30, l=40, r=20),
        legend=dict(orientation='h', y=1.05),
        yaxis=dict(title='NTD', tickformat=','),
    )
    return fig


def normalized_price_chart(ohlcv_map: dict[str, pd.DataFrame]) -> go.Figure:
    fig = go.Figure()
    for ticker, df in ohlcv_map.items():
        if df is None or df.empty:
            continue
        df = df.sort_values('date').reset_index(drop=True)
        base = float(df.iloc[0]['close'])
        if base == 0:
            continue
        fig.add_trace(go.Scatter(
            x=df['date'].tolist(),
            y=(df['close'] / base).tolist(),
            mode='lines', name=ticker,
        ))
    fig.update_layout(
        height=360, margin=dict(t=20, b=30, l=40, r=20),
        yaxis=dict(title='Normalized (base=1.0)'),
        legend=dict(orientation='h', y=1.05),
    )
    return fig


def candlestick_chart(ohlcv: pd.DataFrame, trades: list[Trade]) -> go.Figure:
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                         row_heights=[0.7, 0.3], vertical_spacing=0.05,
                         subplot_titles=('K 線', '累計投入'))

    if ohlcv is not None and not ohlcv.empty:
        fig.add_trace(go.Candlestick(
            x=ohlcv['date'], open=ohlcv['open'], high=ohlcv['high'],
            low=ohlcv['low'], close=ohlcv['close'], name='K',
            increasing_line_color='#d32f2f', decreasing_line_color='#388e3c',
        ), row=1, col=1)

        if 'quality_flag' in ohlcv.columns:
            ff = ohlcv[ohlcv['quality_flag'] == 'forward_filled']
            for d in ff['date']:
                fig.add_vrect(x0=d, x1=d, fillcolor='#cccccc', opacity=0.3,
                               line_width=0, row=1, col=1)

    buys = [t for t in trades if t.action == 'BUY']
    sells = [t for t in trades if t.action == 'SELL']
    first_buy = buys[:1]
    add_buys = buys[1:]
    if first_buy:
        fig.add_trace(go.Scatter(
            x=[t.date for t in first_buy], y=[t.price for t in first_buy],
            mode='markers', name='買入',
            marker=dict(symbol='triangle-up', color='#1976d2', size=12),
        ), row=1, col=1)
    if add_buys:
        fig.add_trace(go.Scatter(
            x=[t.date for t in add_buys], y=[t.price for t in add_buys],
            mode='markers', name='加碼',
            marker=dict(symbol='triangle-up', color='#64b5f6', size=10,
                         line=dict(color='#1976d2', width=1)),
        ), row=1, col=1)
    if sells:
        fig.add_trace(go.Scatter(
            x=[t.date for t in sells], y=[t.price for t in sells],
            mode='markers', name='賣出',
            marker=dict(symbol='triangle-down', color='#f57c00', size=12),
        ), row=1, col=1)

    if trades and ohlcv is not None and not ohlcv.empty:
        dates_sorted = sorted({d for d in ohlcv['date'].tolist()})
        trade_by_date: dict[str, list[Trade]] = {}
        for t in trades:
            trade_by_date.setdefault(t.date.isoformat(), []).append(t)
        invested = 0.0
        series_x, series_y = [], []
        for d in dates_sorted:
            for t in trade_by_date.get(d, []):
                if t.action == 'BUY':
                    invested += t.amount + t.fee
                elif t.action == 'SELL':
                    invested = 0.0
            series_x.append(d); series_y.append(invested)
        fig.add_trace(go.Scatter(
            x=series_x, y=series_y, mode='lines', name='累計投入',
            line=dict(color='#7b1fa2', width=2),
        ), row=2, col=1)

    fig.update_layout(
        height=600, margin=dict(t=40, b=30, l=40, r=20),
        legend=dict(orientation='h', y=1.05),
        xaxis_rangeslider_visible=False,
    )
    return fig


# Back-compat shims
def stock_overlay_chart(ohlcv_map: dict[str, pd.DataFrame]) -> go.Figure:
    return normalized_price_chart(ohlcv_map)


def portfolio_line_chart(results) -> go.Figure:
    if not results:
        return go.Figure()
    r = results[0] if isinstance(results, list) else results
    if hasattr(r, 'daily_snapshots'):
        return portfolio_3line_chart(r.daily_snapshots)
    return go.Figure()
```

- [ ] **Step 4: Run test — pass**

Run: `pytest tests/ui/test_charts.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
mkdir -p tests/ui && touch tests/ui/__init__.py
git add ui/components/charts.py tests/ui/test_charts.py tests/ui/__init__.py
git commit -m "feat(ui/charts): 3-line portfolio, normalized overlay, candlestick with invested subplot"
```

---

## Phase 6 — UI Pages

### Task 12: Home page rewrite + state + tables

**Files:**
- Modify: `ui/state.py`
- Modify: `ui/components/tables.py`
- Modify: `ui/pages/home.py`
- Test: `tests/ui/test_home_layout.py`

- [ ] **Step 1: Write failing layout test**

Create `tests/ui/test_home_layout.py`:
```python
from __future__ import annotations


def test_layout_has_capital_and_exec_inputs():
    import dash
    dash.Dash(__name__, suppress_callback_exceptions=True)
    from ui.pages.home import layout
    html = str(layout())
    assert 'initial-capital' in html
    assert 'exec-price' in html


def test_default_dates_set_to_2026_to_today():
    import dash
    dash.Dash(__name__, suppress_callback_exceptions=True)
    from ui.pages.home import layout
    html = str(layout())
    assert '2026-01-01' in html
```

- [ ] **Step 2: Run test — fail**

Run: `pytest tests/ui/test_home_layout.py -v`
Expected: FAIL.

- [ ] **Step 3: Replace ui/state.py**

Replace `ui/state.py`:
```python
from __future__ import annotations
from backtest.models import BacktestResult

_results: list[BacktestResult] = []


def set_results(results: list[BacktestResult]) -> None:
    _results.clear()
    _results.extend(results)


def current_result() -> BacktestResult | None:
    return _results[0] if _results else None
```

- [ ] **Step 4: Replace ui/components/tables.py**

Replace `ui/components/tables.py`:
```python
from __future__ import annotations
from backtest.models import BacktestResult, Trade

STRATEGY_LABEL = {
    'dip_and_take_profit': '逢跌加碼止盈',
    'infinite_average_v0': '無限攤平_V0',
}


def per_ticker_rows(result: BacktestResult) -> list[dict]:
    rows = []
    for tr in result.ticker_results:
        m = tr.metrics
        if m is None:
            continue
        label = STRATEGY_LABEL.get(tr.strategy_class, tr.strategy_class)
        rows.append({
            'ticker':         f"[{tr.ticker}](/stock/{tr.strategy_class}/{tr.ticker})",
            'strategy':       f"[{label}](/strategy/{tr.strategy_class})",
            'realized_pnl':   f"${m.realized_pnl:+,.0f} ({m.realized_pnl_pct:+.1%})",
            'unrealized_pnl': f"${m.unrealized_pnl:+,.0f}",
            'final_nav':      f"${m.final_nav:,.0f}",
            'mdd':            f"{m.max_drawdown:.1%}",
            'sharpe':         f"{m.sharpe_ratio:.2f}",
            'win_rate':       f"{m.win_rate:.0%}",
            'profit_factor':  f"{m.profit_factor:.2f}" if m.profit_factor != float('inf') else '∞',
            'avg_hold_days':  f"{m.avg_hold_days:.0f}d",
        })
    return rows


def trades_table_rows(trades: list[Trade]) -> list[dict]:
    return [{
        'date':        t.date.isoformat(),
        'action':      t.action,
        'shares':      t.shares,
        'price':       f"${t.price:,.0f}",
        'amount':      f"${t.amount:,.0f}",
        'fee_tax':     f"${t.fee + t.tax:,.0f}",
        'realized_pnl': f"${t.realized_pnl:+,.0f}" if t.realized_pnl is not None else '—',
        'hold_days':   t.hold_days if t.hold_days is not None else '—',
    } for t in trades]
```

- [ ] **Step 5: Replace ui/pages/home.py**

Replace `ui/pages/home.py`:
```python
from __future__ import annotations
from datetime import date
import dash
from dash import html, dash_table, dcc, callback, Input, Output, State, ALL, MATCH, no_update

from ui.components.charts import portfolio_3line_chart
from ui.components.tables import per_ticker_rows
from ui.state import current_result, set_results

dash.register_page(__name__, path='/')

_INPUT = {'border':'1px solid #ddd','borderRadius':'4px','padding':'6px 10px',
          'fontSize':'13px','width':'100%','boxSizing':'border-box'}
_LABEL = {'fontSize':'12px','color':'#666','marginBottom':'4px','display':'block'}
_COL = {'flex':'1','marginRight':'12px'}
_CARD = {'background':'#f8f9fa','border':'1px solid #e0e0e0','borderRadius':'8px',
         'padding':'20px','marginBottom':'16px'}

STRATEGY_OPTIONS = [
    {'label':'無限攤平_V0','value':'infinite_average_v0'},
    {'label':'逢跌加碼止盈','value':'dip_and_take_profit'},
]


def _card(step, title, children):
    return html.Div([
        html.Div([
            html.Span(f"Step {step}", style={
                'background':'#1a73e8','color':'#fff','fontSize':'11px',
                'fontWeight':'600','padding':'2px 8px','borderRadius':'10px',
                'marginRight':'8px'}),
            html.Span(title, style={'fontSize':'14px','fontWeight':'600','color':'#333'}),
        ], style={'marginBottom':'16px'}),
        *children,
    ], style=_CARD)


def _num(id_, label, value, min_, max_, step):
    spec = {'id': id_, 'type':'number', 'value':value, 'min':min_, 'step':step,
             'style':{**_INPUT}}
    if max_ is not None:
        spec['max'] = max_
    return html.Div([html.Label(label, style=_LABEL), dcc.Input(**spec)], style=_COL)


def _param_inputs(idx, strategy_class):
    if strategy_class == 'dip_and_take_profit':
        children = [
            _num({'type':'param','idx':idx,'name':'dip_pct'},        '逢跌幅度(%)',    7, 1, 50, 0.5),
            _num({'type':'param','idx':idx,'name':'take_profit_pct'},'止盈幅度(%)',    5, 0.5, 50, 0.5),
            _num({'type':'param','idx':idx,'name':'add_amount'},     '單次加碼(元)', 10000, 1000, None, 1000),
            _num({'type':'param','idx':idx,'name':'max_position'},   '部位上限(元)',100000,10000,None,10000),
            _num({'type':'param','idx':idx,'name':'max_hold_days'},  '最長持有天數',  60, 1, None, 1),
        ]
    else:
        children = [
            _num({'type':'param','idx':idx,'name':'dip_pct'},        '加碼/再進場跌幅(%)', 5, 1, 50, 0.5),
            _num({'type':'param','idx':idx,'name':'take_profit_pct'},'止盈幅度(%)',         5, 0.5, 50, 0.5),
            _num({'type':'param','idx':idx,'name':'add_amount'},     '單次加碼(元)',      10000, 1000, None, 1000),
            _num({'type':'param','idx':idx,'name':'max_position'},   '部位上限(元)',     100000,10000,None,10000),
        ]
    return html.Div(children, style={'display':'flex','gap':'8px'})


def _ticker_row(idx, ticker):
    return html.Div([
        html.Div(ticker, style={'fontWeight':'600','width':'80px'}),
        html.Div([
            html.Label('策略', style=_LABEL),
            dcc.Dropdown(id={'type':'strat-select','idx':idx},
                          options=STRATEGY_OPTIONS, value='infinite_average_v0',
                          clearable=False, style={'fontSize':'13px'}),
        ], style={'width':'180px','marginRight':'12px'}),
        html.Div(id={'type':'param-block','idx':idx}, style={'flex':'1'}),
    ], style={'display':'flex','alignItems':'center','marginBottom':'10px',
              'padding':'8px','border':'1px solid #eee','borderRadius':'4px'})


def _render_results():
    r = current_result()
    if r is None:
        return html.Div('尚無回測結果，請完成上方設定後點擊「執行回測」。',
                         style={'color':'#999','padding':'20px 0','fontSize':'14px'})
    columns = [
        {'name':'標的','id':'ticker','presentation':'markdown'},
        {'name':'策略','id':'strategy','presentation':'markdown'},
        {'name':'已實現損益','id':'realized_pnl'},
        {'name':'未實現損益','id':'unrealized_pnl'},
        {'name':'最終淨值','id':'final_nav'},
        {'name':'MDD','id':'mdd'},
        {'name':'Sharpe','id':'sharpe'},
        {'name':'Win Rate','id':'win_rate'},
        {'name':'Profit Factor','id':'profit_factor'},
        {'name':'Avg Hold (days)','id':'avg_hold_days'},
    ]
    return html.Div([
        html.H2('回測結果', style={'marginBottom':'16px','fontSize':'18px'}),
        dcc.Graph(figure=portfolio_3line_chart(r.daily_snapshots),
                   style={'marginBottom':'24px'}),
        html.H3('每檔績效', style={'marginBottom':'8px','fontSize':'14px','opacity':'.7'}),
        dash_table.DataTable(
            data=per_ticker_rows(r), columns=columns,
            style_cell={'textAlign':'left','padding':'8px 12px','fontSize':'13px'},
            style_header={'fontWeight':'600','opacity':'.6','fontSize':'11px'},
        ),
    ])


def layout() -> html.Div:
    return html.Div([
        _card(1, '選擇模式', [
            dcc.RadioItems(id='mode-radio', value='manual', inline=True,
                options=[
                    {'label': html.Span('個股（手動）', style={'marginLeft':'6px','marginRight':'28px'}), 'value':'manual'},
                    {'label': html.Span('全隨機', style={'marginLeft':'6px','marginRight':'28px'}), 'value':'random'},
                    {'label': html.Span('半隨機', style={'marginLeft':'6px'}), 'value':'semi'},
                ],
                labelStyle={'cursor':'pointer','fontSize':'13px'}),
        ]),
        _card(2, '標的與全域設定', [
            html.Div([
                html.Div([html.Label('起始日期', style=_LABEL),
                          dcc.Input(id='start-date', type='date', value='2026-01-01', style=_INPUT)], style=_COL),
                html.Div([html.Label('結束日期', style=_LABEL),
                          dcc.Input(id='end-date', type='date', value=date.today().isoformat(), style=_INPUT)], style=_COL),
                html.Div([html.Label('總資金 (元)', style=_LABEL),
                          dcc.Input(id='initial-capital', type='number', value=500000, min=10000, step=10000, style=_INPUT)], style=_COL),
                html.Div([html.Label('執行價', style=_LABEL),
                          dcc.Dropdown(id='exec-price',
                                       options=[{'label':'收盤價','value':'close'},
                                                {'label':'開盤價','value':'open'},
                                                {'label':'VWAP','value':'vwap'}],
                                       value='close', clearable=False)],
                          style={**_COL,'marginRight':'0'}),
            ], style={'display':'flex','marginBottom':'14px'}),
            html.Div([
                html.Label('股票代號（逗號分隔）', style=_LABEL),
                dcc.Input(id='tickers-input', type='text', value='2330',
                          placeholder='2330, 2317, 0050', style=_INPUT),
            ], id='sec-manual', style={'marginBottom':'4px'}),
            html.Div([
                html.Label('隨機選取檔數', style=_LABEL),
                dcc.Input(id='n-stocks', type='number', value=5, min=1, max=100, step=1,
                          style={**_INPUT,'width':'120px'}),
            ], id='sec-n', style={'display':'none'}),
            html.Div([
                html.Label('市場別', style={**_LABEL,'marginTop':'10px'}),
                dcc.RadioItems(id='market-radio', value='all', inline=True,
                    options=[
                        {'label':html.Span('全部',style={'marginLeft':'5px','marginRight':'20px'}),'value':'all'},
                        {'label':html.Span('上市',style={'marginLeft':'5px','marginRight':'20px'}),'value':'TWSE'},
                        {'label':html.Span('上櫃',style={'marginLeft':'5px'}),'value':'TPEx'},
                    ]),
            ], id='sec-market', style={'display':'none'}),
        ]),
        _card(3, '指派策略', [html.Div(id='strategy-assignments')]),
        html.Div([
            html.Button('執行回測', id='run-btn', n_clicks=0, style={
                'backgroundColor':'#1a73e8','color':'#fff','border':'none',
                'borderRadius':'4px','padding':'10px 32px','fontSize':'14px',
                'cursor':'pointer','fontWeight':'500'}),
            html.Span(id='run-error', style={'marginLeft':'16px','color':'#c62828','fontSize':'13px'}),
        ], style={'marginBottom':'28px'}),
        dcc.Loading(type='circle',
                    children=html.Div(id='home-content', children=_render_results())),
    ])


@callback(
    Output('sec-manual','style'), Output('sec-n','style'), Output('sec-market','style'),
    Input('mode-radio','value'),
)
def _toggle_sections(mode):
    show = {'marginBottom':'4px'}
    hide = {'display':'none'}
    if mode == 'manual': return show, hide, hide
    if mode == 'random': return hide, show, hide
    return hide, show, {}


@callback(
    Output('strategy-assignments','children'),
    Input('mode-radio','value'),
    Input('tickers-input','value'),
)
def _render_assignments(mode, tickers_str):
    if mode == 'manual':
        tickers = [t.strip() for t in str(tickers_str or '').replace('，', ',').split(',') if t.strip()]
        if not tickers:
            return html.Div('請先在 Step 2 輸入股票代號',
                             style={'color':'#999','fontSize':'13px'})
        return [_ticker_row(i, t) for i, t in enumerate(tickers)]
    return _ticker_row(0, '(隨機抽中的所有 ticker 將共用同一策略)')


@callback(
    Output({'type':'param-block','idx':MATCH},'children'),
    Input({'type':'strat-select','idx':MATCH},'value'),
    State({'type':'strat-select','idx':MATCH},'id'),
)
def _render_params(strat_class, id_):
    return _param_inputs(id_['idx'], strat_class)


@callback(
    Output('home-content','children'),
    Output('run-error','children'),
    Input('run-btn','n_clicks'),
    State('mode-radio','value'),
    State('tickers-input','value'),
    State('start-date','value'),
    State('end-date','value'),
    State('n-stocks','value'),
    State('market-radio','value'),
    State('initial-capital','value'),
    State('exec-price','value'),
    State({'type':'strat-select','idx':ALL},'value'),
    State({'type':'param','idx':ALL,'name':ALL},'value'),
    State({'type':'param','idx':ALL,'name':ALL},'id'),
    prevent_initial_call=True,
)
def _run_backtest(n, mode, tickers_str, start, end, n_stocks, market,
                   capital, exec_price, strat_classes, param_vals, param_ids):
    from data.provider import DataProvider
    from backtest.engine import BacktestEngine
    from backtest.models import TickerAssignment

    try:
        start_d = date.fromisoformat(start); end_d = date.fromisoformat(end)
    except (TypeError, ValueError):
        return no_update, '日期格式錯誤'
    if start_d >= end_d:
        return no_update, '起始日期須早於結束日期'

    provider = DataProvider()
    if mode == 'manual':
        tickers = [t.strip() for t in str(tickers_str or '').replace('，', ',').split(',') if t.strip()]
        if not tickers:
            return no_update, '請輸入股票代號'
    else:
        n_ = int(n_stocks or 5)
        tl = provider.get_ticker_list()
        if tl is None or tl.empty:
            return no_update, '無法取得股票清單'
        if mode == 'semi' and market and market != 'all':
            tl = tl[tl['market'] == market]
        if tl.empty:
            return no_update, '市場別無符合標的'
        import random as _rnd
        tickers = _rnd.sample(tl['ticker'].tolist(), min(n_, len(tl)))

    params_by_idx: dict[int, dict] = {}
    for pid, pval in zip(param_ids, param_vals):
        params_by_idx.setdefault(pid['idx'], {})[pid['name']] = float(pval)

    assignments = []
    if mode == 'manual':
        for i, ticker in enumerate(tickers):
            sc = strat_classes[i] if i < len(strat_classes) else 'infinite_average_v0'
            assignments.append(TickerAssignment(ticker, sc, params_by_idx.get(i, {})))
    else:
        sc = strat_classes[0] if strat_classes else 'infinite_average_v0'
        p = params_by_idx.get(0, {})
        for ticker in tickers:
            assignments.append(TickerAssignment(ticker, sc, dict(p)))

    for a in assignments:
        if 'dip_pct' in a.params:        a.params['dip_pct'] /= 100.0
        if 'take_profit_pct' in a.params: a.params['take_profit_pct'] /= 100.0

    try:
        result = BacktestEngine(provider).run(
            assignments, start_d, end_d, float(capital), exec_price)
    except Exception as e:
        return no_update, f'回測失敗：{e}'

    set_results([result])
    return _render_results(), ''
```

- [ ] **Step 6: Run test — pass**

Run: `pytest tests/ui/test_home_layout.py -v`
Expected: 2 passed.

- [ ] **Step 7: Commit**

```bash
git add ui/state.py ui/components/tables.py ui/pages/home.py tests/ui/test_home_layout.py
git commit -m "feat(ui/home): dynamic per-ticker Step 3, capital + exec-price, 3-line results"
```

---

### Task 13: Strategy class page

**Files:**
- Modify: `ui/pages/strategy.py`

- [ ] **Step 1: Replace strategy.py**

Replace `ui/pages/strategy.py`:
```python
from __future__ import annotations
from datetime import timedelta
import dash
import pandas as pd
from dash import html, dash_table, dcc

from ui.components.charts import normalized_price_chart
from ui.components.tables import STRATEGY_LABEL
from ui.state import current_result

dash.register_page(__name__, path_template='/strategy/<class_name>')


def layout(class_name: str = '') -> html.Div:
    label = STRATEGY_LABEL.get(class_name, class_name)
    result = current_result()
    if result is None:
        return html.Div('尚無回測結果', style={'padding':'40px'})

    matches = [tr for tr in result.ticker_results if tr.strategy_class == class_name]
    if not matches:
        return html.Div(f'此策略類別無 ticker：{class_name}', style={'padding':'40px'})

    ohlcv_map: dict[str, pd.DataFrame] = {}
    if result.daily_snapshots:
        from data.provider import DataProvider
        s = result.daily_snapshots[0].date - timedelta(days=14)
        e = result.daily_snapshots[-1].date + timedelta(days=14)
        provider = DataProvider()
        for tr in matches:
            df = provider.get_ohlcv(tr.ticker, s, e)
            if df is not None and not df.empty:
                ohlcv_map[tr.ticker] = df

    rows = []
    for tr in matches:
        sells = [t for t in tr.trades if t.realized_pnl is not None]
        realized = sum(t.realized_pnl for t in sells)
        wr = (sum(1 for t in sells if t.realized_pnl > 0) / len(sells)) if sells else 0.0
        rows.append({
            'ticker':       f"[{tr.ticker}](/stock/{class_name}/{tr.ticker})",
            'trade_count':  len(sells),
            'realized_pnl': f"${realized:+,.0f}",
            'win_rate':     f"{wr:.0%}",
        })

    columns = [
        {'name':'標的','id':'ticker','presentation':'markdown'},
        {'name':'交易次數','id':'trade_count'},
        {'name':'已實現損益','id':'realized_pnl'},
        {'name':'Win Rate','id':'win_rate'},
    ]
    return html.Div([
        html.A('← 返回主頁', href='/', style={'fontSize':'13px','opacity':'.6'}),
        html.H2(f'策略類別：{label}', style={'margin':'12px 0 20px'}),
        dcc.Graph(figure=normalized_price_chart(ohlcv_map), style={'marginBottom':'24px'}),
        html.H3('各標的表現', style={'fontSize':'14px','opacity':'.7','marginBottom':'8px'}),
        dash_table.DataTable(
            data=rows, columns=columns,
            style_cell={'textAlign':'left','padding':'8px 12px','fontSize':'13px'},
            style_header={'fontWeight':'600','opacity':'.6','fontSize':'11px'},
        ),
    ], style={'padding':'24px 0'})
```

- [ ] **Step 2: Smoke-import**

Run: `python3 -c "import ui.app; from dash import page_registry; print(any('strategy' in k for k in page_registry))"`
Expected: `True`.

- [ ] **Step 3: Commit**

```bash
git add ui/pages/strategy.py
git commit -m "feat(ui/strategy): strategy-class page with normalized overlay + ticker table"
```

---

### Task 14: Stock page

**Files:**
- Modify: `ui/pages/stock.py`

- [ ] **Step 1: Replace stock.py**

Replace `ui/pages/stock.py`:
```python
from __future__ import annotations
from datetime import timedelta
import pandas as pd
import dash
from dash import html, dash_table, dcc

from ui.components.charts import candlestick_chart
from ui.components.tables import trades_table_rows, STRATEGY_LABEL
from ui.state import current_result

dash.register_page(__name__, path_template='/stock/<class_name>/<ticker>')


def layout(class_name: str = '', ticker: str = '') -> html.Div:
    result = current_result()
    if result is None:
        return html.Div('尚無回測結果', style={'padding':'40px'})

    tr = next((x for x in result.ticker_results
                if x.strategy_class == class_name and x.ticker == ticker), None)
    if tr is None:
        return html.Div(f'找不到：{class_name} / {ticker}', style={'padding':'40px'})

    ohlcv_df = pd.DataFrame(columns=['date','open','high','low','close','quality_flag'])
    if result.daily_snapshots:
        from data.provider import DataProvider
        s = result.daily_snapshots[0].date - timedelta(days=14)
        e = result.daily_snapshots[-1].date + timedelta(days=14)
        df = DataProvider().get_ohlcv(ticker, s, e)
        if df is not None and not df.empty:
            ohlcv_df = df

    columns = [
        {'name':'日期','id':'date'},
        {'name':'動作','id':'action'},
        {'name':'股數','id':'shares'},
        {'name':'成交價','id':'price'},
        {'name':'成交金額','id':'amount'},
        {'name':'手續費+稅','id':'fee_tax'},
        {'name':'已實現損益','id':'realized_pnl'},
        {'name':'持有天數','id':'hold_days'},
    ]
    label = STRATEGY_LABEL.get(class_name, class_name)
    return html.Div([
        html.A(f'← 返回策略 {label}', href=f'/strategy/{class_name}',
               style={'fontSize':'13px','opacity':'.6'}),
        html.H2(f'{ticker} — {label}', style={'margin':'12px 0 20px'}),
        dcc.Graph(figure=candlestick_chart(ohlcv_df, tr.trades),
                   style={'marginBottom':'24px'}),
        html.H3('逐筆交易記錄',
                 style={'fontSize':'14px','opacity':'.7','marginBottom':'8px'}),
        dash_table.DataTable(
            data=trades_table_rows(tr.trades), columns=columns,
            style_cell={'textAlign':'left','padding':'8px 12px','fontSize':'13px'},
            style_header={'fontWeight':'600','opacity':'.6','fontSize':'11px'},
        ),
    ], style={'padding':'24px 0'})
```

- [ ] **Step 2: Smoke-import**

Run: `python3 -c "import ui.app"`
Expected: no exception.

- [ ] **Step 3: Commit**

```bash
git add ui/pages/stock.py
git commit -m "feat(ui/stock): K-line with distinct annotation colors + cumulative-invested subplot"
```

---

## Phase 7 — End-to-end Smoke

### Task 15: Smoke + HTTP route check

**Files:**
- Test: `tests/test_smoke_v2.py`

- [ ] **Step 1: Write smoke test**

Create `tests/test_smoke_v2.py`:
```python
from __future__ import annotations
from datetime import date
import pandas as pd
from unittest.mock import MagicMock
from backtest.engine import BacktestEngine
from backtest.models import TickerAssignment


def test_two_tickers_two_strategies():
    df_a = pd.DataFrame([
        {'date': f'2026-01-0{d}', 'open': 100+d, 'high': 105+d, 'low': 95+d,
         'close': 100+d, 'volume': 1000, 'quality_flag': 'clean'}
        for d in range(2, 7)
    ])
    df_b = pd.DataFrame([
        {'date': f'2026-01-0{d}', 'open': 50+d*2, 'high': 55+d*2, 'low': 45+d*2,
         'close': 50+d*2, 'volume': 1000, 'quality_flag': 'clean'}
        for d in range(2, 7)
    ])
    provider = MagicMock()
    provider.get_ohlcv.side_effect = lambda t, s, e: df_a if t == '2330' else df_b

    result = BacktestEngine(provider).run(
        assignments=[
            TickerAssignment('2330', 'dip_and_take_profit',
                {'dip_pct':0.05,'take_profit_pct':0.05,
                 'add_amount':5000,'max_position':50000,'max_hold_days':60}),
            TickerAssignment('2317', 'infinite_average_v0',
                {'dip_pct':0.05,'take_profit_pct':0.05,
                 'add_amount':5000,'max_position':50000}),
        ],
        start=date(2026,1,1), end=date(2026,1,31),
        initial_capital=100_000, execution_price='close',
    )
    assert len(result.ticker_results) == 2
    assert {tr.ticker for tr in result.ticker_results} == {'2330', '2317'}
    assert all(tr.metrics is not None for tr in result.ticker_results)
    assert len(result.daily_snapshots) >= 1
    assert result.daily_snapshots[0].cash <= 100_000
```

- [ ] **Step 2: Run smoke**

Run: `pytest tests/test_smoke_v2.py -v`
Expected: passed.

- [ ] **Step 3: Run full pytest**

Run: `pytest --tb=short`
Expected: all pass.

- [ ] **Step 4: HTTP route smoke**

Run:
```bash
pkill -f "ui.app" 2>/dev/null; sleep 1
python3 -m ui.app > /tmp/dash.log 2>&1 &
sleep 3
for url in / /strategy/infinite_average_v0 /stock/infinite_average_v0/2330; do
  echo -n "$url "
  curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8050$url
done
```
Expected: all `200`.

- [ ] **Step 5: Commit**

```bash
git add tests/test_smoke_v2.py
git commit -m "test(smoke): v2 engine end-to-end + HTTP route check"
```

---

## Phase 8 — Cleanup

### Task 16: DEVELOPMENT.md + dead-code sweep

**Files:**
- Modify: `DEVELOPMENT.md`

- [ ] **Step 1: Hunt v1 leftovers**

Run: `grep -rn "BacktestResult(\s*strategy_name\|strategy_name=" --include="*.py" .`
Expected: no hits (or only in tests already updated).

If hits found in non-test files, edit those files to use v2 schema. If hits in tests, decide: keep if testing v1 backward-compat shim, else update.

- [ ] **Step 2: Update DEVELOPMENT.md**

Edit `DEVELOPMENT.md`. Locate the `## Architecture` section (or top of doc) and replace with:
```markdown
## Architecture (v2)

Five-layer monolith, unidirectional dependencies:

```
ui/         Layer 5 — Dash pages (home / strategy-class / stock)
backtest/   Layer 4 — engine + metrics; per-ticker results + shared cash pool
strategy/   Layer 3 — BaseStrategy ABC; DipAndTakeProfit + InfiniteAverageV0
selection/  Layer 2 — Manual / Random / Semi
data/       Layer 1 — DataProvider with finmind/yfinance/forward-fill + quality_flag
```

### Key v2 design points

- **Per-ticker assignment**: `BacktestEngine.run(assignments: list[TickerAssignment])` — each ticker has its own strategy class + params.
- **Shared cash pool**: one capital float across all tickers in a run.
- **Execution price**: `close | open | vwap`, set once per run.
- **Net unrealized PnL**: `(shares × price × (1-sell_fee-tax)) − total_invested`. Used by both strategy triggers and UI display.
- **Data quality**: `quality_flag ∈ {clean, yfinance, forward_filled}`. Forward-filled rows are always retried on next read.
- **UI routes**: `/`, `/strategy/<class>`, `/stock/<class>/<ticker>` where `<class>` is English (avoids URL-encode issues).
```

- [ ] **Step 3: Commit**

```bash
git add DEVELOPMENT.md
git commit -m "docs: DEVELOPMENT.md reflects v2 architecture"
```

---

## Done

After all 16 tasks:
- v2 backtest engine runs per-ticker mixed strategies with shared capital
- New InfiniteAverageV0 strategy supports re-entry after drop
- Data quality layer detects gaps + falls back through finmind → yfinance → forward-fill
- UI shows 3-line chart, per-ticker results, strategy-class overlay, K-line + invested overlay
- Full test suite passes with v2 schema
