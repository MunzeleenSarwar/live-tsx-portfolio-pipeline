from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from tsx_pipeline.config import BENCHMARK_SYMBOL, STOCK_SYMBOLS
from tsx_pipeline.strategy_evaluation import (
    backtest_momentum, batch_ev, evaluate_strategy, performance_metrics,
)

OUT = ROOT / "data" / "strategy_evaluation_outputs"
OUT.mkdir(parents=True, exist_ok=True)


def placebo_random_selection(monthly_prices: pd.DataFrame, monthly_returns: pd.DataFrame,
                             formation_dates: list, trials: int = 500,
                             seed: int = 123, cost_bps: float = 10.0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    stocks = STOCK_SYMBOLS
    rows = []
    for trial in range(trials):
        previous = pd.Series(0.0, index=stocks)
        returns = []
        for i, formation in enumerate(formation_dates):
            holding = monthly_prices.index[monthly_prices.index.get_loc(formation) + 1]
            chosen = rng.choice(stocks, size=3, replace=False)
            weights = pd.Series(0.0, index=stocks)
            weights[list(chosen)] = 1 / 3
            gross = float((weights * monthly_returns.loc[holding, stocks]).sum())
            turnover = float((weights - previous).abs().sum())
            returns.append(gross - turnover * cost_bps / 10_000)
            previous = weights
        metrics = performance_metrics(pd.Series(returns))
        rows.append({"trial": trial, **metrics})
    return pd.DataFrame(rows)


def main() -> int:
    prices = pd.read_csv(ROOT / "data" / "clean" / "adjusted_close_filled_matrix.csv",
                         index_col=0, parse_dates=True)
    result = backtest_momentum(prices, STOCK_SYMBOLS, BENCHMARK_SYMBOL)
    monthly, lots, scores = result["monthly"], result["lots"], result["scores"]
    evaluation = evaluate_strategy(monthly, lots, trials=10_000, seed=42)

    monthly.to_csv(OUT / "monthly_strategy_returns.csv", index=False)
    lots.to_csv(OUT / "trade_lots.csv", index=False)
    pd.DataFrame([evaluation["payoff"]]).to_csv(OUT / "payoff_summary.csv", index=False)
    metrics_table = pd.DataFrame([
        {"series": name, **values} for name, values in evaluation["metrics"].items()
    ])
    metrics_table.to_csv(OUT / "performance_metrics.csv", index=False)
    evaluation["bootstrap"]["iid"].to_csv(OUT / "bootstrap_iid.csv", index=False)
    evaluation["bootstrap"]["block"].to_csv(OUT / "bootstrap_block.csv", index=False)
    pd.DataFrame([evaluation["bootstrap_summary"]]).to_csv(OUT / "bootstrap_summary.csv", index=False)
    evaluation["stress"].to_csv(OUT / "stress_tests.csv", index=False)
    evaluation["criteria"].to_csv(OUT / "decision_criteria.csv", index=False)

    payoff = evaluation["payoff"]
    sensitivity_rows = []
    for p_shift in [-0.10, -0.05, 0.0, 0.05]:
        for rr_mult in [0.8, 0.9, 1.0, 1.1]:
            sensitivity_rows.append({
                "win_probability": payoff["win_probability"] + p_shift,
                "reward_risk": payoff["reward_risk"] * rr_mult,
            })
    batch_ev(pd.DataFrame(sensitivity_rows)).to_csv(OUT / "ev_sensitivity.csv", index=False)

    monthly_prices = result["monthly_prices"]
    monthly_returns = monthly_prices.pct_change()
    formation_dates = list(monthly["formation_date"].unique())
    placebo = placebo_random_selection(monthly_prices, monthly_returns, formation_dates)
    placebo.to_csv(OUT / "placebo_random_selection.csv", index=False)
    actual_total = evaluation["metrics"]["strategy"]["total_return"]
    actual_sharpe = evaluation["metrics"]["strategy"]["sharpe"]
    placebo_summary = {
        "trials": int(len(placebo)),
        "actual_total_return_percentile": float((placebo["total_return"] < actual_total).mean() * 100),
        "actual_sharpe_percentile": float((placebo["sharpe"] < actual_sharpe).mean() * 100),
        "placebo_median_annualised_return": float(placebo["annualised_return"].median()),
        "placebo_median_sharpe": float(placebo["sharpe"].median()),
    }
    pd.DataFrame([placebo_summary]).to_csv(OUT / "placebo_summary.csv", index=False)

    latest_scores = scores.iloc[-1][STOCK_SYMBOLS].dropna().sort_values(ascending=False)
    current_picks = list(latest_scores.head(3).index)
    summary = {
        "strategy": "Monthly 12-1 momentum, top 3 of 10 TSX stocks, equal weight",
        "evaluation_start": str(monthly["holding_date"].min()),
        "evaluation_end": str(monthly["holding_date"].max()),
        "months": evaluation["metrics"]["strategy"]["months"],
        "decision": evaluation["decision"],
        "payoff": payoff,
        "strategy_metrics": evaluation["metrics"]["strategy"],
        "benchmark_metrics": evaluation["metrics"]["benchmark"],
        "equal_weight_metrics": evaluation["metrics"]["equal_weight"],
        "bootstrap_summary": evaluation["bootstrap_summary"],
        "placebo_summary": placebo_summary,
        "current_formation_date": str(scores.index[-1].date()),
        "current_picks": current_picks,
        "current_scores": {k: float(v) for k, v in latest_scores.items()},
    }
    (OUT / "strategy_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
