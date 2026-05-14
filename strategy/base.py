from __future__ import annotations
from abc import ABC, abstractmethod
from backtest.models import Action, PriceContext, TickerState


class BaseStrategy(ABC):
    @abstractmethod
    def on_price_update(self, ctx: PriceContext, state: TickerState) -> Action:
        ...

    def on_session_end(self, state: TickerState) -> Action:
        return Action(type="HOLD")
