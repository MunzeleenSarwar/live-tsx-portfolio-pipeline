import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tsx_pipeline.strategies import refresh_strategies
from tsx_pipeline.config import STOCK_SYMBOLS


def test_strategy_constraints_and_weights_sum_to_one():
    rng = np.random.default_rng(7)
    dates = pd.date_range("2024-01-05", periods=130, freq="W-FRI")
    base = rng.normal(0.001, 0.02, size=(130, len(STOCK_SYMBOLS))).cumsum(axis=0)
    prices = pd.DataFrame(100 + base, index=dates, columns=STOCK_SYMBOLS)
    weights, metrics, sectors = refresh_strategies(prices, estimation_weeks=104)
    totals = weights.groupby("strategy")["weight"].sum()
    assert np.allclose(totals, 1.0)
    assert weights["weight"].max() <= 0.200001
    assert sectors["sector_weight"].max() <= 0.400001
    assert set(metrics["strategy"]) == {
        "Equal Weight", "Minimum Variance", "Risk Parity", "Minimum CVaR (latest window)"
    }
