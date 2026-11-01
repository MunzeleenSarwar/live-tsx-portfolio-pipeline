# Data Quality Report

Run completed: 2026-10-30T20:29:14.947466+00:00
Latest daily session: 2026-10-30

## Run totals

- Daily raw rows: 28,754
- Daily clean rows: 28,754
- Quarantined rows: 0
- Missing sessions filled: 0
- Outliers flagged and retained: 720
- Corporate actions: 328

## Symbol summary

| symbol | raw_rows | clean_rows | first_date | latest_date | latest_session | expected_sessions_in_range | missing_sessions | filled_sessions | unfilled_sessions | coverage_pct | invalid_rows_quarantined | duplicate_rows_flagged | largest_gap_sessions | outliers_flagged | corporate_actions | quality_status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| CNQ.TO | 2614 | 2614 | 2016-06-01 00:00:00 | 2026-10-30 00:00:00 | 2026-10-30 00:00:00 | 2614 | 0 | 0 | 0 | 100.0 | 0 | 0 | 0 | 53 | 44 | warning |
| ENB.TO | 2614 | 2614 | 2016-06-01 00:00:00 | 2026-10-30 00:00:00 | 2026-10-30 00:00:00 | 2614 | 0 | 0 | 0 | 100.0 | 0 | 0 | 0 | 54 | 41 | warning |
| CCO.TO | 2614 | 2614 | 2016-06-01 00:00:00 | 2026-10-30 00:00:00 | 2026-10-30 00:00:00 | 2614 | 0 | 0 | 0 | 100.0 | 0 | 0 | 0 | 63 | 15 | warning |
| TD.TO | 2614 | 2614 | 2016-06-01 00:00:00 | 2026-10-30 00:00:00 | 2026-10-30 00:00:00 | 2614 | 0 | 0 | 0 | 100.0 | 0 | 0 | 0 | 78 | 42 | warning |
| BN.TO | 2614 | 2614 | 2016-06-01 00:00:00 | 2026-10-30 00:00:00 | 2026-10-30 00:00:00 | 2614 | 0 | 0 | 0 | 100.0 | 0 | 0 | 0 | 65 | 43 | warning |
| SHOP.TO | 2614 | 2614 | 2016-06-01 00:00:00 | 2026-10-30 00:00:00 | 2026-10-30 00:00:00 | 2614 | 0 | 0 | 0 | 100.0 | 0 | 0 | 0 | 64 | 1 | warning |
| TIH.TO | 2614 | 2614 | 2016-06-01 00:00:00 | 2026-10-30 00:00:00 | 2026-10-30 00:00:00 | 2614 | 0 | 0 | 0 | 100.0 | 0 | 0 | 0 | 71 | 42 | warning |
| ABX.TO | 2614 | 2614 | 2016-06-01 00:00:00 | 2026-10-30 00:00:00 | 2026-10-30 00:00:00 | 2614 | 0 | 0 | 0 | 100.0 | 0 | 0 | 0 | 56 | 40 | warning |
| L.TO | 2614 | 2614 | 2016-06-01 00:00:00 | 2026-10-30 00:00:00 | 2026-10-30 00:00:00 | 2614 | 0 | 0 | 0 | 100.0 | 0 | 0 | 0 | 54 | 44 | warning |
| CAE.TO | 2614 | 2614 | 2016-06-01 00:00:00 | 2026-10-30 00:00:00 | 2026-10-30 00:00:00 | 2614 | 0 | 0 | 0 | 100.0 | 0 | 0 | 0 | 97 | 16 | warning |
| ^GSPTSE | 2614 | 2614 | 2016-06-01 00:00:00 | 2026-10-30 00:00:00 | 2026-10-30 00:00:00 | 2614 | 0 | 0 | 0 | 100.0 | 0 | 0 | 0 | 65 | 0 | warning |

## Policy

Invalid OHLCV rows are quarantined. Return outliers are flagged but retained because a large market move can be genuine. Missing adjusted closes are forward-filled only for gaps of five sessions or fewer, and every filled observation remains flagged in the fill report. Raw data are preserved separately from clean data.