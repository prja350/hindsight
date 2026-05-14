from __future__ import annotations
from dataclasses import dataclass
from backtest.models import Action, PriceContext, TickerState
from strategy.base import BaseStrategy
from strategy.pnl import net_unrealized_pct


@dataclass
class DipAndTakeProfitStrategy(BaseStrategy):
    dip_pct: float
    take_profit_pct: float
    add_amount: float
    max_position: float
    max_hold_days: int

    def on_price_update(self, ctx: PriceContext, state: TickerState) -> Action:
        pos = state.position
        if pos is None:
            return Action(type="BUY", amount=self.add_amount)

        hold_days = (ctx.date - pos.entry_date).days
        if hold_days >= self.max_hold_days:
            return Action(type="SELL")

        pnl_pct = net_unrealized_pct(state, ctx.price)
        if pnl_pct >= self.take_profit_pct:
            return Action(type="SELL")
        if pnl_pct < -self.dip_pct:
            if pos.total_invested + self.add_amount <= self.max_position:
                return Action(type="BUY", amount=self.add_amount)
        return Action(type="HOLD")
