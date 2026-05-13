from __future__ import annotations
from datetime import date

try:
    import pandas_market_calendars as mcal
    _XTAI = mcal.get_calendar('XTAI')
    _HAS_MCAL = True
except Exception:
    _HAS_MCAL = False

from data.calendar_fallback import trading_days_fallback


def trading_days(start: date, end: date) -> list[date]:
    if _HAS_MCAL:
        sched = _XTAI.valid_days(start.isoformat(), end.isoformat())
        return [d.date() for d in sched]
    return trading_days_fallback(start, end)
