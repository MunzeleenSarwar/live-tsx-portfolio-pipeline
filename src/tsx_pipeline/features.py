from __future__ import annotations

import numpy as np
import pandas as pd

from .config import BENCHMARK_SYMBOL, SHORT_BY_SYMBOL, STOCK_SYMBOLS


def add_returns(prices: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame(index=prices.index)
    out["simple_return"] = prices.pct_change()
    out["log_return"] = np.log(prices / prices.shift(1))
    return out


def build_daily_features(adjusted_filled: pd.DataFrame) -> pd.DataFrame:
    """Create a tidy daily feature table from the filled adjusted-close matrix."""
    benchmark = adjusted_filled[BENCHMARK_SYMBOL]
    bench_log = np.log(benchmark / benchmark.shift(1))
    rows = []
    for symbol in STOCK_SYMBOLS + [BENCHMARK_SYMBOL]:
        prices = adjusted_filled[symbol]
        log_ret = np.log(prices / prices.shift(1))
        simple_ret = prices.pct_change()
        rolling_high = prices.rolling(252, min_periods=1).max()
        frame = pd.DataFrame({
            "timestamp": adjusted_filled.index,
            "symbol": symbol,
            "short": SHORT_BY_SYMBOL[symbol],
            "adjusted_close": prices.values,
            "simple_return": simple_ret.values,
            "log_return": log_ret.values,
            "realized_vol_20d": log_ret.rolling(20).std(ddof=1).values * np.sqrt(252),
            "realized_vol_60d": log_ret.rolling(60).std(ddof=1).values * np.sqrt(252),
            "drawdown_252d": (prices / rolling_high - 1).values,
        })
        if symbol != BENCHMARK_SYMBOL:
            aligned = pd.concat([log_ret, bench_log], axis=1).dropna()
            rolling_beta = log_ret.rolling(252).cov(bench_log) / bench_log.rolling(252).var()
            rolling_corr = log_ret.rolling(252).corr(bench_log)
            frame["beta_252d"] = rolling_beta.values
            frame["correlation_252d"] = rolling_corr.values
        else:
            frame["beta_252d"] = 1.0
            frame["correlation_252d"] = 1.0
        rows.append(frame)
    features = pd.concat(rows, ignore_index=True)
    return features.sort_values(["timestamp", "symbol"])


def build_weekly_prices(adjusted_filled: pd.DataFrame) -> pd.DataFrame:
    weekly = adjusted_filled.resample("W-FRI").last()
    return weekly.dropna(how="all")


def latest_snapshot(features: pd.DataFrame, intraday_latest: pd.DataFrame | None = None) -> pd.DataFrame:
    snapshots = []
    for symbol, group in features.sort_values("timestamp").groupby("symbol"):
        latest = group.iloc[-1]
        # Returns over several horizons use ordered observations for this symbol.
        closes = group["adjusted_close"]
        def horizon_return(periods: int):
            return float(closes.iloc[-1] / closes.iloc[-periods - 1] - 1) if len(closes) > periods else np.nan
        row = {
            "symbol": symbol, "short": latest["short"],
            "latest_daily_date": latest["timestamp"],
            "adjusted_close": latest["adjusted_close"],
            "return_1d": horizon_return(1), "return_5d": horizon_return(5),
            "return_21d": horizon_return(21), "return_252d": horizon_return(252),
            "realized_vol_20d": latest["realized_vol_20d"],
            "realized_vol_60d": latest["realized_vol_60d"],
            "beta_252d": latest["beta_252d"],
            "correlation_252d": latest["correlation_252d"],
            "drawdown_252d": latest["drawdown_252d"],
        }
        if intraday_latest is not None and not intraday_latest.empty:
            match = intraday_latest[intraday_latest.symbol.eq(symbol)]
            if len(match):
                row["latest_intraday_timestamp"] = match.iloc[-1]["timestamp"]
                row["latest_intraday_close"] = match.iloc[-1]["close"]
        snapshots.append(row)
    return pd.DataFrame(snapshots).sort_values("symbol")
