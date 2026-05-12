from __future__ import annotations
from datetime import date
from backtest.models import Action, Position
from strategy.base import BaseStrategy


class DipAndTakeProfitStrategy(BaseStrategy):
    def __init__(
        self,
        dip_pct: float = 0.07,
        add_amount: float = 10_000.0,
        take_profit_pct: float = 0.03,
        max_position: float = 100_000.0,
        max_hold_days: int = 60,
    ) -> None:
        self.dip_pct = dip_pct
        self.add_amount = add_amount
        self.take_profit_pct = take_profit_pct
        self.max_position = max_position
        self.max_hold_days = max_hold_days

    def on_price_update(self, dt: date, price: float, position: Position | None) -> Action:
        if position is None:
            return Action(type="BUY", amount=self.add_amount)

        hold_days = (dt - position.entry_date).days
        if hold_days >= self.max_hold_days:
            return Action(type="SELL")

        unrealized_pct = (price - position.avg_cost) / position.avg_cost
        if unrealized_pct >= self.take_profit_pct:
            return Action(type="SELL")

        drop_pct = (position.avg_cost - price) / position.avg_cost
        if drop_pct >= self.dip_pct:
            if position.total_invested + self.add_amount <= self.max_position:
                return Action(type="BUY", amount=self.add_amount)

        return Action(type="HOLD")
