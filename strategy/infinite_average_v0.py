from __future__ import annotations
from dataclasses import dataclass
from backtest.models import Action, PriceContext, TickerState
from strategy.base import BaseStrategy
from strategy.pnl import net_unrealized_pct


@dataclass
class InfiniteAverageV0Strategy(BaseStrategy):
    dip_pct: float
    take_profit_pct: float
    add_amount: float
    max_position: float

    def on_price_update(self, ctx: PriceContext, state: TickerState) -> Action:
        pos = state.position
        if pos is None:
            # Re-entry the day after a sell (or first entry). No price gate.
            return Action(type="BUY", amount=self.add_amount)

        pnl_pct = net_unrealized_pct(state, ctx.price)
        if pnl_pct >= self.take_profit_pct:
            return Action(type="SELL")
        if pnl_pct < -self.dip_pct:
            if pos.total_invested + self.add_amount <= self.max_position:
                return Action(type="BUY", amount=self.add_amount)
        return Action(type="HOLD")
