import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tsx_pipeline.quality import detect_gaps, modified_z_scores, validate_ohlcv


def sample_frame():
    return pd.DataFrame({
        "timestamp": pd.to_datetime(["2026-01-05", "2026-01-06"]),
        "symbol": ["TD.TO", "TD.TO"], "short": ["TD", "TD"],
        "open": [100, 101], "high": [102, 100], "low": [99, 99],
        "close": [101, 100], "adjusted_close": [101, 100],
        "volume": [1000, 1000], "dividends": [0, 0], "stock_splits": [0, 0],
        "retrieved_at": ["2026-01-07"] * 2,
    })


def test_invalid_high_is_flagged():
    checked = validate_ohlcv(sample_frame())
    assert not checked.iloc[1].is_valid
    assert "high_below_other_prices" in checked.iloc[1].quality_errors


def test_modified_z_scores_flags_extreme_value():
    values = pd.Series(np.linspace(-0.01, 0.01, 20).tolist() + [0.50])
    scores = modified_z_scores(values)
    assert abs(scores.iloc[-1]) > 3.5


def test_gap_detection_against_benchmark_sessions():
    clean = pd.DataFrame({
        "timestamp": pd.to_datetime(["2026-01-05", "2026-01-07"]),
        "symbol": ["TD.TO", "TD.TO"], "adjusted_close": [100, 102],
    })
    sessions = pd.to_datetime(["2026-01-05", "2026-01-06", "2026-01-07"])
    gaps, fills = detect_gaps(clean, sessions)
    assert gaps.iloc[0].missing_sessions == 1
    assert bool(fills.iloc[0].filled)
