"""Build charts, workbook, dashboard, notebook and PDF for the regime extension."""
from __future__ import annotations

import html
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "regime_outputs"
CHARTS = ROOT / "charts" / "regimes"
REPORTS = ROOT / "reports"
CHARTS.mkdir(parents=True, exist_ok=True)
SUMMARY = json.loads((DATA / "regime_summary.json").read_text(encoding="utf-8"))
SPECTRUM = pd.read_csv(DATA / "spectrum.csv")
SPECTRUM_STD = pd.read_csv(DATA / "spectrum_standardized.csv")
LOADINGS = pd.read_csv(DATA / "dominant_directions.csv", index_col=0)
LOADINGS_STD = pd.read_csv(DATA / "dominant_directions_standardized.csv", index_col=0)
DAILY = pd.read_csv(DATA / "daily_projections.csv", parse_dates=["timestamp"])
RECON = pd.read_csv(DATA / "reconstruction_quality.csv")
ANNUAL = pd.read_csv(DATA / "annual_structure.csv")
ROLLING = pd.read_csv(DATA / "rolling_structure.csv", parse_dates=["window_start", "window_end"])
STATES = pd.read_csv(DATA / "market_state_summary.csv")
EXTREMES = pd.read_csv(DATA / "extreme_days.csv", parse_dates=["date"])
TRANSITIONS = pd.read_csv(DATA / "largest_transition_days.csv")
MATERIAL = pd.read_csv(DATA / "material_transition_days.csv")
STATE_COLORS = {
    "Calm advance": "#4C78A8",
    "Calm pullback": "#F58518",
    "High-volatility advance": "#54A24B",
    "High-volatility decline": "#E45756",
    "Warm-up": "#999999",
}


def pct(x: float, digits: int = 1) -> str:
    if pd.isna(x):
        return "NA"
    if abs(x) < 0.000005:
        x = 0.0
    return f"{x * 100:.{digits}f}%"


def build_charts() -> None:
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10})

    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.bar(SPECTRUM.component, SPECTRUM.explained_variance_ratio * 100, color="#1f4e79", label="Explained variance")
    ax2 = ax.twinx()
    ax2.plot(SPECTRUM.component, SPECTRUM.cumulative_explained_variance * 100, color="#c00000", marker="o", label="Cumulative")
    ax.set_ylabel("Explained variance (%)")
    ax2.set_ylabel("Cumulative (%)")
    ax.set_title("SVD spectrum: variance by component")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout(); fig.savefig(CHARTS / "spectrum.png", dpi=180); plt.close(fig)

    view = LOADINGS[["PC1", "PC2", "PC3", "PC4", "PC5"]].copy()
    view.index = [str(x).replace(".TO", "") for x in view.index]
    fig, ax = plt.subplots(figsize=(9, 6))
    image = ax.imshow(view.to_numpy(), cmap="RdBu_r", vmin=-0.85, vmax=0.85)
    ax.set_xticks(range(len(view.columns)), view.columns)
    ax.set_yticks(range(len(view.index)), view.index)
    ax.set_title("Dominant directions: asset loadings")
    for i in range(view.shape[0]):
        for j in range(view.shape[1]):
            value = view.iloc[i, j]
            ax.text(j, i, f"{value:.2f}", ha="center", va="center", fontsize=8,
                    color="white" if abs(value) > 0.48 else "black")
    fig.colorbar(image, ax=ax, shrink=0.85)
    fig.tight_layout(); fig.savefig(CHARTS / "loadings_heatmap.png", dpi=180); plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 6.5))
    for state, group in DAILY.groupby("market_state"):
        ax.scatter(group.PC1 * 100, group.PC2 * 100, s=11, alpha=0.48,
                   label=state, color=STATE_COLORS.get(state, "#333333"))
    top = DAILY.nlargest(3, "distance_from_center")
    for row in top.itertuples(index=False):
        ax.annotate(row.timestamp.strftime("%Y-%m-%d"), (row.PC1 * 100, row.PC2 * 100), fontsize=8,
                    xytext=(5, 5), textcoords="offset points")
    ax.axhline(0, color="black", linewidth=0.7); ax.axvline(0, color="black", linewidth=0.7)
    ax.set_xlabel("PC1 score (%)")
    ax.set_ylabel("PC2 score (%)")
    ax.set_title("Market days in reduced space, coloured by trailing market state")
    ax.grid(alpha=0.25); ax.legend(fontsize=8, markerscale=2)
    fig.tight_layout(); fig.savefig(CHARTS / "reduced_space.png", dpi=180); plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.plot(RECON["rank"], RECON.variance_explained * 100, marker="o", color="#1f4e79", label="Variance explained")
    ax2 = ax.twinx()
    ax2.bar(RECON["rank"], RECON.residual_rms_bp, alpha=0.35, color="#c00000", label="Residual RMS")
    ax.set_xlabel("Reconstruction rank")
    ax.set_ylabel("Variance explained (%)")
    ax2.set_ylabel("Residual RMS (basis points)")
    ax.set_title("What is lost when the market is compressed?")
    ax.grid(alpha=0.3)
    fig.tight_layout(); fig.savefig(CHARTS / "reconstruction_quality.png", dpi=180); plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.plot(ROLLING.window_end, ROLLING.pc1_explained_variance * 100, color="#1f4e79", label="PC1 explained variance")
    ax.plot(ROLLING.window_end, ROLLING.top3_explained_variance * 100, color="#c00000", label="Top 3 explained variance")
    ax2 = ax.twinx()
    ax2.plot(ROLLING.window_end, ROLLING.average_pairwise_correlation, color="#54A24B", alpha=0.75, label="Average pairwise correlation")
    ax.set_ylabel("Explained variance (%)")
    ax2.set_ylabel("Average correlation")
    ax.set_title("Rolling 252-day market structure")
    ax.grid(alpha=0.3)
    lines, labels = ax.get_legend_handles_labels(); lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(lines + lines2, labels + labels2, fontsize=8)
    fig.tight_layout(); fig.savefig(CHARTS / "rolling_structure.png", dpi=180); plt.close(fig)

    fig, ax = plt.subplots(figsize=(11, 5.5))
    ax.plot(DAILY.timestamp, DAILY.distance_from_center, color="#999999", linewidth=0.6, label="Daily distance")
    ax.plot(DAILY.timestamp, DAILY.distance_from_center.rolling(20).mean(), color="#1f4e79", linewidth=1.4, label="20-day average")
    threshold = DAILY.distance_from_center.quantile(0.75)
    ax.axhline(threshold, color="#c00000", linestyle="--", label="75th percentile")
    extreme = DAILY.loc[DAILY.distance_from_center.idxmax()]
    ax.annotate("16 Mar 2020", (extreme.timestamp, extreme.distance_from_center), xytext=(10, 10), textcoords="offset points")
    ax.set_ylabel("Distance from centre")
    ax.set_title("How far was each day from the average market day?")
    ax.grid(alpha=0.3); ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(CHARTS / "distance_timeline.png", dpi=180); plt.close(fig)


def build_excel() -> Path:
    path = REPORTS / "TSX_Regime_Structure_Model.xlsx"
    wb = Workbook(); wb.remove(wb.active)
    header_font = Font(bold=True, color="000000")
    header_fill = PatternFill("solid", fgColor="D9D9D9")

    def add(name: str, frame: pd.DataFrame, index: bool = False) -> None:
        ws = wb.create_sheet(name[:31])
        data = frame.reset_index() if index else frame
        ws.append(list(data.columns))
        for cell in ws[1]:
            cell.font = header_font; cell.fill = header_fill
            cell.alignment = Alignment(vertical="center", wrap_text=True)
        for row in data.itertuples(index=False, name=None):
            ws.append(list(row))
        ws.freeze_panes = "A2"; ws.auto_filter.ref = ws.dimensions
        for idx, col in enumerate(data.columns, 1):
            values = [str(col)] + ["" if pd.isna(v) else str(v) for v in data[col].head(250)]
            ws.column_dimensions[get_column_letter(idx)].width = min(max(max(map(len, values)) + 2, 11), 42)

    summary_df = pd.DataFrame([{"item": k, "value": v} for k, v in SUMMARY.items()])
    add("Summary", summary_df)
    add("Spectrum", SPECTRUM)
    add("Loadings", LOADINGS, index=True)
    add("Spectrum Standardized", SPECTRUM_STD)
    add("Loadings Standardized", LOADINGS_STD, index=True)
    add("Daily Projections", DAILY)
    add("Market States", STATES)
    add("Reconstruction", RECON)
    add("Annual Structure", ANNUAL)
    add("Rolling Structure", ROLLING)
    add("Extreme Days", EXTREMES)
    add("Largest Transitions", TRANSITIONS)
    add("Material Transitions", MATERIAL)
    method = pd.DataFrame([
        {"item": "Input", "detail": "Daily log returns for ten TSX stocks from the live pipeline clean adjusted-close matrix, 2 Jun 2016 to 30 Oct 2026."},
        {"item": "Centring", "detail": "Each stock return series is centred on its own full-sample mean before SVD. The core analysis does not divide by volatility."},
        {"item": "SVD", "detail": "Singular values squared give variance along each orthogonal direction. Right singular vectors give asset loadings."},
        {"item": "Sign rule", "detail": "SVD signs are arbitrary. PC1 is oriented so its loadings sum positive. Other directions are oriented so the largest absolute loading is positive."},
        {"item": "Market states", "detail": "Trailing 20-day benchmark return and volatility define four descriptive states. The high-volatility cutoff is the full-sample 75th percentile, so the labels are retrospective and are not a live trading rule."},
        {"item": "Reconstruction", "detail": "A rank-k reconstruction keeps the first k directions and the asset means. Residual share measures information removed by compression."},
        {"item": "Angles", "detail": "Angles compare centred return vectors on consecutive days. A large angle alone ignores magnitude, so material transitions also require both days to be at or above the 75th percentile of distance from centre."},
        {"item": "Standardized check", "detail": "A second SVD divides each return series by its full-sample standard deviation. This separates correlation structure from volatility scale."},
        {"item": "Limit", "detail": "The analysis is descriptive. It does not forecast returns and does not replace the V2 HMM regime model or backtest."},
    ])
    add("Method", method)
    wb.save(path)
    return path


def table_html(frame: pd.DataFrame, limit: int = 20) -> str:
    view = frame.head(limit).copy()
    for col in view.columns:
        if pd.api.types.is_float_dtype(view[col]):
            view[col] = view[col].map(lambda x: "" if pd.isna(x) else f"{x:,.4f}")
        else:
            view[col] = view[col].astype(str)
    return view.to_html(index=False, escape=True, border=0, classes="data-table")


def build_dashboard() -> Path:
    path = REPORTS / "regime_dashboard.html"
    body = f"""<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">
<title>Discovering Market Regimes Through Structure</title>
<style>body{{font-family:Arial,sans-serif;margin:32px;color:#111;max-width:1180px}}table{{border-collapse:collapse;width:100%;font-size:13px;margin:10px 0 26px}}th,td{{border:1px solid #999;padding:6px;text-align:left}}th{{background:#ddd}}img{{max-width:100%}}.card{{border:1px solid #bbb;padding:14px;margin:12px 0}}</style></head>
<body><h1>Discovering Market Regimes Through Structure</h1>
<p>Daily data from {html.escape(SUMMARY['data_start'])} to {html.escape(SUMMARY['data_end'])}. Ten TSX stocks. Latest trailing state: {html.escape(SUMMARY['latest_market_state'])}.</p>
<div class=\"card\"><strong>PC1:</strong> {SUMMARY['pc1_explained_variance_pct']:.1f}% of variance<br>
<strong>Top 3 directions:</strong> {SUMMARY['top3_explained_variance_pct']:.1f}%<br>
<strong>Rank-3 residual:</strong> {SUMMARY['rank3_residual_share_pct']:.1f}%<br>
<strong>Most extreme day:</strong> {html.escape(SUMMARY['most_extreme_day'])}<br>
<strong>Material large transitions:</strong> {SUMMARY['material_large_transitions']}</div>
<h2>Spectrum</h2>{table_html(SPECTRUM)}
<h2>Market states</h2>{table_html(STATES)}
<h2>Extreme days</h2>{table_html(EXTREMES, 10)}
<h2>Charts</h2>
<img src=\"../charts/regimes/spectrum.png\" alt=\"SVD spectrum\">
<img src=\"../charts/regimes/loadings_heatmap.png\" alt=\"Dominant direction loadings\">
<img src=\"../charts/regimes/reduced_space.png\" alt=\"Market days in reduced space\">
<img src=\"../charts/regimes/reconstruction_quality.png\" alt=\"Reconstruction quality\">
<img src=\"../charts/regimes/rolling_structure.png\" alt=\"Rolling market structure\">
<img src=\"../charts/regimes/distance_timeline.png\" alt=\"Distance from centre over time\">
</body></html>"""
    path.write_text(body, encoding="utf-8")
    return path


def build_notebook() -> Path:
    import nbformat as nbf
    nb = nbf.v4.new_notebook()
    nb.metadata = {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.12"},
    }
    cells = [
        nbf.v4.new_markdown_cell(f"""# Discovering Market Regimes Through Structure

This notebook uses the saved outputs from the SVD regime analysis.

- Sample: **{SUMMARY['days']:,} daily observations**, ten TSX stocks
- Period: **{SUMMARY['data_start']} to {SUMMARY['data_end']}**
- PC1 explained variance: **{SUMMARY['pc1_explained_variance_pct']:.1f}%**
- First three directions: **{SUMMARY['top3_explained_variance_pct']:.1f}%**
- Most extreme day: **{SUMMARY['most_extreme_day']}**

The analysis is descriptive. It does not forecast returns."""),
        nbf.v4.new_markdown_cell("""## 1. Load the outputs"""),
        nbf.v4.new_code_cell("""from pathlib import Path
import json
import pandas as pd

ROOT = Path.cwd()
if (ROOT / 'data' / 'regime_outputs').exists():
    BASE = ROOT
else:
    BASE = ROOT.parent
DATA = BASE / 'data' / 'regime_outputs'
summary = json.loads((DATA / 'regime_summary.json').read_text())
spectrum = pd.read_csv(DATA / 'spectrum.csv')
loadings = pd.read_csv(DATA / 'dominant_directions.csv', index_col=0)
daily = pd.read_csv(DATA / 'daily_projections.csv', parse_dates=['timestamp'])
states = pd.read_csv(DATA / 'market_state_summary.csv')
summary"""),
        nbf.v4.new_markdown_cell("""## 2. Read the spectrum

A singular value squared is proportional to variance along its direction. The first direction is important, but it does not describe the whole market."""),
        nbf.v4.new_code_cell("""spectrum"""),
        nbf.v4.new_markdown_cell("""## 3. Interpret the loadings

PC1 has positive loadings for every stock, but Shopify is much larger than the others. That is a volatility-scale effect in raw returns. The standardized loadings in the workbook provide the comparison."""),
        nbf.v4.new_code_cell("""loadings[['PC1', 'PC2', 'PC3']].round(3)"""),
        nbf.v4.new_markdown_cell("""## 4. Compare market states

The states use trailing 20-day benchmark direction and volatility. They are descriptive labels, not a live trading rule."""),
        nbf.v4.new_code_cell("""states"""),
        nbf.v4.new_markdown_cell("""## 5. Find extreme and transition days"""),
        nbf.v4.new_code_cell("""extremes = pd.read_csv(DATA / 'extreme_days.csv')
material = pd.read_csv(DATA / 'material_transition_days.csv')
extremes.head(10), material.head(10)"""),
        nbf.v4.new_markdown_cell("""## 6. Check reconstruction loss"""),
        nbf.v4.new_code_cell("""recon = pd.read_csv(DATA / 'reconstruction_quality.csv')
recon"""),
        nbf.v4.new_markdown_cell("""## Main conclusion

Three directions capture 68.6 percent of daily return variance, but 31.4 percent remains outside the rank-3 structure. Market stress days are farther from the centre and are captured better by the dominant directions. That supports a structural difference between calm and stress periods, while also showing why a low-rank market model cannot describe every stock move."""),
    ]
    nb.cells = cells
    path = ROOT / "notebooks" / "regime_structure_walkthrough.ipynb"
    nbf.write(nb, path)
    return path


def build_report() -> Path:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    styles = getSampleStyleSheet()
    title = ParagraphStyle("RTitle", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=21, leading=25, textColor=colors.black, alignment=TA_CENTER, spaceAfter=4)
    subtitle = ParagraphStyle("RSubtitle", parent=styles["Normal"], fontName="Helvetica", fontSize=11, leading=14, textColor=colors.black, alignment=TA_CENTER, spaceAfter=10)
    h1 = ParagraphStyle("RH1", parent=styles["Heading1"], fontName="Helvetica-Bold", fontSize=14, leading=17, textColor=colors.black, spaceBefore=10, spaceAfter=5)
    h2 = ParagraphStyle("RH2", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=11.5, leading=14, textColor=colors.black, spaceBefore=8, spaceAfter=4)
    body = ParagraphStyle("RBody", parent=styles["BodyText"], fontName="Helvetica", fontSize=9.5, leading=13.2, textColor=colors.black, spaceAfter=5)
    small = ParagraphStyle("RSmall", parent=body, fontSize=8.2, leading=10.5)
    cell = ParagraphStyle("RCell", parent=body, fontSize=8.2, leading=10.2, spaceAfter=0)
    cellh = ParagraphStyle("RCellH", parent=cell, fontName="Helvetica-Bold")

    def P(text, style=body):
        return Paragraph(text, style)

    def tbl(data, widths):
        wrapped = [[Paragraph(str(c), cellh if r == 0 else cell) for c in row] for r, row in enumerate(data)]
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

    def chart(name, ratio=0.55, width=170 * mm):
        return Image(str(CHARTS / name), width=width, height=width * ratio)

    path = REPORTS / "TSX_Market_Regimes_Through_Structure_Report.pdf"
    doc = SimpleDocTemplate(str(path), pagesize=A4, leftMargin=17 * mm, rightMargin=17 * mm,
                            topMargin=16 * mm, bottomMargin=16 * mm,
                            title="Discovering Market Regimes Through Structure", author="Munzeleen Sarwar")
    story = []
    story.append(P("Discovering Market Regimes Through Structure", title))
    story.append(P("Munzeleen Sarwar", subtitle))
    story.append(P("Daily returns for ten TSX stocks, 2 June 2016 to 30 October 2026. Data source: the Live TSX Portfolio Market Data Pipeline.", small))

    story.append(P("Executive summary", h1))
    story.append(P("Each trading day can be treated as one point in ten-dimensional space. One coordinate records the return on each stock. Singular value decomposition, or SVD, rotates that space into new directions ordered by how much return variance each direction explains. The rotation does not create new information. It shows which combinations of stock returns account for most movement and which part of a day cannot be described by those combinations."))
    story.append(P("The first direction explains 35.6 percent of daily return variance. The first two explain 54.9 percent, the first three explain 68.6 percent, and the first five explain 85.8 percent. Market movement is therefore strongly structured, but it is not one-dimensional. A three-direction model still leaves 31.4 percent of variance in the residual."))
    story.append(P("The clearest regime result concerns stress. Days in the trailing high-volatility decline state were farther from the average day and were described better by the first three directions than calm advance days. Their average rank-3 residual share was 35.5 percent, compared with 44.1 percent for calm advance days. In stress, stocks moved together more strongly along the dominant directions. In calm advances, a larger share of movement was stock-specific."))
    story.append(P("The analysis is descriptive. It does not forecast returns, assign probabilities to future states, or replace the hidden Markov model used in the earlier portfolio study."))

    story.append(P("1. Why use geometry?", h1))
    story.append(P("A correlation table shows pairs of stocks. Geometry shows the whole cross-section at once. A calm day usually sits near the centre of the return space, where most stock returns are close to their averages. A market-wide shock pushes the day far from the centre. A sector event pushes it in a different direction from a broad market event, even when the size of the move is similar. Distance measures how unusual the size of a day was. Direction measures what kind of day it was."))
    story.append(P("This differs from the earlier two-state hidden Markov model. That model estimated calm and distress probabilities from weekly benchmark returns, volatility and VIX, using only information available at the time. The SVD analysis studies the shape of daily returns across ten stocks over the full sample. It is a structure analysis, not a competing trading model."))

    story.append(P("2. Data and method", h1))
    story.append(P("The input is the clean adjusted-close matrix produced by the live market data pipeline. Daily log returns are calculated for CNQ, ENB, CCO, TD, BN, SHOP, TIH, ABX, L and CAE. The sample contains 2,613 daily return vectors. The benchmark is used for trailing state labels and comparisons, but it is not one of the ten coordinates in the SVD."))
    story.append(P("Each stock return series is centred on its own sample mean. The core SVD uses raw return scale. It does not divide each stock by its volatility. That choice preserves the fact that some stocks normally move more than others, but it also means volatile stocks can dominate a direction. A second SVD using volatility-standardized returns is reported as a check."))
    story.append(P("SVD writes the centred return matrix as U, S and V transpose. The columns of V are the dominant directions. Each squared singular value in S is proportional to variance along its direction. Projecting a day onto a direction gives its score on that pattern. Reconstructing a day from the first k directions shows how much of the day the low-rank structure captures and how much is lost."))

    story.append(PageBreak())
    story.append(P("3. The spectrum", h1))
    srows = [["Component", "Singular value", "Variance explained", "Cumulative"]]
    for row in SPECTRUM.itertuples(index=False):
        srows.append([row.component, f"{row.singular_value:.2f}", pct(row.explained_variance_ratio), pct(row.cumulative_explained_variance)])
    story.append(tbl(srows, [32 * mm, 36 * mm, 48 * mm, 54 * mm]))
    story.append(chart("spectrum.png"))
    story.append(P("No single direction dominates completely. PC1 is material at 35.6 percent, but PC2 adds 19.4 points and PC3 adds 13.7 points. The market needs several patterns: a broad movement pattern, at least one major contrast between groups of stocks, and further resource and stock-specific patterns. The smooth decline in the spectrum also warns against treating the first three directions as the only real structure. They are a useful compression, not a complete description."))

    story.append(P("4. Dominant directions", h1))
    lrows = [["Stock", "PC1", "PC2", "PC3", "Reading"]]
    readings = {
        "CNQ.TO": "Energy; opposite PC2 and PC3 contrasts",
        "ENB.TO": "Moderate common loading",
        "CCO.TO": "Large in all three directions",
        "TD.TO": "Low raw PC1 loading",
        "BN.TO": "Second group in PC1",
        "SHOP.TO": "Dominates PC1 and PC2",
        "TIH.TO": "Low loadings in first three",
        "ABX.TO": "Main positive PC3 partner with CCO",
        "L.TO": "Smallest PC1 loading",
        "CAE.TO": "Material PC1; negative PC3",
    }
    for stock, row in LOADINGS.iterrows():
        short = str(stock).replace(".TO", "")
        lrows.append([short, f"{row.PC1:.3f}", f"{row.PC2:.3f}", f"{row.PC3:.3f}", readings.get(str(stock), "")])
    story.append(tbl(lrows, [24 * mm, 22 * mm, 22 * mm, 22 * mm, 80 * mm]))
    story.append(chart("loadings_heatmap.png", ratio=0.667))
    story.append(P("PC1, the common direction", h2))
    story.append(P("Every PC1 loading is positive. A positive PC1 score therefore means the ten stocks generally rose together relative to their averages, and a negative score means they generally fell together. The direction is still not an equal market basket. Shopify has a loading of 0.734, followed by Cameco at 0.385 and CAE at 0.291. Loblaw is only 0.051 and Barrick Mining is 0.115. PC1 combines common movement with the greater daily variance of Shopify and other volatile stocks."))
    story.append(P("PC2, the Shopify and energy contrast", h2))
    story.append(P("PC2 places Shopify at 0.652 against Canadian Natural Resources at -0.474 and Cameco at -0.432. It separates days when Shopify moved strongly from days led by energy. This is a relative pattern. A high PC2 score does not require energy stocks to fall in absolute terms, only to move less than Shopify relative to the pattern."))
    story.append(P("PC3, the resource split", h2))
    story.append(P("PC3 places Cameco at 0.634 and Barrick Mining at 0.519 against CAE at -0.351 and Canadian Natural Resources at -0.337. It separates uranium and gold miners from oil and industrial names. The first three directions therefore capture one broad pattern and two economically readable contrasts."))

    story.append(PageBreak())
    story.append(P("5. Market days and descriptive states", h1))
    story.append(P("Four states are assigned from the benchmark's trailing 20-day return and trailing 20-day volatility. High volatility means trailing volatility at or above 13.49 percent, the full-sample 75th percentile. The threshold uses the full sample, so the labels are for retrospective description. They are not presented as a rule that could have been traded in real time."))
    strows = [["Trailing state", "Days", "Share", "Average distance", "Rank-3 residual share", "Average spell"]]
    for row in STATES.itertuples(index=False):
        strows.append([row.market_state, str(row.days), f"{row.share_pct:.1f}%", f"{row.average_distance_from_center:.3f}", pct(row.average_rank3_residual_share), f"{row.average_spell_days:.1f} days"])
    story.append(tbl(strows, [42 * mm, 18 * mm, 20 * mm, 30 * mm, 34 * mm, 26 * mm]))
    story.append(chart("reduced_space.png", ratio=0.65))
    story.append(P("Calm advances account for 52.9 percent of classified days and have the longest average spell at 16.0 days. High-volatility declines account for 12.1 percent and have a shorter average spell of 5.7 days. Their average distance from the centre is 0.085, compared with 0.052 for calm advances. The geometry and the state labels therefore agree on the main point: stress days are not simply normal days with a negative sign. They are larger, more common-driven moves."))
    story.append(P("The latest date, 30 October 2026, carries a trailing high-volatility advance label because the benchmark remained positive over the trailing 20 days and trailing volatility was 14.86 percent. The day itself was a broad fall: the equal-weight return was -2.72 percent and the PC1 score was strongly negative. The state describes the trailing window, not the direction of that single day."))

    story.append(P("6. Extreme days", h1))
    erows = [["Date", "Distance", "Equal-weight return", "Benchmark return", "Smallest stock return"]]
    for row in EXTREMES.head(8).itertuples(index=False):
        erows.append([str(row.date)[:10], f"{row.distance_from_center:.3f}", pct(row.equal_weight_return), pct(row.benchmark_return), f"{str(row.smallest_return_stock).replace('.TO', '')} {pct(row.smallest_return)}"])
    story.append(tbl(erows, [30 * mm, 26 * mm, 38 * mm, 38 * mm, 38 * mm]))
    story.append(chart("distance_timeline.png", ratio=0.5))
    story.append(P("The most extreme day was 16 March 2020. Its distance from the centre was 0.493, the equal-weight return was -11.8 percent, and the benchmark return was -10.4 percent. Only 2.7 percent of that day's squared distance remained outside the first three directions. The day was extreme in size but ordinary in direction: it followed the dominant market pattern closely. This distinction is central to the project. A large residual share points to an unusual mixture of stock moves. A large distance with a small residual share points to a large common shock."))

    story.append(PageBreak())
    story.append(P("7. Reconstruction and information loss", h1))
    rrows = [["Rank", "Variance explained", "Residual share", "Residual RMS"]]
    for row in RECON.itertuples(index=False):
        if row.rank in [0, 1, 2, 3, 4, 5, 6, 8, 10]:
            rrows.append([str(row.rank), pct(row.variance_explained), pct(row.residual_share), f"{row.residual_rms_bp:.1f} bp"])
    story.append(tbl(rrows, [28 * mm, 46 * mm, 46 * mm, 50 * mm]))
    story.append(chart("reconstruction_quality.png"))
    story.append(P("A rank-1 model captures only the broad direction and loses 64.4 percent of variance. Rank 3 is a practical summary at 68.6 percent explained, but the residual root mean square remains 121.8 basis points per stock-day. Rank 5 raises explained variance to 85.8 percent and lowers residual RMS to 82.0 basis points. Compression is useful for visualisation and for separating common from stock-specific movement. It is not accurate enough to replace the original returns in portfolio risk calculations."))

    story.append(P("8. How structure changes over time", h1))
    arows = [["Year", "PC1", "Top 3", "Average correlation", "Equal-weight volatility"]]
    for row in ANNUAL.itertuples(index=False):
        arows.append([str(row.year), pct(row.pc1_explained_variance), pct(row.top3_explained_variance), f"{row.average_pairwise_correlation:.3f}", pct(row.equal_weight_volatility)])
    story.append(tbl(arows, [26 * mm, 30 * mm, 32 * mm, 42 * mm, 40 * mm]))
    story.append(chart("rolling_structure.png"))
    story.append(P("Structure strengthened in 2020 and 2022. PC1 explained 52.7 percent in 2020, when average pairwise correlation was 0.406, and 51.4 percent in 2022, when average correlation was 0.260. Calm years were less one-directional: PC1 explained 29.5 percent in 2017 and 29.8 percent in 2019. The rolling chart shows the same pattern in 252-day windows. Common structure rises when markets are under broad pressure and falls back when stock-specific news carries more weight."))
    story.append(P("The 2026 figure needs care. Through 30 October, PC1 explains 38.3 percent, but average pairwise correlation is only 0.084. A high PC1 share in raw returns can result from one or two volatile stocks rather than broad correlation. The standardized check is therefore necessary before calling a period a common-factor regime."))

    story.append(P("9. Angles and transitions", h1))
    story.append(P("The angle between consecutive centred return vectors has a mean of 90.0 degrees and a median of 90.5 degrees. In plain terms, the pattern of stock returns on one day is usually close to unrelated to the pattern on the previous day. Daily cross-sectional direction has little persistence at this horizon."))
    story.append(P("An angle above 135 degrees occurred 113 times, or 4.3 percent of transitions. Angle alone ignores the size of both days, so a near-average day can produce a large angle without economic importance. The material transition screen also requires both days to have distance at or above the 75th percentile of 0.070. Only 19 transitions pass both tests. These include 10 April 2025, after the large advance on 9 April, and several reversals in March 2020 and early 2022. The material count is the more defensible result."))

    story.append(P("10. Standardized check", h1))
    story.append(P("When each stock is divided by its own full-sample volatility, PC1 explains 34.6 percent and the first three directions explain 56.6 percent. The standardized PC1 loadings are much more even: Brookfield 0.425, TD 0.414, Enbridge 0.390, CAE 0.356 and Canadian Natural Resources 0.348, with Shopify at 0.221. The common correlation factor is broad. The raw PC1 result is still correct for return variance, but its Shopify weight is mainly a scale effect. Keeping both versions prevents a false interpretation."))

    story.append(P("11. Limitations", h1))
    story.append(P("The SVD is fitted on the full sample. Its directions use information from the whole period and cannot be treated as directions known at the start of the sample. The state threshold also uses the full sample. The ten stocks were selected for the earlier portfolio project and are not a point-in-time TSX universe. Survivorship and selection effects therefore remain. Daily returns contain substantial stock-specific noise, so a two-dimensional plot is a summary rather than a map of all market states. Finally, SVD directions are mathematical patterns. Economic labels such as energy contrast or resource split are interpretations of the loadings, not separate estimated factors."))
    story.append(P("The project adds a structural view to the live pipeline. The pipeline ensures that prices are collected and checked. The SVD layer then shows how the resulting market days are organised: a broad common direction, readable group contrasts, greater common structure in stress, and a material residual that prevents the market from being reduced to a single factor."))

    doc.build(story)
    return path


if __name__ == "__main__":
    build_charts()
    print(build_excel())
    print(build_dashboard())
    print(build_notebook())
    print(build_report())
