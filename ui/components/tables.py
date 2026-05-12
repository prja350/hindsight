from __future__ import annotations
from backtest.models import BacktestResult, Trade


def strategy_metrics_rows(results: list[BacktestResult]) -> list[dict]:
    rows = []
    for r in results:
        m = r.metrics
        if m is None:
            continue
        rows.append({
            'strategy':       r.strategy_name,
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
    } for t in trades]
