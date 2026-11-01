from __future__ import annotations

import numpy as np
import pandas as pd


def trade_profit(quantity: float, entry_price: float, expected_return: float,
                 adv_shares: float, impact_slope: float = 0.25,
                 fixed_cost: float = 0.0) -> float:
    """Expected profit after a quadratic market-impact cost.

    Gross expected profit is quantity times entry price times expected return.
    Total impact is entry price times impact_slope times quantity squared
    divided by average daily volume, so impact per share rises with size.
    """
    gross = quantity * entry_price * expected_return
    impact = entry_price * impact_slope * quantity ** 2 / adv_shares
    return float(gross - impact - fixed_cost)


def profit(quantity: float, entry_price: float, expected_return: float,
           adv_shares: float, impact_slope: float = 0.25,
           fixed_cost: float = 0.0) -> float:
    return trade_profit(quantity, entry_price, expected_return, adv_shares, impact_slope, fixed_cost)


def marginal_profit(quantity: float, entry_price: float, expected_return: float,
                    adv_shares: float, impact_slope: float = 0.25) -> float:
    return float(entry_price * expected_return
                 - 2 * entry_price * impact_slope * quantity / adv_shares)


def optimal_size_impact_only(entry_price: float, expected_return: float,
                             adv_shares: float, impact_slope: float = 0.25) -> float:
    if expected_return <= 0:
        return 0.0
    return float(expected_return * adv_shares / (2 * impact_slope))


def profit_analysis(quantities: np.ndarray, entry_price: float, expected_return: float,
                    adv_shares: float, impact_slope: float = 0.25) -> pd.DataFrame:
    rows = []
    for q in quantities:
        rows.append({
            "quantity": float(q),
            "position_value": float(q * entry_price),
            "expected_profit": profit(q, entry_price, expected_return, adv_shares, impact_slope),
            "marginal_profit_per_share": marginal_profit(q, entry_price, expected_return, adv_shares, impact_slope),
            "impact_cost": float(entry_price * impact_slope * q ** 2 / adv_shares),
        })
    return pd.DataFrame(rows)


def risk_adjusted_return(leverage: float, expected_return: float, horizon_volatility: float,
                         risk_aversion: float = 10.0, financing_rate: float = 0.05,
                         horizon_years: float = 20 / 252) -> float:
    """Certainty-equivalent return on capital for a position leverage multiple.

    Leverage here means position value divided by account capital.
    """
    gross = leverage * expected_return
    financing = max(leverage - 1, 0.0) * financing_rate * horizon_years
    penalty = 0.5 * risk_aversion * (leverage * horizon_volatility) ** 2
    return float(gross - financing - penalty)


def optimal_leverage(expected_return: float, horizon_volatility: float,
                     risk_aversion: float = 10.0, financing_rate: float = 0.05,
                     horizon_years: float = 20 / 252) -> float:
    if expected_return <= 0 or horizon_volatility <= 0:
        return 0.0
    no_borrow = expected_return / (risk_aversion * horizon_volatility ** 2)
    if no_borrow <= 1:
        return float(no_borrow)
    borrowed = (expected_return - financing_rate * horizon_years) / (
        risk_aversion * horizon_volatility ** 2)
    return float(max(borrowed, 0.0))


def kelly_fraction(win_probability: float, reward_risk: float) -> float:
    """Fraction of capital to risk, not fraction to invest, for a binary payoff."""
    return float(win_probability - (1 - win_probability) / reward_risk)


def kelly_analysis(win_probability: float, reward_risk: float, stop_distance: float) -> pd.DataFrame:
    full = kelly_fraction(win_probability, reward_risk)
    rows = []
    for label, multiple in [("Quarter Kelly", 0.25), ("Half Kelly", 0.5), ("Full Kelly", 1.0)]:
        risk_fraction = full * multiple
        rows.append({
            "method": label,
            "kelly_multiple": multiple,
            "capital_risk_fraction": risk_fraction,
            "implied_position_fraction": risk_fraction / stop_distance if stop_distance else np.nan,
        })
    return pd.DataFrame(rows)


def no_edge_win_prob(stop_distance: float, target_distance: float) -> float:
    """Win probability under a driftless random walk, ignoring costs and gaps."""
    total = stop_distance + target_distance
    return float(stop_distance / total) if total else np.nan


def stoploss_analysis(entry_price: float, atr: float, quantity: float,
                      stop_multiples: np.ndarray, reward_risk: float = 1.5) -> pd.DataFrame:
    rows = []
    for multiple in stop_multiples:
        stop_distance = multiple * atr
        target_distance = reward_risk * stop_distance
        rows.append({
            "stop_atr_multiple": float(multiple),
            "stop_price": entry_price - stop_distance,
            "target_price": entry_price + target_distance,
            "stop_distance": float(stop_distance),
            "target_distance": float(target_distance),
            "stop_distance_pct": float(stop_distance / entry_price),
            "target_distance_pct": float(target_distance / entry_price),
            "reward_risk": reward_risk,
            "no_edge_win_probability": no_edge_win_prob(stop_distance, target_distance),
            "dollar_risk_at_quantity": float(quantity * stop_distance),
            "dollar_gain_at_target": float(quantity * target_distance),
        })
    return pd.DataFrame(rows)


def execution_cost(horizon_days: float, quantity: float, adv_shares: float,
                   daily_volatility: float, impact_bps_at_full_participation: float = 10.0,
                   timing_risk_weight: float = 0.25) -> dict:
    participation_per_day = quantity / (adv_shares * horizon_days)
    impact_bps = impact_bps_at_full_participation * np.sqrt(participation_per_day)
    timing_bps = timing_risk_weight * daily_volatility * np.sqrt(horizon_days) * 10_000
    return {
        "horizon_days": float(horizon_days),
        "participation_per_day": float(participation_per_day),
        "impact_bps": float(impact_bps),
        "timing_risk_allowance_bps": float(timing_bps),
        "total_planning_cost_bps": float(impact_bps + timing_bps),
    }


def execution_analysis(horizons: np.ndarray, quantity: float, adv_shares: float,
                       daily_volatility: float) -> pd.DataFrame:
    return pd.DataFrame([
        execution_cost(h, quantity, adv_shares, daily_volatility) for h in horizons
    ])


def design_trade(entry_price: float, win_probability: float, stop_distance_pct: float,
                 target_distance_pct: float, horizon_volatility: float,
                 adv_shares: float, capital: float = 1_000_000.0,
                 round_trip_cost_pct: float = 0.002, risk_budget_pct: float = 0.01,
                 position_cap_pct: float = 0.20, risk_aversion: float = 10.0) -> dict:
    reward_risk = target_distance_pct / stop_distance_pct
    gross_expected = win_probability * target_distance_pct - (1 - win_probability) * stop_distance_pct
    expected_return = gross_expected - round_trip_cost_pct
    q_impact = optimal_size_impact_only(entry_price, expected_return, adv_shares)
    lev = optimal_leverage(expected_return, horizon_volatility, risk_aversion=risk_aversion)
    q_risk_adjusted = lev * capital / entry_price
    q_risk_cap = risk_budget_pct * capital / (entry_price * stop_distance_pct)
    q_position_cap = position_cap_pct * capital / entry_price
    final_quantity = int(max(0, np.floor(min(q_impact, q_risk_adjusted, q_risk_cap, q_position_cap))))
    binding = min(
        [("market impact optimum", q_impact), ("risk-adjusted optimum", q_risk_adjusted),
         ("1% risk budget", q_risk_cap), ("20% position cap", q_position_cap)],
        key=lambda item: item[1],
    )[0]
    position_value = final_quantity * entry_price
    dollar_risk = final_quantity * entry_price * stop_distance_pct
    dollar_target = final_quantity * entry_price * target_distance_pct
    expected_profit = final_quantity * entry_price * expected_return
    return {
        "entry_price": entry_price,
        "stop_price": entry_price * (1 - stop_distance_pct),
        "target_price": entry_price * (1 + target_distance_pct),
        "stop_distance_pct": stop_distance_pct,
        "target_distance_pct": target_distance_pct,
        "reward_risk": reward_risk,
        "win_probability_scenario": win_probability,
        "gross_expected_return": gross_expected,
        "expected_return_after_costs": expected_return,
        "break_even_probability": 1 / (1 + reward_risk),
        "kelly_risk_fraction": kelly_fraction(win_probability, reward_risk),
        "optimal_quantity_impact_only": q_impact,
        "optimal_leverage_risk_adjusted": lev,
        "optimal_quantity_risk_adjusted": q_risk_adjusted,
        "quantity_risk_cap": q_risk_cap,
        "quantity_position_cap": q_position_cap,
        "binding_constraint": binding,
        "final_quantity": final_quantity,
        "position_value": position_value,
        "position_pct_of_capital": position_value / capital,
        "dollar_risk_at_stop": dollar_risk,
        "risk_pct_of_capital": dollar_risk / capital,
        "dollar_gain_at_target": dollar_target,
        "expected_profit_after_costs": expected_profit,
    }
