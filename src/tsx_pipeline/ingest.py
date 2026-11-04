from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import time

import pandas as pd
import yfinance as yf

from .config import ALL_SYMBOLS, PROJECT_ROOT, SHORT_BY_SYMBOL, TIMEZONE

DAILY_COLUMNS = [
    "timestamp", "symbol", "short", "open", "high", "low", "close",
    "adjusted_close", "volume", "dividends", "stock_splits", "retrieved_at",
]
INTRADAY_COLUMNS = [
    "timestamp", "symbol", "short", "open", "high", "low", "close",
    "volume", "retrieved_at",
]


def _normalise_daily(symbol: str, frame: pd.DataFrame, retrieved_at: str) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(columns=DAILY_COLUMNS)
    out = frame.reset_index().copy()
    rename = {
        "Date": "timestamp", "Datetime": "timestamp", "Open": "open",
        "High": "high", "Low": "low", "Close": "close",
        "Adj Close": "adjusted_close", "Volume": "volume",
        "Dividends": "dividends", "Stock Splits": "stock_splits",
    }
    out = out.rename(columns=rename)
    out["timestamp"] = pd.to_datetime(out["timestamp"])
    try:
        out["timestamp"] = out["timestamp"].dt.tz_localize(None)
    except TypeError:
        out["timestamp"] = out["timestamp"].dt.tz_convert(TIMEZONE).dt.tz_localize(None)
    out["timestamp"] = out["timestamp"].dt.normalize()
    out["symbol"] = symbol
    out["short"] = SHORT_BY_SYMBOL[symbol]
    out["retrieved_at"] = retrieved_at
    for col in DAILY_COLUMNS:
        if col not in out:
            out[col] = 0.0 if col in {"dividends", "stock_splits"} else pd.NA
    return out[DAILY_COLUMNS].sort_values("timestamp")


def _normalise_intraday(symbol: str, frame: pd.DataFrame, retrieved_at: str) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(columns=INTRADAY_COLUMNS)
    out = frame.reset_index().copy()
    out = out.rename(columns={
        "Datetime": "timestamp", "Date": "timestamp", "Open": "open",
        "High": "high", "Low": "low", "Close": "close", "Volume": "volume",
    })
    ts = pd.to_datetime(out["timestamp"])
    if getattr(ts.dt, "tz", None) is None:
        ts = ts.dt.tz_localize(TIMEZONE)
    else:
        ts = ts.dt.tz_convert(TIMEZONE)
    out["timestamp"] = ts.dt.tz_localize(None)
    out["symbol"] = symbol
    out["short"] = SHORT_BY_SYMBOL[symbol]
    out["retrieved_at"] = retrieved_at
    for col in INTRADAY_COLUMNS:
        if col not in out:
            out[col] = pd.NA
    return out[INTRADAY_COLUMNS].sort_values("timestamp")


def fetch_daily(symbols=ALL_SYMBOLS, start: str = "2016-06-01", end: str | None = None,
                retries: int = 3) -> tuple[pd.DataFrame, list[dict]]:
    retrieved_at = datetime.now(timezone.utc).isoformat()
    if end is None:
        end = (pd.Timestamp.now(tz=TIMEZONE).normalize() + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    frames, status = [], []
    for symbol in symbols:
        frame = pd.DataFrame()
        error = ""
        for attempt in range(retries):
            try:
                raw = yf.Ticker(symbol).history(
                    start=start, end=end, interval="1d",
                    auto_adjust=False, actions=True,
                )
                frame = _normalise_daily(symbol, raw, retrieved_at)
                if not frame.empty:
                    break
                error = "empty response"
            except Exception as exc:  # Source errors must be visible in run status.
                error = f"{type(exc).__name__}: {exc}"
            if attempt < retries - 1:
                time.sleep(2 * (attempt + 1))
        frames.append(frame)
        status.append({
            "symbol": symbol, "short": SHORT_BY_SYMBOL[symbol],
            "rows": int(len(frame)), "status": "ok" if len(frame) else "failed",
            "error": error if frame.empty else "",
            "first_timestamp": str(frame.timestamp.min()) if len(frame) else "",
            "last_timestamp": str(frame.timestamp.max()) if len(frame) else "",
        })
        print(f"daily {symbol}: {len(frame)} rows", flush=True)
    return pd.concat(frames, ignore_index=True), status


def fetch_intraday(symbols=ALL_SYMBOLS, period: str = "5d", retries: int = 2) -> tuple[pd.DataFrame, list[dict]]:
    retrieved_at = datetime.now(timezone.utc).isoformat()
    frames, status = [], []
    for symbol in symbols:
        frame = pd.DataFrame()
        error = ""
        for attempt in range(retries):
            try:
                raw = yf.Ticker(symbol).history(
                    period=period, interval="15m", auto_adjust=False, actions=False,
                )
                frame = _normalise_intraday(symbol, raw, retrieved_at)
                if not frame.empty:
                    break
                error = "empty response"
            except Exception as exc:
                error = f"{type(exc).__name__}: {exc}"
            if attempt < retries - 1:
                time.sleep(1)
        frames.append(frame)
        status.append({
            "symbol": symbol, "short": SHORT_BY_SYMBOL[symbol],
            "rows": int(len(frame)), "status": "ok" if len(frame) else "failed",
            "error": error if frame.empty else "",
            "first_timestamp": str(frame.timestamp.min()) if len(frame) else "",
            "last_timestamp": str(frame.timestamp.max()) if len(frame) else "",
        })
        print(f"intraday {symbol}: {len(frame)} rows", flush=True)
    return pd.concat(frames, ignore_index=True), status


def write_raw(daily: pd.DataFrame, intraday: pd.DataFrame, root: Path = PROJECT_ROOT) -> None:
    daily_dir = root / "data" / "raw" / "daily"
    intraday_dir = root / "data" / "raw" / "intraday"
    daily_dir.mkdir(parents=True, exist_ok=True)
    intraday_dir.mkdir(parents=True, exist_ok=True)
    bronze_dir = root / "data" / "bronze"
    bronze_dir.mkdir(parents=True, exist_ok=True)
    for symbol, frame in daily.groupby("symbol"):
        frame.to_parquet(daily_dir / f"{symbol.replace('^', '')}.parquet", index=False)
    for symbol, frame in intraday.groupby("symbol"):
        frame.to_parquet(intraday_dir / f"{symbol.replace('^', '')}.parquet", index=False)
    daily.to_csv(bronze_dir / "daily_ohlcv_raw.csv.gz", index=False, compression="gzip")
    if not intraday.empty:
        intraday.to_csv(bronze_dir / "intraday_15m_raw.csv.gz", index=False, compression="gzip")
