from __future__ import annotations

import numpy as np
import pandas as pd


def stock_value(shares: float, price: float) -> float:
    return float(shares * price)


def portfolio_value(shares: np.ndarray, prices: np.ndarray) -> float:
    return float(np.dot(np.asarray(shares, dtype=float), np.asarray(prices, dtype=float)))


def create_evaluation_grid(shares: np.ndarray, prices: np.ndarray,
                           shocks_a: np.ndarray, shocks_b: np.ndarray) -> pd.DataFrame:
    rows = []
    for a in shocks_a:
        for b in shocks_b:
            shocked = np.array([prices[0] * (1 + a), prices[1] * (1 + b)])
            value = portfolio_value(shares, shocked)
            rows.append({
                "shock_a": float(a), "shock_b": float(b),
                "price_a": float(shocked[0]), "price_b": float(shocked[1]),
                "portfolio_value": value,
            })
    out = pd.DataFrame(rows)
    base = portfolio_value(shares, prices)
    out["pnl"] = out["portfolio_value"] - base
    out["pnl_pct"] = out["pnl"] / base
    return out


def _finite_gradient(function, point: np.ndarray, steps: np.ndarray) -> np.ndarray:
    point = np.asarray(point, dtype=float)
    gradient = np.zeros(len(point))
    for i in range(len(point)):
        plus = point.copy(); minus = point.copy()
        plus[i] += steps[i]; minus[i] -= steps[i]
        gradient[i] = (function(plus) - function(minus)) / (2 * steps[i])
    return gradient


def compute_partial_derivatives(function, point: np.ndarray,
                                steps: np.ndarray | None = None) -> np.ndarray:
    point = np.asarray(point, dtype=float)
    if steps is None:
        steps = np.array([1e-5] * len(point))
    return _finite_gradient(function, point, np.asarray(steps, dtype=float))


def directional_derivative(gradient: np.ndarray, direction: np.ndarray) -> float:
    direction = np.asarray(direction, dtype=float)
    norm = np.linalg.norm(direction)
    if norm == 0:
        return 0.0
    return float(np.dot(np.asarray(gradient, dtype=float), direction / norm))


def analyze_directions(shares: np.ndarray, prices: np.ndarray,
                       scenarios: dict[str, tuple[float, float]]) -> pd.DataFrame:
    """Exact and first-order P&L for combined percentage price shocks."""
    allocations = np.asarray(shares, dtype=float) * np.asarray(prices, dtype=float)
    base = allocations.sum()
    rows = []
    for name, (a, b) in scenarios.items():
        shock = np.array([a, b])
        exact = float(allocations @ shock)
        unit = directional_derivative(allocations, shock)
        rows.append({
            "scenario": name, "shock_a": a, "shock_b": b,
            "exact_pnl": exact, "exact_pnl_pct": exact / base,
            "directional_derivative_per_unit": unit,
            "first_order_pnl": float(unit * np.linalg.norm(shock)),
        })
    return pd.DataFrame(rows)


def compute_hessian(function, point: np.ndarray,
                    steps: np.ndarray | None = None) -> np.ndarray:
    point = np.asarray(point, dtype=float)
    if steps is None:
        steps = np.array([1e-4] * len(point))
    steps = np.asarray(steps, dtype=float)
    n = len(point)
    hessian = np.zeros((n, n))
    f0 = function(point)
    for i in range(n):
        plus = point.copy(); minus = point.copy()
        plus[i] += steps[i]; minus[i] -= steps[i]
        hessian[i, i] = (function(plus) - 2 * f0 + function(minus)) / steps[i] ** 2
        for j in range(i + 1, n):
            pp = point.copy(); pm = point.copy(); mp = point.copy(); mm = point.copy()
            pp[i] += steps[i]; pp[j] += steps[j]
            pm[i] += steps[i]; pm[j] -= steps[j]
            mp[i] -= steps[i]; mp[j] += steps[j]
            mm[i] -= steps[i]; mm[j] -= steps[j]
            value = (function(pp) - function(pm) - function(mp) + function(mm)) / (4 * steps[i] * steps[j])
            hessian[i, j] = value
            hessian[j, i] = value
    return hessian


def analyze_hessian(hessian: np.ndarray) -> dict:
    values, vectors = np.linalg.eigh(np.asarray(hessian, dtype=float))
    if np.all(values > 1e-10):
        shape = "positive definite: locally bowl-shaped"
    elif np.all(values < -1e-10):
        shape = "negative definite: locally cap-shaped"
    elif np.any(values > 1e-10) and np.any(values < -1e-10):
        shape = "indefinite: saddle-shaped"
    else:
        shape = "positive or negative semidefinite: flat in at least one direction"
    return {"eigenvalues": values, "eigenvectors": vectors, "classification": shape}


def first_order_approximation(base_value: float, gradient: np.ndarray, delta: np.ndarray) -> float:
    return float(base_value + np.asarray(gradient) @ np.asarray(delta))


def second_order_approximation(base_value: float, gradient: np.ndarray,
                               hessian: np.ndarray, delta: np.ndarray) -> float:
    delta = np.asarray(delta, dtype=float)
    return float(base_value + np.asarray(gradient) @ delta
                 + 0.5 * delta @ np.asarray(hessian) @ delta)


def portfolio_volatility(weight_a: float, correlation: float,
                         vol_a: float, vol_b: float) -> float:
    variance = ((weight_a * vol_a) ** 2 + ((1 - weight_a) * vol_b) ** 2
                + 2 * weight_a * (1 - weight_a) * correlation * vol_a * vol_b)
    return float(np.sqrt(max(variance, 0.0)))


def minimum_volatility_weight(correlation: float, vol_a: float, vol_b: float) -> float:
    numerator = vol_b ** 2 - correlation * vol_a * vol_b
    denominator = vol_a ** 2 + vol_b ** 2 - 2 * correlation * vol_a * vol_b
    if denominator == 0:
        return 0.5
    return float(np.clip(numerator / denominator, 0.0, 1.0))


def risk_surface_grid(weights: np.ndarray, correlations: np.ndarray,
                      vol_a: float, vol_b: float) -> pd.DataFrame:
    rows = []
    for rho in correlations:
        for w in weights:
            rows.append({
                "weight_a": float(w), "correlation": float(rho),
                "portfolio_volatility": portfolio_volatility(w, rho, vol_a, vol_b),
            })
    return pd.DataFrame(rows)


def correlation_scenarios(correlations: list[float], vol_a: float, vol_b: float) -> pd.DataFrame:
    rows = []
    for rho in correlations:
        w = minimum_volatility_weight(rho, vol_a, vol_b)
        rows.append({
            "correlation": rho,
            "minimum_volatility_weight_a": w,
            "minimum_volatility": portfolio_volatility(w, rho, vol_a, vol_b),
            "equal_weight_volatility": portfolio_volatility(0.5, rho, vol_a, vol_b),
        })
    return pd.DataFrame(rows)


def risk_report(returns: pd.DataFrame, asset_a: str, asset_b: str,
                capital: float = 100_000.0) -> dict:
    pair = returns[[asset_a, asset_b]].dropna()
    vols = pair.std(ddof=1) * np.sqrt(252)
    corr = float(pair.corr().iloc[0, 1])
    vol_a, vol_b = float(vols.iloc[0]), float(vols.iloc[1])
    base_weight = minimum_volatility_weight(corr, vol_a, vol_b)
    base_point = np.array([base_weight, corr])
    risk_function = lambda p: portfolio_volatility(p[0], p[1], vol_a, vol_b)
    risk_gradient = compute_partial_derivatives(risk_function, base_point, steps=np.array([1e-5, 1e-5]))
    risk_hessian = compute_hessian(risk_function, base_point, steps=np.array([1e-4, 1e-4]))
    return {
        "vol_a": vol_a, "vol_b": vol_b, "correlation": corr,
        "base_weight_a": base_weight,
        "base_volatility": risk_function(base_point),
        "risk_gradient": risk_gradient,
        "risk_hessian": risk_hessian,
        "risk_hessian_analysis": analyze_hessian(risk_hessian),
        "capital": capital,
    }
