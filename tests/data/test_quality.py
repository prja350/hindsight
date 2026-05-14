from __future__ import annotations
from datetime import date
import pandas as pd
from data.quality import detect_gaps


def test_no_gaps_returns_empty():
    df = pd.DataFrame({'date': ['2025-01-02', '2025-01-03', '2025-01-06']})
    expected = [date(2025, 1, 2), date(2025, 1, 3), date(2025, 1, 6)]
    assert detect_gaps(df, expected) == []


def test_single_day_gap():
    df = pd.DataFrame({'date': ['2025-01-02', '2025-01-06']})
    expected = [date(2025, 1, 2), date(2025, 1, 3), date(2025, 1, 6)]
    assert detect_gaps(df, expected) == [(date(2025, 1, 3), date(2025, 1, 3))]


def test_contiguous_gap_merged():
    df = pd.DataFrame({'date': ['2025-01-02', '2025-01-07']})
    expected = [date(2025, 1, 2), date(2025, 1, 3), date(2025, 1, 6), date(2025, 1, 7)]
    assert detect_gaps(df, expected) == [(date(2025, 1, 3), date(2025, 1, 6))]


def test_empty_df_returns_full_range():
    df = pd.DataFrame({'date': []})
    expected = [date(2025, 1, 2), date(2025, 1, 3)]
    assert detect_gaps(df, expected) == [(date(2025, 1, 2), date(2025, 1, 3))]
