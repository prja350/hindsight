from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date
from typing import Literal


@dataclass
class Action:
    type: Literal["BUY", "SELL", "HOLD"]
    amount: float = 0.0  # BUY: 買入金額(元); SELL: 0 = 全賣


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
    realized_pnl: float | None = None  # 僅 SELL 時有值
    hold_days: int | None = None        # 僅 SELL 時有值


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
class BacktestResult:
    strategy_name: str
    trades: list[Trade] = field(default_factory=list)
    daily_snapshots: list[tuple[date, float]] = field(default_factory=list)
    metrics: Metrics | None = None
