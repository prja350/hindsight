from __future__ import annotations
import math
from datetime import date
from backtest.models import Metrics, Trade


class MetricsCalculator:
    def __init__(self, trades: list[Trade], snapshots: list[tuple[date, float]],
                 initial_capital: float) -> None:
        self.trades = trades
        self.snapshots = snapshots
        self.initial_capital = initial_capital

    def calculate(self) -> Metrics:
        sell_trades = [t for t in self.trades if t.realized_pnl is not None]
        realized_pnl = sum(t.realized_pnl for t in sell_trades)  # type: ignore[misc]
        final_nav = self.snapshots[-1][1] if self.snapshots else self.initial_capital
        unrealized_pnl = final_nav - self.initial_capital - realized_pnl
        return Metrics(
            realized_pnl=realized_pnl,
            realized_pnl_pct=realized_pnl / self.initial_capital if self.initial_capital else 0.0,
            unrealized_pnl=unrealized_pnl,
            final_cost=self.initial_capital,
            final_nav=final_nav,
            max_drawdown=self._max_drawdown(),
            sharpe_ratio=self._sharpe(),
            win_rate=self._win_rate(sell_trades),
            profit_factor=self._profit_factor(sell_trades),
            avg_hold_days=self._avg_hold_days(sell_trades),
        )

    def _max_drawdown(self) -> float:
        if not self.snapshots:
            return 0.0
        peak, max_dd = self.snapshots[0][1], 0.0
        for _, v in self.snapshots:
            peak = max(peak, v)
            dd = (peak - v) / peak if peak > 0 else 0.0
            max_dd = max(max_dd, dd)
        return max_dd

    def _sharpe(self) -> float:
        values = [v for _, v in self.snapshots]
        if len(values) < 2:
            return 0.0
        returns = [(values[i] - values[i-1]) / values[i-1] for i in range(1, len(values))]
        mean_r = sum(returns) / len(returns)
        var = sum((r - mean_r)**2 for r in returns) / max(len(returns) - 1, 1)
        std = math.sqrt(var)
        return (mean_r / std) * math.sqrt(252) if std > 0 else 0.0

    def _win_rate(self, sell_trades: list[Trade]) -> float:
        if not sell_trades:
            return 0.0
        return sum(1 for t in sell_trades if t.realized_pnl > 0) / len(sell_trades)  # type: ignore[operator]

    def _profit_factor(self, sell_trades: list[Trade]) -> float:
        profit = sum(t.realized_pnl for t in sell_trades if t.realized_pnl > 0)  # type: ignore[misc]
        loss = abs(sum(t.realized_pnl for t in sell_trades if t.realized_pnl < 0))  # type: ignore[misc]
        if loss == 0:
            return float('inf') if profit > 0 else 0.0
        return profit / loss

    def _avg_hold_days(self, sell_trades: list[Trade]) -> float:
        days = [t.hold_days for t in sell_trades if t.hold_days is not None]
        return sum(days) / len(days) if days else 0.0
