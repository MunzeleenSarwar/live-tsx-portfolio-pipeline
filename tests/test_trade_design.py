import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tsx_pipeline.trade_design import (
    design_trade, kelly_fraction, marginal_profit, no_edge_win_prob,
    optimal_size_impact_only, profit, risk_adjusted_return,
)


def test_profit_is_concave_and_optimum_matches_derivative():
    args = dict(entry_price=100.0, expected_return=0.02, adv_shares=1_000_000)
    q_star = optimal_size_impact_only(**args)
    assert q_star > 0
    assert abs(marginal_profit(q_star, **args)) < 1e-6
    assert profit(q_star, **args) > profit(q_star * 0.5, **args)
    assert profit(q_star, **args) > profit(q_star * 1.5, **args)


def test_no_edge_probability_and_kelly():
    assert np.isclose(no_edge_win_prob(4.0, 6.0), 0.4)
    assert np.isclose(kelly_fraction(0.55, 1.0), 0.10)


def test_risk_adjusted_return_falls_after_optimum():
    low = risk_adjusted_return(0.2, 0.02, 0.07)
    high = risk_adjusted_return(3.0, 0.02, 0.07)
    assert low > high


def test_design_trade_respects_caps():
    plan = design_trade(
        entry_price=80.0, win_probability=0.56, stop_distance_pct=0.05,
        target_distance_pct=0.075, horizon_volatility=0.07,
        adv_shares=8_000_000, capital=1_000_000,
    )
    assert plan["position_pct_of_capital"] <= 0.20 + 1e-9
    assert plan["risk_pct_of_capital"] <= 0.0105
    assert plan["final_quantity"] > 0
