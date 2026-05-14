from __future__ import annotations
import json
from datetime import date
from pathlib import Path
from typing import Literal

import pandas as pd

_MANUAL_FILE = Path(__file__).parent / "splits_manual.json"

SplitSource = Literal['manual', 'heuristic']


def _load_manual() -> dict:
    if not _MANUAL_FILE.exists():
        return {}
    try:
        with _MANUAL_FILE.open(encoding='utf-8') as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def manual_splits(ticker: str) -> list[tuple[date, float]]:
    """Manual split table entries for ticker.

    Returns ascending list of (split_date, ratio). ratio = pre-split close
    divided by post-split close (so dividing pre-split OHLC by ratio yields
    continuous prices).
    """
    data = _load_manual().get(ticker, [])
    out: list[tuple[date, float]] = []
    for entry in data:
        try:
            d = date.fromisoformat(entry['date'])
            r = float(entry['ratio'])
            if r > 0 and r != 1.0:
                out.append((d, r))
        except (KeyError, ValueError, TypeError):
            continue
    return sorted(out)


def heuristic_splits(df: pd.DataFrame, ratio_threshold: float = 1.5) -> list[tuple[date, float]]:
    """Detect candidate splits from consecutive-day close ratios.

    Triggers when close[t]/close[t-1] crosses outside [1/threshold, threshold].
    Returns (split_date, split_ratio) where split_ratio = close[t-1]/close[t].
    """
    if df is None or df.empty or 'close' not in df.columns:
        return []
    d = df.sort_values('date').reset_index(drop=True)
    out: list[tuple[date, float]] = []
    for i in range(1, len(d)):
        prev = float(d.iloc[i - 1]['close'])
        cur = float(d.iloc[i]['close'])
        if prev <= 0 or cur <= 0:
            continue
        r = cur / prev
        if r < (1 / ratio_threshold) or r > ratio_threshold:
            split_date = date.fromisoformat(str(d.iloc[i]['date']))
            split_ratio = prev / cur
            out.append((split_date, split_ratio))
    return out


def merged_splits(
    ticker: str, df: pd.DataFrame, ratio_threshold: float = 1.5,
) -> list[tuple[date, float, SplitSource]]:
    """Manual splits + heuristic candidates (heuristic skipped within ±3 days of manual)."""
    manual = manual_splits(ticker)
    heur = heuristic_splits(df, ratio_threshold)
    out: list[tuple[date, float, SplitSource]] = [(d, r, 'manual') for d, r in manual]
    manual_dates = {d for d, _ in manual}
    for d, r in heur:
        if any(abs((d - md).days) <= 3 for md in manual_dates):
            continue
        out.append((d, r, 'heuristic'))
    return sorted(out, key=lambda x: x[0])


def apply_splits(
    df: pd.DataFrame,
    splits: list[tuple[date, float, SplitSource]] | list[tuple[date, float]],
) -> pd.DataFrame:
    """Retroactively adjust OHLCV for splits.

    For each (split_date, ratio[, src]): rows with date < split_date get
    OHLC divided by ratio, volume multiplied by ratio.
    """
    if df is None or df.empty or not splits:
        return df
    out = df.copy()
    for entry in splits:
        if len(entry) == 3:
            split_date, ratio, _src = entry
        else:
            split_date, ratio = entry
        if ratio <= 0 or ratio == 1.0:
            continue
        mask = out['date'].astype(str) < split_date.isoformat()
        if not mask.any():
            continue
        for col in ('open', 'high', 'low', 'close'):
            if col in out.columns:
                out.loc[mask, col] = out.loc[mask, col] / ratio
        if 'volume' in out.columns:
            out.loc[mask, 'volume'] = (out.loc[mask, 'volume'].astype(float) * ratio).round().astype('int64')
    return out
