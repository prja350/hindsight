from __future__ import annotations
from datetime import date
from data.calendar import trading_days


def test_excludes_weekends():
    days = trading_days(date(2025, 1, 1), date(2025, 1, 7))
    assert date(2025, 1, 4) not in days  # Sat
    assert date(2025, 1, 5) not in days  # Sun


def test_includes_weekdays():
    days = trading_days(date(2025, 1, 6), date(2025, 1, 6))  # Mon
    assert date(2025, 1, 6) in days


def test_returns_sorted_list():
    days = trading_days(date(2025, 1, 1), date(2025, 1, 10))
    assert days == sorted(days)
