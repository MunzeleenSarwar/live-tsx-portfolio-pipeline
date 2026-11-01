from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
NOTEBOOKS = ROOT / "notebooks"
SE_DIR = ROOT / "data" / "strategy_evaluation_outputs"
TD_DIR = ROOT / "data" / "trade_design_outputs"
RS_DIR = ROOT / "data" / "risk_surface_outputs"
SE_CHARTS = ROOT / "charts" / "strategy_evaluation"
TD_CHARTS = ROOT / "charts" / "trade_design"
RS_CHARTS = ROOT / "charts" / "risk_surface"
for folder in [REPORTS, NOTEBOOKS, SE_CHARTS, TD_CHARTS, RS_CHARTS]:
    folder.mkdir(parents=True, exist_ok=True)

SE = json.loads((SE_DIR / "strategy_summary.json").read_text())
TD = json.loads((TD_DIR / "trade_plan.json").read_text())
RS = json.loads((RS_DIR / "risk_surface_summary.json").read_text())
SE_MONTHLY = pd.read_csv(SE_DIR / "monthly_strategy_returns.csv", parse_dates=["formation_date", "holding_date"])
SE_LOTS = pd.read_csv(SE_DIR / "trade_lots.csv", parse_dates=["formation_date", "holding_date"])
SE_PAYOFF = pd.read_csv(SE_DIR / "payoff_summary.csv").iloc[0]
SE_METRICS = pd.read_csv(SE_DIR / "performance_metrics.csv")
SE_BOOT = pd.read_csv(SE_DIR / "bootstrap_iid.csv")
SE_STRESS = pd.read_csv(SE_DIR / "stress_tests.csv")
SE_CRITERIA = pd.read_csv(SE_DIR / "decision_criteria.csv")
SE_EV = pd.read_csv(SE_DIR / "ev_sensitivity.csv")
SE_PLACEBO = pd.read_csv(SE_DIR / "placebo_random_selection.csv")
TD_PROFIT = pd.read_csv(TD_DIR / "profit_by_size.csv")
TD_LEV = pd.read_csv(TD_DIR / "leverage_analysis.csv")
TD_KELLY = pd.read_csv(TD_DIR / "kelly_analysis.csv")
TD_STOP = pd.read_csv(TD_DIR / "stoploss_analysis.csv")
TD_EXEC = pd.read_csv(TD_DIR / "execution_analysis.csv")
TD_CNQ = pd.read_csv(TD_DIR / "cnq_payoff_summary.csv").iloc[0]
RS_DIRECTIONS = pd.read_csv(RS_DIR / "direction_scenarios.csv")
RS_CORR = pd.read_csv(RS_DIR / "correlation_scenarios.csv")
RS_TAYLOR = pd.read_csv(RS_DIR / "taylor_risk_approximations.csv")
RS_VALUE_GRID = pd.read_csv(RS_DIR / "value_surface_grid.csv")
RS_RISK_GRID = pd.read_csv(RS_DIR / "risk_surface_grid.csv")

NAVY = "#12395B"
TEAL = "#2A7F62"
RUST = "#C05621"
GREY = "#666666"


def pct(x, digits=1):
    if pd.isna(x):
        return "NA"
    if abs(x) < 0.000005:
        x = 0.0
    return f"{x * 100:.{digits}f}%"


def money(x):
    return f"${x:,.0f}"


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


def add_sheet(wb, title, frame, widths, first=False):
    ws = wb.active if first else wb.create_sheet()
    ws.title = title
    ws.append(list(frame.columns))
    for row in frame.itertuples(index=False):
        ws.append(list(row))
    style_sheet(ws, widths)
    return ws


def add_notes_sheet(wb, title, rows, first=False):
    ws = wb.active if first else wb.create_sheet()
    ws.title = title
    ws.append(["Item", "Detail"])
    for key, value in rows:
        ws.append([key, value])
    style_sheet(ws, [34, 118])
    for row in ws.iter_rows(min_row=2, max_col=2):
        row[1].alignment = Alignment(wrap_text=True, vertical="top")
    return ws


# ---------------------------------------------------------------- strategy charts

def strategy_charts():
    monthly = SE_MONTHLY.sort_values("holding_date")
    growth = pd.DataFrame({
        "Momentum": (1 + monthly["net_return"]).cumprod().to_numpy() * 100,
        "TSX benchmark": (1 + monthly["benchmark_return"]).cumprod().to_numpy() * 100,
        "Equal weight": (1 + monthly["equal_weight_return"]).cumprod().to_numpy() * 100,
    }, index=monthly["holding_date"].to_numpy())
    fig, ax = plt.subplots(figsize=(10, 4.8))
    growth.plot(ax=ax, color=[NAVY, GREY, TEAL], linewidth=1.8)
    ax.set_title("Growth of $100, monthly momentum strategy, Aug 2017 to Oct 2026")
    ax.set_ylabel("Value of $100"); ax.set_xlabel("")
    ax.grid(alpha=0.25); ax.legend(frameon=False)
    fig.tight_layout(); fig.savefig(SE_CHARTS / "growth.png", dpi=180); plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 4.4))
    ax.hist(SE_BOOT["annualised_return"] * 100, bins=40, color=NAVY, alpha=0.85)
    ax.axvline(SE["strategy_metrics"]["annualised_return"] * 100, color=RUST, linewidth=2, label="Observed")
    ax.axvline(SE["benchmark_metrics"]["annualised_return"] * 100, color=TEAL, linewidth=2, label="Benchmark actual")
    ax.set_title("Bootstrap distribution of annualised return, 10,000 resampled paths")
    ax.set_xlabel("Annualised return (%)"); ax.legend(frameon=False); ax.grid(alpha=0.25)
    fig.tight_layout(); fig.savefig(SE_CHARTS / "bootstrap.png", dpi=180); plt.close(fig)

    pivot = SE_EV.pivot(index="win_probability", columns="reward_risk", values="expected_value_R")
    fig, ax = plt.subplots(figsize=(8.5, 5.2))
    im = ax.imshow(pivot.values, cmap="RdYlGn", aspect="auto")
    ax.set_xticks(range(len(pivot.columns)), [f"{c:.2f}" for c in pivot.columns])
    ax.set_yticks(range(len(pivot.index)), [f"{i:.2f}" for i in pivot.index])
    ax.set_xlabel("Reward-risk ratio"); ax.set_ylabel("Win probability")
    ax.set_title("Expected value in R: win probability against payoff")
    for i in range(pivot.shape[0]):
        for j in range(pivot.shape[1]):
            ax.text(j, i, f"{pivot.values[i, j]:+.2f}", ha="center", va="center", fontsize=8)
    fig.colorbar(im, ax=ax, shrink=0.85)
    fig.tight_layout(); fig.savefig(SE_CHARTS / "ev_heatmap.png", dpi=180); plt.close(fig)

    stress = SE_STRESS.copy()
    fig, ax = plt.subplots(figsize=(10, 4.8))
    x = np.arange(len(stress))
    ax.bar(x - 0.2, stress["annualised_return"] * 100, width=0.4, color=NAVY, label="Annualised return %")
    ax.bar(x + 0.2, -stress["max_drawdown"] * 100, width=0.4, color=RUST, label="Maximum drawdown %")
    ax.set_xticks(x, [s.replace(", ", "\n") for s in stress["scenario"]], fontsize=7.5, rotation=25, ha="left")
    ax.set_title("Stress tests: return falls and drawdown deepens under adverse changes")
    ax.legend(frameon=False); ax.grid(axis="y", alpha=0.25)
    fig.tight_layout(); fig.savefig(SE_CHARTS / "stress.png", dpi=180); plt.close(fig)


# ---------------------------------------------------------------- trade charts

def trade_charts():
    fig, ax = plt.subplots(figsize=(10, 4.8))
    ax.plot(TD_PROFIT["quantity"], TD_PROFIT["expected_profit"] / 1000, color=NAVY, linewidth=2)
    ax.axvline(TD["final_quantity"], color=RUST, linestyle="--",
               label=f"Final size {TD['final_quantity']:,} shares (20% cap)")
    ax.axvline(TD["optimal_quantity_risk_adjusted"], color=TEAL, linestyle=":",
               label=f"Risk-adjusted optimum {TD['optimal_quantity_risk_adjusted']:,.0f}")
    ax.set_title("Expected profit by trade size, after quadratic market impact")
    ax.set_xlabel("Shares"); ax.set_ylabel("Expected profit ($000)")
    ax.grid(alpha=0.25); ax.legend(frameon=False)
    fig.tight_layout(); fig.savefig(TD_CHARTS / "profit_by_size.png", dpi=180); plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 4.4))
    ax.plot(TD_LEV["leverage"], TD_LEV["risk_adjusted_return"] * 100, color=NAVY, linewidth=2)
    ax.axvline(TD["optimal_leverage_risk_adjusted"], color=RUST, linestyle="--",
               label=f"Optimum {TD['optimal_leverage_risk_adjusted']:.2f}x")
    ax.axvline(1.0, color=GREY, linestyle=":", label="No leverage")
    ax.set_title("Risk-adjusted return on capital by position leverage")
    ax.set_xlabel("Position value / capital"); ax.set_ylabel("Certainty-equivalent return (%)")
    ax.grid(alpha=0.25); ax.legend(frameon=False)
    fig.tight_layout(); fig.savefig(TD_CHARTS / "leverage.png", dpi=180); plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 4.2))
    levels = [("Target", TD["target_price"], TEAL), ("Entry", TD["entry_price"], NAVY),
              ("Stop", TD["stop_price"], RUST)]
    for i, (label, price, colour) in enumerate(levels):
        ax.barh(i, price, color=colour, alpha=0.85)
        ax.text(price + 1, i, f"{label} ${price:,.2f}", va="center", fontsize=10)
    ax.set_yticks([])
    ax.set_xlim(60, 95)
    ax.set_title("CNQ trade levels: stop at 2 x ATR, target at 3 x ATR")
    ax.set_xlabel("Price ($)")
    fig.tight_layout(); fig.savefig(TD_CHARTS / "trade_levels.png", dpi=180); plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 4.4))
    ax.plot(TD_EXEC["horizon_days"], TD_EXEC["impact_bps"], marker="o", color=TEAL, label="Market impact")
    ax.plot(TD_EXEC["horizon_days"], TD_EXEC["timing_risk_allowance_bps"], marker="o", color=RUST,
            label="Timing risk allowance")
    ax.plot(TD_EXEC["horizon_days"], TD_EXEC["total_planning_cost_bps"], marker="o", color=NAVY,
            label="Total planning cost")
    ax.set_xscale("log")
    ax.set_title("Execution cost by horizon: waiting costs more than impact at this size")
    ax.set_xlabel("Execution horizon, days (log scale)"); ax.set_ylabel("Basis points")
    ax.grid(alpha=0.25); ax.legend(frameon=False)
    fig.tight_layout(); fig.savefig(TD_CHARTS / "execution.png", dpi=180); plt.close(fig)


# ---------------------------------------------------------------- risk surface charts

def risk_charts():
    value_pivot = RS_VALUE_GRID.pivot(index="shock_b", columns="shock_a", values="portfolio_value")
    X, Y = np.meshgrid(value_pivot.columns.values, value_pivot.index.values)
    fig = plt.figure(figsize=(10, 5.6))
    ax = fig.add_subplot(111, projection="3d")
    ax.plot_surface(X * 100, Y * 100, value_pivot.values, cmap="viridis", linewidth=0, antialiased=True)
    ax.set_xlabel("ENB shock (%)"); ax.set_ylabel("TD shock (%)"); ax.set_zlabel("Portfolio value ($)")
    ax.set_title("Portfolio value surface, ENB and TD price shocks")
    fig.tight_layout(); fig.savefig(RS_CHARTS / "value_surface.png", dpi=160); plt.close(fig)

    risk_pivot = RS_RISK_GRID.pivot(index="correlation", columns="weight_a", values="portfolio_volatility")
    X, Y = np.meshgrid(risk_pivot.columns.values, risk_pivot.index.values)
    fig = plt.figure(figsize=(10, 5.6))
    ax = fig.add_subplot(111, projection="3d")
    ax.plot_surface(X, Y, risk_pivot.values * 100, cmap="plasma", linewidth=0, antialiased=True)
    ax.set_xlabel("Weight in ENB"); ax.set_ylabel("Correlation"); ax.set_zlabel("Volatility (%)")
    ax.set_title("Portfolio risk surface: weight in ENB against correlation")
    fig.tight_layout(); fig.savefig(RS_CHARTS / "risk_surface.png", dpi=160); plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 4.6))
    ax.plot(RS_CORR["correlation"], RS_CORR["minimum_volatility"] * 100, marker="o", color=NAVY,
            label="Minimum possible volatility")
    ax.plot(RS_CORR["correlation"], RS_CORR["equal_weight_volatility"] * 100, marker="o", color=GREY,
            linestyle="--", label="50/50 volatility")
    ax.set_title("Correlation changes the level of risk far more than the safest weight")
    ax.set_xlabel("ENB and TD correlation"); ax.set_ylabel("Annualised volatility (%)")
    ax.grid(alpha=0.25); ax.legend(frameon=False)
    fig.tight_layout(); fig.savefig(RS_CHARTS / "correlation_scenarios.png", dpi=180); plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 4.6))
    labels = [f"dw {r.delta_weight_a:+.2f}\ndrho {r.delta_correlation:+.2f}" for r in RS_TAYLOR.itertuples(index=False)]
    x = np.arange(len(labels))
    ax.bar(x - 0.2, np.abs(RS_TAYLOR["first_order_error"]) * 100, width=0.4, color=NAVY, label="First-order error")
    ax.bar(x + 0.2, np.abs(RS_TAYLOR["second_order_error"]) * 100, width=0.4, color=TEAL, label="Second-order error")
    ax.set_xticks(x, labels, fontsize=8)
    ax.set_title("Taylor approximation error for volatility, percentage points")
    ax.set_ylabel("Absolute error (pp)"); ax.grid(axis="y", alpha=0.25); ax.legend(frameon=False)
    fig.tight_layout(); fig.savefig(RS_CHARTS / "taylor_errors.png", dpi=180); plt.close(fig)


# ---------------------------------------------------------------- Excel builders

def strategy_excel() -> Path:
    wb = Workbook()
    add_notes_sheet(wb, "Summary", [
        ("Project", "Is This Trading Strategy Actually Profitable?"),
        ("Strategy", "Monthly 12-1 momentum: rank the ten TSX stocks on the return from 13 months ago to 1 month ago, hold the top 3 in equal weight for one month"),
        ("Sample", f"{SE['months']} months, {SE['evaluation_start'][:10]} to {SE['evaluation_end'][:10]}, after 10 bps transaction costs on turnover"),
        ("Decision", SE["decision"]),
        ("Why", "Positive expected value, a t-statistic above 2 and a high bootstrap win probability were not enough. The strategy Sharpe ratio is below the equal-weight universe, maximum drawdown breaches the 25% limit, and the ten stocks were selected in 2026 rather than from a point-in-time universe."),
        ("Annualised return", pct(SE["strategy_metrics"]["annualised_return"])),
        ("Sharpe", f"{SE['strategy_metrics']['sharpe']:.2f}"),
        ("Maximum drawdown", pct(SE["strategy_metrics"]["max_drawdown"])),
        ("Current picks", ", ".join(SE["current_picks"])),
    ], first=True)
    add_sheet(wb, "Performance", SE_METRICS, [16, 10, 16, 18, 20, 12, 14, 14, 14, 14, 16])
    add_sheet(wb, "Payoff", pd.DataFrame([SE_PAYOFF]), [10, 18, 14, 14, 14, 18, 24, 24, 24])
    monthly = SE_MONTHLY.copy()
    monthly["formation_date"] = monthly["formation_date"].dt.date
    monthly["holding_date"] = monthly["holding_date"].dt.date
    add_sheet(wb, "Monthly Returns", monthly, [14, 14, 34, 14, 12, 10, 14, 18, 20])
    lots = SE_LOTS.copy()
    lots["formation_date"] = lots["formation_date"].dt.date
    lots["holding_date"] = lots["holding_date"].dt.date
    add_sheet(wb, "Trade Lots", lots, [14, 14, 12, 14])
    boot = pd.DataFrame([{
        "iid_probability_profitable": SE["bootstrap_summary"]["iid_probability_profitable"],
        "iid_probability_beats_benchmark": SE["bootstrap_summary"]["iid_probability_beats_benchmark"],
        "iid_median_annualised_return": SE["bootstrap_summary"]["iid_median_annualised_return"],
        "iid_p05_annualised_return": SE["bootstrap_summary"]["iid_p05_annualised_return"],
        "iid_p95_annualised_return": SE["bootstrap_summary"]["iid_p95_annualised_return"],
        "block_probability_profitable": SE["bootstrap_summary"]["block_probability_profitable"],
        "block_probability_beats_benchmark": SE["bootstrap_summary"]["block_probability_beats_benchmark"],
        "block_median_annualised_return": SE["bootstrap_summary"]["block_median_annualised_return"],
    }])
    add_sheet(wb, "Bootstrap Summary", boot, [24, 28, 26, 24, 24, 26, 30, 26])
    add_sheet(wb, "Stress Tests", SE_STRESS, [38, 10, 16, 18, 20, 12, 14, 14, 14, 14, 16])
    add_sheet(wb, "Decision Criteria", SE_CRITERIA, [58, 14, 14, 10])
    add_sheet(wb, "EV Sensitivity", SE_EV, [18, 14, 18, 24, 24])
    placebo = pd.DataFrame([SE["placebo_summary"]])
    add_sheet(wb, "Placebo Summary", placebo, [12, 30, 26, 30, 20])
    add_notes_sheet(wb, "Method", [
        ("Momentum score", "Price 1 month ago divided by price 13 months ago, minus 1, at each month-end formation date. The most recent month is skipped."),
        ("Costs", "10 bps charged on turnover, defined as the sum of absolute weight changes. Initial entry counts as turnover of 1."),
        ("Trade lots", "Each selected stock held for one month is one lot: 111 months times 3 stocks equals 333 lots."),
        ("Bootstrap", "10,000 paths resampling the 111 monthly net returns with replacement, plus a 6-month block bootstrap."),
        ("Placebo", "500 trials selecting 3 random stocks each month under the same cost rule. Random selection in the same universe reached a median annualised return near 19.6%, which shows the universe itself did much of the work."),
        ("Main limitation", "The ten-stock universe was chosen in 2026 for a different project. It is not a point-in-time TSX universe, so selection and survivorship bias are built into every statistic."),
    ])
    path = REPORTS / "TSX_Strategy_Evaluation_Model.xlsx"
    wb.save(path)
    return path


def trade_excel() -> Path:
    wb = Workbook()
    plan = pd.DataFrame([{k: v for k, v in TD.items()}])
    add_notes_sheet(wb, "Summary", [
        ("Project", "Designing an Optimal Trade"),
        ("Trade", "Long Canadian Natural Resources (CNQ), rank 1 on 12-1 momentum at 30 Oct 2026"),
        ("Account assumption", "Hypothetical $1,000,000 trading account. This is a design exercise, not a recommendation."),
        ("Entry", money(TD["entry_price"])), ("Stop", money(TD["stop_price"])),
        ("Target", money(TD["target_price"])),
        ("Final size", f"{TD['final_quantity']:,} shares, {money(TD['position_value'])} (20% position cap binds)"),
        ("Risk at stop", f"{money(TD['dollar_risk_at_stop'])} ({pct(TD['risk_pct_of_capital'], 2)} of capital)"),
        ("Expected profit", f"{money(TD['expected_profit_after_costs'])} under the scenario win probability"),
        ("Decision link", "The companion strategy evaluation returns DO NOT TRADE for live capital. This plan is for paper trading and study."),
    ], first=True)
    add_sheet(wb, "Trade Plan", plan, [38, 30])
    add_sheet(wb, "Profit by Size", TD_PROFIT, [14, 16, 18, 26, 16])
    add_sheet(wb, "Leverage", TD_LEV, [12, 16, 24, 26, 22])
    add_sheet(wb, "Kelly", TD_KELLY, [16, 16, 22, 26])
    add_sheet(wb, "Stop Loss", TD_STOP, [18, 12, 13, 15, 16, 18, 19, 13, 24, 24, 24])
    add_sheet(wb, "Execution", TD_EXEC, [14, 22, 13, 26, 24])
    add_sheet(wb, "CNQ Payoff", pd.DataFrame([TD_CNQ]), [10, 18, 14, 14, 14, 18, 24, 24, 24])
    add_notes_sheet(wb, "Method", [
        ("Stop and target", "Stop at entry minus 2 times the 14-day average true range. Target at 1.5 times the stop distance, giving a reward-risk ratio of 1.5."),
        ("Win probability scenario", "56.2%, the win rate across all 333 momentum trade lots. It is a planning scenario for this stop design, not a measured probability of this exact trade."),
        ("Profit function", "Expected profit equals quantity times entry times expected return, minus entry times 0.25 times quantity squared divided by 20-day average daily volume, a stylised quadratic impact cost."),
        ("Risk penalty", "Certainty-equivalent return subtracts half of risk aversion (10) times the squared capital volatility. The optimum position leverage is 0.34 times capital before caps."),
        ("Kelly warning", "The Kelly figure is a fraction of capital to risk, not a position weight. Full Kelly implies risking 26.9% of capital and a position above 500% of capital once the stop distance is applied. It is rejected."),
        ("Caps", "Position at most 20% of capital. Loss at the stop at most 1% of capital. No leverage."),
    ])
    path = REPORTS / "TSX_Optimal_Trade_Design_Model.xlsx"
    wb.save(path)
    return path


def risk_excel() -> Path:
    wb = Workbook()
    add_notes_sheet(wb, "Summary", [
        ("Project", "Exploring a Portfolio Risk Surface"),
        ("Assets", "Enbridge (ENB) and TD Bank (TD), last 252 trading days of daily returns"),
        ("Capital example", money(RS["capital"])),
        ("Volatilities", f"ENB {pct(RS['vol_a'])}, TD {pct(RS['vol_b'])}"),
        ("Correlation", f"{RS['correlation']:.3f}"),
        ("Minimum-volatility mix", f"ENB {pct(RS['base_weight_a'])}, TD {pct(1 - RS['base_weight_a'])}"),
        ("Minimum volatility", pct(RS["base_volatility"])),
        ("Risk gradient", f"Weight direction {RS['risk_gradient'][0]:.4f} (zero at the safest weight), correlation direction {RS['risk_gradient'][1]:.4f}"),
        ("Hessian", RS["risk_hessian_classification"]),
        ("Main finding", "Correlation moves the level of portfolio risk far more than it moves the safest weight, because the two volatilities are close. Minimum volatility rises from 8.6% at correlation -0.5 to 16.8% at correlation 0.9, while the safest ENB weight moves only from 49.4% to 40.6%."),
    ], first=True)
    add_sheet(wb, "Value Surface", RS_VALUE_GRID, [12, 12, 12, 12, 18, 14, 12])
    add_sheet(wb, "Risk Surface", RS_RISK_GRID, [12, 14, 22])
    add_sheet(wb, "Direction Scenarios", RS_DIRECTIONS, [32, 10, 10, 14, 14, 30, 16])
    add_sheet(wb, "Correlation Scenarios", RS_CORR, [14, 28, 22, 24])
    add_sheet(wb, "Taylor Approximations", RS_TAYLOR, [16, 18, 14, 16, 18, 22, 24, 18, 20])
    add_notes_sheet(wb, "Method", [
        ("Value surface", "Portfolio value over a grid of ENB and TD percentage price shocks, using the minimum-volatility share counts on $100,000."),
        ("Partial derivatives of value", "The derivative of value with respect to each price is the share count. In shock-fraction terms the gradient is the two dollar allocations."),
        ("Risk surface", "Annualised portfolio volatility as a function of the ENB weight and the ENB-TD correlation, holding the two asset volatilities at their 252-day values."),
        ("Hessian", "Computed by finite differences on the volatility function. One eigenvalue is positive and one is negative at the base point, so the joint surface is a saddle: bowl-shaped along weight, cap-shaped along correlation."),
        ("Taylor use", "First and second order approximations are local. Errors grow when the correlation change is large."),
    ])
    path = REPORTS / "TSX_Portfolio_Risk_Surface_Model.xlsx"
    wb.save(path)
    return path


# ---------------------------------------------------------------- dashboards

def dashboard(path: Path, title: str, subtitle: str, cards: list[tuple[str, str]],
              chart_folder: str, chart_files: list[str], table_html: str, note: str) -> Path:
    card_html = "".join(
        f"<div class='card'><div class='label'>{label}</div><div class='value'>{value}</div></div>"
        for label, value in cards)
    images = "".join(
        f"<img src='../charts/{chart_folder}/{name}' alt='{name}'>" for name in chart_files)
    html = f"""<!doctype html><html lang='en'><head><meta charset='utf-8'>
<title>{title}</title><style>
body{{font-family:Arial,sans-serif;margin:32px;color:#111;background:#fff;max-width:1180px}}
h1{{font-size:28px;margin-bottom:4px}} .sub{{color:#555;margin-bottom:20px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin:18px 0}}
.card{{border:1px solid #ddd;border-radius:8px;padding:14px}} .label{{color:#666;font-size:12px;text-transform:uppercase}}
.value{{font-size:22px;font-weight:700;margin-top:5px}} img{{max-width:100%;border:1px solid #e2e2e2;border-radius:8px;margin:10px 0}}
table{{border-collapse:collapse;width:100%;margin:14px 0}} th,td{{border:1px solid #ccc;padding:6px 8px;text-align:left;font-size:13px}}
th{{background:#12395B;color:#fff}} .note{{background:#f4f4f4;border-radius:8px;padding:14px;line-height:1.5}}
</style></head><body><h1>{title}</h1><div class='sub'>{subtitle}</div>
<div class='grid'>{card_html}</div>{images}{table_html}<div class='note'>{note}</div></body></html>"""
    path.write_text(html, encoding="utf-8")
    return path


def table_html(frame: pd.DataFrame) -> str:
    return frame.to_html(index=False, border=0)


def build_dashboards():
    sm = SE["strategy_metrics"]
    p1 = dashboard(
        REPORTS / "strategy_evaluation_dashboard.html",
        "Is This Trading Strategy Actually Profitable?",
        "Monthly 12-1 momentum, top 3 of 10 TSX stocks, Aug 2017 to Oct 2026, 10 bps costs",
        [("Decision", SE["decision"]), ("Annualised return", pct(sm["annualised_return"])),
         ("Sharpe", f"{sm['sharpe']:.2f}"), ("t-statistic", f"{sm['t_statistic']:.2f}"),
         ("Max drawdown", pct(sm["max_drawdown"])), ("Expected value", f"+{SE_PAYOFF['expected_value_R']:.2f}R")],
        "strategy_evaluation", ["growth.png", "bootstrap.png", "ev_heatmap.png", "stress.png"],
        table_html(SE_CRITERIA.assign(value=SE_CRITERIA["value"].round(3), hurdle=SE_CRITERIA["hurdle"].round(3))),
        "The strategy was profitable in this sample and beat the benchmark in most bootstrap paths. It still fails the decision rule: its Sharpe ratio is below simply holding the same ten stocks in equal weight, its drawdown breaches the 25% limit, and the stock universe was selected in 2026, so the test is not point-in-time. Verdict: research and paper trading only.")
    p2 = dashboard(
        REPORTS / "trade_design_dashboard.html",
        "Designing an Optimal Trade: Long CNQ",
        "Single-variable calculus applied to size, leverage, stop placement and execution, 30 Oct 2026",
        [("Entry", money(TD["entry_price"])), ("Stop", money(TD["stop_price"])),
         ("Target", money(TD["target_price"])), ("Final size", f"{TD['final_quantity']:,} shares"),
         ("Risk at stop", money(TD["dollar_risk_at_stop"])), ("Expected profit", money(TD["expected_profit_after_costs"]))],
        "trade_design", ["profit_by_size.png", "leverage.png", "trade_levels.png", "execution.png"],
        table_html(TD_STOP[["stop_atr_multiple", "stop_price", "target_price", "dollar_risk_at_quantity"]].round(2)),
        "The impact-only optimum is more than 300,000 shares, which shows that market impact cannot size a trade on a liquid stock. A risk penalty lowers the optimum to about 4,300 shares, and the 20% position cap sets the final size at 2,551 shares. Full Kelly is rejected: it would risk 26.9% of capital. The companion strategy evaluation says DO NOT TRADE with live capital, so this plan is a paper-trade design.")
    p3 = dashboard(
        REPORTS / "risk_surface_dashboard.html",
        "Exploring a Portfolio Risk Surface: ENB and TD",
        "Multivariable calculus on portfolio value and volatility, last 252 trading days",
        [("ENB volatility", pct(RS["vol_a"])), ("TD volatility", pct(RS["vol_b"])),
         ("Correlation", f"{RS['correlation']:.3f}"), ("Safest ENB weight", pct(RS["base_weight_a"])),
         ("Minimum volatility", pct(RS["base_volatility"])), ("Surface shape", "Saddle in weight and correlation")],
        "risk_surface", ["value_surface.png", "risk_surface.png", "correlation_scenarios.png", "taylor_errors.png"],
        table_html(RS_DIRECTIONS[["scenario", "exact_pnl", "exact_pnl_pct"]].round(2)),
        "Portfolio value is linear in the two prices, so first-order approximations are exact and its Hessian is zero. Volatility is not linear. At the safest weight its gradient in the weight direction is zero, correlation raises risk, and the Hessian is indefinite, which makes the joint surface a saddle. Correlation changes the level of risk far more than the safest weight for this pair.")
    return [p1, p2, p3]


# ---------------------------------------------------------------- notebooks

def build_notebooks():
    import nbformat as nbf

    def make(filename, cells):
        nb = nbf.v4.new_notebook()
        nb.metadata = {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                       "language_info": {"name": "python", "version": "3.12"}}
        nb.cells = cells
        path = NOTEBOOKS / filename
        nbf.write(nb, path)
        return path

    loader = """from pathlib import Path
import json
import pandas as pd

ROOT = Path.cwd()
if not (ROOT / 'data').exists():
    ROOT = ROOT.parent
"""
    p1 = make("strategy_evaluation_walkthrough.ipynb", [
        nbf.v4.new_markdown_cell(f"""# Is This Trading Strategy Actually Profitable?

Monthly 12-1 momentum on ten TSX stocks: **{SE['months']} months**, annualised return **{pct(SE['strategy_metrics']['annualised_return'])}**, t-statistic **{SE['strategy_metrics']['t_statistic']:.2f}**, decision **{SE['decision']}**.

Profitable in sample is not the same as worth trading. This notebook walks through the full test."""),
        nbf.v4.new_markdown_cell("## 1. Load the saved outputs"),
        nbf.v4.new_code_cell(loader + """DATA = ROOT / 'data' / 'strategy_evaluation_outputs'
summary = json.loads((DATA / 'strategy_summary.json').read_text())
monthly = pd.read_csv(DATA / 'monthly_strategy_returns.csv', parse_dates=['holding_date'])
lots = pd.read_csv(DATA / 'trade_lots.csv')
summary['decision']"""),
        nbf.v4.new_markdown_cell("## 2. Expected value comes before returns\n\nA trade can win less than half the time and still be profitable if wins are larger than losses. The 333 trade lots give the payoff table."),
        nbf.v4.new_code_cell("""payoff = pd.read_csv(DATA / 'payoff_summary.csv')
payoff"""),
        nbf.v4.new_markdown_cell("## 3. Portfolio results and the equal-weight problem\n\nThe strategy beat the index. The harder test is the same ten stocks held in equal weight, which had a higher Sharpe ratio and a smaller drawdown."),
        nbf.v4.new_code_cell("""pd.read_csv(DATA / 'performance_metrics.csv')"""),
        nbf.v4.new_markdown_cell("## 4. Monte Carlo and the placebo\n\nBootstrap paths resample the realised months. The placebo selects random stocks each month in the same universe. Random selection did well too, which points to universe selection, not only to momentum skill."),
        nbf.v4.new_code_cell("""boot = pd.read_csv(DATA / 'bootstrap_summary.csv')
placebo = pd.read_csv(DATA / 'placebo_summary.csv')
boot, placebo"""),
        nbf.v4.new_markdown_cell("## 5. Stress tests and the decision"),
        nbf.v4.new_code_cell("""stress = pd.read_csv(DATA / 'stress_tests.csv')
criteria = pd.read_csv(DATA / 'decision_criteria.csv')
stress[['scenario', 'annualised_return', 'sharpe', 'max_drawdown']], criteria"""),
        nbf.v4.new_markdown_cell("## Conclusion\n\nThe strategy passes the profitability tests and fails the risk and data-integrity tests. DO NOT TRADE with live capital. Keep it as a research strategy and a paper-trading candidate."),
    ])
    p2 = make("trade_design_walkthrough.ipynb", [
        nbf.v4.new_markdown_cell(f"""# Designing an Optimal Trade

A long trade in CNQ, the rank 1 momentum stock on 30 Oct 2026, designed for a hypothetical $1,000,000 account.

Final plan: **{TD['final_quantity']:,} shares** at **{money(TD['entry_price'])}**, stop **{money(TD['stop_price'])}**, target **{money(TD['target_price'])}**, risk at stop **{money(TD['dollar_risk_at_stop'])}**."""),
        nbf.v4.new_markdown_cell("## 1. Load the plan"),
        nbf.v4.new_code_cell(loader + """DATA = ROOT / 'data' / 'trade_design_outputs'
plan = json.loads((DATA / 'trade_plan.json').read_text())
plan"""),
        nbf.v4.new_markdown_cell("## 2. Profit as a function of size\n\nGross expected profit rises in a straight line with size. The quadratic impact cost bends it down. On a stock this liquid the impact-only optimum is unrealistically large, which is itself the lesson."),
        nbf.v4.new_code_cell("""pd.read_csv(DATA / 'profit_by_size.csv')"""),
        nbf.v4.new_markdown_cell("## 3. Leverage and the risk penalty\n\nAdding a variance penalty gives an interior optimum near 0.34 times capital. Raw Kelly is shown only to be rejected."),
        nbf.v4.new_code_cell("""lev = pd.read_csv(DATA / 'leverage_analysis.csv')
kelly = pd.read_csv(DATA / 'kelly_analysis.csv')
lev.iloc[::5], kelly"""),
        nbf.v4.new_markdown_cell("## 4. Stop placement\n\nUnder a driftless random walk, the probability of reaching the target before the stop depends only on the two distances. With a 1.5 reward-risk ratio the no-edge win probability is 40%, which is also the break-even probability."),
        nbf.v4.new_code_cell("""pd.read_csv(DATA / 'stoploss_analysis.csv')"""),
        nbf.v4.new_markdown_cell("## 5. Execution speed\n\nAt 2,551 shares the order is about 0.03% of one day's volume. Impact is below 1 bp even in a single day, while the timing risk of waiting grows with the square root of time. Execute within one day."),
        nbf.v4.new_code_cell("""pd.read_csv(DATA / 'execution_analysis.csv')"""),
        nbf.v4.new_markdown_cell("## Conclusion\n\nThe 20% position cap binds and sets the size. The design is internally consistent, and the companion evaluation still limits it to paper trading."),
    ])
    p3 = make("risk_surface_walkthrough.ipynb", [
        nbf.v4.new_markdown_cell(f"""# Exploring a Portfolio Risk Surface

Enbridge and TD over the last 252 trading days. Volatilities **{pct(RS['vol_a'])}** and **{pct(RS['vol_b'])}**, correlation **{RS['correlation']:.3f}**, safest mix **{pct(RS['base_weight_a'])} ENB** with volatility **{pct(RS['base_volatility'])}**."""),
        nbf.v4.new_markdown_cell("## 1. Load the summary"),
        nbf.v4.new_code_cell(loader + """DATA = ROOT / 'data' / 'risk_surface_outputs'
summary = json.loads((DATA / 'risk_surface_summary.json').read_text())
summary"""),
        nbf.v4.new_markdown_cell("## 2. The two surfaces\n\nValue is a plane in the two prices. Volatility is a curved surface in weight and correlation. The grid files hold both."),
        nbf.v4.new_code_cell("""value = pd.read_csv(DATA / 'value_surface_grid.csv')
risk = pd.read_csv(DATA / 'risk_surface_grid.csv')
value.shape, risk.shape"""),
        nbf.v4.new_markdown_cell("## 3. Directional moves\n\nA directional derivative prices a combined move in one step. For value it is exact, because value is linear. Note the near-offset when ENB falls 10% and TD rises 10%."),
        nbf.v4.new_code_cell("""pd.read_csv(DATA / 'direction_scenarios.csv')"""),
        nbf.v4.new_markdown_cell("## 4. Correlation scenarios\n\nThe safest weight barely moves with correlation. The level of risk moves a lot."),
        nbf.v4.new_code_cell("""pd.read_csv(DATA / 'correlation_scenarios.csv')"""),
        nbf.v4.new_markdown_cell("## 5. Taylor approximations\n\nFirst order is the tangent plane. Second order adds curvature from the Hessian. Both are local tools: errors grow for large correlation changes."),
        nbf.v4.new_code_cell("""pd.read_csv(DATA / 'taylor_risk_approximations.csv')"""),
        nbf.v4.new_markdown_cell("## Conclusion\n\nAt the safest weight the volatility gradient in the weight direction is zero, as it must be at a minimum. The Hessian has one positive and one negative eigenvalue, so the joint surface is a saddle: bowl-shaped along weight and cap-shaped along correlation."),
    ])
    return [p1, p2, p3]


# ---------------------------------------------------------------- PDF builders

def pdf_kit():
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    styles = getSampleStyleSheet()
    s = {
        "title": ParagraphStyle("STitle", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=20, leading=24, textColor=colors.black, alignment=TA_CENTER, spaceAfter=4),
        "subtitle": ParagraphStyle("SSub", parent=styles["Normal"], fontName="Helvetica", fontSize=11, leading=14, textColor=colors.black, alignment=TA_CENTER, spaceAfter=10),
        "h1": ParagraphStyle("SH1", parent=styles["Heading1"], fontName="Helvetica-Bold", fontSize=14, leading=17, textColor=colors.black, spaceBefore=10, spaceAfter=5),
        "h2": ParagraphStyle("SH2", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=11.5, leading=14, textColor=colors.black, spaceBefore=8, spaceAfter=4),
        "body": ParagraphStyle("SBody", parent=styles["BodyText"], fontName="Helvetica", fontSize=9.5, leading=13.2, textColor=colors.black, spaceAfter=5),
        "small": ParagraphStyle("SSmall", parent=styles["BodyText"], fontName="Helvetica", fontSize=8.2, leading=10.5, textColor=colors.black, spaceAfter=4),
    }
    s["cell"] = ParagraphStyle("SCell", parent=s["body"], fontSize=8.2, leading=10.2, spaceAfter=0)
    s["cellh"] = ParagraphStyle("SCellH", parent=s["cell"], fontName="Helvetica-Bold")

    def P(text, style="body"):
        return Paragraph(text, s[style])

    def tbl(data, widths):
        wrapped = [[Paragraph(str(c), s["cellh"] if r == 0 else s["cell"]) for c in row] for r, row in enumerate(data)]
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

    def chart(folder, name, ratio=0.48, width=170):
        return Image(str(folder / name), width=width * mm, height=width * ratio * mm)

    def doc(path, title_text):
        return SimpleDocTemplate(str(path), pagesize=A4, leftMargin=17 * mm, rightMargin=17 * mm,
                                 topMargin=16 * mm, bottomMargin=16 * mm, title=title_text,
                                 author="Munzeleen Sarwar")
    return P, tbl, chart, doc, PageBreak, Spacer, mm


def strategy_report() -> Path:
    P, tbl, chart, doc, PageBreak, Spacer, mm = pdf_kit()
    sm, bm, em = SE["strategy_metrics"], SE["benchmark_metrics"], SE["equal_weight_metrics"]
    path = REPORTS / "TSX_Strategy_Evaluation_Report.pdf"
    story = [P("Is This Trading Strategy Actually Profitable?", "title"), P("Munzeleen Sarwar", "subtitle"),
             P("Monthly momentum on ten TSX stocks, August 2017 to October 2026. Data: Live TSX Portfolio Market Data Pipeline.", "small")]
    story.append(P("Executive summary", "h1"))
    story.append(P("The strategy is simple. At each month end, rank the ten stocks on 12-1 momentum, meaning the return from 13 months ago to 1 month ago. Hold the top three in equal weight for the next month. Charge 10 basis points on turnover. Over 111 months the strategy returned 27.7 percent a year, against 9.7 percent for the S&P/TSX Composite, with a t-statistic of 3.27 on the monthly mean return. By the simple tests, it was profitable."))
    story.append(P("The fuller test gives a different answer. The same ten stocks held in equal weight returned 22.7 percent a year with a higher Sharpe ratio, 1.24 against 1.00, and a smaller maximum drawdown, 19.2 percent against 28.0 percent. Randomly picking three stocks each month in the same universe also produced a median return of 19.6 percent a year. The universe, chosen in 2026 and containing the decade's winners, did much of the work. The verdict under the decision rule set for this project is DO NOT TRADE with live capital. The strategy remains a research and paper-trading candidate."))
    story.append(P("1. The strategy and the decision rule", "h1"))
    story.append(P("A decision rule has to be stated before the results, or any result can be argued into a trade. The rule used here has six tests. Expected value per trade lot must be positive. The t-statistic on monthly returns must reach 2. At least 80 percent of bootstrap paths must beat the benchmark. The Sharpe ratio must at least match the equal-weight version of the same universe. Maximum drawdown must stay within 25 percent. The universe must be point-in-time, with no selection bias. The strategy passes the first three tests and fails the last three."))
    story.append(P("2. Expected value: win rate is not the edge", "h1"))
    story.append(P("Each stock held for one month is one trade lot, so the test has 333 lots. The win rate is 56.2 percent. The average winning lot gained 9.1 percent and the average losing lot lost 6.3 percent, a reward-risk ratio of 1.46. Expected value is 0.56 times 1.46 minus 0.44, which is +0.38R per lot. The break-even win rate at this payoff is 40.7 percent, so the observed win rate sits 15.4 points above break-even. The three example setups in the QuantFrame preview make the same point in miniature: a 35 percent win rate at a 3 to 1 payoff has higher expected value than a 55 percent win rate at 1 to 1."))
    story.append(chart(SE_CHARTS, "ev_heatmap.png", ratio=0.61))
    story.append(P("The sensitivity grid also shows the limit of the edge. If the win rate falls by 10 points and the payoff falls by 20 percent at the same time, expected value is zero. The edge is real in this sample and not wide."))
    story.append(P("3. Portfolio results", "h1"))
    rows = [["Series", "Annualised return", "Volatility", "Sharpe", "t-statistic", "Max drawdown"]]
    for label, m in [("Momentum top 3", sm), ("S&P/TSX Composite", bm), ("Equal weight, same 10 stocks", em)]:
        rows.append([label, pct(m["annualised_return"]), pct(m["annualised_volatility"]), f"{m['sharpe']:.2f}",
                     f"{m['t_statistic']:.2f}", pct(m["max_drawdown"])])
    story.append(tbl(rows, [46 * mm, 30 * mm, 24 * mm, 20 * mm, 24 * mm, 26 * mm]))
    story.append(chart(SE_CHARTS, "growth.png"))
    story.append(P("The strategy made money in every calendar year of the test, which is unusual and is itself a warning sign about the sample. A rule that never has a losing year in a backtest usually reflects the universe it was tested on. Momentum also carried far more risk than the index: monthly CVaR at 95 percent was -12.7 percent, and the worst single month lost 26.0 percent."))
    story.append(PageBreak())
    story.append(P("4. Monte Carlo: what resampling can and cannot prove", "h1"))
    story.append(P("Ten thousand bootstrap paths resample the 111 realised months with replacement. In 99.8 percent of paths the strategy ends profitable, and in 96.7 percent it beats the benchmark's total return. A six-month block bootstrap, which keeps short runs of months together, gives similar results. These numbers measure how much of the result depends on the exact order and mix of the realised months. They cannot repair a biased universe, because every resampled month is drawn from the same ten selected stocks."))
    story.append(chart(SE_CHARTS, "bootstrap.png", ratio=0.44))
    story.append(P("The placebo test addresses that gap directly. Five hundred trials picked three random stocks each month under the same cost rule. The median random trial returned 19.6 percent a year. The momentum rule ranked at the 92nd percentile of random trials on total return, but only the 74th percentile on Sharpe ratio. Selection added return. It added much less risk-adjusted return."))
    story.append(P("5. Stress tests", "h1"))
    srows = [["Scenario", "Annualised return", "Sharpe", "Max drawdown"]]
    for row in SE_STRESS.itertuples(index=False):
        srows.append([row.scenario, pct(row.annualised_return), f"{row.sharpe:.2f}", pct(row.max_drawdown)])
    story.append(tbl(srows, [62 * mm, 36 * mm, 24 * mm, 48 * mm]))
    story.append(chart(SE_CHARTS, "stress.png"))
    story.append(P("Costs are not the problem: at 50 basis points the strategy still returns 25.4 percent a year. Concentration in a few strong months is a problem. Removing the best 12 months cuts the annualised return to 6.1 percent and the t-statistic to 1.16, below any reasonable significance line. Increasing the worst decile of losses by half pushes drawdown to 40.6 percent. The result depends on a small set of very good months and would look ordinary without them."))
    story.append(P("6. Decision", "h1"))
    crows = [["Test", "Value", "Hurdle", "Passed"]]
    for row in SE_CRITERIA.itertuples(index=False):
        crows.append([row.criterion, f"{row.value:.3f}", f"{row.hurdle:.3f}", "Yes" if row.passed else "No"])
    story.append(tbl(crows, [84 * mm, 26 * mm, 26 * mm, 34 * mm]))
    story.append(P("DO NOT TRADE. The strategy is profitable on paper and still fails as an investment decision, for three reasons. It does not beat the simplest use of the same universe on a risk-adjusted basis. Its drawdown exceeds the stated limit. Its test universe was selected with hindsight, so the headline statistics overstate what a trader in 2017 could have earned. The correct next step is a point-in-time test on a full TSX universe, followed by paper trading. That is a stronger conclusion than a trade signal, because it says exactly what evidence is missing."))
    story.append(P("Limitations", "h1"))
    story.append(P("Monthly rebalancing ignores intra-month price moves and assumes execution at month-end adjusted closes. Dividends and splits are handled through adjusted prices. The 10 basis point cost is a flat assumption, not a broker quote. The bootstrap treats months as exchangeable apart from the block version. None of these limits changes the verdict, because the verdict rests on the universe and the risk comparison, not on small cost differences."))
    doc(path, "Is This Trading Strategy Actually Profitable?").build(story)
    return path


def trade_report() -> Path:
    P, tbl, chart, doc, PageBreak, Spacer, mm = pdf_kit()
    path = REPORTS / "TSX_Optimal_Trade_Design_Report.pdf"
    story = [P("Designing an Optimal Trade", "title"), P("Munzeleen Sarwar", "subtitle"),
             P("A long trade in Canadian Natural Resources, designed with single-variable calculus, 30 October 2026.", "small")]
    story.append(P("Executive summary", "h1"))
    story.append(P(f"The trade is a long position in Canadian Natural Resources (CNQ), the rank 1 stock on 12-1 momentum at 30 October 2026, with a score of +56.8 percent. The account is a hypothetical $1,000,000. Entry is the adjusted close of ${TD['entry_price']:,.2f}. The stop is two times the 14-day average true range below entry, at ${TD['stop_price']:,.2f}. The target is 1.5 times the stop distance above entry, at ${TD['target_price']:,.2f}."))
    story.append(P(f"Three sizing answers come from three different questions. Market impact alone gives an optimum above 300,000 shares, which is not a usable answer. A risk penalty gives about 4,300 shares. The project's caps then bind: the final size is {TD['final_quantity']:,} shares, a position of {money(TD['position_value'])}, with {money(TD['dollar_risk_at_stop'])} at risk at the stop, or 0.96 percent of capital. The plan is internally consistent. The companion strategy evaluation still limits it to paper trading, and that limit is part of the design."))
    story.append(P("1. Framing the problem", "h1"))
    story.append(P("Designing a trade means choosing numbers before entry: size, maximum loss, target, and execution method. Each choice in this project is made by changing one variable at a time and finding where the relevant function stops improving. The inputs are the momentum payoff record from the strategy evaluation, CNQ volatility and range from the live pipeline, and stated account rules. The win probability used for planning is 56.2 percent, the win rate across all 333 momentum trade lots. It is a scenario input for this stop design, not a measured probability of this exact trade."))
    story.append(P("2. Profit as a function of trade size", "h1"))
    story.append(P("Expected gross profit is quantity times entry price times expected return, a straight line in quantity. Market impact is charged as a quadratic cost: total impact equals entry price times 0.25 times quantity squared, divided by 20-day average daily volume of 8.66 million shares. The derivative of expected profit is the per-share edge minus a term that grows with quantity. Setting it to zero gives an optimum of about 302,000 shares, worth roughly $23.7 million on a $1,000,000 account."))
    story.append(chart(TD_CHARTS, "profit_by_size.png"))
    story.append(P("That answer is mathematically correct and practically wrong. CNQ is so liquid relative to this account that impact does not bind at any sensible size. A model whose only cost is impact will always push size past every risk limit. The correct use of the calculus result is to show that impact is not the constraint here, so sizing must come from risk."))
    story.append(P("3. Leverage and the risk penalty", "h1"))
    story.append(P("Let leverage mean position value divided by capital. Expected return on capital rises in a straight line with leverage. A risk penalty equal to half of risk aversion, set at 10, times the squared capital volatility bends the function down. The optimum is where the marginal edge equals the marginal penalty, at 0.34 times capital, or about 4,300 shares. Financing cost on borrowed amounts above 1.0 times capital does not change the answer, because the optimum sits below 1."))
    story.append(chart(TD_CHARTS, "leverage.png", ratio=0.44))
    story.append(P("The Kelly criterion gives a larger and misleading number. With a 56.2 percent win probability and a 1.5 payoff, the Kelly fraction is 26.9 percent. That figure is a share of capital to risk, not a position weight. Divided by the 4.8 percent stop distance, full Kelly implies a position of about 560 percent of capital, and half Kelly about 280 percent. Both are rejected. Kelly assumes many repeated, independent bets with no gaps through the stop. A single stock trade meets none of those conditions."))
    story.append(PageBreak())
    story.append(P("4. Stop-loss placement as an optimisation problem", "h1"))
    story.append(P("The stop must sit far enough away that ordinary noise does not end the trade, and close enough that a loss stays inside the risk budget. The 14-day average true range is $1.88, or 2.4 percent of the entry price. The chosen stop is two ranges below entry. It also sits just above the 20-day moving average of $73.99, so a stop exit and a trend break happen at close to the same price."))
    story.append(chart(TD_CHARTS, "trade_levels.png", ratio=0.42))
    srows = [["ATR multiple", "Stop", "Target", "Risk at final size", "Gain at target"]]
    for row in TD_STOP.itertuples(index=False):
        srows.append([f"{row.stop_atr_multiple:.1f}", f"${row.stop_price:,.2f}", f"${row.target_price:,.2f}",
                      money(row.dollar_risk_at_quantity), money(row.dollar_gain_at_target)])
    story.append(tbl(srows, [30 * mm, 28 * mm, 28 * mm, 42 * mm, 42 * mm]))
    story.append(P("Under a driftless random walk with no costs, the probability of reaching the target before the stop is the stop distance divided by the sum of the two distances. At a 1.5 reward-risk ratio that probability is 40 percent at every ATR multiple in the table. It is also the break-even win rate. Widening the stop does not change the no-edge probability when the target widens with it. It changes the dollars at risk. Stop placement is therefore a dollar risk decision, not a way to manufacture edge. Gaps and overnight moves can carry the exit past the stop, so the dollar risk is a planning figure, not a guarantee."))
    story.append(P("5. Execution speed against slippage", "h1"))
    story.append(P("The final order of 2,551 shares is 0.03 percent of one day's volume. A square-root impact model puts the impact of a one-day execution below 0.2 basis points. The timing risk allowance, one quarter of daily volatility times the square root of the horizon, is about 40 basis points at one day and grows from there. Waiting is the expensive choice at this size. The plan is to execute within one trading day, worked as a limit order near the entry level, and not to chase the price more than one quarter of an ATR above the planned entry."))
    story.append(chart(TD_CHARTS, "execution.png", ratio=0.44))
    story.append(P("6. The final trade plan", "h1"))
    prows = [["Item", "Value"], ["Instrument", "Canadian Natural Resources (CNQ.TO), long"],
             ["Entry", f"${TD['entry_price']:,.2f}"], ["Stop", f"${TD['stop_price']:,.2f}"],
             ["Target", f"${TD['target_price']:,.2f}"], ["Size", f"{TD['final_quantity']:,} shares"],
             ["Position", f"{money(TD['position_value'])} (20.0% of capital, cap binds)"],
             ["Risk at stop", f"{money(TD['dollar_risk_at_stop'])} (0.96% of capital)"],
             ["Gain at target", money(TD["dollar_gain_at_target"])],
             ["Expected profit", f"{money(TD['expected_profit_after_costs'])} under the 56.2% win scenario"],
             ["Horizon", "20 trading days, matching the monthly momentum holding period"],
             ["Execution", "Within one trading day, limit order, no chasing beyond entry plus 0.25 ATR"],
             ["Status", "Paper trade only, per the strategy evaluation verdict"]]
    story.append(tbl(prows, [40 * mm, 130 * mm]))
    story.append(P("The design does what calculus can do: it makes each choice consistent with the others and shows which constraint actually binds. It cannot create an edge. Whether the underlying momentum rule deserves capital is a separate question, and the evaluation project answers it in the negative for now."))
    doc(path, "Designing an Optimal Trade").build(story)
    return path


def risk_report_pdf() -> Path:
    P, tbl, chart, doc, PageBreak, Spacer, mm = pdf_kit()
    path = REPORTS / "TSX_Portfolio_Risk_Surface_Report.pdf"
    story = [P("Exploring a Portfolio Risk Surface", "title"), P("Munzeleen Sarwar", "subtitle"),
             P("Enbridge and TD Bank, daily returns over the last 252 trading days to 30 October 2026.", "small")]
    story.append(P("Executive summary", "h1"))
    story.append(P(f"A two-asset portfolio has two surfaces. Value is a flat plane over the two stock prices. Risk is a curved surface over the portfolio weight and the correlation between the stocks. This project maps both for Enbridge and TD, computes their partial derivatives, gradients, directional derivatives and Hessians, and tests Taylor approximations against exact values."))
    story.append(P(f"Enbridge volatility is {pct(RS['vol_a'])} and TD volatility is {pct(RS['vol_b'])}. Their correlation over the window is close to zero at {RS['correlation']:.3f}. The minimum-volatility mix is {pct(RS['base_weight_a'])} Enbridge and {pct(1 - RS['base_weight_a'])} TD, with volatility of {pct(RS['base_volatility'])}, well below either stock alone. The main finding is that correlation changes the level of risk far more than it changes the safest weight. Minimum volatility rises from 8.6 percent at a correlation of -0.5 to 16.8 percent at 0.9, while the safest Enbridge weight moves only from 49.4 percent to 40.6 percent."))
    story.append(P("1. The mathematical object", "h1"))
    story.append(P(f"The example portfolio holds $100,000 at the minimum-volatility mix: {RS['shares_a']:,.0f} Enbridge shares worth {money(RS['allocation_a'])} and {RS['shares_b']:,.0f} TD shares worth {money(RS['allocation_b'])}. Portfolio value is the sum of shares times prices. Portfolio risk is the annualised volatility implied by the two asset volatilities, the weight, and the correlation. The estimation window is the last 252 trading days, the same features layer used by the live pipeline's risk snapshot."))
    story.append(P("2. Seeing the surfaces", "h1"))
    story.append(chart(RS_CHARTS, "value_surface.png", ratio=0.56))
    story.append(chart(RS_CHARTS, "risk_surface.png", ratio=0.56))
    story.append(P("The value surface is a plane because value is a weighted sum of two prices. The risk surface has a valley running across the correlation range. The floor of the valley is near a 49 percent Enbridge weight at every correlation shown, because the two volatilities are close. What changes with correlation is the depth of the valley."))
    story.append(PageBreak())
    story.append(P("3. Local behaviour: partial derivatives and the gradient", "h1"))
    story.append(P(f"The partial derivative of value with respect to a price is the share count: {RS['shares_a']:,.0f} dollars of value per one-dollar Enbridge move, and {RS['shares_b']:,.0f} per one-dollar TD move. In percentage shock terms, the gradient is the pair of allocations, {money(RS['allocation_a'])} and {money(RS['allocation_b'])} per unit shock. There is no interaction term. A combined move costs exactly the sum of its parts."))
    story.append(P(f"Volatility behaves differently. At the base point the partial derivative of volatility with respect to the Enbridge weight is 0.000 to four decimal places. That must be true at the minimum: the surface is flat along the valley floor. The partial derivative with respect to correlation is {RS['risk_gradient'][1]:.3f}. A correlation rise of 0.10 adds about 0.6 percentage points to volatility, locally. The gradient therefore points almost entirely in the correlation direction: for this pair, at this point, risk management is correlation management, not weight adjustment."))
    story.append(P("4. Combined market moves: directional derivatives", "h1"))
    drows = [["Scenario", "ENB shock", "TD shock", "Exact P&L", "P&L %"]]
    for row in RS_DIRECTIONS.itertuples(index=False):
        drows.append([row.scenario, pct(row.shock_a, 0), pct(row.shock_b, 0), money(row.exact_pnl), pct(row.exact_pnl_pct)])
    story.append(tbl(drows, [58 * mm, 26 * mm, 26 * mm, 32 * mm, 28 * mm]))
    story.append(P("The near-offset case is the diversification benefit in one line. Enbridge down 10 percent with TD up 10 percent changes the portfolio by only +$193, because the two allocations are close in size. Both stocks down 10 percent costs the full $10,000. Directional derivatives reproduce every figure in the table exactly, which confirms that the value function has no curvature to approximate."))
    story.append(P("5. Curvature and the Hessian", "h1"))
    story.append(P("The Hessian of the value function is the zero matrix. A plane has no curvature, and its second-order Taylor approximation is identical to its first-order one. The Hessian of volatility at the base point has eigenvalues of 0.475 and -0.030. One positive and one negative eigenvalue make the joint surface a saddle. Along the weight it is bowl-shaped, which is why a minimum exists. Along correlation it is slightly cap-shaped, because volatility is a square root of a function that is linear in correlation, and square roots are concave. Reading the two eigenvalues together prevents a common error: calling the whole surface convex because the weight slice is convex."))
    story.append(P("6. Approximating the surface: Taylor expansions", "h1"))
    trows = [["Weight change", "Correlation change", "Exact vol", "First order", "Second order", "First error", "Second error"]]
    for row in RS_TAYLOR.itertuples(index=False):
        trows.append([f"{row.delta_weight_a:+.2f}", f"{row.delta_correlation:+.2f}", pct(row.exact_volatility, 2),
                      pct(row.first_order_volatility, 2), pct(row.second_order_volatility, 2),
                      f"{row.first_order_error * 100:+.2f} pp", f"{row.second_order_error * 100:+.2f} pp"])
    story.append(tbl(trows, [26 * mm, 30 * mm, 22 * mm, 24 * mm, 26 * mm, 22 * mm, 24 * mm]))
    story.append(chart(RS_CHARTS, "taylor_errors.png", ratio=0.46))
    story.append(P("For small and moderate moves the approximations are good to a few hundredths of a percentage point. The largest error comes from the joint move of weight +0.20 and correlation -0.20, where the first-order error reaches 1.13 percentage points and the second order cuts it to 0.25. Second order is not better in every row. For the largest correlation increase it overshoots. Taylor methods are local tools, and this table shows their working range honestly."))
    story.append(P("7. Correlation scenarios and the risk report", "h1"))
    story.append(chart(RS_CHARTS, "correlation_scenarios.png", ratio=0.46))
    crows = [["Correlation", "Safest ENB weight", "Minimum volatility", "50/50 volatility"]]
    for row in RS_CORR.itertuples(index=False):
        crows.append([f"{row.correlation:.2f}", pct(row.minimum_volatility_weight_a), pct(row.minimum_volatility), pct(row.equal_weight_volatility)])
    story.append(tbl(crows, [34 * mm, 42 * mm, 44 * mm, 50 * mm]))
    story.append(P("Three conclusions follow. First, a two-asset mix of these stocks cuts volatility from about 17 percent to about 12 percent at the current correlation. Second, the protection depends on correlation staying low: at a correlation of 0.9 the same exercise only reaches 16.8 percent, barely below the single-stock level. Third, because the two volatilities are close, the safest weight is not sensitive to correlation, so a portfolio built near 50/50 does not need rebalancing when correlation drifts. It needs monitoring of the level of risk instead."))
    story.append(P("Limitations", "h1"))
    story.append(P("Volatilities and correlation are estimated from the last 252 trading days and treated as fixed inputs to the surface. In a real stress event all three move at once, and the correlation estimate itself is the least stable of the three. The surface is a local map around the current point, not a forecast. The value calculations use adjusted closes and ignore dividends timing, taxes and trading costs."))
    doc(path, "Exploring a Portfolio Risk Surface").build(story)
    return path


if __name__ == "__main__":
    strategy_charts()
    trade_charts()
    risk_charts()
    print(strategy_excel())
    print(trade_excel())
    print(risk_excel())
    for item in build_dashboards():
        print(item)
    for item in build_notebooks():
        print(item)
    print(strategy_report())
    print(trade_report())
    print(risk_report_pdf())
