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
