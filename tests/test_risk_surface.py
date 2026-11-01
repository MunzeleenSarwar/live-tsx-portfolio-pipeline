import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tsx_pipeline.risk_surface import (
    analyze_hessian, compute_hessian, compute_partial_derivatives,
    directional_derivative, first_order_approximation,
    minimum_volatility_weight, portfolio_value, portfolio_volatility,
    second_order_approximation, stock_value,
)


def test_stock_and_portfolio_value():
    assert stock_value(10, 25) == 250
    assert portfolio_value(np.array([10.0, 5.0]), np.array([25.0, 40.0])) == 450


def test_derivatives_of_quadratic():
    f = lambda p: p[0] ** 2 + 2 * p[1] ** 2 + p[0] * p[1]
    point = np.array([1.0, 2.0])
    gradient = compute_partial_derivatives(f, point, steps=np.array([1e-5, 1e-5]))
    assert np.allclose(gradient, [4.0, 9.0], atol=1e-4)
    hessian = compute_hessian(f, point, steps=np.array([1e-4, 1e-4]))
    assert np.allclose(hessian, [[2.0, 1.0], [1.0, 4.0]], atol=1e-3)
    analysis = analyze_hessian(hessian)
    assert "positive definite" in analysis["classification"]
    delta = np.array([0.1, -0.1])
    assert np.isclose(second_order_approximation(f(point), gradient, hessian, delta), f(point + delta), atol=1e-6)
    assert np.isclose(directional_derivative(gradient, np.array([1.0, 0.0])), gradient[0])


def test_portfolio_volatility_and_minimum_weight():
    vol = portfolio_volatility(0.5, 0.0, 0.20, 0.30)
    assert np.isclose(vol, np.sqrt(0.25 * 0.04 + 0.25 * 0.09))
    w = minimum_volatility_weight(0.0, 0.20, 0.30)
    assert 0 < w < 1
    assert portfolio_volatility(w, 0.0, 0.20, 0.30) <= vol


def test_first_order_value_approximation_is_exact_for_linear_value():
    shares = np.array([100.0, 50.0])
    prices = np.array([20.0, 30.0])
    f = lambda p: portfolio_value(shares, p)
    gradient = compute_partial_derivatives(f, prices, steps=np.array([1e-5, 1e-5]))
    delta = np.array([2.0, -3.0])
    assert np.isclose(first_order_approximation(f(prices), gradient, delta), f(prices + delta))
