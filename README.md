# Live TSX Portfolio Market Data Pipeline

An independent production-style market data pipeline project: a five-part study that runs from raw market data to an investment decision, built as a repeatable system for collecting, checking and using current market data.

## Purpose

Portfolio models are only as reliable as the price data behind them. This project builds the layer that sits before the strategy models:

1. Collect daily and intraday OHLCV data.
2. Preserve the raw source data.
3. Validate prices, timestamps, duplicates and volume.
4. Detect missing trading sessions and report any limited forward fills.
5. Flag unusual returns with a median absolute deviation screen.
6. Separate dividends and stock splits into a corporate-action log.
7. Build returns, volatility, beta, correlation and drawdown features.
8. Refresh selected portfolio weights from the latest 104 weekly returns.
9. Publish a run summary, data quality report, dashboard, workbook and report.

This project is independent of the published TSX Portfolio V2 backtest: it does not use, change or revise that study or its conclusions. Current strategy figures are diagnostics for the latest estimation window, not forecasts or recommendations.

## How this differs from the Quantamental Investing and AI portfolio project

This project is independent of the [Quantamental Investing and AI Portfolio](https://github.com/MunzeleenSarwar/quantamental-investing-ai-portfolio) project. It is not a continuation of it. The two projects use the same ten-stock TSX universe and the same 20 percent position cap and 40 percent sector cap, but they answer different questions.

- The Quantamental project asks which of ten portfolio strategies performed best. It runs one shared backtest on weekly data over a fixed test window, January 2022 to October 2026, and its conclusion is a ranking: Minimum Variance had the best risk-adjusted return (Sharpe 1.40) and the LSTM strategy was the weakest.
- This project asks whether the full chain from raw market data to an investment decision can be trusted, step by step. The fixed dataset is replaced by a validated data pipeline that can be re-run on any day: daily and 15-minute data, price validation, gap and outlier checks, and a corporate-action log.
- This project also adds four studies that the Quantamental project does not contain: a singular value decomposition analysis of market structure, an audit of a monthly momentum strategy against a decision rule fixed in advance (expected value, bootstrap, a random-selection placebo test and stress tests), a fully designed single trade (position sizing, stop, target and execution), and a two-asset portfolio risk surface built with multivariable calculus.
- The conclusion here is a decision, not a ranking. The momentum strategy fails the audit, the verdict is DO NOT TRADE, and the trade plan is restricted to paper trading.

The raw and clean Parquet data files are not stored in this repository. Running `run_pipeline.py` regenerates them from Yahoo Finance.

## Universe

Ten TSX stocks: CNQ, ENB, CCO, TD, BN, SHOP, TIH, ABX, L and CAE.

Benchmark: S&P/TSX Composite (`^GSPTSE`).

## Latest completed run

- Latest daily session: 30 October 2026
- Daily history: 1 June 2016 to 30 October 2026
- Daily rows processed: 28,754
- Intraday rows processed: 1,426
- Coverage: 100 percent for all eleven symbols
- Missing sessions: 0
- Quarantined daily rows: 0
- Corporate-action records: 328
- Return outliers flagged for review: 720

All symbols carry a warning status because the strict quality rule does not mark a symbol as pass while it has unresolved outlier review flags. Warning does not mean ingestion failed.

## Strategy refresh

The latest 104 weekly returns feed:

- Equal Weight
- Minimum Variance
- Risk Parity
- Minimum CVaR for the latest window

Rules: long only, maximum 20 percent in one stock, maximum 40 percent in one sector.

The Minimum CVaR calculation here is not the Regime-Aware CVaR strategy used in the earlier portfolio study. It has no regime model and is named differently to avoid confusion.

## Market structure: Discovering Market Regimes Through Structure

A second analysis layer applies singular value decomposition (SVD) to the pipeline's clean daily returns. Each trading day is treated as a ten-dimensional return vector. The analysis finds the dominant directions of market movement, projects every day into reduced space, measures distance from the centre, tests low-rank reconstruction, and compares structure across trailing market states and years.

Latest findings, 2 June 2016 to 30 October 2026 (2,613 daily return vectors):

- PC1 explains 35.6 percent of daily return variance.
- The first three directions explain 68.6 percent; the first five explain 85.8 percent.
- A rank-3 reconstruction leaves 31.4 percent of variance in the residual.
- PC1 is positive for all ten stocks but is dominated by Shopify in raw returns because of Shopify's higher volatility. In the volatility-standardized check, PC1 is much more evenly spread across Brookfield, TD, Enbridge, CAE and Canadian Natural Resources.
- PC2 separates Shopify from energy. PC3 separates Cameco and Barrick Mining from CAE and Canadian Natural Resources.
- High-volatility decline days are farther from the centre and have a lower rank-3 residual share than calm advance days (35.5 percent against 44.1 percent): stocks moved together more along the dominant directions in stress.
- The most extreme day was 16 March 2020.
- There were 113 day-to-day angles above 135 degrees, but only 19 material transitions after also requiring both days to be far from the centre.

The SVD analysis is descriptive. It does not forecast returns and does not replace the earlier hidden Markov model regime analysis.

Market structure files:

- `reports/TSX_Market_Regimes_Through_Structure_Report.pdf`: eight-page report
- `reports/TSX_Regime_Structure_Model.xlsx`: workbook with spectrum, loadings, daily projections, states, reconstruction, annual and rolling structure, extreme days and transitions
- `reports/regime_dashboard.html`: browser dashboard
- `notebooks/regime_structure_walkthrough.ipynb`: guided notebook
- `docs/REGIME_STRUCTURE_GUIDE.md`: plain-language explanation
- `run_regime_analysis.py`: analysis runner

## Three further research components

Three more research components are built on the same data. They share one strategy so the conclusions connect.

### Is This Trading Strategy Actually Profitable?

A monthly 12-1 momentum rule (top 3 of the ten stocks, equal weight, 10 bps costs) is tested with expected value, break-even analysis, bootstrap and block-bootstrap Monte Carlo, a random-selection placebo, and stress tests, against a six-test decision rule. Over 111 months (Aug 2017 to Oct 2026) it returned 27.7 percent a year with a t-statistic of 3.27 and expected value of +0.38R per trade lot. It still receives a **DO NOT TRADE** verdict: its Sharpe ratio (1.00) is below the equal-weight version of the same universe (1.24), its maximum drawdown (-28.0 percent) breaches the 25 percent limit, and the universe was selected in 2026 rather than point-in-time. Random stock selection in the same universe returned a median 19.6 percent a year.

Files: `reports/TSX_Strategy_Evaluation_Report.pdf`, `reports/TSX_Strategy_Evaluation_Model.xlsx`, `reports/strategy_evaluation_dashboard.html`, `notebooks/strategy_evaluation_walkthrough.ipynb`, `docs/STRATEGY_EVALUATION_GUIDE.md`, `run_strategy_evaluation.py`.

### Designing an Optimal Trade

Single-variable calculus designs one trade: long CNQ, the rank 1 momentum stock, for a hypothetical $1,000,000 account. Entry $78.39, stop $74.62 (2 x ATR14), target $84.04 (1.5 reward-risk). The impact-only profit optimum is about 302,000 shares and is not usable; a variance risk penalty gives an optimum near 4,300 shares; the 20 percent position cap binds and sets the final size at 2,551 shares ($199,973), risking $9,617 at the stop. Full Kelly (a 26.9 percent capital risk fraction) is calculated and rejected. Execution analysis shows the order is 0.03 percent of daily volume, so timing risk dominates impact and the order belongs inside one trading day. Status: paper trade only, per the strategy evaluation verdict.

Files: `reports/TSX_Optimal_Trade_Design_Report.pdf`, `reports/TSX_Optimal_Trade_Design_Model.xlsx`, `reports/trade_design_dashboard.html`, `notebooks/trade_design_walkthrough.ipynb`, `docs/TRADE_DESIGN_GUIDE.md`, `run_trade_design.py`.

### Exploring a Portfolio Risk Surface

Multivariable calculus on a two-asset Enbridge and TD portfolio over the last 252 trading days: value and volatility surfaces, partial derivatives, gradients, directional derivatives, the Hessian, and Taylor approximations checked against exact values. Enbridge volatility 17.4 percent, TD 17.1 percent, correlation 0.019. The minimum-volatility mix is 49.0 percent Enbridge with 12.3 percent volatility. The volatility gradient is zero in the weight direction at the minimum and 0.061 in the correlation direction. The Hessian has eigenvalues 0.475 and -0.030, so the joint surface is a saddle. Correlation moves minimum volatility from 8.6 percent at -0.5 to 16.8 percent at 0.9, while the safest weight barely moves.

Files: `reports/TSX_Portfolio_Risk_Surface_Report.pdf`, `reports/TSX_Portfolio_Risk_Surface_Model.xlsx`, `reports/risk_surface_dashboard.html`, `notebooks/risk_surface_walkthrough.ipynb`, `docs/RISK_SURFACE_GUIDE.md`, `run_risk_surface.py`.

## Main files

- `reports/TSX_Live_Market_Data_Pipeline_Report.pdf`: six-page project report
- `reports/TSX_Live_Pipeline_Model.xlsx`: workbook with run summary, quality results, snapshot, weights, metrics, sector weights, corporate actions and outliers
- `reports/dashboard.html`: browser dashboard for the latest run
- `reports/data_quality_report.md`: data quality summary
- `notebooks/live_pipeline_walkthrough.ipynb`: guided notebook using the saved outputs
- `run_pipeline.py`: end-to-end pipeline runner
- `src/tsx_pipeline/`: ingestion, quality, feature and strategy modules
- `tests/`: unit tests for validation, gaps, outliers and strategy constraints
- `docs/CONCEPT_GUIDE.md`: plain-language explanation of the concepts and outputs
- `docs/ARCHITECTURE_AND_SCHEDULING.md`: system design and scheduling notes

## Run the pipeline

```bash
pip install -r requirements.txt
python run_pipeline.py
python scripts/build_deliverables.py
python run_regime_analysis.py
python scripts/build_regime_deliverables.py
python run_strategy_evaluation.py
python run_risk_surface.py
python run_trade_design.py
python scripts/build_stage2_projects.py
```

To run the daily layer without a new intraday download:

```bash
python run_pipeline.py --skip-intraday
```

Run tests:

```bash
python -m pytest -q
```

## Data and method notes

Yahoo Finance is the source. The project is therefore a production-style near-live polling pipeline, not a direct exchange tick feed.

Adjusted close is used for returns and strategy calculations. Raw close remains stored separately. Dividend and split records are preserved in a corporate-action log.

Invalid OHLCV rows are quarantined. Return outliers are flagged and retained, because a large market move can be genuine. A missing adjusted close is forward-filled only when the gap is five sessions or shorter, and the fill remains identified in the fill report.

## Skills demonstrated

Python, pandas, NumPy, SciPy optimisation, yfinance, Parquet, data validation, data quality reporting, market data engineering, feature engineering, portfolio risk measures, singular value decomposition, dimensionality reduction, market regime analysis, single-variable and multivariable calculus, optimisation under constraints, expected value and break-even analysis, Monte Carlo bootstrap, stress testing, Kelly sizing, execution cost modelling, gradients, Hessians and Taylor approximations, Excel, dashboarding and automated testing.
