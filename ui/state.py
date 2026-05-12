from __future__ import annotations

_results: list = []


def set_results(results: list) -> None:
    _results.clear()
    _results.extend(results)
