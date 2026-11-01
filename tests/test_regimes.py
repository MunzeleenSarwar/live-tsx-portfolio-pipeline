import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tsx_pipeline.regimes import (
    angle_between_vectors, compute_svd, count_large_transitions,
    daily_returns, explained_variance_ratios, get_dominant_directions,
    reconstruct_low_rank, reconstruction_quality,
)


def sample_returns():
    rng = np.random.default_rng(11)
    dates = pd.date_range("2024-01-02", periods=80, freq="B")
    common = rng.normal(0, 0.01, len(dates))
    data = {
        "A": common + rng.normal(0, 0.004, len(dates)),
        "B": 0.8 * common + rng.normal(0, 0.005, len(dates)),
        "C": -0.3 * common + rng.normal(0, 0.006, len(dates)),
        "D": rng.normal(0, 0.007, len(dates)),
    }
    return pd.DataFrame(data, index=dates)


def test_daily_returns_from_prices():
    prices = pd.DataFrame({"A": [100.0, 101.0, 102.0], "B": [50.0, 49.0, 51.0]})
    returns = daily_returns(prices)
    assert len(returns) == 2
    assert np.isclose(returns.iloc[0].A, np.log(101 / 100))


def test_svd_ratios_sum_to_one_and_directions_are_orthonormal():
    returns = sample_returns()
    result = compute_svd(returns)
    ratios = explained_variance_ratios(result["singular_values"])
    directions = result["directions"]
    assert np.isclose(ratios.sum(), 1.0)
    assert np.allclose(directions.T @ directions, np.eye(directions.shape[1]), atol=1e-8)


def test_full_rank_reconstruction_recovers_returns():
    returns = sample_returns()
    matrix = returns.to_numpy()
    reconstructed = reconstruct_low_rank(matrix, rank=matrix.shape[1])
    assert np.allclose(matrix, reconstructed, atol=1e-8)
    quality = reconstruction_quality(returns, ranks=[matrix.shape[1]])
    assert np.isclose(quality.iloc[0].variance_explained, 1.0)


def test_angles_and_transition_count():
    assert np.isclose(angle_between_vectors([1, 0], [0, 1]), 90)
    assert np.isclose(angle_between_vectors([1, 0], [-1, 0]), 180)
    assert count_large_transitions(pd.Series([100, 140, 160]), 135) == 2


def test_dominant_directions_shape_and_pc1_orientation():
    returns = sample_returns()
    loadings = get_dominant_directions(returns, n_directions=3)
    assert loadings.shape == (4, 3)
    assert loadings["PC1"].sum() > 0
