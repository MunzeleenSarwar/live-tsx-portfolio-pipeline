# Trade Design Guide

Plain-language notes for the project: Designing an Optimal Trade.

## The trade

Long Canadian Natural Resources at $78.39 on 30 October 2026, for a hypothetical $1,000,000 account. CNQ ranked first on 12-1 momentum. Stop $74.62. Target $84.04. Final size 2,551 shares.

## Profit as a function of size

Expected profit from a trade is roughly a straight line in the number of shares. Market impact bends the line down, because each extra share is a little more expensive to trade than the last. That is why the impact term is quadratic: cost per share grows with size, so total cost grows with size squared.

Setting the derivative to zero gives the size where the next share adds nothing. For CNQ that size is about 302,000 shares. It is correct maths and a useless answer, because the stock is far too liquid for impact to be the real limit on a $1,000,000 account. The lesson: when a model's optimum is absurd, the model is missing the binding constraint.

## The risk penalty

Add a penalty for variance and the function bends down sooner. The optimum is where the extra edge from one more unit of leverage equals the extra penalty. Here it is 0.34 times capital. Risk, not impact, is the first real constraint.

## Kelly, and why it is rejected

Kelly gives a fraction of capital to risk: 26.9 percent here. Two mistakes follow if it is read as a position size. First, it is a risk fraction, not a position weight; divided by the stop distance it implies a position above 500 percent of capital. Second, Kelly assumes many repeated independent bets and no gaps through the stop. A single stock trade has neither. Quarter, half and full Kelly are all above this project's caps.

## Stops

Under a driftless random walk, the chance of touching the target before the stop is stop distance divided by stop plus target distance. At a 1.5 payoff that is 40 percent, which is also the break-even win rate. This does not change when the stop widens, as long as the target widens in proportion. Widening a stop changes the dollars lost, not the no-edge probability. Stop placement is a dollar decision.

The stop here is two times the 14-day average true range. That puts it just above the 20-day moving average, so the risk exit and the trend exit are nearly the same event.

## Execution

The order is 0.03 percent of a day's volume. Impact is below 0.2 basis points if it is done in a day. The cost of waiting, measured as a timing risk allowance, is about 40 basis points a day and grows with the square root of time. At small size, speed is cheap and delay is expensive. Execute within one day with a limit order and a no-chase rule.

## Caps decide

Three caps sit below every optimum: position at most 20 percent of capital, loss at the stop at most 1 percent of capital, no leverage. The 20 percent cap binds. The final design risks 0.96 percent of capital to make 1.44 percent at the target, with an expected profit of about $3,485 under the scenario win rate. The companion evaluation limits the whole design to paper trading.
