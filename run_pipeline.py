from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from tsx_pipeline.config import CONFIG
from tsx_pipeline.features import build_daily_features, build_weekly_prices, latest_snapshot
from tsx_pipeline.ingest import fetch_daily, fetch_intraday, write_raw
from tsx_pipeline.quality import (
    benchmark_sessions, build_close_matrices, detect_gaps, detect_outliers,
    deduplicate_valid, extract_corporate_actions, quality_summary, validate_ohlcv,
)
from tsx_pipeline.reporting import make_charts, write_dashboard, write_quality_markdown
from tsx_pipeline.strategies import refresh_strategies


def save_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)


def save_parquet(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(path, index=False)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Live TSX Portfolio Market Data Pipeline")
    parser.add_argument("--start", default=CONFIG["history"]["daily_start"])
    parser.add_argument("--skip-intraday", action="store_true")
    parser.add_argument("--estimation-weeks", type=int, default=CONFIG["history"]["weekly_estimation_weeks"])
    args = parser.parse_args()

    started = time.time()
    run_started = datetime.now(timezone.utc)
    daily, daily_status = fetch_daily(start=args.start)
    if daily.empty:
        raise RuntimeError("daily ingestion returned no rows")
    failed = [row for row in daily_status if row["status"] != "ok"]
    if failed:
        raise RuntimeError(f"daily ingestion failed for {failed}")

    if args.skip_intraday:
        intraday = pd.DataFrame()
        intraday_status = []
    else:
        intraday, intraday_status = fetch_intraday()
    write_raw(daily, intraday, ROOT)
    save_csv(pd.DataFrame(daily_status), ROOT / "data" / "outputs" / "ingestion_status_daily.csv")
    save_csv(pd.DataFrame(intraday_status), ROOT / "data" / "outputs" / "ingestion_status_intraday.csv")

    validated = validate_ohlcv(daily)
    clean, quarantine = deduplicate_valid(validated)
    sessions = benchmark_sessions(clean)
    gaps, fills = detect_gaps(clean, sessions)
    raw_matrix, adjusted_matrix, filled_matrix = build_close_matrices(clean, fills, sessions)
    outliers = detect_outliers(
        clean,
        threshold=float(CONFIG["history"]["outlier_threshold"]),
        extreme_threshold=float(CONFIG["history"]["extreme_outlier_threshold"]),
    )
    actions = extract_corporate_actions(daily)
    quality = quality_summary(validated, clean, quarantine, gaps, fills, outliers, actions, sessions)

    save_parquet(clean, ROOT / "data" / "clean" / "daily_ohlcv_clean.parquet")
    clean.to_csv(ROOT / "data" / "clean" / "daily_ohlcv_clean.csv.gz", index=False, compression="gzip")
    save_parquet(quarantine, ROOT / "data" / "clean" / "quarantined_rows.parquet")
    save_csv(quarantine, ROOT / "data" / "clean" / "quarantined_rows.csv")
    save_csv(gaps, ROOT / "data" / "outputs" / "gap_report.csv")
    save_csv(fills, ROOT / "data" / "outputs" / "fill_report.csv")
    save_csv(outliers, ROOT / "data" / "outputs" / "outlier_report.csv")
    save_csv(actions, ROOT / "data" / "outputs" / "corporate_actions.csv")
    save_csv(quality, ROOT / "data" / "outputs" / "data_quality_summary.csv")

    for name, matrix in [("raw_close", raw_matrix), ("adjusted_close", adjusted_matrix), ("adjusted_close_filled", filled_matrix)]:
        matrix.to_parquet(ROOT / "data" / "clean" / f"{name}_matrix.parquet")
        matrix.to_csv(ROOT / "data" / "clean" / f"{name}_matrix.csv")

    if not intraday.empty:
        numeric = ["open", "high", "low", "close", "volume"]
        intraday_clean = intraday.copy()
        intraday_clean["timestamp"] = pd.to_datetime(intraday_clean["timestamp"])
        for col in numeric:
            intraday_clean[col] = pd.to_numeric(intraday_clean[col], errors="coerce")
        intraday_clean = (intraday_clean.drop_duplicates(["symbol", "timestamp"], keep="last")
                          .query("open > 0 and high > 0 and low > 0 and close > 0")
                          .sort_values(["timestamp", "symbol"]))
        save_parquet(intraday_clean, ROOT / "data" / "clean" / "intraday_15m_clean.parquet")
        intraday_clean.to_csv(ROOT / "data" / "clean" / "intraday_15m_clean.csv.gz", index=False, compression="gzip")
    else:
        intraday_clean = intraday

    features = build_daily_features(filled_matrix)
    (ROOT / "data" / "features").mkdir(parents=True, exist_ok=True)
    features.to_parquet(ROOT / "data" / "features" / "daily_features.parquet", index=False)
    weekly = build_weekly_prices(filled_matrix)
    weekly.to_parquet(ROOT / "data" / "features" / "weekly_adjusted_prices.parquet")
    weekly.to_csv(ROOT / "data" / "features" / "weekly_adjusted_prices.csv")
    snapshot = latest_snapshot(features, intraday_clean)
    save_csv(snapshot, ROOT / "data" / "outputs" / "latest_risk_snapshot.csv")

    weights, metrics, sector_weights = refresh_strategies(weekly, estimation_weeks=args.estimation_weeks)
    save_csv(weights, ROOT / "data" / "outputs" / "strategy_weights_latest.csv")
    save_csv(metrics, ROOT / "data" / "outputs" / "strategy_metrics_latest_window.csv")
    save_csv(sector_weights, ROOT / "data" / "outputs" / "strategy_sector_weights_latest.csv")

    completed = datetime.now(timezone.utc)
    summary = {
        "project": CONFIG["project"]["name"],
        "run_started_at": run_started.isoformat(),
        "completed_at": completed.isoformat(),
        "elapsed_seconds": round(time.time() - started, 2),
        "source": CONFIG["project"]["source"],
        "feed_description": CONFIG["project"]["feed_description"],
        "daily_start_requested": args.start,
        "latest_daily_date": str(sessions.max().date()),
        "daily_raw_rows": int(len(daily)),
        "daily_clean_rows": int(len(clean)),
        "intraday_raw_rows": int(len(intraday)),
        "intraday_clean_rows": int(len(intraday_clean)),
        "quarantined_rows": int(len(quarantine)),
        "gap_groups": int(len(gaps)),
        "filled_sessions": int(fills["filled"].sum()) if not fills.empty else 0,
        "outliers_flagged": int(len(outliers)),
        "corporate_actions": int(len(actions)),
        "quality_status_counts": quality["quality_status"].value_counts().to_dict(),
        "strategy_estimation_start": str(metrics["estimation_start"].min()),
        "strategy_estimation_end": str(metrics["estimation_end"].max()),
    }
    make_charts(ROOT, quality, snapshot, weights)
    write_quality_markdown(ROOT, summary, quality)
    write_dashboard(ROOT, summary, quality, snapshot, weights, metrics)
    (ROOT / "data" / "outputs" / "run_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
