from __future__ import annotations
from backtest.models import BacktestResult, Trade

STRATEGY_LABEL = {
    'dip_and_take_profit': '逢跌加碼止盈',
    'infinite_average_v0': '無限攤平_V0',
}


def per_ticker_rows(result: BacktestResult) -> list[dict]:
    rows = []
    for tr in result.ticker_results:
        m = tr.metrics
        if m is None:
            continue
        label = STRATEGY_LABEL.get(tr.strategy_class, tr.strategy_class)
        splits = getattr(tr, 'splits_applied', []) or []
        adj_mark = f"⚠ {len(splits)}" if splits else ''
        rows.append({
            'ticker':         f"[{tr.ticker}](/stock/{tr.strategy_class}/{tr.ticker})",
            'strategy':       f"[{label}](/strategy/{tr.strategy_class})",
            'split_adj':      adj_mark,
            'realized_pnl':   f"${m.realized_pnl:+,.0f} ({m.realized_pnl_pct:+.1%})",
            'unrealized_pnl': f"${m.unrealized_pnl:+,.0f}",
            'final_nav':      f"${m.final_nav:,.0f}",
            'mdd':            f"{m.max_drawdown:.1%}",
            'sharpe':         f"{m.sharpe_ratio:.2f}",
            'win_rate':       f"{m.win_rate:.0%}",
            'profit_factor':  f"{m.profit_factor:.2f}" if m.profit_factor != float('inf') else '∞',
            'avg_hold_days':  f"{m.avg_hold_days:.0f}d",
        })
    return rows


def trades_table_rows(trades: list[Trade]) -> list[dict]:
    return [{
        'date':        t.date.isoformat(),
        'action':      t.action,
        'shares':      t.shares,
        'price':       f"${t.price:,.0f}",
        'amount':      f"${t.amount:,.0f}",
        'fee_tax':     f"${t.fee + t.tax:,.0f}",
        'realized_pnl': f"${t.realized_pnl:+,.0f}" if t.realized_pnl is not None else '—',
        'hold_days':   t.hold_days if t.hold_days is not None else '—',
    } for t in trades]
