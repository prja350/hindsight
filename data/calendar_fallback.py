from __future__ import annotations
from datetime import date, timedelta

_HOLIDAYS_2024 = {
    date(2024, 1, 1), date(2024, 2, 8), date(2024, 2, 9), date(2024, 2, 12),
    date(2024, 2, 13), date(2024, 2, 14), date(2024, 2, 28), date(2024, 4, 4),
    date(2024, 4, 5), date(2024, 5, 1), date(2024, 6, 10), date(2024, 9, 17),
    date(2024, 10, 10),
}
_HOLIDAYS_2025 = {
    date(2025, 1, 1), date(2025, 1, 27), date(2025, 1, 28), date(2025, 1, 29),
    date(2025, 1, 30), date(2025, 1, 31), date(2025, 2, 28), date(2025, 4, 3),
    date(2025, 4, 4), date(2025, 5, 1), date(2025, 5, 30), date(2025, 10, 6),
    date(2025, 10, 10),
}
_HOLIDAYS_2026 = {
    date(2026, 1, 1), date(2026, 2, 16), date(2026, 2, 17), date(2026, 2, 18),
    date(2026, 2, 19), date(2026, 2, 20), date(2026, 2, 27), date(2026, 4, 3),
    date(2026, 4, 6), date(2026, 5, 1), date(2026, 6, 19), date(2026, 9, 25),
    date(2026, 10, 9),
}
_HOLIDAYS = _HOLIDAYS_2024 | _HOLIDAYS_2025 | _HOLIDAYS_2026


def trading_days_fallback(start: date, end: date) -> list[date]:
    days = []
    d = start
    while d <= end:
        if d.weekday() < 5 and d not in _HOLIDAYS:
            days.append(d)
        d += timedelta(days=1)
    return days
