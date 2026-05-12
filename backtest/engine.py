from __future__ import annotations
import math
from datetime import date
from typing import TYPE_CHECKING

from backtest.metrics import MetricsCalculator
from backtest.models import Action, BacktestResult, Position, Trade

if TYPE_CHECKING:
    from data.provider import DataProvider
    from strategy.base import BaseStrategy

BUY_FEE_RATE  = 0.001425
SELL_FEE_RATE = 0.001425
SELL_TAX_RATE = 0.003


class BacktestEngine:
    def __init__(self, provider: DataProvider, initial_capital: float = 500_000.0) -> None:
        self.provider = provider
        self.initial_capital = initial_capital

    def run(self, strategy: BaseStrategy, tickers: list[str],
            start: date, end: date, strategy_name: str) -> BacktestResult:
        result = BacktestResult(strategy_name=strategy_name)
        positions: dict[str, Position | None] = {t: None for t in tickers}
        cash = self.initial_capital

        ohlcv_map = {t: df for t in tickers
                     if (df := self.provider.get_ohlcv(t, start, end)) is not None}
        all_dates = sorted({d for df in ohlcv_map.values() for d in df['date'].tolist()})

        for dt_str in all_dates:
            dt = date.fromisoformat(dt_str)
            if not (start <= dt <= end):
                continue

            for ticker, df in ohlcv_map.items():
                row = df[df['date'] == dt_str]
                if row.empty:
                    continue
                price = float(row['close'].iloc[0])
                action = strategy.on_price_update(dt, price, positions[ticker])

                if action.type == "BUY" and action.amount > 0:
                    shares = math.floor(action.amount / price)
                    if shares == 0:
                        continue
                    amount = shares * price
                    fee = round(amount * BUY_FEE_RATE)
                    if amount + fee > cash:
                        continue
                    cash -= amount + fee
                    pos = positions[ticker]
                    if pos is None:
                        positions[ticker] = Position(
                            ticker=ticker, shares=shares, avg_cost=price,
                            entry_date=dt, total_invested=amount,
                        )
                    else:
                        total_shares = pos.shares + shares
                        total_invested = pos.total_invested + amount
                        positions[ticker] = Position(
                            ticker=ticker, shares=total_shares,
                            avg_cost=total_invested / total_shares,
                            entry_date=pos.entry_date, total_invested=total_invested,
                        )
                    result.trades.append(Trade(
                        ticker=ticker, action='BUY', date=dt,
                        price=price, shares=shares, amount=amount, fee=fee, tax=0.0,
                    ))

                elif action.type == "SELL":
                    pos = positions[ticker]
                    if pos is None:
                        continue
                    proceeds = pos.shares * price
                    fee = round(proceeds * SELL_FEE_RATE)
                    tax = round(proceeds * SELL_TAX_RATE)
                    net = proceeds - fee - tax
                    realized_pnl = net - pos.total_invested
                    hold_days = (dt - pos.entry_date).days
                    cash += net
                    result.trades.append(Trade(
                        ticker=ticker, action='SELL', date=dt,
                        price=price, shares=pos.shares, amount=proceeds,
                        fee=fee, tax=tax, realized_pnl=realized_pnl, hold_days=hold_days,
                    ))
                    positions[ticker] = None

            # Daily portfolio value snapshot
            open_value = 0.0
            for ticker, pos in positions.items():
                if pos is None or ticker not in ohlcv_map:
                    continue
                price_row = ohlcv_map[ticker][ohlcv_map[ticker]['date'] == dt_str]
                if not price_row.empty:
                    open_value += pos.shares * float(price_row['close'].iloc[0])
            result.daily_snapshots.append((dt, cash + open_value))

        result.metrics = MetricsCalculator(
            trades=result.trades,
            snapshots=result.daily_snapshots,
            initial_capital=self.initial_capital,
        ).calculate()
        return result
