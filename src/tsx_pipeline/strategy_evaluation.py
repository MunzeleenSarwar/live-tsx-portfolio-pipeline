from __future__ import annotations

import numpy as np
import pandas as pd

RISK_FREE_ANNUAL = 0.02


def win_rate(outcomes: pd.Series | np.ndarray) -> float:
    values = pd.Series(outcomes).dropna()
    return float((values > 0).mean()) if len(values) else np.nan


def create_strategy_params(top_n: int = 3, lookback_months: int = 12,
                           skip_months: int = 1, cost_bps: float = 10.0) -> dict:
    return {
        "top_n": top_n,
        "lookback_months": lookback_months,
        "skip_months": skip_months,
        "cost_bps": cost_bps,
        "rebalance": "monthly",
        "weighting": "equal",
    }


def compute_trade_pnl(entry_price: float, exit_price: float, quantity: float = 1.0,
                      cost: float = 0.0) -> float:
    return float((exit_price - entry_price) * quantity - cost)


def build_outcome_vectors(trade_returns: pd.Series) -> dict[str, np.ndarray]:
    values = pd.Series(trade_returns).dropna().to_numpy(dtype=float)
    return {"wins": values[values > 0], "losses": values[values <= 0], "all": values}


def expected_value(win_probability: float, reward_risk: float) -> float:
    """Expected value in units of R, where one losing trade loses 1R."""
    return float(win_probability * reward_risk - (1 - win_probability))


def ev_from_params(params: dict) -> float:
    return expected_value(params["win_probability"], params["reward_risk"])


def batch_ev(table: pd.DataFrame) -> pd.DataFrame:
    out = table.copy()
    out["expected_value_R"] = out.apply(
        lambda r: expected_value(r["win_probability"], r["reward_risk"]), axis=1)
    out["break_even_probability"] = out["reward_risk"].map(break_even_prob)
    out["margin_above_breakeven"] = out["win_probability"] - out["break_even_probability"]
    return out


def break_even_prob(reward_risk: float) -> float:
    return float(1 / (1 + reward_risk))


def break_even_win(reward_risk: float) -> float:
    """Alias using the naming in the QuantFrame project outline."""
    return break_even_prob(reward_risk)


def margin_above_breakeven(win_probability: float, reward_risk: float) -> float:
    return float(win_probability - break_even_prob(reward_risk))


def payoff_summary(trade_returns: pd.Series) -> dict:
    vectors = build_outcome_vectors(trade_returns)
    wins, losses = vectors["wins"], vectors["losses"]
    p = len(wins) / len(vectors["all"]) if len(vectors["all"]) else np.nan
    avg_win = float(wins.mean()) if len(wins) else np.nan
    avg_loss = float(losses.mean()) if len(losses) else np.nan
    reward_risk = avg_win / abs(avg_loss) if avg_loss else np.nan
    return {
        "trades": int(len(vectors["all"])),
        "win_probability": float(p),
        "average_win": avg_win,
        "average_loss": avg_loss,
        "reward_risk": float(reward_risk),
        "expected_value_R": expected_value(p, reward_risk),
        "expected_return_per_trade": float(vectors["all"].mean()) if len(vectors["all"]) else np.nan,
        "break_even_probability": break_even_prob(reward_risk),
        "margin_above_breakeven": margin_above_breakeven(p, reward_risk),
    }


def month_end_prices(prices: pd.DataFrame) -> pd.DataFrame:
    """Last actual observation in each calendar month, keeping the trading date."""
    return prices.groupby([prices.index.year, prices.index.month]).tail(1)


def momentum_scores(monthly_prices: pd.DataFrame, stocks: list[str]) -> pd.DataFrame:
    """12-1 momentum: return from 13 months ago to 1 month ago."""
    return monthly_prices[stocks].shift(1) / monthly_prices[stocks].shift(13) - 1


def backtest_momentum(prices: pd.DataFrame, stocks: list[str], benchmark: str,
                      params: dict | None = None) -> dict[str, pd.DataFrame]:
    if params is None:
        params = create_strategy_params()
    top_n = int(params["top_n"])
    cost_rate = float(params["cost_bps"]) / 10_000
    monthly = month_end_prices(prices)
    monthly_returns = monthly.pct_change()
    scores = momentum_scores(monthly, stocks)

    formations = []
    previous_weights = pd.Series(0.0, index=stocks)
    for i in range(len(monthly) - 1):
        formation_date = monthly.index[i]
        holding_date = monthly.index[i + 1]
        score = scores.loc[formation_date]
        if score[stocks].isna().any():
            continue
        selected = list(score[stocks].nlargest(top_n).index)
        weights = pd.Series(0.0, index=stocks)
        weights[selected] = 1 / top_n
        gross = float((weights * monthly_returns.loc[holding_date, stocks]).sum())
        turnover = float((weights - previous_weights).abs().sum())
        formations.append({
            "formation_date": formation_date,
            "holding_date": holding_date,
            "selected": ",".join(selected),
            "gross_return": gross,
            "turnover": turnover,
            "cost": turnover * cost_rate,
            "net_return": gross - turnover * cost_rate,
            "benchmark_return": float(monthly_returns.loc[holding_date, benchmark]),
            "equal_weight_return": float(monthly_returns.loc[holding_date, stocks].mean()),
        })
        for stock in selected:
            formations.append({
                "formation_date": formation_date,
                "holding_date": holding_date,
                "selected": stock,
                "gross_return": np.nan,
                "turnover": np.nan,
                "cost": np.nan,
                "net_return": np.nan,
                "benchmark_return": np.nan,
                "equal_weight_return": np.nan,
                "_lot_return": float(monthly_returns.loc[holding_date, stock]),
                "_lot_stock": stock,
            })
        previous_weights = weights

    frame = pd.DataFrame(formations)
    monthly_rows = frame[frame["gross_return"].notna()].copy()
    monthly_out = monthly_rows[[
        "formation_date", "holding_date", "selected", "gross_return",
        "turnover", "cost", "net_return", "benchmark_return", "equal_weight_return",
    ]].reset_index(drop=True)
    monthly_out.index = pd.DatetimeIndex(monthly_out["holding_date"])
    lots = frame[frame["_lot_return"].notna()][[
        "formation_date", "holding_date", "_lot_stock", "_lot_return",
    ]].rename(columns={"_lot_stock": "stock", "_lot_return": "return"}).reset_index(drop=True)
    return {"monthly": monthly_out, "lots": lots, "scores": scores, "monthly_prices": monthly}


def performance_metrics(monthly_returns: pd.Series, risk_free_annual: float = RISK_FREE_ANNUAL) -> dict:
    r = pd.Series(monthly_returns).dropna()
    n = len(r)
    if n == 0:
        return {}
    growth = (1 + r).cumprod()
    drawdown = growth / growth.cummax() - 1
    annual_return = float(growth.iloc[-1] ** (12 / n) - 1)
    annual_vol = float(r.std(ddof=1) * np.sqrt(12))
    monthly_rf = risk_free_annual / 12
    sharpe = float((r.mean() - monthly_rf) / r.std(ddof=1) * np.sqrt(12)) if r.std(ddof=1) else np.nan
    t_stat = float(r.mean() / (r.std(ddof=1) / np.sqrt(n))) if r.std(ddof=1) else np.nan
    tail = r[r <= r.quantile(0.05)]
    return {
        "months": int(n),
        "total_return": float(growth.iloc[-1] - 1),
        "annualised_return": annual_return,
        "annualised_volatility": annual_vol,
        "sharpe": sharpe,
        "t_statistic": t_stat,
        "max_drawdown": float(drawdown.min()),
        "hit_rate": float((r > 0).mean()),
        "best_month": float(r.max()),
        "worst_month": float(r.min()),
        "monthly_cvar95": float(tail.mean()) if len(tail) else np.nan,
    }


def simulate_outcomes(monthly_returns: pd.Series, trials: int = 10_000,
                      seed: int = 42, block_months: int | None = None) -> pd.DataFrame:
    """Bootstrap complete return paths of the same length as the sample."""
    r = pd.Series(monthly_returns).dropna().to_numpy(dtype=float)
    n = len(r)
    rng = np.random.default_rng(seed)
    rows = []
    for trial in range(trials):
        if block_months is None:
            sample = rng.choice(r, size=n, replace=True)
        else:
            blocks = []
            while sum(len(b) for b in blocks) < n:
                start = rng.integers(0, n)
                idx = [(start + j) % n for j in range(block_months)]
                blocks.append(r[idx])
            sample = np.concatenate(blocks)[:n]
        growth = float(np.prod(1 + sample))
        rows.append({
            "trial": trial,
            "terminal_multiple": growth,
            "total_return": growth - 1,
            "annualised_return": growth ** (12 / n) - 1,
        })
    return pd.DataFrame(rows)


def simulate_pnl_path(monthly_returns: pd.Series, starting_value: float = 100.0) -> pd.Series:
    return starting_value * (1 + pd.Series(monthly_returns).dropna()).cumprod()


def run_trials(monthly_returns: pd.Series, trials: int = 10_000, seed: int = 42) -> dict:
    iid = simulate_outcomes(monthly_returns, trials=trials, seed=seed)
    block = simulate_outcomes(monthly_returns, trials=trials, seed=seed + 1, block_months=6)
    return {"iid": iid, "block": block}


def ev_with_slippage(win_probability: float, reward_risk: float, slippage_R: float) -> float:
    return expected_value(win_probability, reward_risk) - slippage_R


def ev_with_tail_risk(win_probability: float, reward_risk: float,
                      tail_probability: float, tail_loss_R: float) -> float:
    base = expected_value(win_probability, reward_risk)
    return float((1 - tail_probability) * base - tail_probability * tail_loss_R)


def stress_test(monthly: pd.DataFrame, gross_returns: pd.Series,
                turnover: pd.Series) -> pd.DataFrame:
    """Stress the monthly strategy series under costs, removed winners and tail shocks."""
    rows = []

    def add(name: str, series: pd.Series) -> None:
        metrics = performance_metrics(series)
        rows.append({"scenario": name, **metrics})

    base_cost = turnover * (10 / 10_000)
    add("Base case, 10 bps costs", gross_returns - base_cost)
    add("Costs at 25 bps", gross_returns - turnover * (25 / 10_000))
    add("Costs at 50 bps", gross_returns - turnover * (50 / 10_000))
    net = gross_returns - base_cost
    add("Best 6 months removed", net.drop(index=net.nlargest(6).index))
    add("Best 12 months removed", net.drop(index=net.nlargest(12).index))
    crisis = pd.concat([net, pd.Series([-0.20], index=[net.index[-1] + pd.offsets.MonthEnd(1)])])
    add("One additional -20% month", crisis)
    stressed = net.copy()
    cutoff = stressed.quantile(0.10)
    stressed.loc[stressed <= cutoff] *= 1.5
    add("Worst decile losses increased by 50%", stressed)
    add("2020 onward only", net[net.index >= "2020-01-01"])
    return pd.DataFrame(rows)


def trading_decision(criteria: pd.DataFrame) -> str:
    failed = criteria.loc[~criteria["passed"], "criterion"].tolist()
    return "DO NOT TRADE" if failed else "TRADE"


def evaluate_strategy(monthly: pd.DataFrame, lots: pd.DataFrame,
                      trials: int = 10_000, seed: int = 42) -> dict:
    net = monthly.set_index("holding_date")["net_return"]
    gross = monthly.set_index("holding_date")["gross_return"]
    turnover = monthly.set_index("holding_date")["turnover"]
    benchmark = monthly.set_index("holding_date")["benchmark_return"]
    equal_weight = monthly.set_index("holding_date")["equal_weight_return"]
    payoff = payoff_summary(lots["return"])
    metrics = {
        "strategy": performance_metrics(net),
        "benchmark": performance_metrics(benchmark),
        "equal_weight": performance_metrics(equal_weight),
    }
    boots = run_trials(net, trials=trials, seed=seed)
    bench_total = float((1 + benchmark).prod())
    bootstrap_summary = {
        "iid_probability_profitable": float((boots["iid"]["terminal_multiple"] > 1).mean()),
        "iid_probability_beats_benchmark": float((boots["iid"]["terminal_multiple"] > bench_total).mean()),
        "iid_median_annualised_return": float(boots["iid"]["annualised_return"].median()),
        "iid_p05_annualised_return": float(boots["iid"]["annualised_return"].quantile(0.05)),
        "iid_p95_annualised_return": float(boots["iid"]["annualised_return"].quantile(0.95)),
        "block_probability_profitable": float((boots["block"]["terminal_multiple"] > 1).mean()),
        "block_probability_beats_benchmark": float((boots["block"]["terminal_multiple"] > bench_total).mean()),
        "block_median_annualised_return": float(boots["block"]["annualised_return"].median()),
    }
    stresses = stress_test(monthly, gross, turnover)
    criteria = pd.DataFrame([
        {"criterion": "Positive expected value per trade lot", "value": payoff["expected_value_R"],
         "hurdle": 0.0, "passed": payoff["expected_value_R"] > 0},
        {"criterion": "Monthly mean return t-statistic at least 2", "value": metrics["strategy"]["t_statistic"],
         "hurdle": 2.0, "passed": metrics["strategy"]["t_statistic"] >= 2},
        {"criterion": "Bootstrap probability of beating the benchmark at least 80%",
         "value": bootstrap_summary["iid_probability_beats_benchmark"], "hurdle": 0.80,
         "passed": bootstrap_summary["iid_probability_beats_benchmark"] >= 0.80},
        {"criterion": "Sharpe ratio at least equal to the equal-weight universe",
         "value": metrics["strategy"]["sharpe"], "hurdle": metrics["equal_weight"]["sharpe"],
         "passed": metrics["strategy"]["sharpe"] >= metrics["equal_weight"]["sharpe"]},
        {"criterion": "Maximum drawdown no worse than 25%",
         "value": metrics["strategy"]["max_drawdown"], "hurdle": -0.25,
         "passed": metrics["strategy"]["max_drawdown"] >= -0.25},
        {"criterion": "Point-in-time universe with no selection bias",
         "value": 0.0, "hurdle": 1.0, "passed": False},
    ])
    return {
        "payoff": payoff,
        "metrics": metrics,
        "bootstrap": boots,
        "bootstrap_summary": bootstrap_summary,
        "stress": stresses,
        "criteria": criteria,
        "decision": trading_decision(criteria),
    }
