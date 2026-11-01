from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
OUT = ROOT / "data" / "outputs"
REG = ROOT / "data" / "regime_outputs"
SE_DIR = ROOT / "data" / "strategy_evaluation_outputs"
TD_DIR = ROOT / "data" / "trade_design_outputs"
RS_DIR = ROOT / "data" / "risk_surface_outputs"

RUN = json.loads((OUT / "run_summary.json").read_text())
REGS = json.loads((REG / "regime_summary.json").read_text())
SE = json.loads((SE_DIR / "strategy_summary.json").read_text())
TD = json.loads((TD_DIR / "trade_plan.json").read_text())
RS = json.loads((RS_DIR / "risk_surface_summary.json").read_text())

QUALITY = pd.read_csv(OUT / "data_quality_summary.csv")
SNAPSHOT = pd.read_csv(OUT / "latest_risk_snapshot.csv")
REFRESH_WEIGHTS = pd.read_csv(OUT / "strategy_weights_latest.csv")
REFRESH_METRICS = pd.read_csv(OUT / "strategy_metrics_latest_window.csv")
SPECTRUM = pd.read_csv(REG / "spectrum.csv")
LOADINGS = pd.read_csv(REG / "dominant_directions.csv", index_col=0)
STATES = pd.read_csv(REG / "market_state_summary.csv")
ANNUAL = pd.read_csv(REG / "annual_structure.csv")
EXTREMES = pd.read_csv(REG / "extreme_days.csv")
SE_METRICS = pd.read_csv(SE_DIR / "performance_metrics.csv")
SE_PAYOFF = pd.read_csv(SE_DIR / "payoff_summary.csv")
SE_MONTHLY = pd.read_csv(SE_DIR / "monthly_strategy_returns.csv")
SE_STRESS = pd.read_csv(SE_DIR / "stress_tests.csv")
SE_CRITERIA = pd.read_csv(SE_DIR / "decision_criteria.csv")
SE_EV = pd.read_csv(SE_DIR / "ev_sensitivity.csv")
TD_PROFIT = pd.read_csv(TD_DIR / "profit_by_size.csv")
TD_LEV = pd.read_csv(TD_DIR / "leverage_analysis.csv")
TD_KELLY = pd.read_csv(TD_DIR / "kelly_analysis.csv")
TD_STOP = pd.read_csv(TD_DIR / "stoploss_analysis.csv")
TD_EXEC = pd.read_csv(TD_DIR / "execution_analysis.csv")
RS_DIRECTIONS = pd.read_csv(RS_DIR / "direction_scenarios.csv")
RS_CORR = pd.read_csv(RS_DIR / "correlation_scenarios.csv")
RS_TAYLOR = pd.read_csv(RS_DIR / "taylor_risk_approximations.csv")


def pct(x, digits=1):
    if pd.isna(x):
        return "NA"
    if abs(x) < 0.000005:
        x = 0.0
    return f"{x * 100:.{digits}f}%"


def money(x):
    return f"${x:,.0f}"


# ---------------------------------------------------------------- workbook

def style_sheet(ws, widths):
    header_fill = PatternFill("solid", fgColor="12395B")
    header_font = Font(bold=True, color="FFFFFF")
    for cell in ws[1]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", wrap_text=True)
    ws.freeze_panes = "A2"
    for i, width in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = width


def auto_widths(frame, first=30):
    widths = [first]
    for col in list(frame.columns)[1:]:
        widths.append(max(13, min(30, int(len(str(col)) * 1.7) + 4)))
    return widths


def add_sheet(wb, title, frame, first=False, widths=None):
    ws = wb.active if first else wb.create_sheet()
    ws.title = title
    ws.append(list(frame.columns))
    for row in frame.itertuples(index=False):
        ws.append(list(row))
    style_sheet(ws, widths or auto_widths(frame))
    return ws


def add_notes(wb, title, rows, first=False):
    ws = wb.active if first else wb.create_sheet()
    ws.title = title
    ws.append(["Item", "Detail"])
    for key, value in rows:
        ws.append([key, value])
    style_sheet(ws, [34, 120])
    for row in ws.iter_rows(min_row=2, max_col=2):
        row[1].alignment = Alignment(wrap_text=True, vertical="top")
    return ws


def build_workbook() -> Path:
    wb = Workbook()
    add_notes(wb, "Contents", [
        ("Combined workbook", "Live TSX Portfolio: From Market Data to an Investment Decision, latest run 30 October 2026"),
        ("Layer 1: Data pipeline", "Sheets: Pipeline Run, Data Quality, Latest Snapshot, Refresh Weights, Refresh Metrics"),
        ("Layer 2: Market regimes through structure (SVD)", "Sheets: Regime Spectrum, Regime Loadings, Regime States, Regime Annual, Regime Extremes"),
        ("Layer 3: Strategy evaluation", "Sheets: Momentum Performance, Momentum Payoff, Momentum Monthly, Momentum Stress, Decision Criteria, EV Sensitivity"),
        ("Layer 4: Optimal trade design", "Sheets: Trade Plan, Trade Sizing, Leverage, Kelly, Stop Loss, Execution"),
        ("Layer 5: Portfolio risk surface", "Sheets: Risk Surface Summary, Direction Scenarios, Correlation Scenarios, Taylor Approximations"),
        ("Headline results", "Pipeline coverage 100% with no missing sessions. PC1 explains 35.6% of daily variance. The momentum strategy returned 27.7% a year in sample but the verdict is DO NOT TRADE. The CNQ trade design is capped at 2,551 shares. The ENB and TD minimum-volatility mix is 49.0% ENB at 12.3% volatility."),
        ("Full detail", "The separate project workbooks hold the complete grids and daily projection files. This workbook combines the decision-level tables."),
    ], first=True)
    add_notes(wb, "Pipeline Run", [
        ("Source", RUN["source"]), ("Feed", RUN["feed_description"]),
        ("Daily history from", RUN["daily_start_requested"]),
        ("Latest daily date", RUN["latest_daily_date"]),
        ("Daily rows", f"{RUN['daily_raw_rows']:,}"), ("Intraday rows", f"{RUN['intraday_raw_rows']:,}"),
        ("Quarantined rows", RUN["quarantined_rows"]), ("Gap groups", RUN["gap_groups"]),
        ("Filled sessions", RUN["filled_sessions"]), ("Outliers flagged", RUN["outliers_flagged"]),
        ("Corporate actions", RUN["corporate_actions"]),
        ("Strategy window", f"{RUN['strategy_estimation_start'][:10]} to {RUN['strategy_estimation_end'][:10]}"),
    ])
    add_sheet(wb, "Data Quality", QUALITY)
    snap = SNAPSHOT[["short", "adjusted_close", "return_1d", "return_21d", "return_252d",
                      "realized_vol_60d", "beta_252d", "drawdown_252d"]]
    add_sheet(wb, "Latest Snapshot", snap)
    add_sheet(wb, "Refresh Weights", REFRESH_WEIGHTS)
    add_sheet(wb, "Refresh Metrics", REFRESH_METRICS)
    add_sheet(wb, "Regime Spectrum", SPECTRUM)
    loadings = LOADINGS.reset_index().rename(columns={"index": "stock"})
    add_sheet(wb, "Regime Loadings", loadings)
    add_sheet(wb, "Regime States", STATES)
    add_sheet(wb, "Regime Annual", ANNUAL)
    add_sheet(wb, "Regime Extremes", EXTREMES.head(15))
    add_sheet(wb, "Momentum Performance", SE_METRICS)
    add_sheet(wb, "Momentum Payoff", SE_PAYOFF)
    add_sheet(wb, "Momentum Monthly", SE_MONTHLY)
    add_sheet(wb, "Momentum Stress", SE_STRESS)
    add_sheet(wb, "Decision Criteria", SE_CRITERIA)
    add_sheet(wb, "EV Sensitivity", SE_EV)
    add_notes(wb, "Trade Plan", [
        ("Instrument", "Canadian Natural Resources (CNQ.TO), long"),
        ("Signal", TD["signal"]), ("Account", "Hypothetical $1,000,000"),
        ("Entry", f"${TD['entry_price']:,.2f}"), ("Stop", f"${TD['stop_price']:,.2f}"),
        ("Target", f"${TD['target_price']:,.2f}"), ("ATR14", f"${TD['atr14']:,.2f}"),
        ("Final quantity", f"{TD['final_quantity']:,} shares"),
        ("Position", money(TD["position_value"])), ("Binding constraint", TD["binding_constraint"]),
        ("Risk at stop", money(TD["dollar_risk_at_stop"])),
        ("Gain at target", money(TD["dollar_gain_at_target"])),
        ("Expected profit", money(TD["expected_profit_after_costs"])),
        ("Status", "Paper trade only, per the strategy evaluation verdict"),
    ])
    add_sheet(wb, "Trade Sizing", TD_PROFIT)
    add_sheet(wb, "Leverage", TD_LEV)
    add_sheet(wb, "Kelly", TD_KELLY)
    add_sheet(wb, "Stop Loss", TD_STOP)
    add_sheet(wb, "Execution", TD_EXEC)
    add_notes(wb, "Risk Surface Summary", [
        ("Assets", "Enbridge (ENB) and TD Bank (TD)"), ("Window", f"{RS['window_start']} to {RS['window_end']}, {RS['observations']} days"),
        ("Capital example", money(RS["capital"])),
        ("ENB volatility", pct(RS["vol_a"])), ("TD volatility", pct(RS["vol_b"])),
        ("Correlation", f"{RS['correlation']:.3f}"),
        ("Safest mix", f"ENB {pct(RS['base_weight_a'])}, TD {pct(1 - RS['base_weight_a'])}"),
        ("Minimum volatility", pct(RS["base_volatility"])),
        ("Risk gradient", f"weight {RS['risk_gradient'][0]:.4f}, correlation {RS['risk_gradient'][1]:.4f}"),
        ("Hessian eigenvalues", f"{RS['risk_hessian_eigenvalues'][0]:.3f} and {RS['risk_hessian_eigenvalues'][1]:.3f}"),
        ("Hessian reading", RS["risk_hessian_classification"]),
    ])
    add_sheet(wb, "Direction Scenarios", RS_DIRECTIONS)
    add_sheet(wb, "Correlation Scenarios", RS_CORR)
    add_sheet(wb, "Taylor Approximations", RS_TAYLOR)
    add_notes(wb, "Method and Limits", [
        ("Pipeline", "Yahoo Finance daily OHLCV from 1 June 2016 and 15-minute bars for the latest five days. Adjusted close is the canonical series. The feed is a near-live polling pipeline, not a direct exchange tick feed."),
        ("Regimes", "SVD on centred daily log returns for the ten stocks. State labels are retrospective: the volatility threshold uses the full sample. The layer describes structure and does not replace the earlier hidden Markov model or forecast returns."),
        ("Strategy", "12-1 momentum, top 3, equal weight, monthly, 10 bps on turnover. The universe was selected in 2026, so selection bias applies to every statistic. Verdict: DO NOT TRADE with live capital."),
        ("Trade design", "The win probability is a planning scenario taken from the momentum lot record. Impact uses a stylised quadratic coefficient. Dollar risk at the stop is a planning figure; gaps can exceed it."),
        ("Risk surface", "Volatilities and correlation are 252-day estimates held fixed across the surfaces. Taylor approximations are local."),
        ("Testing", "The full project test suite has 20 passing tests."),
    ])
    path = REPORTS / "TSX_Portfolio_Combined_Model.xlsx"
    wb.save(path)
    return path


# ---------------------------------------------------------------- combined report

def build_report() -> Path:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (Image, PageBreak, Paragraph, Preformatted,
                                    SimpleDocTemplate, Spacer, Table, TableStyle)

    styles = getSampleStyleSheet()
    S = {
        "title": ParagraphStyle("VTitle", parent=styles["Title"], fontName="Times-Bold", fontSize=21, leading=25, textColor=colors.black, alignment=TA_CENTER, spaceAfter=4),
        "subtitle": ParagraphStyle("VSub", parent=styles["Normal"], fontName="Times-Roman", fontSize=11, leading=14, textColor=colors.black, alignment=TA_CENTER, spaceAfter=10),
        "h1": ParagraphStyle("VH1", parent=styles["Heading1"], fontName="Times-Bold", fontSize=14.5, leading=17, textColor=colors.black, spaceBefore=11, spaceAfter=5),
        "h2": ParagraphStyle("VH2", parent=styles["Heading2"], fontName="Times-Bold", fontSize=11.5, leading=14, textColor=colors.black, spaceBefore=8, spaceAfter=4),
        "body": ParagraphStyle("VBody", parent=styles["BodyText"], fontName="Times-Roman", fontSize=10, leading=13.8, textColor=colors.black, spaceAfter=5),
        "small": ParagraphStyle("VSmall", parent=styles["BodyText"], fontName="Times-Roman", fontSize=8.2, leading=10.5, textColor=colors.black, spaceAfter=4),
        "figcap": ParagraphStyle("VFigCap", parent=styles["Normal"], fontName="Times-Italic", fontSize=8.5, leading=11, textColor=colors.black, alignment=TA_CENTER, spaceBefore=2, spaceAfter=4),
        "tbltitle": ParagraphStyle("VTblTitle", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=9.5, leading=12, textColor=colors.black, spaceBefore=5, spaceAfter=3),
        "code": ParagraphStyle("VCode", parent=styles["Code"], fontName="Courier", fontSize=7.4, leading=9.4, textColor=colors.black),
    }
    S["cell"] = ParagraphStyle("VCell", parent=S["body"], fontName="Helvetica", fontSize=8.2, leading=10.2, spaceAfter=0)
    S["cellh"] = ParagraphStyle("VCellH", parent=S["cell"], fontName="Helvetica-Bold")

    def P(text, style="body"):
        return Paragraph(text, S[style])

    def tbl(data, widths):
        wrapped = [[Paragraph(str(c), S["cellh"] if r == 0 else S["cell"]) for c in row] for r, row in enumerate(data)]
        t = Table(wrapped, colWidths=widths, repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#DDDDDD")),
            ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.black),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        return t

    counters = {"fig": 0, "tbl": 0, "lst": 0}

    def figure(rel, caption, ratio=0.48, width=170):
        counters["fig"] += 1
        return [Image(str(ROOT / rel), width=width * mm, height=width * ratio * mm),
                P(f"Figure {counters['fig']}. {caption}", "figcap")]

    def table_title(caption):
        counters["tbl"] += 1
        return P(f"Table {counters['tbl']}. {caption}", "tbltitle")

    def listing(code_text, caption):
        counters["lst"] += 1
        pre = Preformatted(code_text.strip("\n"), S["code"], maxLineLength=120)
        t = Table([[pre]], colWidths=[176 * mm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F5F5F5")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#999999")),
            ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        return [P(f"Listing {counters['lst']}. {caption}", "tbltitle"), t, Spacer(1, 2 * mm)]

    sm, bm, em = SE["strategy_metrics"], SE["benchmark_metrics"], SE["equal_weight_metrics"]
    story = [P("Live TSX Portfolio: From Market Data to an Investment Decision", "title"),
             P("Munzeleen Sarwar", "subtitle")]

    # ---------------------------------------------------------- executive summary
    story.append(P("Executive summary", "h1"))
    story.append(P("Objective and scope:", "h2"))
    story.append(P("This report documents a five-part quantitative study conducted on a single dataset: daily and intraday prices for ten TSX-listed stocks and the S&P/TSX Composite index, collected, validated and stored by a purpose-built market data pipeline. The study was designed to examine the full sequence of work that precedes an investment decision, from data acquisition to trade design, and to record for each part the method applied, the results obtained, and the conclusions those results support. All market data extend to 30 October 2026. The implementation is written in Python; the relevant source files are identified in each section, representative code is reproduced, and Appendix A catalogues every file in the project with its function and its outputs."))
    story.append(P("Relation to the Quantamental Investing and AI portfolio project.", "h2"))
    story.append(P("This study is an independent project. It is not a continuation of the Quantamental Investing and AI portfolio project, and it neither uses nor revises that project's backtest or conclusions. The two projects are related in subject only: both use a ten-stock TSX universe under the same position and sector limits. The Quantamental project ranks ten portfolio strategies on a fixed weekly dataset over a fixed test window, and its output is a performance ranking. This project examines a different question: whether the complete sequence from raw market data to an investment decision can be verified at each step. Its data are daily and intraday records maintained by a validated pipeline rather than a fixed download, and it adds a market structure analysis, a strategy audit conducted against criteria fixed in advance, a fully specified trade design and a portfolio risk surface, none of which appears in the earlier project. Its output is a decision, recorded in the Conclusions, rather than a ranking."))
    story.append(P("Data pipeline.", "h2"))
    story.append(P("The pipeline acquired 28,754 daily price records and 1,426 intraday records from Yahoo Finance, beginning 1 June 2016. In the latest completed run, coverage was 100 percent for all eleven symbols, with no missing trading sessions and no records quarantined as invalid; 328 corporate actions were extracted and 720 return outliers were flagged and retained for review. Four portfolio allocations were refreshed on the latest 104 weekly returns under long-only constraints of 20 percent per stock and 40 percent per sector. The principal result of this part is evidential rather than financial: every subsequent part rests on a dataset whose completeness and adjustments have been measured and reported, rather than assumed."))
    story.append(P("Market structure.", "h2"))
    story.append(P("Singular value decomposition was applied to 2,613 daily return vectors. The first direction accounts for 35.6 percent of daily return variance, the first three directions for 68.6 percent, and a three-direction reconstruction leaves 31.4 percent of variance unexplained. Market states defined on trailing benchmark return and volatility show a consistent pattern: days in the high-volatility decline state are located farther from the sample centre and exhibit a lower residual share (35.5 percent) than calm advance days (44.1 percent). Common movement therefore accounts for a larger proportion of returns during market stress, and diversification measured over calm periods overstates the protection available during declines."))
    story.append(P("Strategy evaluation.", "h2"))
    story.append(P("A monthly momentum strategy, holding the three highest-ranked stocks on a 12-1 momentum measure, was evaluated against a decision rule specified in advance. Over 111 months the strategy returned 27.7 percent per annum, with a t-statistic of 3.27 on the mean monthly return and an expected value of +0.38R per trade lot. The strategy nevertheless failed three of the six decision criteria: its Sharpe ratio of 1.00 was below the 1.24 obtained by an equal-weight holding of the same universe; its maximum drawdown of 28.0 percent exceeded the 25 percent limit; and the universe, selected in 2026, was not point-in-time, as demonstrated by a placebo test in which random stock selection within the same universe produced a median return of 19.6 percent per annum. The recorded decision is that the strategy is not approved for trading with real capital."))
    story.append(P("Trade design.", "h2"))
    story.append(P("A single trade in Canadian Natural Resources, the highest-ranked momentum stock at the final formation date, was designed in full for a hypothetical $1,000,000 account: entry at the adjusted close of $78.39, a stop at $74.62 set at two times the 14-day average true range, and a target at $84.04. Three sizing methods were compared. An impact-only optimum of approximately 302,000 shares was rejected as inconsistent with any risk constraint; a variance-penalised optimum corresponded to a position of 0.34 times capital; the final size of 2,551 shares was determined by the 20 percent position limit and carries $9,617 of risk at the stop, or 0.96 percent of capital. Consistent with the decision recorded in the strategy evaluation, the plan is designated for paper trading only."))
    story.append(P("Portfolio risk surface.", "h2"))
    story.append(P("A two-asset portfolio of Enbridge and TD was analysed using multivariable calculus over the most recent 252 trading days. Portfolio value is linear in the two prices, and its derivatives are exact. Portfolio volatility is nonlinear: at the minimum-volatility allocation of 49.0 percent in Enbridge, volatility is 12.3 percent, the gradient with respect to the allocation weight is zero, and the gradient with respect to correlation is 0.061. The Hessian of the volatility function has one positive and one negative eigenvalue, identifying a saddle surface. Across correlation scenarios, the minimum attainable volatility ranges from 8.6 percent at a correlation of -0.5 to 16.8 percent at 0.9, while the risk-minimising weight changes comparatively little. Risk monitoring for such a portfolio should therefore focus on the level of correlation rather than on frequent adjustment of weights."))
    story.append(P("Conclusions.", "h2"))
    story.append(P("Three conclusions follow from the study as a whole. First, data quality is a measurable output and should be reported with the same rigour as performance. Second, the structure of returns is state-dependent, and risk estimates formed in calm periods should not be extrapolated to stressed periods. Third, a favourable backtest result is not sufficient evidence for a trading decision where the test itself is not point-in-time; the strategy examined here is accordingly not approved, and the associated trade design is restricted to paper trading. Each conclusion is stated within the limits of the data and methods described in the corresponding section."))

    # ---------------------------------------------------------- 1. pipeline
    story.append(P("1. The live market data pipeline", "h1"))
    story.append(P("Objective", "h2"))
    story.append(P("The objective of this section is to produce an analysis-ready market dataset through a repeatable and auditable process. Three requirements govern the design. Completeness: missing observations must be detected against a defined trading calendar rather than passed over. Consistency: a single price basis must be used for return calculations so that splits and dividends do not distort results. Auditability: every record removed, filled or flagged must be counted and reported, so that the state of the data can be verified independently of the analysis built on it."))
    story.append(P("Method", "h2"))
    story.append(P("Daily open, high, low, close, adjusted close and volume data are obtained from Yahoo Finance from 1 June 2016 for ten stocks (Canadian Natural Resources, Enbridge, Cameco, TD, Brookfield, Shopify, Toromont, Barrick Mining, Loblaw and CAE) and for the S&P/TSX Composite. Fifteen-minute bars for the most recent five trading days provide the intraday layer. Raw records are stored by symbol in Parquet format with retrieval timestamps. Adjusted close is adopted as the canonical series for returns and features because it incorporates splits and dividends."))
    story.append(P("Validation and cleaning proceed in a fixed order. Records failing price and volume checks are classified as invalid and quarantined. Duplicate symbol-date records are removed, retaining the most recently retrieved version. Trading sessions are defined by the benchmark calendar; a stock absent on a benchmark session is recorded as a gap. Missing adjusted closes may be forward-filled only for gaps of five sessions or fewer, and all fills remain flagged. Corporate actions are extracted into a dedicated table. Daily returns are screened using a modified z-score based on the median absolute deviation, with a threshold of 3.5; flagged returns are retained, since extreme returns in this sample correspond predominantly to genuine market events, and their removal would understate risk in later sections."))
    story.append(P("Features are computed from the cleaned series: returns over 1, 5, 21 and 252 sessions; realised volatility over 20 and 60 days; beta and correlation against the benchmark over 252 days; and drawdown from the 252-day high. Weekly prices support a strategy refresh in which four allocations (Equal Weight, Minimum Variance, Risk Parity and Minimum CVaR) are re-estimated on the latest 104 weekly returns under long-only constraints of 20 percent per stock and 40 percent per sector."))
    story.append(P("Implementation", "h2"))
    story.append(P("This section is implemented in the package directory src/tsx_pipeline. The module ingest.py provides fetch_daily and fetch_intraday, which retrieve and normalise the Yahoo Finance data, and write_raw, which stores the raw Parquet files. The module quality.py provides validate_ohlcv, which applies the record-level checks; deduplicate_valid, which separates clean records from quarantined records; detect_gaps and build_close_matrices, which construct the raw, adjusted and filled price matrices; detect_outliers, which applies the modified z-score screen; and extract_corporate_actions. The module features.py computes the daily features and weekly prices. The module strategies.py performs the constrained optimisation for the refreshed allocations. The runner run_pipeline.py executes the steps in sequence. Listing 1 reproduces the central sequence of the runner."))
    story += listing("""
daily, daily_status = fetch_daily(start=args.start)
intraday, intraday_status = fetch_intraday()
write_raw(daily, intraday, ROOT)

validated = validate_ohlcv(daily)
clean, quarantine = deduplicate_valid(validated)
sessions = benchmark_sessions(clean)
gaps, fills = detect_gaps(clean, sessions)
raw_matrix, adjusted_matrix, filled_matrix = build_close_matrices(clean, fills, sessions)
outliers = detect_outliers(clean, threshold=..., extreme_threshold=...)
actions = extract_corporate_actions(daily)
quality = quality_summary(validated, clean, quarantine, gaps, fills,
                          outliers, actions, sessions)
""", "run_pipeline.py: acquisition, validation, gap detection and quality summary, in execution order")
    story.append(P("Each function in Listing 1 returns both data and accounting information. validate_ohlcv attaches an error string and a status to every record, so no record is dropped without a recorded reason. quality_summary aggregates the counts that appear in Table 1. The runner writes the cleaned data to data/clean, the accounting tables to data/outputs, and a run summary to data/outputs/run_summary.json, which is the source of the figures reported in this section. The reporting module reporting.py generates the charts, the HTML dashboard and the Markdown data quality report from the same outputs."))
    story.append(P("Results", "h2"))
    story.append(table_title("Latest pipeline run: coverage, quality counts and strategy window"))
    rows = [["Measure", "Latest run"], ["Daily rows", f"{RUN['daily_raw_rows']:,}"], ["Intraday rows", f"{RUN['intraday_raw_rows']:,}"],
            ["Coverage", "100% for all 11 symbols"], ["Missing sessions", "0"], ["Quarantined rows", "0"],
            ["Corporate actions extracted", str(RUN["corporate_actions"])], ["Return outliers flagged and kept", str(RUN["outliers_flagged"])],
            ["Latest daily date", RUN["latest_daily_date"]]]
    story.append(tbl(rows, [70 * mm, 100 * mm]))
    story.append(P("The quality status recorded for each symbol in the latest run is warning. The warning arises from outlier returns that remain open for review. Given that the sample includes the market decline of March 2020, a status of warning is the accurate classification; the flagged observations are documented in the outlier report rather than removed."))
    story += figure("charts/latest_strategy_weights.png", "Refreshed strategy weights for the ten stocks under the 20 percent stock cap and 40 percent sector cap")
    story.append(table_title("Refreshed strategies on the latest 104 weekly returns: in-window results"))
    mrows = [["Refreshed strategy, latest 104 weeks", "Return", "Volatility", "Sharpe", "Max drawdown"]]
    for row in REFRESH_METRICS.itertuples(index=False):
        mrows.append([row.strategy, pct(row.annualised_return_window), pct(row.annualised_volatility_window),
                      f"{row.sharpe_window:.2f}", pct(row.max_drawdown_window)])
    story.append(tbl(mrows, [62 * mm, 28 * mm, 28 * mm, 22 * mm, 30 * mm]))
    story.append(P("Interpretation", "h2"))
    story.append(P("Minimum Variance records the highest Sharpe ratio in the estimation window, at 3.43. This figure is a diagnostic of the window, which was a strong period for Canadian equities, and is not a forecast of the strategy. The refresh is a monitoring function: it reports the allocations that fixed rules produce on current data. It does not amend the conclusions of the earlier portfolio study, and it does not constitute a recommendation to hold the refreshed weights. The data source is a polling feed rather than a direct exchange feed; this classification is stated because the appropriate use of intraday data depends on it, and no result in this report requires tick-level data."))

    # ---------------------------------------------------------- 2. regimes
    story.append(P("2. Market regimes through structure", "h1"))
    story.append(P("Objective", "h2"))
    story.append(P("The objective of this section is to characterise the structure of daily returns across the ten stocks: the extent to which daily movement is common to all stocks, the extent to which it separates identifiable groups of stocks, and the extent to which it is specific to individual stocks, together with the variation of that structure between calm and stressed market conditions. The analysis is descriptive. It produces no return forecast and no trading rule."))
    story.append(P("Method", "h2"))
    story.append(P("Each trading day is represented as a vector of ten daily log returns. The sample comprises 2,613 vectors from 2 June 2016 to 30 October 2026, computed from the cleaned adjusted-close matrix produced in Section 1. Each stock series is centred on its own sample mean. Singular value decomposition of the centred matrix yields orthogonal directions ordered by explained variance; the squared singular values, normalised, give the variance shares. Projecting each day onto the directions gives daily scores. The Euclidean norm of a centred day vector is its distance from the centre. A rank-k reconstruction rebuilds each day from the first k directions; the residual measures the information excluded by the compression."))
    story.append(P("Three supporting analyses are performed. A second decomposition standardises each stock by its own volatility before decomposition, separating correlation structure from volatility scale. Market states are assigned from the trailing 20-day benchmark return and the trailing 20-day benchmark volatility, with the high-volatility boundary at the full-sample 75th percentile of 13.49 percent, producing four states: calm advance, calm pullback, high-volatility advance and high-volatility decline. Angles between consecutive day vectors measure directional persistence, and a transition is classified as material only where the angle exceeds 135 degrees and both days lie at or above the 75th percentile of distance."))
    story.append(P("Implementation", "h2"))
    story.append(P("This section is implemented in src/tsx_pipeline/regimes.py and executed by run_regime_analysis.py. The module implements the functions specified for this project type, including create_return_vector, stack_return_vectors, get_singular_values, explained_variance_ratios, get_dominant_directions, project_all_days, distances_from_center, find_most_extreme_day, reconstruct_low_rank, compute_residuals, angle_between_vectors and count_large_transitions, together with prepare_matrix and compute_svd. Listing 2 reproduces compute_svd. The function centres or standardises the matrix through prepare_matrix, applies numpy.linalg.svd, reorients the directions under a fixed sign convention so that results are comparable between runs, and recomputes the scores against the oriented directions. The runner writes fourteen output tables to data/regime_outputs, including the spectrum, both sets of loadings, daily projections, reconstruction quality by rank, state summaries and spells, extreme days and transition tables, together with a summary file, data/regime_outputs/regime_summary.json, from which the figures in this section are taken."))
    story += listing("""
def compute_svd(returns, standardize=False):
    prepared, center, scales = prepare_matrix(returns, standardize=standardize)
    u, singular, vt = np.linalg.svd(prepared, full_matrices=False)
    directions = _orient_directions(vt.T)
    # Keep scores consistent with the oriented directions.
    scores = prepared @ directions
    return {"prepared": prepared, "center": center, "scales": scales,
            "left_vectors": u, "singular_values": singular,
            "directions": directions, "scores": scores}
""", "src/tsx_pipeline/regimes.py: compute_svd, the decomposition at the centre of this section")
    story.append(P("Results", "h2"))
    story.append(table_title("SVD spectrum: variance explained by each direction, raw centred returns"))
    srows = [["Component", "Variance explained", "Cumulative"]]
    for row in SPECTRUM.head(6).itertuples(index=False):
        srows.append([row.component, pct(row.explained_variance_ratio), pct(row.cumulative_explained_variance)])
    story.append(tbl(srows, [50 * mm, 55 * mm, 65 * mm]))
    story += figure("charts/regimes/spectrum.png", "Variance explained by each principal direction, with the cumulative share")
    story.append(P("The first direction has positive loadings for all ten stocks and is interpreted as a common-movement direction. In raw returns its largest loading is Shopify at 0.734 and its smallest is Loblaw at 0.051, reflecting differences in return volatility across the stocks. In the standardised decomposition the first direction is broadly distributed, with loadings of 0.425 for Brookfield, 0.414 for TD and 0.390 for Enbridge, and 0.221 for Shopify. The two decompositions are consistent once their different normalisations are recognised: the first describes the distribution of variance, the second the distribution of correlation. The second raw direction contrasts Shopify (0.652) with Canadian Natural Resources (-0.474) and Cameco (-0.432). The third contrasts Cameco (0.634) and Barrick Mining (0.519) with CAE (-0.351) and Canadian Natural Resources (-0.337)."))
    story += figure("charts/regimes/reduced_space.png", "Market days projected onto the first two directions, coloured by trailing market state")
    story.append(table_title("Descriptive market states: frequency, distance from the centre and residual share"))
    strows = [["Trailing state", "Days", "Share", "Average distance", "Rank-3 residual share"]]
    for row in STATES.itertuples(index=False):
        strows.append([row.market_state, str(row.days), f"{row.share_pct:.1f}%", f"{row.average_distance_from_center:.3f}", pct(row.average_rank3_residual_share)])
    story.append(tbl(strows, [46 * mm, 20 * mm, 22 * mm, 38 * mm, 44 * mm]))
    story.append(P("Interpretation", "h2"))
    story.append(P("The state comparison in Table 4 provides the principal finding of this section. High-volatility decline days have the greatest mean distance from the centre (0.085, against 0.052 for calm advance days) and the lowest mean rank-3 residual share (35.5 percent, against 44.1 percent). Returns on stressed days are therefore both larger and more concentrated in the dominant directions. The most extreme observation, 16 March 2020, illustrates the distinction between magnitude and composition: its distance of 0.493 is the largest in the sample, while its rank-3 residual share of 2.7 percent is among the smallest, indicating a large movement that conformed closely to the common pattern."))
    story.append(P("Directional persistence at the daily horizon is low. The mean angle between consecutive day vectors is 89.95 degrees and the median is 90.47 degrees, close to the value expected for unrelated directions in this space. Of 113 angles exceeding 135 degrees, 19 satisfy the additional distance condition and are classified as material transitions. Reporting the unfiltered count would overstate the frequency of structural change. The limitations of this analysis are material and are recorded here: the directions and the volatility threshold are estimated on the full sample, so the state labels are retrospective and could not have been produced in real time; the universe is the fixed list selected for the earlier study; and the economic labels attached to the second and third directions are interpretations of loadings, not estimated factors. The analysis complements, and does not replace, the probabilistic regime model used in the earlier portfolio study."))

    # ---------------------------------------------------------- 3. strategy evaluation
    story.append(P("3. Is the momentum strategy actually profitable?", "h1"))
    story.append(P("Objective", "h2"))
    story.append(P("The objective of this section is to reach a documented decision on a specified trading strategy. Because favourable backtest results are readily produced and selectively reported, the evaluation criteria are fixed before the results are examined, and the report records performance against every criterion, including those the strategy fails. The decision sought is binary and practical: whether the strategy, on the evidence available, should be traded with real capital."))
    story.append(P("Method", "h2"))
    story.append(P("The strategy is monthly cross-sectional momentum. At each month-end formation date, stocks are ranked by 12-1 momentum, defined as the price one month before formation divided by the price thirteen months before formation, less one. The most recent month is excluded from the measure, consistent with the momentum literature, in which very short-horizon returns exhibit reversal. The three highest-ranked stocks are held in equal weight during the following month. Formation uses only data available at the formation date, so the backtest contains no look-ahead in security selection. Transaction costs of 10 basis points are applied to turnover, defined as the sum of absolute weight changes between consecutive portfolios, with the initial establishment of positions charged in full. The evaluation sample comprises 111 holding months, from August 2017 to October 2026, the first twelve months of the data being consumed by the momentum lookback."))
    story.append(P("Evidence is assembled in four parts. First, the payoff record: each stock held for one month constitutes one trade lot, yielding 333 lots, from which the win rate, mean winning return, mean losing return, payoff ratio and expected value are computed. Second, portfolio statistics: annualised return and volatility, Sharpe ratio against a 2 percent risk-free rate, the t-statistic of the mean monthly return, maximum drawdown and monthly CVaR at 95 percent, computed identically for the strategy, the benchmark and an equal-weight portfolio of the same universe. Third, resampling: 10,000 bootstrap paths of the realised monthly returns, and 10,000 paths under a six-month block bootstrap, estimate the sensitivity of the outcome to the particular months realised. Fourth, a placebo test and stress tests: the placebo replaces momentum selection with random selection of three stocks per month over 500 trials under the same cost rule; the stress tests re-estimate performance at transaction costs of 25 and 50 basis points, after removal of the six and twelve most favourable months, after the addition of a synthetic month returning -20 percent, with the worst decile of losses increased by one half, and over the subsample from 2020."))
    story.append(P("Implementation", "h2"))
    story.append(P("This section is implemented in src/tsx_pipeline/strategy_evaluation.py and executed by run_strategy_evaluation.py. The function month_end_prices extracts the final observation of each calendar month, retaining actual trading dates; momentum_scores implements the 12-1 measure as a ratio of lagged price frames; backtest_momentum conducts the formation and holding loop and returns the monthly series and the lot record. The functions expected_value, break_even_prob and payoff_summary implement the payoff analysis; performance_metrics computes the portfolio statistics; simulate_outcomes performs both bootstrap variants; stress_test and evaluate_strategy assemble the stress results and the decision table. Listing 3 reproduces the two lines at the centre of the method: the momentum measure and the expected value function. Expected value is expressed in units of R, the loss on a losing lot, so that strategies with different payoff scales can be compared on a common basis."))
    story += listing("""
def momentum_scores(monthly_prices, stocks):
    \"\"\"12-1 momentum: return from 13 months ago to 1 month ago.\"\"\"
    return monthly_prices[stocks].shift(1) / monthly_prices[stocks].shift(13) - 1

def expected_value(win_probability, reward_risk):
    \"\"\"Expected value in units of R, where one losing trade loses 1R.\"\"\"
    return float(win_probability * reward_risk - (1 - win_probability))
""", "src/tsx_pipeline/strategy_evaluation.py: the momentum measure and the expected value function")
    story.append(P("The runner writes the monthly return series, the complete lot record, the payoff summary, the performance table, the bootstrap distributions and their summary statistics, the stress table, the decision criteria table, the expected value sensitivity grid and the placebo results to data/strategy_evaluation_outputs. The decision recorded in that directory, in strategy_summary.json, is the decision reported here."))
    story.append(P("Results", "h2"))
    story.append(table_title("Momentum strategy against the benchmark and the equal-weight universe, August 2017 to October 2026"))
    prows = [["Series", "Annualised return", "Volatility", "Sharpe", "t-statistic", "Max drawdown"]]
    for label, m in [("Momentum top 3", sm), ("S&P/TSX Composite", bm), ("Equal weight, same 10 stocks", em)]:
        prows.append([label, pct(m["annualised_return"]), pct(m["annualised_volatility"]), f"{m['sharpe']:.2f}", f"{m['t_statistic']:.2f}", pct(m["max_drawdown"])])
    story.append(tbl(prows, [46 * mm, 30 * mm, 24 * mm, 20 * mm, 24 * mm, 26 * mm]))
    story += figure("charts/strategy_evaluation/growth.png", "Growth of $100 in the momentum strategy, the benchmark and the equal-weight universe")
    story.append(P("The payoff record indicates a positive expected value within the sample. Of 333 lots, 56.2 percent were profitable; the mean winning lot returned 9.1 percent and the mean losing lot -6.3 percent, giving a payoff ratio of 1.46 and an expected value of +0.38R per lot. The break-even win rate at this payoff is 40.7 percent, so the observed win rate exceeds break-even by 15.4 percentage points. Sensitivity analysis qualifies this margin: a simultaneous reduction of ten percentage points in the win rate and 20 percent in the payoff ratio reduces expected value to approximately zero. Portfolio results are summarised in Table 5. The strategy returned 27.7 percent per annum against 9.7 percent for the benchmark, with volatility of 26.0 percent against 13.5 percent. In the bootstrap, the strategy was profitable in 99.8 percent of resampled paths and exceeded the benchmark total return in 96.7 percent. Under stress, the result is robust to transaction costs, remaining at 25.4 percent per annum at 50 basis points, but is sensitive to the removal of favourable months: excluding the best twelve months reduces the annualised return to 6.1 percent and the t-statistic to 1.16."))
    story += figure("charts/strategy_evaluation/ev_heatmap.png", "Expected value in R across win probability and payoff combinations, with the break-even boundary")
    story.append(P("Interpretation and decision", "h2"))
    story.append(P("The decision is DO NOT TRADE. The strategy satisfies the criteria on expected value, statistical significance and bootstrap performance against the benchmark. It fails three criteria. Its Sharpe ratio of 1.00 is below the 1.24 of the equal-weight portfolio of the same universe, so the selection rule does not improve on the simplest alternative employment of the same securities. Its maximum drawdown of -28.0 percent exceeds the 25 percent limit specified in the decision rule. The test universe was selected in 2026 for a separate project and is not point-in-time; the placebo test quantifies the consequence, with random selection in the same universe achieving a median annualised return of 19.6 percent and the strategy ranking only at the 74th percentile of placebo trials on Sharpe ratio. Resampling methods cannot correct this defect, because every resampled observation is drawn from the same selected universe."))
    story.append(P("The conclusion is specific to the evidence. It is not a finding that momentum strategies are unprofitable in general. The evidence required to reconsider the decision is identifiable: a re-estimation of the identical rule on a point-in-time TSX universe, including securities subsequently removed from the index, followed by a period of paper trading under the designed execution rules. Pending that evidence, the strategy is retained as a research candidate, and its status determines the status of the trade design in Section 4."))

    # ---------------------------------------------------------- 4. trade design
    story.append(P("4. Designing an optimal trade", "h1"))
    story.append(P("Objective", "h2"))
    story.append(P("The objective of this section is to convert a trading signal into a complete and internally consistent trade plan, in which each parameter (entry price, stop price, target price, position size, execution schedule and holding period) is derived by a stated method rather than selected by judgement. The analytical framework is single-variable calculus: each decision is formulated as a function of one variable, and the optimum is located where the derivative of that function is zero, subject to the account constraints, which are applied as binding limits where they are more restrictive than the unconstrained optimum."))
    story.append(P("Method", "h2"))
    story.append(P(f"The instrument is Canadian Natural Resources, ranked first on the momentum measure of Section 3 at the formation date of 30 October 2026, with a score of +56.8 percent. The account is a hypothetical $1,000,000, and the holding period is 20 trading days, consistent with the monthly holding period of the strategy. Entry is the adjusted close of ${TD['entry_price']:,.2f}. The stop is placed two times the 14-day average true range ($1.88) below entry, at ${TD['stop_price']:,.2f}; this level is close to the 20-day moving average of $73.99, so the risk exit and the invalidation of the short-term trend occur at approximately the same price. The target is set at 1.5 times the stop distance, at ${TD['target_price']:,.2f}, giving a payoff ratio of 1.5."))
    story.append(P("Position size is determined by three methods in sequence. The first expresses expected profit as a function of the number of shares traded: gross expected profit is proportional to size, and market impact is modelled as a quadratic cost, in which the impact cost per share increases linearly with the quantity traded relative to average daily volume. The optimum of this function is obtained from its first derivative. The second method introduces a variance penalty: expected return on capital is expressed as a function of position leverage, less a financing charge on any borrowed component, less a penalty of one half of the risk aversion coefficient (set to 10) multiplied by the squared volatility of capital over the holding period; the optimum is again obtained from the first derivative. The third method applies the account constraints directly: a maximum position of 20 percent of capital, a maximum loss at the stop of 1 percent of capital, and no leverage. The Kelly criterion is computed for comparison. Execution is evaluated with a square-root market impact model, in which impact decreases with the execution horizon, set against a timing-risk allowance that increases with the square root of the horizon."))
    story.append(P("Implementation", "h2"))
    story.append(P("This section is implemented in src/tsx_pipeline/trade_design.py and executed by run_trade_design.py, which reads the payoff summary produced in Section 3 and the cleaned daily data produced in Section 1. The function trade_profit implements the profit function; marginal_profit implements its derivative; optimal_size_impact_only returns the closed-form optimum; risk_adjusted_return and optimal_leverage implement the penalised objective and its optimum; kelly_fraction and kelly_analysis implement the Kelly calculations; no_edge_win_prob and stoploss_analysis implement the stop analysis; execution_cost and execution_analysis implement the execution model; and design_trade assembles the final plan by taking the minimum of the quantities implied by the four sizing rules and recording which constraint binds. Listing 4 reproduces trade_profit and the sizing selection inside design_trade."))
    story += listing("""
def trade_profit(quantity, entry_price, expected_return, adv_shares,
                 impact_slope=0.25, fixed_cost=0.0):
    gross = quantity * entry_price * expected_return
    impact = entry_price * impact_slope * quantity ** 2 / adv_shares
    return float(gross - impact - fixed_cost)

final_quantity = int(max(0, floor(min(q_impact, q_risk_adjusted,
                                      q_risk_cap, q_position_cap))))
""", "src/tsx_pipeline/trade_design.py: the profit function and the final size selection")
    story.append(P("The runner writes the completed plan to data/trade_design_outputs/trade_plan.json, together with the profit-by-size table, the leverage analysis, the Kelly table, the stop-loss table at five average true range multiples, the execution analysis at nine horizons, and a payoff summary restricted to Canadian Natural Resources lots."))
    story.append(P("Results", "h2"))
    story += figure("charts/trade_design/profit_by_size.png", "Expected profit by number of shares, after quadratic market impact, with the risk-adjusted optimum and the final capped size")
    story.append(P("The three sizing methods produce materially different quantities, and the divergence is itself informative. The impact-only optimum is approximately 302,000 shares. Average daily volume in Canadian Natural Resources over the preceding 20 sessions was 8.66 million shares; at quantities relevant to a $1,000,000 account, market impact is too small to constrain size, and a model containing no risk term returns a quantity exceeding the account by a factor of more than twenty. The variance-penalised optimum corresponds to a position of 0.34 times capital, approximately 4,300 shares. The position limit of 20 percent of capital is more restrictive than both the penalised optimum and the 1 percent risk budget, and therefore determines the final size of 2,551 shares. The Kelly fraction for the planning parameters is 26.9 percent of capital at risk; combined with the stop distance of 4.8 percent, this implies a position of approximately 560 percent of capital. The Kelly figure is a proportion of capital exposed to loss, not a position weight, and its assumptions of repeated independent trials and execution at the stop price do not hold for a single equity position. It is recorded and not used."))
    story += figure("charts/trade_design/trade_levels.png", "Entry, stop and target levels for the CNQ trade, set from the 14-day average true range")
    story.append(table_title("The completed trade plan"))
    trows = [["Item", "Value"], ["Entry", f"${TD['entry_price']:,.2f}"], ["Stop", f"${TD['stop_price']:,.2f}"],
             ["Target", f"${TD['target_price']:,.2f}"], ["Size", f"{TD['final_quantity']:,} shares"],
             ["Position", f"{money(TD['position_value'])} (20% cap binds)"], ["Risk at stop", money(TD["dollar_risk_at_stop"])],
             ["Gain at target", money(TD["dollar_gain_at_target"])], ["Expected profit", money(TD["expected_profit_after_costs"])],
             ["Status", "Paper trade only"]]
    story.append(tbl(trows, [40 * mm, 130 * mm]))
    story.append(P("Interpretation", "h2"))
    story.append(P("Two properties of the plan should be noted. First, under a driftless random walk the probability of the target being reached before the stop is the stop distance divided by the sum of the two distances; at a payoff ratio of 1.5 this probability is 40 percent, identical to the break-even win rate. Scaling both distances by the same factor leaves this probability unchanged and alters only the monetary amount at risk. Stop placement is therefore a determination of the size of a loss, not a source of expected return, and the choice of two average true ranges is justified by reference to the recent trading range and the moving average, not by any improvement in win probability. Second, the planning win probability of 56.2 percent is taken from the lot record of Section 3 and is a scenario assumption for this stop and target configuration, not an estimated probability of the configuration itself; the expected profit of $3,485 is conditional on that assumption. Execution analysis indicates that the order represents 0.03 percent of average daily volume, with estimated impact below 0.2 basis points over a one-day horizon and a timing-risk allowance of approximately 40 basis points per day of delay, so the plan specifies completion within one trading day under a limit order with a defined maximum chase of one quarter of the average true range. The status of the plan is paper trading only, as determined in Section 3."))

    # ---------------------------------------------------------- 5. risk surface
    story.append(P("5. Exploring a portfolio risk surface", "h1"))
    story.append(P("Objective", "h2"))
    story.append(P("The objective of this section is to characterise the response of a two-asset portfolio to simultaneous changes in two variables. Single-variable sensitivity analysis holds one input constant and therefore cannot represent combined movements, which are the cases of practical interest. Multivariable calculus supplies the required instruments: partial derivatives for the response to each variable separately, the gradient for the direction of steepest change, directional derivatives for specified combined movements, the Hessian for curvature, and Taylor expansions for local approximation. Each instrument is applied to the same portfolio so that their outputs can be compared directly."))
    story.append(P("Method", "h2"))
    story.append(P(f"The portfolio comprises Enbridge and TD, with parameters estimated from daily log returns over the most recent 252 trading days: Enbridge volatility {pct(RS['vol_a'])}, TD volatility {pct(RS['vol_b'])}, and correlation {RS['correlation']:.3f}. The reference portfolio is a $100,000 holding at the minimum-volatility allocation, {pct(RS['base_weight_a'])} in Enbridge and {pct(1 - RS['base_weight_a'])} in TD. Two functions are analysed. Portfolio value, the sum over the two assets of shares multiplied by price, is evaluated over a grid of price shocks from -30 percent to +30 percent in each asset. Portfolio volatility, given by the standard two-asset formula in the Enbridge weight and the correlation, is evaluated over weights from 0 to 1 and correlations from -0.5 to 0.95. Derivatives of the value function are obtained analytically; derivatives and the Hessian of the volatility function are obtained by central finite differences. All Taylor approximations are compared with exact function values at the same points, and the errors are reported."))
    story.append(P("Implementation", "h2"))
    story.append(P("This section is implemented in src/tsx_pipeline/risk_surface.py and executed by run_risk_surface.py. The functions stock_value and portfolio_value implement the value function; create_evaluation_grid evaluates it over the shock grid; compute_partial_derivatives and compute_hessian implement central finite-difference derivatives for an arbitrary function; directional_derivative and analyze_directions evaluate combined movements; first_order_approximation and second_order_approximation implement the Taylor expansions; portfolio_volatility and minimum_volatility_weight implement the risk function and its closed-form minimiser; and risk_report assembles the estimates, gradient and Hessian at the reference point. Listing 5 reproduces portfolio_volatility, from which the surface, the gradient, the Hessian and all approximations in this section are derived."))
    story += listing("""
def portfolio_volatility(weight_a, correlation, vol_a, vol_b):
    variance = ((weight_a * vol_a) ** 2 + ((1 - weight_a) * vol_b) ** 2
                + 2 * weight_a * (1 - weight_a) * correlation * vol_a * vol_b)
    return float(np.sqrt(max(variance, 0.0)))
""", "src/tsx_pipeline/risk_surface.py: portfolio_volatility, the risk function analysed in this section")
    story.append(P("The runner writes the value grid (625 points), the risk grid (5,959 points), the direction scenarios, the correlation scenarios and the Taylor comparison table to data/risk_surface_outputs, together with risk_surface_summary.json, which records the parameter estimates, the allocations and share counts, the gradient, the Hessian and its eigenvalues."))
    story.append(P("Results", "h2"))
    story += figure("charts/risk_surface/risk_surface.png", "Portfolio volatility surface over the Enbridge weight and the Enbridge-TD correlation")
    story.append(P(f"The value function is linear. Its partial derivative with respect to each price is the corresponding share count: {RS['shares_a']:,.0f} dollars of value per one-dollar change in the Enbridge price and {RS['shares_b']:,.0f} per one-dollar change in the TD price. Its Hessian is the zero matrix, and first-order approximations of combined movements are exact. The scenario analysis illustrates the consequence: a movement of -10 percent in Enbridge combined with +10 percent in TD changes portfolio value by +$193, whereas a movement of -10 percent in both reduces value by $10,000. Diversification, expressed in these terms, is a property of the direction of a market movement and not a uniform reduction in loss."))
    story.append(P(f"The volatility function is nonlinear. At the reference allocation its value is {pct(RS['base_volatility'])}, compared with approximately 17 percent for either asset held alone. The partial derivative with respect to the Enbridge weight is zero at this allocation, as required at a minimum; the partial derivative with respect to correlation is {RS['risk_gradient'][1]:.3f}, implying that an increase in correlation of 0.10 raises volatility by approximately 0.6 percentage points locally. The Hessian at the reference point has eigenvalues of 0.475 and -0.030. The presence of both signs classifies the surface as a saddle: convex in the weight direction, in which a minimum exists, and concave in the correlation direction, because volatility is the square root of a function that is linear in correlation. A description of the surface as convex, based on the weight direction alone, would be incorrect."))
    story.append(table_title("Correlation scenarios: safest Enbridge weight and minimum volatility at each correlation"))
    crows = [["Correlation", "Safest ENB weight", "Minimum volatility", "50/50 volatility"]]
    for row in RS_CORR.itertuples(index=False):
        crows.append([f"{row.correlation:.2f}", pct(row.minimum_volatility_weight_a), pct(row.minimum_volatility), pct(row.equal_weight_volatility)])
    story.append(tbl(crows, [34 * mm, 42 * mm, 44 * mm, 50 * mm]))
    story += figure("charts/risk_surface/correlation_scenarios.png", "Minimum achievable volatility and 50/50 volatility across correlation levels")
    story.append(P("Interpretation", "h2"))
    story.append(P("The correlation scenarios in Table 7 establish the relative importance of the two variables. As correlation increases from -0.5 to 0.9, the minimum attainable volatility increases from 8.6 percent to 16.8 percent, a range of 8.2 percentage points, while the risk-minimising Enbridge weight decreases only from 49.4 percent to 40.6 percent. The stability of the weight follows from the similarity of the two asset volatilities; the sensitivity of the risk level follows from the correlation term in the variance formula. For a portfolio of this composition, periodic rebalancing toward a recomputed minimum-volatility weight contributes little, because the optimum is comparatively insensitive to the parameter that changes. Re-estimation of correlation, and of the expected level of portfolio volatility conditional on it, is the informative monitoring activity."))
    story.append(P("The Taylor comparison defines the range over which local approximation is reliable. For small and moderate displacements, first and second order approximations differ from exact values by a few hundredths of a percentage point. For the largest joint displacement examined (weight +0.20, correlation -0.20), the first-order error is 1.13 percentage points and the second-order error 0.25 percentage points. For the largest correlation increase examined, the second-order approximation overshoots and the first-order approximation is more accurate. Approximation error is therefore reported alongside the approximations themselves. A final qualification applies to the entire analysis: volatilities and correlation are point estimates from a single 252-day window, and correlation is the least stable of the three parameters. The surface is a local representation around the current portfolio and should be re-estimated rather than extrapolated."))

    # ---------------------------------------------------------- 6/7 closing
    story.append(P("6. Synthesis", "h1"))
    story.append(P("The five parts of the study were designed as a sequence, and their conclusions are consistent when read in that order. The data pipeline establishes that the inputs to all later work are complete and accounted for. The market structure analysis establishes that returns in this universe contain a substantial common component whose share increases under stress. The strategy evaluation establishes that a strategy exploiting price trends in the same universe produces a favourable in-sample record that does not withstand scrutiny of the test design, and records a negative decision. The trade design demonstrates that the mechanics of sizing, stop placement and execution can be made rigorous independently of that decision, and that risk constraints, rather than model optima, determine the final parameters of a plan. The risk surface analysis establishes that, for the two-asset portfolio examined, the level of risk is governed principally by correlation, a parameter that weight adjustments cannot offset."))
    story.append(P("Each conclusion is conditional, and the conditions are stated in the relevant sections. The strategy decision would be reopened by a point-in-time re-estimation. The trade plan parameters would be revised by a paper-trading record at the designed size, which would test the stop and execution assumptions against realised prices. The risk surface would be revised by re-estimation on a longer window or under stressed correlation assumptions. The findings on market structure would be revised by re-estimation on a point-in-time universe. The report records these conditions so that subsequent work can proceed from identified questions rather than from general reservations."))

    story.append(P("7. Overall limitations", "h1"))
    story.append(P("The limitations of the study are as follows. All parts of the study rest on a single data source, Yahoo Finance, and on a fixed universe of ten stocks selected in 2026; selection and survivorship effects therefore affect all results, and no result should be generalised to the Toronto Stock Exchange as a whole. The data feed is a polling process and the intraday layer is limited to 15-minute bars. The decomposition directions, the state threshold and the volatility and correlation estimates are fitted on the samples they describe, which makes the structural findings retrospective. The strategy evaluation assumes execution at month-end adjusted closes and a flat transaction cost that is an assumption rather than a broker quotation. The trade design employs a scenario win probability drawn from a different exit configuration than the one designed, and a stylised impact coefficient; the monetary risk at the stop is a planning figure that a discontinuity in prices can exceed. No part of the study produces a forecast of returns. The decisions recorded are decisions about the sufficiency of evidence, and on the evidence presented the strategy is not approved for trading."))

    # ---------------------------------------------------------- appendix
    story.append(P("Appendix A. Python implementation: files, functions and outputs", "h1"))
    story.append(P("The project is implemented in Python 3 using pandas, NumPy and SciPy. Source code is organised in three groups: runner scripts at the project root, which execute each part end to end; the package src/tsx_pipeline, which contains the reusable functions; and scripts, which generate reports, workbooks, dashboards and notebooks from the saved outputs. A test suite of 20 tests in the tests directory verifies the quality rules, the decomposition properties, the strategy statistics, the trade sizing constraints and the derivative calculations. Table 8 catalogues every Python file in the project. The build scripts for the individual project reports (build_deliverables.py, build_notebook.py, build_regime_deliverables.py and build_stage2_projects.py) and the script that assembles the combined report and combined workbook (build_combined.py) operate only on saved outputs and do not alter the underlying data."))
    story += listing("""
python run_pipeline.py                 # Section 1: data pipeline and strategy refresh
python run_regime_analysis.py          # Section 2: SVD market structure
python run_strategy_evaluation.py      # Section 3: momentum strategy evaluation
python run_risk_surface.py             # Section 5: two-asset risk surface
python run_trade_design.py             # Section 4: CNQ trade design (reads Section 3 outputs)
python scripts/build_combined.py       # Combined report and combined workbook
python -m pytest tests                 # 20 tests
""", "Reproduction sequence for the full study, from the project root")
    arows = [["File", "Function", "Principal outputs"]]
    appendix_rows = [
        ("run_pipeline.py", "Executes the data pipeline end to end", "Clean data, quality tables, run summary"),
        ("run_regime_analysis.py", "Executes the market structure analysis end to end", "14 regime tables, regime summary JSON"),
        ("run_strategy_evaluation.py", "Executes the strategy evaluation, including the placebo test", "Monthly series, lots, bootstrap, decision JSON"),
        ("run_trade_design.py", "Executes the trade design from the pipeline and strategy evaluation outputs", "Trade plan JSON, sizing and execution tables"),
        ("run_risk_surface.py", "Executes the risk surface analysis end to end", "Value and risk grids, Taylor table, summary JSON"),
        ("src/tsx_pipeline/config.py", "Universe, sectors, paths and run configuration", "Shared constants for all components"),
        ("src/tsx_pipeline/ingest.py", "Retrieval and normalisation of Yahoo Finance data", "Raw Parquet files by symbol"),
        ("src/tsx_pipeline/quality.py", "Validation, deduplication, gaps, fills, outliers, corporate actions", "Clean and quarantine sets, quality accounting"),
        ("src/tsx_pipeline/features.py", "Daily features and weekly prices", "Feature table, latest risk snapshot"),
        ("src/tsx_pipeline/strategies.py", "Constrained allocation optimisation and refresh metrics", "Refreshed weights, metrics, sector weights"),
        ("src/tsx_pipeline/reporting.py", "Pipeline charts, dashboard and quality report", "PNG charts, HTML dashboard, Markdown report"),
        ("src/tsx_pipeline/regimes.py", "SVD decomposition, projections, reconstruction, states, transitions", "Regime analysis tables used in Section 2"),
        ("src/tsx_pipeline/strategy_evaluation.py", "Momentum backtest, payoff analysis, bootstrap, stress tests, decision", "Evaluation tables used in Section 3"),
        ("src/tsx_pipeline/trade_design.py", "Profit, leverage, Kelly, stop and execution functions; plan assembly", "Sizing tables and trade plan used in Section 4"),
        ("src/tsx_pipeline/risk_surface.py", "Value and volatility functions, derivatives, Hessian, Taylor approximations", "Surface grids and scenarios used in Section 5"),
        ("scripts/build_deliverables.py", "Pipeline report, workbook, dashboard and charts", "Pipeline report PDF and workbook"),
        ("scripts/build_notebook.py", "Pipeline guided notebook", "live_pipeline_walkthrough.ipynb"),
        ("scripts/build_regime_deliverables.py", "Market structure report, workbook, dashboard and notebook", "Regime report PDF and workbook"),
        ("scripts/build_stage2_projects.py", "Strategy, trade and risk reports, workbooks, dashboards and notebooks", "Three report PDFs and three workbooks"),
        ("scripts/build_combined.py", "Combined report and combined workbook", "TSX_Portfolio_Combined_Report.pdf, TSX_Portfolio_Combined_Model.xlsx"),
        ("tests/test_quality.py", "Tests of validation, gaps and outlier rules", "Pipeline tests (4 across both files)"),
        ("tests/test_strategies.py", "Tests of allocation constraints and metrics", "Pipeline tests (4 across both files)"),
        ("tests/test_regimes.py", "Tests of decomposition, reconstruction and angles", "5 tests"),
        ("tests/test_strategy_evaluation.py", "Tests of expected value, break-even and payoff summaries", "3 tests"),
        ("tests/test_trade_design.py", "Tests of profit concavity, Kelly, no-edge probability and caps", "4 tests"),
        ("tests/test_risk_surface.py", "Tests of derivatives, Hessian and volatility functions", "4 tests"),
    ]
    for file_name, function_text, outputs_text in appendix_rows:
        arows.append([file_name, function_text, outputs_text])
    story.append(table_title("Python files in the project, by function and output"))
    story.append(tbl(arows, [52 * mm, 62 * mm, 56 * mm]))
    story.append(P("Data outputs are stored under data/outputs (Section 1), data/regime_outputs (Section 2), data/strategy_evaluation_outputs (Section 3), data/trade_design_outputs (Section 4) and data/risk_surface_outputs (Section 5). Cleaned price data are stored under data/clean, and raw data under data/raw. All figures reported in Sections 1 to 5 are taken from these saved outputs, so that every number in the report can be traced to a file produced by the code listed in Table 8."))

    path = REPORTS / "TSX_Portfolio_Combined_Report.pdf"
    doc = SimpleDocTemplate(str(path), pagesize=A4, leftMargin=17 * mm, rightMargin=17 * mm,
                            topMargin=13 * mm, bottomMargin=13 * mm,
                            title="Live TSX Portfolio: Combined Report", author="Munzeleen Sarwar")
    doc.build(story)
    return path

if __name__ == "__main__":
    print(build_workbook())
    print(build_report())
