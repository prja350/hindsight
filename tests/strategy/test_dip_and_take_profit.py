from __future__ import annotations
from datetime import date
from backtest.models import Position, PriceContext, TickerState
from strategy.dip_and_take_profit import DipAndTakeProfitStrategy


def _ctx(d, price):
    return PriceContext(d, price, price, price, price, 'clean')


def test_first_entry_buys():
    s = DipAndTakeProfitStrategy(0.05, 0.05, 10_000, 100_000, 60)
    a = s.on_price_update(_ctx(date(2025, 1, 2), 100), TickerState())
    assert a.type == "BUY" and a.amount == 10_000


def test_adds_when_below_dip_threshold():
    pos = Position('2330', shares=10, avg_cost=100, entry_date=date(2025, 1, 2),
                   total_invested=1000)
    s = DipAndTakeProfitStrategy(0.05, 0.05, 10_000, 100_000, 60)
    a = s.on_price_update(_ctx(date(2025, 1, 10), 80), TickerState(position=pos))
    assert a.type == "BUY"


def test_sells_at_take_profit():
    pos = Position('2330', shares=10, avg_cost=100, entry_date=date(2025, 1, 2),
                   total_invested=1000)
    s = DipAndTakeProfitStrategy(0.05, 0.05, 10_000, 100_000, 60)
    a = s.on_price_update(_ctx(date(2025, 1, 10), 120), TickerState(position=pos))
    assert a.type == "SELL"


def test_max_hold_forces_sell():
    pos = Position('2330', shares=10, avg_cost=100,
                   entry_date=date(2025, 1, 2), total_invested=1000)
    s = DipAndTakeProfitStrategy(0.05, 0.05, 10_000, 100_000, 5)
    a = s.on_price_update(_ctx(date(2025, 1, 10), 100), TickerState(position=pos))
    assert a.type == "SELL"


def test_max_position_blocks_add():
    pos = Position('2330', shares=1000, avg_cost=100, entry_date=date(2025, 1, 2),
                   total_invested=100_000)
    s = DipAndTakeProfitStrategy(0.05, 0.05, 10_000, 100_000, 60)
    a = s.on_price_update(_ctx(date(2025, 1, 5), 80), TickerState(position=pos))
    assert a.type == "HOLD"
