from __future__ import annotations
from datetime import date
import pandas as pd


def detect_gaps(df: pd.DataFrame, expected: list[date]) -> list[tuple[date, date]]:
    """Return contiguous missing date ranges. Pure function, no I/O.
    Contiguity is measured in *trading-day* order (consecutive entries in `expected`).
    """
    have = set()
    if not df.empty and 'date' in df.columns:
        have = {date.fromisoformat(str(d)) for d in df['date'].tolist()}
    missing_set = {d for d in expected if d not in have}
    if not missing_set:
        return []
    gaps: list[tuple[date, date]] = []
    run_start: date | None = None
    prev: date | None = None
    for d in expected:
        if d in missing_set:
            if run_start is None:
                run_start = d
            prev = d
        else:
            if run_start is not None and prev is not None:
                gaps.append((run_start, prev))
            run_start = None
            prev = None
    if run_start is not None and prev is not None:
        gaps.append((run_start, prev))
    return gaps
