from datetime import date
from backtest.models import Action, Position
from strategy.base import BaseStrategy


class AlwaysBuyStrategy(BaseStrategy):
    def on_price_update(self, dt: date, price: float, position: Position | None) -> Action:
        return Action(type="BUY", amount=10_000.0)


def test_subclass_returns_buy():
    s = AlwaysBuyStrategy()
    action = s.on_price_update(date(2023, 1, 3), 500.0, None)
    assert action.type == "BUY"


def test_default_session_end_returns_hold():
    s = AlwaysBuyStrategy()
    assert s.on_session_end(None).type == "HOLD"
