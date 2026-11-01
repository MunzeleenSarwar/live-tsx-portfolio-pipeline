"""Build the Excel workbook and PDF report from the latest pipeline outputs."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "outputs"
REPORTS = ROOT / "reports"
SUMMARY = json.loads((OUT / "run_summary.json").read_text(encoding="utf-8"))
QUALITY = pd.read_csv(OUT / "data_quality_summary.csv")
SNAPSHOT = pd.read_csv(OUT / "latest_risk_snapshot.csv", parse_dates=["latest_daily_date"])
WEIGHTS = pd.read_csv(OUT / "strategy_weights_latest.csv")
METRICS = pd.read_csv(OUT / "strategy_metrics_latest_window.csv")
SECTORS = pd.read_csv(OUT / "strategy_sector_weights_latest.csv")
ACTIONS = pd.read_csv(OUT / "corporate_actions.csv")
OUTLIERS = pd.read_csv(OUT / "outlier_report.csv")


def pct(x: float, digits: int = 1) -> str:
    return "NA" if pd.isna(x) else f"{x * 100:.{digits}f}%"


def build_excel() -> Path:
    path = REPORTS / "TSX_Live_Pipeline_Model.xlsx"
    wb = Workbook()
    wb.remove(wb.active)
    header_font = Font(bold=True, color="000000")
    header_fill = PatternFill("solid", fgColor="D9D9D9")

    def add_sheet(name: str, frame: pd.DataFrame) -> None:
        ws = wb.create_sheet(name[:31])
        ws.append(list(frame.columns))
        for cell in ws[1]:
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(vertical="center", wrap_text=True)
        for row in frame.itertuples(index=False, name=None):
            ws.append(list(row))
        ws.freeze_panes = "A2"
        ws.auto_filter.ref = ws.dimensions
        for idx, col in enumerate(frame.columns, 1):
            values = [str(col)] + ["" if pd.isna(v) else str(v) for v in frame[col].head(300)]
            width = min(max(max(map(len, values)) + 2, 11), 42)
            ws.column_dimensions[get_column_letter(idx)].width = width

    summary_df = pd.DataFrame([
        {"item": key, "value": value if not isinstance(value, dict) else json.dumps(value)}
        for key, value in SUMMARY.items()
    ])
    add_sheet("Run Summary", summary_df)
    add_sheet("Data Quality", QUALITY)
    add_sheet("Latest Snapshot", SNAPSHOT)
    add_sheet("Strategy Weights", WEIGHTS)
    add_sheet("Strategy Metrics", METRICS)
    add_sheet("Sector Weights", SECTORS)
    add_sheet("Corporate Actions", ACTIONS)
    add_sheet("Outliers", OUTLIERS)
    method = pd.DataFrame([
        {"step": "Ingestion", "method": "Daily OHLCV from 2016-06-01 and 15-minute bars for the latest five days, retrieved from Yahoo Finance."},
        {"step": "Raw layer", "method": "Unchanged source data are written by symbol in Parquet format, with retrieval timestamps."},
        {"step": "Validation", "method": "Rows must have positive prices, valid high and low ranges, and non-negative volume. Invalid rows are quarantined."},
        {"step": "Sessions and gaps", "method": "Benchmark dates define expected trading sessions. Missing adjusted closes are forward-filled only for gaps of five sessions or fewer and remain flagged."},
        {"step": "Outliers", "method": "Log returns are screened with a modified z-score from the median absolute deviation. Flags are retained for review and are not treated as proof of bad data."},
        {"step": "Corporate actions", "method": "Dividend and split records are extracted into a separate log. Adjusted close is the return series used for features and strategies."},
        {"step": "Features", "method": "Daily simple and log returns, 20-day and 60-day realised volatility, rolling beta, rolling correlation and 252-day drawdown."},
        {"step": "Strategy refresh", "method": "The latest 104 weekly returns feed Equal Weight, Minimum Variance, Risk Parity and a latest-window Minimum CVaR calculation. Position cap 20 percent and sector cap 40 percent."},
        {"step": "Important limit", "method": "Strategy figures are historical diagnostics for the estimation window. They are not forecasts and they do not revise the published V2 backtest."},
    ])
    add_sheet("Method", method)
    wb.save(path)
    return path


styles = getSampleStyleSheet()
TITLE = ParagraphStyle("Title2", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=22, leading=26, textColor=colors.black, alignment=TA_CENTER, spaceAfter=4)
SUBTITLE = ParagraphStyle("Subtitle2", parent=styles["Normal"], fontName="Helvetica", fontSize=11, leading=14, textColor=colors.black, alignment=TA_CENTER, spaceAfter=10)
H1 = ParagraphStyle("H1", parent=styles["Heading1"], fontName="Helvetica-Bold", fontSize=14, leading=17, textColor=colors.black, spaceBefore=10, spaceAfter=5)
H2 = ParagraphStyle("H2", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=11.5, leading=14, textColor=colors.black, spaceBefore=8, spaceAfter=4)
BODY = ParagraphStyle("Body", parent=styles["BodyText"], fontName="Helvetica", fontSize=9.5, leading=13.2, textColor=colors.black, spaceAfter=5)
SMALL = ParagraphStyle("Small", parent=BODY, fontSize=8.2, leading=10.5)
CELL = ParagraphStyle("Cell", parent=BODY, fontSize=8.2, leading=10.2, spaceAfter=0)
CELLH = ParagraphStyle("CellH", parent=CELL, fontName="Helvetica-Bold")


def P(text: str, style=BODY) -> Paragraph:
    return Paragraph(text, style)


def table(data: list[list[str]], widths: list[float]) -> Table:
    wrapped = [[Paragraph(str(cell), CELLH if r == 0 else CELL) for cell in row] for r, row in enumerate(data)]
    t = Table(wrapped, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#DDDDDD")),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.black),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return t


def chart(name: str, width: float = 170 * mm, ratio: float = 0.55) -> Image:
    return Image(str(ROOT / "charts" / name), width=width, height=width * ratio)


def metric(strategy: str, column: str) -> float:
    return float(METRICS.loc[METRICS["strategy"].eq(strategy), column].iloc[0])


def build_report() -> Path:
    path = REPORTS / "TSX_Live_Market_Data_Pipeline_Report.pdf"
    doc = SimpleDocTemplate(str(path), pagesize=A4, leftMargin=17 * mm, rightMargin=17 * mm,
                            topMargin=16 * mm, bottomMargin=16 * mm,
                            title="Live TSX Portfolio Market Data Pipeline",
                            author="Munzeleen Sarwar")
    story = []
    story.append(P("Live TSX Portfolio Market Data Pipeline", TITLE))
    story.append(P("Munzeleen Sarwar", SUBTITLE))
    story.append(P(f"Latest completed run: {SUMMARY['latest_daily_date']}. Source: Yahoo Finance. Coverage: ten TSX stocks and the S&amp;P/TSX Composite.", SMALL))

    story.append(P("Executive summary", H1))
    story.append(P("The TSX Portfolio V2 project used a fixed historical dataset. This extension adds the data system that a live portfolio process needs before any strategy result can be trusted. The pipeline collects daily and intraday prices, preserves the raw data, checks the data, builds features, and refreshes selected portfolio weights from the latest 104 weeks."))
    story.append(P(f"The latest run processed {SUMMARY['daily_raw_rows']:,} daily rows and {SUMMARY['intraday_raw_rows']:,} intraday rows. All eleven symbols had 100 percent coverage of the benchmark sessions in their available history. No daily rows were quarantined, no sessions were missing, and no fills were required. The run recorded {SUMMARY['corporate_actions']} corporate-action records and flagged {SUMMARY['outliers_flagged']} return outliers for review."))
    story.append(P("The main result is operational rather than a new investment claim: the portfolio project now has a repeatable route from raw market data to clean, documented outputs. The published V2 backtest remains unchanged. Strategy figures in this report describe the latest estimation window only and are not forecasts."))

    story.append(P("1. Relation to the TSX Portfolio project", H1))
    story.append(P("The original project compared ten portfolio strategies on one ten-stock TSX universe. Its weakness as a working system was the dataset: prices were downloaded for a study, saved, and then treated as fixed. A production research process has a different problem. New prices arrive every trading day, source files can contain gaps or errors, dividends and splits change price history, and a model should never consume data that has not been checked."))
    story.append(P("This project therefore adds an infrastructure layer underneath the portfolio work. It does not rerun or revise the V2 backtest, and it does not change the V2 conclusions. It creates the clean weekly price series that a future strategy run can use, together with evidence about what was checked and what was flagged."))

    story.append(P("2. Pipeline design", H1))
    design = [
        ["Stage", "What happens", "Main output"],
        ["Ingestion", "Daily OHLCV history from 1 June 2016 and 15-minute bars for the latest five days are retrieved for ten stocks and the benchmark.", "Source status by symbol"],
        ["Raw storage", "Unchanged data are stored by symbol in Parquet files. Every row carries the retrieval time.", "Raw daily and intraday files"],
        ["Validation", "Prices, high and low ranges, volume, duplicates and timestamps are checked. Invalid rows are separated rather than silently corrected.", "Clean data and quarantine file"],
        ["Sessions and gaps", "Benchmark dates define expected sessions. Gaps are reported. A missing adjusted close can be forward-filled only when the gap is five sessions or shorter.", "Gap report and fill report"],
        ["Outlier review", "Daily log returns are screened with the median absolute deviation and a modified z-score. Flags remain in the data because a large return can be genuine.", "Outlier report"],
        ["Corporate actions", "Dividend and split records are separated into their own log. Adjusted close is used for returns so price changes are not confused with distributions or splits.", "Corporate-action log"],
        ["Features", "Returns, realised volatility, beta, correlation and drawdown are calculated from the clean adjusted series.", "Daily features and weekly prices"],
        ["Strategy refresh", "The latest 104 weekly returns feed four transparent allocation calculations under the existing position and sector caps.", "Current weights and window diagnostics"],
    ]
    story.append(table(design, [27 * mm, 83 * mm, 60 * mm]))
    story.append(P("The feed is described as near-live rather than exchange live. Yahoo Finance is suitable for a research pipeline and a portfolio project, but it is not a direct exchange tick feed and it provides no institutional delivery guarantee. That limit is stated in the code, the dashboard and the run summary."))

    story.append(P("3. Data quality framework", H1))
    story.append(P("Validation", H2))
    story.append(P("A daily row is invalid when a required price is missing or not positive, when the high is below another price in the row, when the low is above another price in the row, or when volume is negative. Invalid rows are written to a quarantine file with the error recorded. Duplicate symbol and date rows are flagged and deduplicated by keeping the latest retrieved version."))
    story.append(P("Gaps and fills", H2))
    story.append(P("The benchmark supplies the trading calendar. This is a practical proxy, not a full exchange calendar. Missing observations are grouped into gap periods. Forward filling is limited and transparent: the fill report records the symbol, date, filled value, method and reason. A long gap is left unfilled because a stale price would create false low risk in the feature layer."))
    story.append(P("Outliers", H2))
    story.append(P("The outlier screen uses the median and the median absolute deviation, which are less sensitive to extreme returns than the mean and standard deviation. A modified z-score above 3.5 is flagged and a score above 10 is marked extreme. A flag starts a review. It does not delete the observation. This distinction matters for market data: the largest flags in the current run are concentrated in March 2020, when large market moves were genuine."))
    story.append(P("One limit of the current method is that the median absolute deviation is calculated over the full history for each symbol. Volatility regimes change over ten years, so a fixed history-wide screen can flag many observations in a crisis and too few in a calm period. A rolling screen is the clearest technical improvement for the next version."))

    story.append(PageBreak())
    story.append(P("4. Latest data quality results", H1))
    qrows = [["Symbol", "Coverage", "Missing", "Outliers", "Actions", "Status"]]
    for row in QUALITY.itertuples(index=False):
        qrows.append([row.symbol, f"{row.coverage_pct:.2f}%", str(row.missing_sessions), str(row.outliers_flagged), str(row.corporate_actions), row.quality_status])
    story.append(table(qrows, [29 * mm, 25 * mm, 24 * mm, 24 * mm, 24 * mm, 44 * mm]))
    story.append(P("Every symbol is marked warning rather than pass because each one has return outliers requiring review. In this context, warning does not mean the source data failed. Coverage was complete, no rows were quarantined, and no gap had to be filled. The status system is deliberately strict: a symbol cannot be marked pass while it has unresolved review flags."))
    story.append(chart("data_coverage.png"))
    story.append(P(f"Corporate actions totalled {SUMMARY['corporate_actions']} records. Most were quarterly dividends. Shopify had one recorded action in the extracted history, and the benchmark had none. Keeping these records separate from prices makes it possible to check whether a sharp price move coincides with a dividend or split before treating it as a market return."))

    story.append(P("5. Latest risk snapshot", H1))
    srows = [["Symbol", "Close", "21-day return", "252-day return", "60-day volatility", "Drawdown"]]
    for row in SNAPSHOT.itertuples(index=False):
        srows.append([row.short, f"{row.adjusted_close:,.2f}", pct(row.return_21d), pct(row.return_252d), pct(row.realized_vol_60d), pct(row.drawdown_252d)])
    story.append(table(srows, [24 * mm, 28 * mm, 29 * mm, 31 * mm, 31 * mm, 27 * mm]))
    story.append(P("Shopify had the highest 60-day realised volatility at 49.7 percent. Cameco had the largest drawdown from its 252-day high at 41.1 percent, with 60-day volatility of 43.5 percent. Canadian Natural Resources was at its 252-day high on the latest date. Enbridge had the lowest 60-day volatility among the ten stocks at 16.8 percent. The benchmark drawdown was 3.6 percent."))
    story.append(chart("volatility_drawdown.png", ratio=0.667))
    story.append(P("Beta and correlation are included in the Excel workbook and the snapshot file. They use daily log returns over the latest 252 sessions. They should be read as recent market relationships, not stable company constants."))

    story.append(PageBreak())
    story.append(P("6. Strategy refresh", H1))
    story.append(P("The strategy layer uses weekly adjusted prices and the latest 104 weekly returns, from 8 November 2024 to 30 October 2026 in the current run. Four allocations are calculated: Equal Weight, Minimum Variance, Risk Parity, and Minimum CVaR for the latest window. Allocations are long only, no stock can exceed 20 percent, and no sector can exceed 40 percent."))
    story.append(P("The Minimum CVaR calculation in this pipeline is not the Regime-Aware CVaR strategy from V2. It has no regime model. It directly minimises the average loss in the worst 5 percent of weekly return observations in the latest window. The different name is intentional, so the two methods are not confused."))
    pivot = WEIGHTS.pivot(index="short", columns="strategy", values="weight")
    wrows = [["Stock", "Equal", "Minimum Variance", "Risk Parity", "Minimum CVaR"]]
    order = ["Equal Weight", "Minimum Variance", "Risk Parity", "Minimum CVaR (latest window)"]
    for short, row in pivot.sort_index().iterrows():
        wrows.append([short] + [pct(row[col], 1) for col in order])
    story.append(table(wrows, [28 * mm, 30 * mm, 37 * mm, 32 * mm, 43 * mm]))
    story.append(chart("latest_strategy_weights.png"))
    story.append(P("Minimum Variance placed 20 percent in both Loblaw and TD and 18.0 percent in Enbridge. Minimum CVaR placed 20 percent in Loblaw and TD, 19.9 percent in Canadian Natural Resources, and no weight in CAE or Cameco. Risk Parity was more even, as expected from a method that balances risk contributions rather than seeking the lowest total variance."))

    story.append(P("Window diagnostics", H2))
    mrows = [["Strategy", "Return", "Volatility", "Sharpe", "Maximum drawdown", "Weekly CVaR"]]
    for row in METRICS.itertuples(index=False):
        mrows.append([row.strategy, pct(row.annualised_return_window), pct(row.annualised_volatility_window), f"{row.sharpe_window:.2f}", pct(row.max_drawdown_window), pct(row.weekly_cvar95_window, 2)])
    story.append(table(mrows, [43 * mm, 23 * mm, 25 * mm, 20 * mm, 31 * mm, 28 * mm]))
    story.append(P(f"Within the estimation window, Minimum Variance had the lowest volatility at {pct(metric('Minimum Variance', 'annualised_volatility_window'))}. Minimum CVaR had the least severe weekly CVaR at {pct(metric('Minimum CVaR (latest window)', 'weekly_cvar95_window'), 2)} and the smallest maximum drawdown at {pct(metric('Minimum CVaR (latest window)', 'max_drawdown_window'))}. These are descriptions of the same window used to calculate the weights. They are not out-of-sample results, expected returns, or a recommendation."))

    story.append(P("7. Scheduling and controls", H1))
    story.append(P("The command line runner can be scheduled after the Toronto close on each trading day. The project includes a GitHub Actions workflow for a scheduled run and a manual run. Each run writes a unique completion time, source status, row counts, latest session, quality counts and strategy estimation dates to the run summary. The dashboard gives a quick view, while the underlying CSV and Parquet files preserve the evidence behind the summary."))
    story.append(P("A failed symbol stops the daily run rather than producing a partial strategy update. This is a deliberate control. A portfolio calculation based on nine current stocks and one stale stock would look complete while being wrong. The ingestion status file records which symbol failed and the source error."))

    story.append(P("8. Limitations and next steps", H1))
    story.append(P("Yahoo Finance is a free research source. It can change fields, delay data, revise adjusted prices, or fail without notice. The pipeline records retrieval times and raw responses in normalised form, but it does not have a second source for cross-checking prices. A production system would use a licensed feed and a backup source."))
    story.append(P("The benchmark calendar proxy does not encode every TSX holiday or symbol-specific halt. The outlier screen should move from a full-history median absolute deviation to a rolling window. Intraday data are currently checked and summarised but are not used in the weekly strategy layer. The next useful additions are a rolling outlier screen, a second price source for sampled cross-checks, data alerts, and storage of each run in a versioned database rather than a latest-output folder."))
    story.append(P("The result is a working research pipeline with clear limits. It extends the TSX Portfolio project from a one-time backtest into a system that can receive new market data, test the data before use, explain its quality decisions, and produce updated portfolio inputs on a repeatable schedule."))

    doc.build(story)
    return path


if __name__ == "__main__":
    excel = build_excel()
    report = build_report()
    print(excel)
    print(report)
