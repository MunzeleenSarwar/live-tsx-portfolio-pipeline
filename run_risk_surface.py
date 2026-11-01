from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from tsx_pipeline.risk_surface import (
    analyze_directions, correlation_scenarios, create_evaluation_grid,
    first_order_approximation, portfolio_value, portfolio_volatility,
    risk_report, risk_surface_grid, second_order_approximation,
)

OUT = ROOT / "data" / "risk_surface_outputs"
OUT.mkdir(parents=True, exist_ok=True)

ASSET_A = "ENB.TO"
ASSET_B = "TD.TO"
CAPITAL = 100_000.0


def main() -> int:
    prices = pd.read_csv(ROOT / "data" / "clean" / "adjusted_close_filled_matrix.csv",
                         index_col=0, parse_dates=True)
    log_returns = np.log(prices / prices.shift(1)).dropna()
    window = log_returns.tail(252)
    report = risk_report(window, ASSET_A, ASSET_B, capital=CAPITAL)

    latest_prices = np.array([float(prices[ASSET_A].iloc[-1]), float(prices[ASSET_B].iloc[-1])])
    weights = np.array([report["base_weight_a"], 1 - report["base_weight_a"]])
    allocations = weights * CAPITAL
    shares = allocations / latest_prices
    base_value = portfolio_value(shares, latest_prices)

    shocks = np.round(np.arange(-0.30, 0.3001, 0.025), 4)
    value_grid = create_evaluation_grid(shares, latest_prices, shocks, shocks)
    value_grid.to_csv(OUT / "value_surface_grid.csv", index=False)

    risk_grid = risk_surface_grid(np.round(np.arange(0, 1.001, 0.01), 4),
                                  np.round(np.arange(-0.50, 0.951, 0.025), 4),
                                  report["vol_a"], report["vol_b"])
    risk_grid.to_csv(OUT / "risk_surface_grid.csv", index=False)

    scenarios = {
        "Both fall 10%": (-0.10, -0.10),
        "ENB falls 10%, TD falls 5%": (-0.10, -0.05),
        "ENB falls 10%, TD rises 10%": (-0.10, 0.10),
        "ENB rises 10%, TD falls 10%": (0.10, -0.10),
        "Both rise 10%": (0.10, 0.10),
        "ENB falls 20%, TD rises 5%": (-0.20, 0.05),
        "ENB rises 5%, TD falls 20%": (0.05, -0.20),
    }
    directions = analyze_directions(shares, latest_prices, scenarios)
    directions.to_csv(OUT / "direction_scenarios.csv", index=False)

    corr_values = sorted(set([-0.5, -0.25, 0.0, round(report["correlation"], 4), 0.3, 0.6, 0.9]))
    corr_table = correlation_scenarios(corr_values, report["vol_a"], report["vol_b"])
    corr_table.to_csv(OUT / "correlation_scenarios.csv", index=False)

    risk_function = lambda p: portfolio_volatility(p[0], p[1], report["vol_a"], report["vol_b"])
    base_point = np.array([report["base_weight_a"], report["correlation"]])
    taylor_rows = []
    for d_w, d_rho in [(0.05, 0.10), (0.10, 0.20), (-0.10, 0.30), (0.20, -0.20), (-0.20, 0.50)]:
        delta = np.array([d_w, d_rho])
        point = base_point + delta
        point[0] = np.clip(point[0], 0.0, 1.0)
        point[1] = np.clip(point[1], -0.99, 0.99)
        exact = risk_function(point)
        first = first_order_approximation(report["base_volatility"], report["risk_gradient"], delta)
        second = second_order_approximation(
            report["base_volatility"], report["risk_gradient"], report["risk_hessian"], delta)
        taylor_rows.append({
            "delta_weight_a": d_w, "delta_correlation": d_rho,
            "new_weight_a": point[0], "new_correlation": point[1],
            "exact_volatility": exact, "first_order_volatility": first,
            "second_order_volatility": second,
            "first_order_error": first - exact, "second_order_error": second - exact,
        })
    pd.DataFrame(taylor_rows).to_csv(OUT / "taylor_risk_approximations.csv", index=False)

    summary = {
        "asset_a": ASSET_A, "asset_b": ASSET_B,
        "window_start": str(window.index.min().date()),
        "window_end": str(window.index.max().date()),
        "observations": int(len(window)),
        "capital": CAPITAL,
        "price_a": float(latest_prices[0]), "price_b": float(latest_prices[1]),
        "vol_a": report["vol_a"], "vol_b": report["vol_b"],
        "correlation": report["correlation"],
        "base_weight_a": report["base_weight_a"], "base_weight_b": 1 - report["base_weight_a"],
        "allocation_a": float(allocations[0]), "allocation_b": float(allocations[1]),
        "shares_a": float(shares[0]), "shares_b": float(shares[1]),
        "base_value": float(base_value),
        "base_volatility": report["base_volatility"],
        "value_gradient_per_price": shares.tolist(),
        "value_gradient_per_shock_fraction": allocations.tolist(),
        "risk_gradient": report["risk_gradient"].tolist(),
        "risk_hessian": report["risk_hessian"].tolist(),
        "risk_hessian_eigenvalues": report["risk_hessian_analysis"]["eigenvalues"].tolist(),
        "risk_hessian_classification": report["risk_hessian_analysis"]["classification"],
    }
    (OUT / "risk_surface_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
