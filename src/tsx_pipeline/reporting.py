from __future__ import annotations

import html
import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


def make_charts(root: Path, quality: pd.DataFrame, snapshot: pd.DataFrame,
                weights: pd.DataFrame) -> list[str]:
    charts = root / "charts"
    charts.mkdir(parents=True, exist_ok=True)
    created = []
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10})

    order = quality.sort_values("coverage_pct")
    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.barh(order["symbol"], order["coverage_pct"], color="#1f4e79")
    ax.set_xlim(95, 100.15)
    ax.set_xlabel("Coverage of benchmark sessions (%)")
    ax.set_title("Data coverage by symbol")
    ax.grid(axis="x", alpha=0.3)
    fig.tight_layout(); fig.savefig(charts / "data_coverage.png", dpi=180); plt.close(fig)
    created.append("charts/data_coverage.png")

    stocks = snapshot[~snapshot.symbol.eq("^GSPTSE")].copy()
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.scatter(stocks["realized_vol_60d"] * 100, stocks["drawdown_252d"] * 100, s=70, color="#1f4e79")
    for row in stocks.itertuples(index=False):
        ax.annotate(row.short, (row.realized_vol_60d * 100, row.drawdown_252d * 100), fontsize=8, xytext=(4, 4), textcoords="offset points")
    ax.set_xlabel("60-day realised volatility (%)")
    ax.set_ylabel("Drawdown from 252-day high (%)")
    ax.set_title("Latest volatility and drawdown")
    ax.grid(alpha=0.3)
    fig.tight_layout(); fig.savefig(charts / "volatility_drawdown.png", dpi=180); plt.close(fig)
    created.append("charts/volatility_drawdown.png")

    pivot = weights.pivot(index="short", columns="strategy", values="weight") * 100
    fig, ax = plt.subplots(figsize=(11, 6))
    pivot.plot(kind="bar", ax=ax)
    ax.set_ylabel("Weight (%)")
    ax.set_xlabel("Stock")
    ax.set_title("Latest-window strategy weights")
    ax.grid(axis="y", alpha=0.3)
    ax.legend(title="Strategy", fontsize=8)
    fig.tight_layout(); fig.savefig(charts / "latest_strategy_weights.png", dpi=180); plt.close(fig)
    created.append("charts/latest_strategy_weights.png")
    return created


def _table_html(frame: pd.DataFrame, max_rows: int = 30) -> str:
    view = frame.head(max_rows).copy()
    for col in view.columns:
        if pd.api.types.is_float_dtype(view[col]):
            view[col] = view[col].map(lambda x: "" if pd.isna(x) else f"{x:,.4f}")
        else:
            view[col] = view[col].astype(str)
    return view.to_html(index=False, escape=True, border=0, classes="data-table")


def write_dashboard(root: Path, summary: dict, quality: pd.DataFrame,
                    snapshot: pd.DataFrame, weights: pd.DataFrame, metrics: pd.DataFrame) -> Path:
    path = root / "reports" / "dashboard.html"
    path.parent.mkdir(parents=True, exist_ok=True)
    title = "Live TSX Portfolio Market Data Pipeline"
    body = f"""<!doctype html>
<html lang=\"en\"><head><meta charset=\"utf-8\"><title>{html.escape(title)}</title>
<style>body{{font-family:Arial,sans-serif;margin:32px;color:#111;max-width:1180px}}h1,h2{{color:#111}}table{{border-collapse:collapse;margin:12px 0 28px;width:100%;font-size:13px}}th,td{{border:1px solid #999;padding:6px;text-align:left}}th{{background:#ddd}}.card{{border:1px solid #bbb;padding:14px;margin:10px 0}}img{{max-width:100%;height:auto}}</style></head>
<body><h1>{html.escape(title)}</h1>
<p>Run completed at {html.escape(str(summary['completed_at']))}. Latest daily session: {html.escape(str(summary['latest_daily_date']))}. Source: Yahoo Finance. This is a production-style near-live polling pipeline, not a direct exchange tick feed.</p>
<div class=\"card\"><strong>Quality status:</strong> {html.escape(json.dumps(summary['quality_status_counts']))}<br>
<strong>Daily rows:</strong> {summary['daily_raw_rows']:,} raw and {summary['daily_clean_rows']:,} clean<br>
<strong>Corporate actions:</strong> {summary['corporate_actions']:,}<br>
<strong>Outliers flagged:</strong> {summary['outliers_flagged']:,}</div>
<h2>Latest risk snapshot</h2>{_table_html(snapshot)}
<h2>Data quality by symbol</h2>{_table_html(quality)}
<h2>Latest-window strategy diagnostics</h2>{_table_html(metrics)}
<h2>Latest strategy weights</h2>{_table_html(weights)}
<h2>Charts</h2><img src=\"../charts/data_coverage.png\" alt=\"Data coverage chart\">
<img src=\"../charts/volatility_drawdown.png\" alt=\"Volatility and drawdown chart\">
<img src=\"../charts/latest_strategy_weights.png\" alt=\"Latest strategy weights chart\">
</body></html>"""
    path.write_text(body, encoding="utf-8")
    return path


def _markdown_table(frame: pd.DataFrame) -> str:
    headers = [str(col) for col in frame.columns]
    lines = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    for row in frame.itertuples(index=False, name=None):
        values = [str(value).replace("|", "\\|") for value in row]
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def write_quality_markdown(root: Path, summary: dict, quality: pd.DataFrame) -> Path:
    path = root / "reports" / "data_quality_report.md"
    lines = [
        "# Data Quality Report",
        "",
        f"Run completed: {summary['completed_at']}",
        f"Latest daily session: {summary['latest_daily_date']}",
        "",
        "## Run totals",
        "",
        f"- Daily raw rows: {summary['daily_raw_rows']:,}",
        f"- Daily clean rows: {summary['daily_clean_rows']:,}",
        f"- Quarantined rows: {summary['quarantined_rows']:,}",
        f"- Missing sessions filled: {summary['filled_sessions']:,}",
        f"- Outliers flagged and retained: {summary['outliers_flagged']:,}",
        f"- Corporate actions: {summary['corporate_actions']:,}",
        "",
        "## Symbol summary",
        "",
        _markdown_table(quality),
        "",
        "## Policy",
        "",
        "Invalid OHLCV rows are quarantined. Return outliers are flagged but retained because a large market move can be genuine. Missing adjusted closes are forward-filled only for gaps of five sessions or fewer, and every filled observation remains flagged in the fill report. Raw data are preserved separately from clean data.",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    return path
