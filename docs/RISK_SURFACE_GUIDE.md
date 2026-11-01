# Risk Surface Guide

Plain-language notes for the project: Exploring a Portfolio Risk Surface.

## Two surfaces

A portfolio of Enbridge and TD has a value for every pair of prices and a volatility for every pair of weight and correlation. Plotted, value is a flat plane. Volatility is a curved surface with a valley. Calculus is the set of tools for reading surfaces: slope in one direction, slope in all directions, curvature, and local approximation.

## Partial derivatives

A partial derivative changes one input and holds the other still. For value, the derivative with respect to a stock price is just the number of shares held. For volatility at the safest weight, the derivative with respect to the weight is zero. That is not a coincidence: at the bottom of a valley the ground is flat.

The derivative of volatility with respect to correlation is 0.061 at the base point. Correlation is the direction in which risk actually moves for this pair.

## Gradient and directional derivatives

The gradient collects the partial derivatives into one vector: the direction of steepest increase. A directional derivative prices any combined move. Enbridge down 10 percent and TD up 10 percent nearly cancel in this portfolio, at +$193, because the two allocations are close in size. Both down 10 percent costs the full 10 percent. Diversification is a statement about directions.

## The Hessian and the saddle

The Hessian collects second derivatives: curvature. Value has a zero Hessian; a plane does not curve. Volatility has eigenvalues 0.475 and -0.030. Mixed signs mean a saddle. Along weight the surface is a bowl, so a safest weight exists. Along correlation it is a shallow cap, because volatility is a square root of something linear in correlation, and square roots bend downward. A surface can be both, and this one is.

## Taylor approximations

A first-order approximation is the tangent plane. A second-order one adds the Hessian's curvature. For moves near the base point both are accurate to a few hundredths of a percentage point. For a joint move of weight +0.20 and correlation -0.20, the first-order error reaches 1.13 percentage points and the second order reduces it to 0.25. For the largest correlation increase, the second order overshoots and the first order is closer. Approximations have a working range, and the honest output is the error table, not just the formula.

## Correlation scenarios

Correlation from -0.5 to 0.9 moves minimum volatility from 8.6 percent to 16.8 percent. It moves the safest Enbridge weight only from 49.4 percent to 40.6 percent, because the two stocks have similar volatilities. Practical consequence: this portfolio does not need rebalancing when correlation drifts. It needs its risk level rechecked.

## One-minute explanation

Value is linear, so its calculus is exact and simple. Risk is not. At the safest mix, risk is flat in the weight direction and rising in the correlation direction, and the surface is a saddle. The pair cuts volatility from about 17 percent to about 12 percent only while correlation stays low. The map is local, built from the last 252 trading days, and it describes the neighbourhood of the current portfolio rather than the whole future.
