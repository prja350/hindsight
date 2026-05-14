from __future__ import annotations
from backtest.models import BacktestResult

_results: list[BacktestResult] = []


def set_results(results: list[BacktestResult]) -> None:
    _results.clear()
    _results.extend(results)


def current_result() -> BacktestResult | None:
    return _results[0] if _results else None
