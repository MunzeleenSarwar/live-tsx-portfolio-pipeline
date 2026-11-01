from __future__ import annotations

import numpy as np
import pandas as pd

from .config import BENCHMARK_SYMBOL, STOCK_SYMBOLS

NUMERIC_COLUMNS = [
    "open", "high", "low", "close", "adjusted_close", "volume",
    "dividends", "stock_splits",
]


def validate_ohlcv(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    out["timestamp"] = pd.to_datetime(out["timestamp"])
    for col in NUMERIC_COLUMNS:
        if col in out:
            out[col] = pd.to_numeric(out[col], errors="coerce")
        else:
            out[col] = np.nan
    out = out.sort_values(["symbol", "timestamp", "retrieved_at"])
    out["is_duplicate"] = out.duplicated(["symbol", "timestamp"], keep=False)

    errors: list[str] = []
    warnings: list[str] = []
    for row in out.itertuples(index=False):
        row_errors = []
        row_warnings = []
        values = [row.open, row.high, row.low, row.close, row.adjusted_close]
        if pd.isna(row.timestamp):
            row_errors.append("missing_timestamp")
        if any(pd.isna(v) for v in values):
            row_errors.append("missing_ohlc_or_adjusted_close")
        elif any(v <= 0 for v in values):
            row_errors.append("non_positive_price")
        else:
            if row.high < max(row.open, row.close, row.low):
                row_errors.append("high_below_other_prices")
            if row.low > min(row.open, row.close, row.high):
                row_errors.append("low_above_other_prices")
        if pd.notna(row.volume) and row.volume < 0:
            row_errors.append("negative_volume")
        if pd.isna(row.volume):
            row_warnings.append("missing_volume")
        elif row.volume == 0 and not str(row.symbol).startswith("^"):
            row_warnings.append("zero_volume")
        if row.is_duplicate:
            row_warnings.append("duplicate_timestamp")
        errors.append(";".join(row_errors))
        warnings.append(";".join(row_warnings))
    out["quality_errors"] = errors
    out["quality_warnings"] = warnings
    out["is_valid"] = out["quality_errors"].eq("")
    out["quality_status"] = np.where(
        ~out["is_valid"], "invalid",
        np.where(out["quality_warnings"].ne(""), "warning", "valid"),
    )
    return out


def deduplicate_valid(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    ordered = frame.sort_values(["symbol", "timestamp", "retrieved_at"])
    duplicate_rows = ordered.duplicated(["symbol", "timestamp"], keep=False)
    deduped = ordered.drop_duplicates(["symbol", "timestamp"], keep="last")
    quarantine = deduped.loc[~deduped["is_valid"]].copy()
    clean = deduped.loc[deduped["is_valid"]].copy()
    clean.attrs["duplicate_rows_removed"] = int(duplicate_rows.sum() - clean.duplicated(["symbol", "timestamp"]).sum())
    return clean.sort_values(["timestamp", "symbol"]), quarantine.sort_values(["timestamp", "symbol"])


def benchmark_sessions(clean: pd.DataFrame) -> pd.DatetimeIndex:
    dates = clean.loc[clean["symbol"].eq(BENCHMARK_SYMBOL), "timestamp"]
    return pd.DatetimeIndex(sorted(dates.unique()))


def detect_gaps(clean: pd.DataFrame, sessions: pd.DatetimeIndex) -> tuple[pd.DataFrame, pd.DataFrame]:
    gap_rows, fill_rows = [], []
    session_pos = {date: i for i, date in enumerate(sessions)}
    for symbol in STOCK_SYMBOLS + [BENCHMARK_SYMBOL]:
        group = clean[clean["symbol"].eq(symbol)]
        if group.empty:
            continue
        first, last = group.timestamp.min(), group.timestamp.max()
        expected = sessions[(sessions >= first) & (sessions <= last)]
        missing = sorted(set(expected) - set(group.timestamp))
        # Group contiguous missing sessions.
        groups: list[list[pd.Timestamp]] = []
        for date in missing:
            if groups and session_pos[date] == session_pos[groups[-1][-1]] + 1:
                groups[-1].append(date)
            else:
                groups.append([date])
        known = group.set_index("timestamp")["adjusted_close"].sort_index()
        for dates in groups:
            gap_rows.append({
                "symbol": symbol, "gap_start": dates[0], "gap_end": dates[-1],
                "missing_sessions": len(dates),
            })
            prior = known[known.index < dates[0]]
            previous_close = float(prior.iloc[-1]) if len(prior) else np.nan
            fillable = len(dates) <= 5 and len(prior) > 0
            for date in dates:
                fill_rows.append({
                    "symbol": symbol, "timestamp": date,
                    "filled": bool(fillable), "fill_method": "forward_fill" if fillable else "not_filled",
                    "filled_adjusted_close": previous_close if fillable else np.nan,
                    "reason": "missing_from_source" if fillable else "gap_too_long_or_no_prior_price",
                })
    return pd.DataFrame(gap_rows), pd.DataFrame(fill_rows)


def build_close_matrices(clean: pd.DataFrame, fill_report: pd.DataFrame,
                         sessions: pd.DatetimeIndex) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    symbols = STOCK_SYMBOLS + [BENCHMARK_SYMBOL]
    adjusted = clean.pivot(index="timestamp", columns="symbol", values="adjusted_close").reindex(sessions)
    raw = clean.pivot(index="timestamp", columns="symbol", values="close").reindex(sessions)
    filled = adjusted.copy()
    was_filled = pd.DataFrame(False, index=sessions, columns=symbols)
    if not fill_report.empty:
        for row in fill_report[fill_report["filled"]].itertuples(index=False):
            filled.loc[row.timestamp, row.symbol] = row.filled_adjusted_close
            was_filled.loc[row.timestamp, row.symbol] = True
    adjusted.index.name = "timestamp"
    raw.index.name = "timestamp"
    filled.index.name = "timestamp"
    return raw, adjusted, filled.rename_axis(index="timestamp")


def modified_z_scores(values: pd.Series) -> pd.Series:
    median = values.median()
    mad = (values - median).abs().median()
    if pd.isna(mad) or mad == 0:
        return pd.Series(0.0, index=values.index)
    return 0.6745 * (values - median) / mad


def detect_outliers(clean: pd.DataFrame, threshold: float = 3.5,
                    extreme_threshold: float = 10.0) -> pd.DataFrame:
    rows = []
    for symbol, group in clean.sort_values("timestamp").groupby("symbol"):
        returns = np.log(group["adjusted_close"] / group["adjusted_close"].shift(1))
        z = modified_z_scores(returns)
        temp = pd.DataFrame({
            "timestamp": group["timestamp"].values, "symbol": symbol,
            "adjusted_close": group["adjusted_close"].values,
            "log_return": returns.values, "modified_z_score": z.values,
        })
        temp["is_outlier"] = temp["modified_z_score"].abs() > threshold
        temp["is_extreme_outlier"] = temp["modified_z_score"].abs() > extreme_threshold
        rows.append(temp[temp["is_outlier"]])
    if not rows:
        return pd.DataFrame(columns=[
            "timestamp", "symbol", "adjusted_close", "log_return",
            "modified_z_score", "is_outlier", "is_extreme_outlier",
        ])
    return pd.concat(rows, ignore_index=True).sort_values(["timestamp", "symbol"])


def extract_corporate_actions(raw: pd.DataFrame) -> pd.DataFrame:
    mask = (raw.get("dividends", 0).fillna(0) > 0) | (raw.get("stock_splits", 0).fillna(0) > 0)
    cols = ["timestamp", "symbol", "short", "close", "adjusted_close", "dividends", "stock_splits"]
    return raw.loc[mask, cols].sort_values(["timestamp", "symbol"]).copy()


def quality_summary(validated: pd.DataFrame, clean: pd.DataFrame, quarantine: pd.DataFrame,
                    gaps: pd.DataFrame, fills: pd.DataFrame, outliers: pd.DataFrame,
                    actions: pd.DataFrame, sessions: pd.DatetimeIndex) -> pd.DataFrame:
    rows = []
    latest_session = sessions.max() if len(sessions) else pd.NaT
    for symbol in STOCK_SYMBOLS + [BENCHMARK_SYMBOL]:
        source = validated[validated.symbol.eq(symbol)]
        good = clean[clean.symbol.eq(symbol)]
        expected = sessions[(sessions >= good.timestamp.min()) & (sessions <= good.timestamp.max())] if len(good) else sessions[:0]
        missing = int(len(expected) - good.timestamp.nunique())
        filled = int(fills[fills.symbol.eq(symbol)]["filled"].sum()) if not fills.empty else 0
        coverage = good.timestamp.nunique() / len(expected) if len(expected) else 0.0
        invalid = int(quarantine[quarantine.symbol.eq(symbol)].shape[0])
        duplicate_count = int(source["is_duplicate"].sum())
        outlier_count = int(outliers[outliers.symbol.eq(symbol)].shape[0]) if not outliers.empty else 0
        action_count = int(actions[actions.symbol.eq(symbol)].shape[0]) if not actions.empty else 0
        latest = good.timestamp.max() if len(good) else pd.NaT
        if coverage < 0.98 or invalid > 0 or latest != latest_session:
            status = "fail"
        elif missing or outlier_count or duplicate_count:
            status = "warning"
        else:
            status = "pass"
        rows.append({
            "symbol": symbol, "raw_rows": int(len(source)), "clean_rows": int(len(good)),
            "first_date": good.timestamp.min() if len(good) else pd.NaT,
            "latest_date": latest, "latest_session": latest_session,
            "expected_sessions_in_range": int(len(expected)), "missing_sessions": missing,
            "filled_sessions": filled, "unfilled_sessions": max(missing - filled, 0),
            "coverage_pct": round(coverage * 100, 4), "invalid_rows_quarantined": invalid,
            "duplicate_rows_flagged": duplicate_count,
            "largest_gap_sessions": int(gaps[gaps.symbol.eq(symbol)]["missing_sessions"].max()) if not gaps.empty and not gaps[gaps.symbol.eq(symbol)].empty else 0,
            "outliers_flagged": outlier_count,
            "corporate_actions": action_count, "quality_status": status,
        })
    return pd.DataFrame(rows)
