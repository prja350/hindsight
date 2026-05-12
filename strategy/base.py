from __future__ import annotations
from abc import ABC, abstractmethod
from datetime import date
from backtest.models import Action, Position


class BaseStrategy(ABC):
    @abstractmethod
    def on_price_update(self, dt: date, price: float, position: Position | None) -> Action: ...

    def on_session_end(self, position: Position | None) -> Action:
        return Action(type="HOLD")
