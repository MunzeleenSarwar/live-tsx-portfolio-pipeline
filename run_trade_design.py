from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from tsx_pipeline.strategy_evaluation import payoff_summary
from tsx_pipeline.trade_design import (
    design_trade, execution_analysis, kelly_analysis, profit_analysis,
    risk_adjusted_return, stoploss_analysis,
)

OUT = ROOT / "data" / "trade_design_outputs"
OUT.mkdir(parents=True, exist_ok=True)
SYMBOL = "CNQ.TO"
CAPITAL = 1_000_000.0


def main() -> int:
    strategy_out = ROOT / "data" / "strategy_evaluation_outputs"
    payoff = pd.read_csv(strategy_out / "payoff_summary.csv").iloc[0].to_dict()
    lots = pd.read_csv(strategy_out / "trade_lots.csv")
    cnq_payoff = payoff_summary(lots.loc[lots["stock"] == SYMBOL, "return"])
    pd.DataFrame([cnq_payoff]).to_csv(OUT / "cnq_payoff_summary.csv", index=False)

    daily = pd.read_parquet(ROOT / "data" / "clean" / "daily_ohlcv_clean.parquet")
    cnq = daily[daily["symbol"] == SYMBOL].sort_values("timestamp").copy()
    for col in ["open", "high", "low", "close", "adjusted_close", "volume"]:
        cnq[col] = pd.to_numeric(cnq[col])
    true_range = pd.concat([
        cnq["high"] - cnq["low"],
        (cnq["high"] - cnq["close"].shift()).abs(),
        (cnq["low"] - cnq["close"].shift()).abs(),
    ], axis=1).max(axis=1)
    atr14 = float(true_range.rolling(14).mean().iloc[-1])
    entry = float(cnq["adjusted_close"].iloc[-1])
    adv20 = float(cnq["volume"].tail(20).mean())
    log_returns = np.log(cnq["adjusted_close"] / cnq["adjusted_close"].shift(1)).dropna()
    daily_vol = float(log_returns.tail(20).std(ddof=1))
    horizon_vol = float(daily_vol * np.sqrt(20))

    stop_distance = 2 * atr14
    target_distance = 1.5 * stop_distance
    plan = design_trade(
        entry_price=entry,
        win_probability=float(payoff["win_probability"]),
        stop_distance_pct=stop_distance / entry,
        target_distance_pct=target_distance / entry,
        horizon_volatility=horizon_vol,
        adv_shares=adv20,
        capital=CAPITAL,
    )
    plan.update({
        "symbol": SYMBOL,
        "signal": "Rank 1 on 12-1 momentum at the latest formation date",
        "atr14": atr14,
        "adv20_shares": adv20,
        "daily_volatility": daily_vol,
        "horizon_volatility_20d": horizon_vol,
        "capital": CAPITAL,
        "win_probability_source": "All 333 momentum trade lots in the strategy evaluation",
        "cnq_only_win_probability": cnq_payoff["win_probability"],
        "cnq_only_trades": cnq_payoff["trades"],
    })
    (OUT / "trade_plan.json").write_text(json.dumps(plan, indent=2), encoding="utf-8")
    pd.DataFrame([{k: v for k, v in plan.items()}]).to_csv(OUT / "trade_plan.csv", index=False)

    quantities = np.array([0, 250, 500, 1000, 1500, 2000, plan["final_quantity"], 3000, 4326,
                           6000, 10000, 25000, 50000, 100000], dtype=float)
    quantities = np.unique(np.round(quantities))
    profit_analysis(quantities, entry, plan["expected_return_after_costs"], adv20).to_csv(
        OUT / "profit_by_size.csv", index=False)

    leverage_rows = []
    for lev in np.round(np.arange(0, 3.01, 0.1), 2):
        leverage_rows.append({
            "leverage": float(lev),
            "position_value": float(lev * CAPITAL),
            "risk_adjusted_return": risk_adjusted_return(
                lev, plan["expected_return_after_costs"], horizon_vol),
            "expected_return_no_penalty": float(lev * plan["expected_return_after_costs"]),
            "volatility_of_capital": float(lev * horizon_vol),
        })
    pd.DataFrame(leverage_rows).to_csv(OUT / "leverage_analysis.csv", index=False)

    kelly_analysis(float(payoff["win_probability"]), plan["reward_risk"],
                   plan["stop_distance_pct"]).to_csv(OUT / "kelly_analysis.csv", index=False)

    stoploss_analysis(entry, atr14, plan["final_quantity"],
                      np.array([1.0, 1.5, 2.0, 2.5, 3.0])).to_csv(
        OUT / "stoploss_analysis.csv", index=False)

    execution_analysis(np.array([0.05, 0.10, 0.25, 0.50, 1.0, 2.0, 3.0, 5.0, 10.0]),
                       plan["final_quantity"], adv20, daily_vol).to_csv(
        OUT / "execution_analysis.csv", index=False)

    print(json.dumps(plan, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
