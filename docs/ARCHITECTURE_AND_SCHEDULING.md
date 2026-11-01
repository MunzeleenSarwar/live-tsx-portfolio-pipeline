# Architecture and Scheduling

## Data flow

```text
Yahoo Finance
    |
    |-- Daily OHLCV and corporate actions
    |-- 15-minute OHLCV, latest five days
    v
Raw layer: Parquet by symbol, retrieval timestamp preserved
    v
Validation: schema, positive prices, OHLC ranges, volume, duplicates
    |-- Invalid rows -> quarantine file
    v
Session checks: benchmark calendar, gap report, limited fill report
    v
Review checks: MAD outlier report and corporate-action log
    v
Clean layer: daily OHLCV, raw close matrix, adjusted close matrix
    v
Feature layer: returns, realised volatility, beta, correlation, drawdown, weekly prices
    v
Strategy layer: Equal Weight, Minimum Variance, Risk Parity, Minimum CVaR
    v
Outputs: JSON run summary, CSV files, Excel workbook, PDF report and HTML dashboard
```

## Storage layout

- `data/raw/daily/`: one raw Parquet file per symbol
- `data/raw/intraday/`: one raw intraday Parquet file per symbol
- `data/bronze/`: combined compressed raw CSV files
- `data/clean/`: validated daily and intraday data, matrices and quarantined rows
- `data/features/`: daily features and weekly adjusted prices
- `data/outputs/`: latest run evidence and strategy outputs
- `reports/`: PDF, Excel, Markdown and HTML deliverables
- `charts/`: generated charts

The current design writes the latest completed run to named output files. The run summary stores the completion time and latest session so a reader can identify which run produced the files.

## Failure rule

If any daily symbol fails after retries, the run stops before strategy outputs are refreshed. This prevents a partial update in which one stock uses stale data while the others use current data.

Intraday failure does not invalidate the daily history, but the current runner records source status by symbol so the failure is visible.

## Scheduling

A practical schedule is once per trading day after the Toronto market close. The included GitHub Actions workflow runs at 21:30 UTC on weekdays and can also be started manually. That time is after the normal 16:00 Toronto close in both daylight and standard time.

A local scheduler can use the same commands:

```bash
python run_pipeline.py
python scripts/build_deliverables.py
```

## Controls worth adding in a larger production system

- A licensed primary feed and an independent backup source
- A versioned database instead of a latest-file layout
- Run identifiers in every output filename
- Alerts for a failed symbol, stale data or a sudden rise in quarantined rows
- A rolling outlier screen that adapts to recent volatility
- A formal exchange calendar rather than a benchmark-date proxy
