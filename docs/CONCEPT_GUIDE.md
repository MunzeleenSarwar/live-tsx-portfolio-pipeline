# Concept Guide

This guide explains the pipeline in plain language, in the order the data moves through it.

## 1. What problem the pipeline solves

A backtest normally starts with a saved price file. That is acceptable for a one-time study, but it leaves basic questions unanswered:

- When were the prices downloaded?
- Did every stock arrive?
- Are any dates missing?
- Did a split or dividend create a false price jump?
- Are any prices impossible?
- Which numbers were changed during cleaning?

The pipeline answers those questions before a portfolio model uses the data.

## 2. OHLCV

OHLCV means:

- Open: first traded price in the period
- High: highest traded price
- Low: lowest traded price
- Close: last traded price
- Volume: number of shares traded

A valid row must obey simple rules. The high cannot be below the open or close. The low cannot be above the open or close. Prices must be positive. Volume cannot be negative.

## 3. Raw, clean and feature layers

The raw layer is the source data as received, with a retrieval timestamp added. It is not edited.

The clean layer contains rows that passed validation. Rows that failed are placed in a quarantine file rather than deleted without a record.

The feature layer contains calculated values such as returns and volatility. Keeping these layers separate makes it possible to trace a result back to the source row that produced it.

## 4. Adjusted close

A stock price can fall because the market fell, or because the company paid a dividend, or because the shares split. Only the first reason is a market loss in the usual return sense.

Adjusted close accounts for dividends and splits. The pipeline uses adjusted close for returns and portfolio weights. It stores raw close separately because both series have different uses.

## 5. Trading sessions and gaps

A trading session is a day when the market is open. The pipeline uses benchmark dates as the expected calendar. If the benchmark has a date and a stock does not, that stock has a gap.

A gap can come from a source failure, a trading halt, a listing change or another reason. The pipeline reports the start, end and length of each gap.

## 6. Forward filling

Forward filling copies the last known price into a missing session. It is sometimes necessary for a calculation, but it can create a false impression that nothing changed.

The pipeline therefore allows a fill only for a gap of five sessions or fewer, and the fill report identifies every filled date. A longer gap remains missing.

In the latest run there were no gaps and no fills.

## 7. Outliers and MAD

An outlier is an observation far from the normal pattern. The screen uses daily log returns.

MAD means median absolute deviation. It measures the typical distance from the median return. The modified z-score then expresses each return as a distance from the median in MAD units.

The pipeline flags a return when the absolute modified z-score is above 3.5. It does not delete the return. Large genuine market moves, especially in March 2020, should be flagged for review but retained.

## 8. Corporate actions

A corporate action is a company event that changes share price or share count. Dividends and stock splits are the main examples in this project.

The pipeline writes these events to a separate log. That allows a reviewer to check whether a large price movement occurred on a dividend or split date.

## 9. Realised volatility

Realised volatility measures how much a price actually moved over a past period. The pipeline calculates it from daily log returns over 20 and 60 sessions and annualises the result.

A 60-day volatility of 40 percent does not predict that the stock will move 40 percent in the next year. It is an annualised summary of recent daily movement.

## 10. Beta and correlation

Correlation measures whether two return series tended to move in the same direction at the same time.

Beta combines correlation with relative volatility. A beta of 1 means the stock moved broadly in line with the benchmark over the measured period. A beta above 1 means it moved more than the benchmark for a given benchmark move. A beta below 1 means it moved less.

The snapshot uses the latest 252 daily sessions. Beta is not a permanent company property.

## 11. Drawdown

Drawdown is the fall from a previous high. If a stock reached 100 and is now 80, the drawdown is 20 percent.

The snapshot uses the highest adjusted close in the latest 252 sessions. Cameco had the largest value in the latest run, at 41.1 percent below its 252-day high.

## 12. Weekly strategy refresh

Daily data are converted to weekly adjusted prices by taking the last available price in each Friday week. The latest 104 weekly returns are used to calculate current allocations.

The four methods are:

- Equal Weight: 10 percent in each stock.
- Minimum Variance: choose weights that minimise estimated portfolio variance.
- Risk Parity: choose weights so each stock contributes a more equal share of portfolio risk.
- Minimum CVaR: choose weights that minimise the average loss in the worst 5 percent of weekly observations in the estimation window.

All methods are long only, with a 20 percent position cap and a 40 percent sector cap.

## 13. Why the strategy numbers are not forecasts

The metrics shown for each allocation are calculated on the same 104 weeks used to select the weights. That makes them useful for checking the optimisation, but it does not make them expected future performance.

A separate out-of-sample test would be required before comparing the methods as investment strategies. The earlier V2 backtest serves that purpose for its own test window and remains unchanged.

## 14. How to explain the project in one minute

The TSX Portfolio project originally used a fixed price history. This extension builds the system that would feed that project in real use. It downloads daily and intraday prices for ten stocks and the benchmark, stores the raw data, validates the prices, checks for missing sessions and unusual returns, records dividends and splits, creates risk features, and refreshes selected portfolio weights. Every cleaning decision is written to a report, and the strategy layer refuses to update if a daily symbol fails. The main contribution is data reliability and repeatability, not a new claim that one strategy will perform best in the future.
