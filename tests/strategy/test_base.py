from __future__ import annotations
from datetime import date
from backtest.models import Action, PriceContext, TickerState
from strategy.base import BaseStrategy


class _HoldAlways(BaseStrategy):
    def on_price_update(self, ctx, state):
        return Action(type="HOLD")


def test_signature_takes_ctx_and_state():
    s = _HoldAlways()
    ctx = PriceContext(date(2025, 1, 2), 100, 100, 100, 100, 'clean')
    st = TickerState()
    assert s.on_price_update(ctx, st).type == "HOLD"


def test_session_end_default_hold():
    s = _HoldAlways()
    assert s.on_session_end(TickerState()).type == "HOLD"
