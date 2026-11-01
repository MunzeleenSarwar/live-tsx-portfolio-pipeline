import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tsx_pipeline.strategy_evaluation import (
    break_even_prob, expected_value, margin_above_breakeven,
    payoff_summary, performance_metrics, win_rate,
)


def test_expected_value_and_breakeven():
    assert np.isclose(expected_value(0.35, 3.0), 0.40)
    assert np.isclose(break_even_prob(3.0), 0.25)
    assert np.isclose(break_even_prob(1.0), 0.50)
    assert np.isclose(margin_above_breakeven(0.55, 1.0), 0.05)


def test_payoff_summary_from_trade_returns():
    trades = pd.Series([0.10, -0.05, 0.20, -0.05])
    summary = payoff_summary(trades)
    assert summary["win_probability"] == 0.5
    assert np.isclose(summary["reward_risk"], 3.0)
    assert np.isclose(summary["expected_value_R"], 1.0)
    assert np.isclose(win_rate(trades), 0.5)


def test_performance_metrics_on_flat_series():
    metrics = performance_metrics(pd.Series([0.0] * 12))
    assert metrics["total_return"] == 0
    assert metrics["annualised_volatility"] == 0
    assert metrics["max_drawdown"] == 0
