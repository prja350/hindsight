from __future__ import annotations
from datetime import date
import json
import pandas as pd
import pytest

from data import splits as splits_mod
from data.splits import (
    apply_splits, heuristic_splits, manual_splits, merged_splits,
)


@pytest.fixture
def sample_df():
    return pd.DataFrame([
        {'ticker': 'X', 'date': '2026-03-23', 'open': 442.0, 'high': 446.0,
         'low': 440.0, 'close': 443.0, 'volume': 10_000},
        {'ticker': 'X', 'date': '2026-03-24', 'open': 443.0, 'high': 447.0,
         'low': 441.0, 'close': 443.15, 'volume': 9_700},
        {'ticker': 'X', 'date': '2026-03-31', 'open': 20.0, 'high': 20.5,
         'low': 19.5, 'close': 19.26, 'volume': 220_000},
        {'ticker': 'X', 'date': '2026-04-01', 'open': 19.5, 'high': 21.5,
         'low': 19.2, 'close': 21.0, 'volume': 195_000},
    ])


def test_heuristic_detects_22x_drop(sample_df):
    found = heuristic_splits(sample_df, ratio_threshold=1.5)
    assert len(found) == 1
    d, r = found[0]
    assert d == date(2026, 3, 31)
    assert abs(r - (443.15 / 19.26)) < 1e-6


def test_heuristic_no_split_on_smooth_data():
    df = pd.DataFrame([
        {'date': f'2026-01-0{i}', 'close': 100 + i} for i in range(2, 7)
    ])
    assert heuristic_splits(df) == []


def test_apply_splits_divides_pre_split_prices(sample_df):
    out = apply_splits(sample_df, [(date(2026, 3, 31), 23.0)])
    pre = out[out['date'] < '2026-03-31']
    post = out[out['date'] >= '2026-03-31']
    assert abs(pre['close'].iloc[0] - 443.0 / 23) < 1e-6
    assert pre['volume'].iloc[0] == round(10_000 * 23)
    assert post['close'].iloc[0] == 19.26
    assert post['volume'].iloc[0] == 220_000


def test_apply_splits_noop_for_empty():
    assert apply_splits(pd.DataFrame(), [(date(2026, 1, 1), 2.0)]).empty


def test_apply_splits_noop_for_no_splits(sample_df):
    out = apply_splits(sample_df, [])
    pd.testing.assert_frame_equal(out, sample_df)


def test_apply_splits_skips_ratio_one(sample_df):
    out = apply_splits(sample_df, [(date(2026, 3, 31), 1.0)])
    pd.testing.assert_frame_equal(out, sample_df)


def test_manual_splits_loads_from_json(tmp_path, monkeypatch):
    f = tmp_path / "splits_manual.json"
    f.write_text(json.dumps({
        "X": [{"date": "2026-03-25", "ratio": 22.0, "note": "test"}]
    }), encoding='utf-8')
    monkeypatch.setattr(splits_mod, '_MANUAL_FILE', f)
    out = manual_splits('X')
    assert out == [(date(2026, 3, 25), 22.0)]


def test_manual_splits_missing_file_returns_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(splits_mod, '_MANUAL_FILE', tmp_path / "nonexistent.json")
    assert manual_splits('X') == []


def test_manual_splits_invalid_entry_skipped(tmp_path, monkeypatch):
    f = tmp_path / "splits_manual.json"
    f.write_text(json.dumps({
        "X": [
            {"date": "bad-date", "ratio": 2.0},
            {"date": "2026-01-01"},
            {"date": "2026-02-01", "ratio": -1.0},
            {"date": "2026-03-01", "ratio": 2.0, "note": "ok"},
        ]
    }), encoding='utf-8')
    monkeypatch.setattr(splits_mod, '_MANUAL_FILE', f)
    assert manual_splits('X') == [(date(2026, 3, 1), 2.0)]


def test_merged_splits_prefers_manual_over_heuristic(sample_df, tmp_path, monkeypatch):
    f = tmp_path / "splits_manual.json"
    f.write_text(json.dumps({
        "X": [{"date": "2026-03-30", "ratio": 22.5, "note": "manual"}]
    }), encoding='utf-8')
    monkeypatch.setattr(splits_mod, '_MANUAL_FILE', f)
    out = merged_splits('X', sample_df)
    assert len(out) == 1
    d, r, src = out[0]
    assert src == 'manual'
    assert d == date(2026, 3, 30)
    assert r == 22.5


def test_merged_splits_keeps_distant_heuristic(sample_df, tmp_path, monkeypatch):
    f = tmp_path / "splits_manual.json"
    f.write_text(json.dumps({
        "X": [{"date": "2030-01-01", "ratio": 5.0}]
    }), encoding='utf-8')
    monkeypatch.setattr(splits_mod, '_MANUAL_FILE', f)
    out = merged_splits('X', sample_df)
    assert len(out) == 2
    sources = {src for _, _, src in out}
    assert sources == {'manual', 'heuristic'}
