from __future__ import annotations
import math
from datetime import date
from typing import TYPE_CHECKING

from backtest.metrics import MetricsCalculator
from backtest.models import (
    BacktestResult, DailySnapshot, PriceContext, Position,
    TickerAssignment, TickerResult, TickerState, Trade,
)

if TYPE_CHECKING:
    from data.provider import DataProvider
    from strategy.base import BaseStrategy

BUY_FEE_RATE = 0.001425
SELL_FEE_RATE = 0.001425
SELL_TAX_RATE = 0.003


def _build_strategy(class_name: str, params: dict) -> "BaseStrategy":
    if class_name == 'dip_and_take_profit':
        from strategy.dip_and_take_profit import DipAndTakeProfitStrategy
        return DipAndTakeProfitStrategy(
            dip_pct=params['dip_pct'],
            take_profit_pct=params['take_profit_pct'],
            add_amount=params['add_amount'],
            max_position=params['max_position'],
            max_hold_days=int(params['max_hold_days']),
        )
    if class_name == 'infinite_average_v0':
        from strategy.infinite_average_v0 import InfiniteAverageV0Strategy
        return InfiniteAverageV0Strategy(
            dip_pct=params['dip_pct'],
            take_profit_pct=params['take_profit_pct'],
            add_amount=params['add_amount'],
            max_position=params['max_position'],
        )
    raise ValueError(f"Unknown strategy class: {class_name}")


def _ctx_from_row(dt: date, row, execution_price: str) -> PriceContext:
    o = float(row['open']); c = float(row['close'])
    h = float(row['high']); lo = float(row['low'])
    vwap = (h + lo + c) / 3
    if execution_price == 'open':
        price = o
    elif execution_price == 'vwap':
        price = vwap
    else:
        price = c
    qf = row['quality_flag'] if 'quality_flag' in row else 'clean'
    return PriceContext(date=dt, open=o, close=c, vwap=vwap, price=price, quality_flag=qf)


class BacktestEngine:
    def __init__(self, provider: "DataProvider") -> None:
        self.provider = provider

    def run(self, assignments: list[TickerAssignment], start: date, end: date,
            initial_capital: float, execution_price: str = "close") -> BacktestResult:

        cash = initial_capital
        states: dict[str, TickerState] = {a.ticker: TickerState() for a in assignments}
        strategies = {a.ticker: _build_strategy(a.strategy_class, a.params)
                      for a in assignments}

        ohlcv_map = {}
        for a in assignments:
            df = self.provider.get_ohlcv(a.ticker, start, end)
            if df is not None and not df.empty:
                ohlcv_map[a.ticker] = df

        all_dates = sorted({d for df in ohlcv_map.values() for d in df['date'].tolist()})

        per_ticker_trades: dict[str, list[Trade]] = {a.ticker: [] for a in assignments}
        daily_snapshots: list[DailySnapshot] = []

        for dt_str in all_dates:
            dt = date.fromisoformat(dt_str)
            if not (start <= dt <= end):
                continue

            for ticker, df in ohlcv_map.items():
                rdf = df[df['date'] == dt_str]
                if rdf.empty:
                    continue
                row = rdf.iloc[0]
                ctx = _ctx_from_row(dt, row, execution_price)
                state = states[ticker]
                action = strategies[ticker].on_price_update(ctx, state)

                if action.type == "BUY" and action.amount > 0:
                    shares = math.floor(action.amount / ctx.price)
                    if shares == 0:
                        continue
                    cost = shares * ctx.price
                    fee = round(cost * BUY_FEE_RATE)
                    if cost + fee > cash:
                        continue
                    cash -= cost + fee
                    if state.position is None:
                        state.position = Position(
                            ticker=ticker, shares=shares, avg_cost=ctx.price,
                            entry_date=dt, total_invested=cost + fee,
                        )
                    else:
                        total_shares = state.position.shares + shares
                        new_total = state.position.total_invested + cost + fee
                        state.position = Position(
                            ticker=ticker, shares=total_shares,
                            avg_cost=new_total / total_shares,
                            entry_date=state.position.entry_date,
                            total_invested=new_total,
                        )
                    state.last_sell_price = None
                    per_ticker_trades[ticker].append(Trade(
                        ticker=ticker, action='BUY', date=dt,
                        price=ctx.price, shares=shares, amount=cost,
                        fee=fee, tax=0.0,
                    ))

                elif action.type == "SELL" and state.position is not None:
                    pos = state.position
                    proceeds = pos.shares * ctx.price
                    fee = round(proceeds * SELL_FEE_RATE)
                    tax = round(proceeds * SELL_TAX_RATE)
                    net = proceeds - fee - tax
                    realized = net - pos.total_invested
                    hold_days = (dt - pos.entry_date).days
                    cash += net
                    per_ticker_trades[ticker].append(Trade(
                        ticker=ticker, action='SELL', date=dt,
                        price=ctx.price, shares=pos.shares, amount=proceeds,
                        fee=fee, tax=tax, realized_pnl=realized, hold_days=hold_days,
                    ))
                    state.last_sell_price = ctx.price
                    state.position = None

            pos_value = 0.0
            for ticker, state in states.items():
                if state.position is None or ticker not in ohlcv_map:
                    continue
                rdf = ohlcv_map[ticker][ohlcv_map[ticker]['date'] == dt_str]
                if rdf.empty:
                    continue
                ctx = _ctx_from_row(dt, rdf.iloc[0], execution_price)
                pos_value += state.position.shares * ctx.price
            daily_snapshots.append(DailySnapshot(date=dt, cash=cash, position_value=pos_value))

        ticker_results = []
        for a in assignments:
            trades = per_ticker_trades[a.ticker]
            metrics = MetricsCalculator(
                trades=trades,
                snapshots=[(s.date, s.total) for s in daily_snapshots],
                initial_capital=initial_capital,
            ).calculate()
            ticker_results.append(TickerResult(
                ticker=a.ticker, strategy_class=a.strategy_class, params=a.params,
                trades=trades, metrics=metrics, final_position=states[a.ticker].position,
            ))

        return BacktestResult(
            initial_capital=initial_capital, execution_price=execution_price,
            start=start, end=end,
            ticker_results=ticker_results, daily_snapshots=daily_snapshots,
            final_cash=cash,
        )
