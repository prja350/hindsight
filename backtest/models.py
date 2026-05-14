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
    total_invested: float


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
