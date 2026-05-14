from __future__ import annotations
from datetime import date
from backtest.models import Position, PriceContext, TickerState
from strategy.infinite_average_v0 import InfiniteAverageV0Strategy


def _ctx(d, p):
    return PriceContext(d, p, p, p, p, 'clean')


def test_first_entry_when_no_position_no_last_sell():
    s = InfiniteAverageV0Strategy(0.05, 0.05, 10_000, 100_000)
    a = s.on_price_update(_ctx(date(2025, 1, 2), 100), TickerState())
    assert a.type == "BUY" and a.amount == 10_000


def test_no_entry_when_last_sell_drop_below_threshold():
    s = InfiniteAverageV0Strategy(0.05, 0.05, 10_000, 100_000)
    st = TickerState(position=None, last_sell_price=100)
    a = s.on_price_update(_ctx(date(2025, 1, 5), 98), st)
    assert a.type == "HOLD"


def test_reentry_when_drop_meets_threshold():
    s = InfiniteAverageV0Strategy(0.05, 0.05, 10_000, 100_000)
    st = TickerState(position=None, last_sell_price=100)
    a = s.on_price_update(_ctx(date(2025, 1, 5), 95), st)
    assert a.type == "BUY"


def test_add_when_net_pnl_below_negative_dip():
    pos = Position('2330', shares=10, avg_cost=100, entry_date=date(2025, 1, 2),
                   total_invested=1000)
    s = InfiniteAverageV0Strategy(0.05, 0.05, 10_000, 100_000)
    a = s.on_price_update(_ctx(date(2025, 1, 10), 80), TickerState(position=pos))
    assert a.type == "BUY"


def test_max_position_blocks_add():
    pos = Position('2330', shares=1000, avg_cost=100, entry_date=date(2025, 1, 2),
                   total_invested=100_000)
    s = InfiniteAverageV0Strategy(0.05, 0.05, 10_000, 100_000)
    a = s.on_price_update(_ctx(date(2025, 1, 10), 80), TickerState(position=pos))
    assert a.type == "HOLD"


def test_sells_at_take_profit():
    pos = Position('2330', shares=10, avg_cost=100, entry_date=date(2025, 1, 2),
                   total_invested=1000)
    s = InfiniteAverageV0Strategy(0.05, 0.05, 10_000, 100_000)
    a = s.on_price_update(_ctx(date(2025, 1, 10), 120), TickerState(position=pos))
    assert a.type == "SELL"


def test_session_end_holds():
    s = InfiniteAverageV0Strategy(0.05, 0.05, 10_000, 100_000)
    a = s.on_session_end(TickerState())
    assert a.type == "HOLD"
