from __future__ import annotations

import numpy as np
import pandas as pd


def daily_returns(prices: pd.DataFrame, log_returns: bool = True) -> pd.DataFrame:
    """Return daily returns from a price matrix, preserving dates and symbols."""
    prices = prices.sort_index()
    if log_returns:
        out = np.log(prices / prices.shift(1))
    else:
        out = prices.pct_change()
    return out.dropna(how="any")


def create_return_vector(returns: pd.DataFrame, date) -> np.ndarray:
    """Return one market day as a vector in asset order."""
    return returns.loc[pd.Timestamp(date)].to_numpy(dtype=float)


def stack_return_vectors(returns: pd.DataFrame) -> tuple[pd.DatetimeIndex, np.ndarray]:
    """Stack all daily return vectors into a date-by-asset matrix."""
    clean = returns.dropna(how="any").sort_index()
    return clean.index, clean.to_numpy(dtype=float)


def get_dimensions(matrix: np.ndarray) -> dict[str, int]:
    matrix = np.asarray(matrix)
    return {"days": int(matrix.shape[0]), "assets": int(matrix.shape[1])}


def prepare_matrix(returns: pd.DataFrame, standardize: bool = False) -> tuple[np.ndarray, pd.Series, pd.Series]:
    """Centre returns by asset. Optionally divide by each asset's sample volatility."""
    values = returns.to_numpy(dtype=float)
    center = pd.Series(values.mean(axis=0), index=returns.columns)
    scales = pd.Series(values.std(axis=0, ddof=1), index=returns.columns)
    prepared = values - center.to_numpy()
    if standardize:
        prepared = prepared / scales.to_numpy()
    return prepared, center, scales


def _orient_directions(directions: np.ndarray) -> np.ndarray:
    """Apply a stable sign rule because SVD signs are arbitrary."""
    out = np.asarray(directions, dtype=float).copy()
    for j in range(out.shape[1]):
        if j == 0:
            flip = np.sum(out[:, j]) < 0
        else:
            flip = out[np.argmax(np.abs(out[:, j])), j] < 0
        if flip:
            out[:, j] *= -1
    return out


def compute_svd(returns: pd.DataFrame, standardize: bool = False) -> dict:
    prepared, center, scales = prepare_matrix(returns, standardize=standardize)
    u, singular, vt = np.linalg.svd(prepared, full_matrices=False)
    directions = _orient_directions(vt.T)
    # Keep scores consistent with the oriented directions.
    scores = prepared @ directions
    return {
        "prepared": prepared,
        "center": center,
        "scales": scales,
        "left_vectors": u,
        "singular_values": singular,
        "directions": directions,
        "scores": scores,
    }


def get_singular_values(matrix: np.ndarray) -> np.ndarray:
    return np.linalg.svd(np.asarray(matrix, dtype=float), compute_uv=False)


def explained_variance_ratios(singular_values: np.ndarray) -> np.ndarray:
    squares = np.asarray(singular_values, dtype=float) ** 2
    total = squares.sum()
    return squares / total if total else np.zeros_like(squares)


def get_dominant_directions(returns: pd.DataFrame, n_directions: int = 3,
                            standardize: bool = False) -> pd.DataFrame:
    result = compute_svd(returns, standardize=standardize)
    directions = result["directions"][:, :n_directions]
    columns = [f"PC{i + 1}" for i in range(n_directions)]
    return pd.DataFrame(directions, index=returns.columns, columns=columns)


def project_onto_direction(vector: np.ndarray, direction: np.ndarray) -> float:
    return float(np.dot(np.asarray(vector, dtype=float), np.asarray(direction, dtype=float)))


def variance_along_direction(matrix: np.ndarray, direction: np.ndarray) -> float:
    matrix = np.asarray(matrix, dtype=float)
    direction = np.asarray(direction, dtype=float)
    projections = matrix @ direction
    total = np.sum((matrix - matrix.mean(axis=0)) ** 2)
    return float(np.sum(projections ** 2) / total) if total else 0.0


def project_all_days(returns: pd.DataFrame, n_directions: int = 5,
                     standardize: bool = False) -> pd.DataFrame:
    result = compute_svd(returns, standardize=standardize)
    columns = [f"PC{i + 1}" for i in range(n_directions)]
    return pd.DataFrame(result["scores"][:, :n_directions], index=returns.index, columns=columns)


def distances_from_center(matrix: np.ndarray) -> np.ndarray:
    matrix = np.asarray(matrix, dtype=float)
    centered = matrix - matrix.mean(axis=0)
    return np.linalg.norm(centered, axis=1)


def find_most_extreme_day(returns: pd.DataFrame) -> pd.Series:
    _, matrix = stack_return_vectors(returns)
    distances = distances_from_center(matrix)
    idx = int(np.argmax(distances))
    return pd.Series({
        "date": returns.dropna(how="any").index[idx],
        "distance_from_center": float(distances[idx]),
        "equal_weight_return": float(returns.dropna(how="any").iloc[idx].mean()),
    })


def reconstruct_low_rank(matrix: np.ndarray, rank: int, center: np.ndarray | None = None) -> np.ndarray:
    matrix = np.asarray(matrix, dtype=float)
    if center is None:
        center = matrix.mean(axis=0)
    centered = matrix - center
    if rank == 0:
        return np.repeat(center.reshape(1, -1), len(matrix), axis=0)
    u, singular, vt = np.linalg.svd(centered, full_matrices=False)
    return (u[:, :rank] * singular[:rank]) @ vt[:rank] + center


def compute_residuals(original: np.ndarray, reconstructed: np.ndarray) -> np.ndarray:
    return np.asarray(original, dtype=float) - np.asarray(reconstructed, dtype=float)


def reconstruction_quality(returns: pd.DataFrame, ranks: range | list[int] | None = None) -> pd.DataFrame:
    _, matrix = stack_return_vectors(returns)
    center = matrix.mean(axis=0)
    centered = matrix - center
    denominator = float(np.sum(centered ** 2))
    if ranks is None:
        ranks = list(range(0, matrix.shape[1] + 1))
    rows = []
    for rank in ranks:
        reconstructed = reconstruct_low_rank(matrix, int(rank), center=center)
        residuals = compute_residuals(matrix, reconstructed)
        residual_ss = float(np.sum(residuals ** 2))
        rows.append({
            "rank": int(rank),
            "variance_explained": 1 - residual_ss / denominator if denominator else 0.0,
            "residual_share": residual_ss / denominator if denominator else 0.0,
            "residual_rms_bp": float(np.sqrt(np.mean(residuals ** 2)) * 10_000),
        })
    return pd.DataFrame(rows)


def angle_between_vectors(first: np.ndarray, second: np.ndarray) -> float:
    first = np.asarray(first, dtype=float)
    second = np.asarray(second, dtype=float)
    denom = np.linalg.norm(first) * np.linalg.norm(second)
    if denom == 0:
        return float("nan")
    cosine = np.clip(np.dot(first, second) / denom, -1.0, 1.0)
    return float(np.degrees(np.arccos(cosine)))


def daily_angles(returns: pd.DataFrame) -> pd.Series:
    _, matrix = stack_return_vectors(returns)
    centered = matrix - matrix.mean(axis=0)
    angles = [np.nan]
    for i in range(1, len(centered)):
        angles.append(angle_between_vectors(centered[i - 1], centered[i]))
    return pd.Series(angles, index=returns.dropna(how="any").index, name="angle_from_previous_day_degrees")


def count_large_transitions(angles: pd.Series | np.ndarray, threshold_degrees: float = 135.0) -> int:
    values = pd.Series(angles).dropna()
    return int((values > threshold_degrees).sum())


def find_transition_days(returns: pd.DataFrame, threshold_degrees: float = 135.0,
                         largest: int | None = None) -> pd.DataFrame:
    angles = daily_angles(returns)
    out = pd.DataFrame({"date": angles.index, "angle_from_previous_day_degrees": angles.values})
    out["previous_date"] = out["date"].shift(1)
    out["is_large_transition"] = out["angle_from_previous_day_degrees"] > threshold_degrees
    if largest is not None:
        return out.sort_values("angle_from_previous_day_degrees", ascending=False).head(largest).reset_index(drop=True)
    return out[out["is_large_transition"]].sort_values("angle_from_previous_day_degrees", ascending=False).reset_index(drop=True)


def assign_market_states(benchmark_returns: pd.Series, window: int = 20,
                         volatility_quantile: float = 0.75) -> pd.DataFrame:
    """Assign descriptive states from trailing benchmark direction and volatility.

    The volatility threshold uses the full sample, so these labels are for
    retrospective description. They are not a real-time trading rule.
    """
    rolling_vol = benchmark_returns.rolling(window).std(ddof=1) * np.sqrt(252)
    rolling_return = benchmark_returns.rolling(window).sum()
    threshold = rolling_vol.quantile(volatility_quantile)
    labels = []
    for vol, ret in zip(rolling_vol, rolling_return):
        if pd.isna(vol) or pd.isna(ret):
            labels.append("Warm-up")
        elif vol >= threshold and ret < 0:
            labels.append("High-volatility decline")
        elif vol >= threshold:
            labels.append("High-volatility advance")
        elif ret < 0:
            labels.append("Calm pullback")
        else:
            labels.append("Calm advance")
    return pd.DataFrame({
        "benchmark_trailing_return": rolling_return,
        "benchmark_trailing_volatility": rolling_vol,
        "volatility_threshold": threshold,
        "market_state": labels,
    }, index=benchmark_returns.index)


def spectrum_table(returns: pd.DataFrame, standardize: bool = False) -> pd.DataFrame:
    result = compute_svd(returns, standardize=standardize)
    ratios = explained_variance_ratios(result["singular_values"])
    return pd.DataFrame({
        "component": [f"PC{i + 1}" for i in range(len(ratios))],
        "singular_value": result["singular_values"],
        "explained_variance_ratio": ratios,
        "cumulative_explained_variance": np.cumsum(ratios),
    })


def annual_structure(returns: pd.DataFrame, benchmark_returns: pd.Series) -> pd.DataFrame:
    rows = []
    for year, group in returns.groupby(returns.index.year):
        if len(group) < 30:
            continue
        spectrum = spectrum_table(group)
        corr = group.corr().to_numpy()
        upper = corr[np.triu_indices_from(corr, k=1)]
        bench = benchmark_returns.reindex(group.index)
        rows.append({
            "year": int(year), "days": int(len(group)),
            "pc1_explained_variance": float(spectrum.iloc[0].explained_variance_ratio),
            "top3_explained_variance": float(spectrum.iloc[:3].explained_variance_ratio.sum()),
            "average_pairwise_correlation": float(np.mean(upper)),
            "equal_weight_volatility": float(group.mean(axis=1).std(ddof=1) * np.sqrt(252)),
            "benchmark_volatility": float(bench.std(ddof=1) * np.sqrt(252)),
        })
    return pd.DataFrame(rows)


def rolling_structure(returns: pd.DataFrame, window: int = 252, step: int = 21) -> pd.DataFrame:
    rows = []
    values = returns.to_numpy(dtype=float)
    for end in range(window, len(values) + 1, step):
        group = returns.iloc[end - window:end]
        spectrum = spectrum_table(group)
        corr = group.corr().to_numpy()
        upper = corr[np.triu_indices_from(corr, k=1)]
        singular = spectrum.singular_value.to_numpy()
        rows.append({
            "window_end": group.index[-1], "window_start": group.index[0],
            "pc1_explained_variance": float(spectrum.iloc[0].explained_variance_ratio),
            "top3_explained_variance": float(spectrum.iloc[:3].explained_variance_ratio.sum()),
            "average_pairwise_correlation": float(np.mean(upper)),
            "pc1_pc2_singular_ratio": float(singular[0] / singular[1]) if singular[1] else np.nan,
        })
    return pd.DataFrame(rows)


def regime_report(returns: pd.DataFrame, benchmark_returns: pd.Series) -> dict[str, pd.DataFrame]:
    """Assemble the main regime-structure tables from a daily return matrix."""
    spectrum = spectrum_table(returns)
    standardized_spectrum = spectrum_table(returns, standardize=True)
    loadings = get_dominant_directions(returns, n_directions=5)
    standardized_loadings = get_dominant_directions(returns, n_directions=5, standardize=True)
    projections = project_all_days(returns, n_directions=5)
    angles = daily_angles(returns)
    states = assign_market_states(benchmark_returns.reindex(returns.index))
    _, matrix = stack_return_vectors(returns)
    distances = distances_from_center(matrix)
    rank3 = reconstruction_quality(returns, ranks=[3]).iloc[0]
    reconstructed = reconstruct_low_rank(matrix, rank=3)
    residuals = compute_residuals(matrix, reconstructed)
    daily = projections.copy()
    daily.insert(0, "benchmark_return", benchmark_returns.reindex(returns.index).values)
    daily.insert(0, "equal_weight_return", returns.mean(axis=1).values)
    daily["distance_from_center"] = distances
    daily["rank3_residual_norm"] = np.linalg.norm(residuals, axis=1)
    daily["rank3_residual_share"] = daily["rank3_residual_norm"] ** 2 / np.maximum(distances ** 2, 1e-16)
    daily["angle_from_previous_day_degrees"] = angles.values
    daily["is_large_transition"] = daily["angle_from_previous_day_degrees"] > 135
    daily = daily.join(states)
    return {
        "spectrum": spectrum,
        "standardized_spectrum": standardized_spectrum,
        "loadings": loadings,
        "standardized_loadings": standardized_loadings,
        "daily": daily,
        "reconstruction": reconstruction_quality(returns),
        "annual_structure": annual_structure(returns, benchmark_returns),
        "rolling_structure": rolling_structure(returns),
    }
