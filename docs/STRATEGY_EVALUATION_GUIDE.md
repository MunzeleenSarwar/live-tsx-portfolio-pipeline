# Strategy Evaluation Guide

Plain-language notes for the project: Is This Trading Strategy Actually Profitable?

## The strategy in one paragraph

At each month end, rank the ten TSX stocks on 12-1 momentum: the return from 13 months ago to 1 month ago. Hold the top three in equal weight for the next month, then repeat. Charge 10 basis points on turnover.

## Expected value

A trade is a bet. If it wins with probability p, gains R for every 1 it loses, its expected value is p x R minus (1 - p). Win rate alone means nothing without the payoff size. A 35 percent win rate at a 3 to 1 payoff beats a 55 percent win rate at 1 to 1.

Break-even win rate is 1 / (1 + R). At R = 1.46, break-even is 40.7 percent. The strategy's lots won 56.2 percent of the time, so the sample edge is +0.38R per lot. The margin is real but thin: lose 10 points of win rate and 20 percent of payoff at the same time and the edge is zero.

## The t-statistic trap

The monthly mean return has a t-statistic of 3.27, which looks decisive. The QuantFrame preview makes the opposite point with a smaller edge: a real edge can fail to reach t = 2 in one year of data. Both directions carry the same lesson: a t-statistic measures the sample, not the truth, and it says nothing about whether the sample was fairly chosen.

## Bootstrap and placebo

The bootstrap resamples the 111 realised months to test whether the result depends on a few of them. It does not: 96.7 percent of paths beat the benchmark.

The placebo test is stronger. Picking three random stocks each month in the same universe returned a median 19.6 percent a year. The universe was chosen in 2026 and is full of the decade's winners. Much of the strategy result is the universe, not the rule.

## Stress tests that mattered

Costs did not matter: the strategy survives 50 basis points. Removing the best 12 months mattered: annualised return falls to 6.1 percent and the t-statistic to 1.16. A result that needs its best months is fragile.

## The decision rule

Six tests were set: positive expected value, t-statistic at least 2, bootstrap beat rate at least 80 percent, Sharpe at least equal to the equal-weight universe, drawdown within 25 percent, and a point-in-time universe. The strategy passed the first three and failed the last three.

## One-minute explanation

The momentum rule was profitable in the sample and beat the index in most resampled paths. It still should not be traded, because simply holding the same ten stocks in equal weight gave a better Sharpe ratio with a smaller drawdown, and the ten stocks were picked with hindsight. Profitable in a backtest is a statement about the test. A trading decision needs the test to be fair.
