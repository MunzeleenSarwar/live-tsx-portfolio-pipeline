# Regime Structure Guide

This guide explains the SVD regime project in plain language.

## 1. A market day as a point

Imagine a table with one row for each trading day and one column for each of the ten stocks. Each cell is that stock's return on that day.

One row is a list of ten numbers. In geometry, a list of ten numbers is a point in ten-dimensional space. A normal day sits near the centre. A market shock sits far away from the centre. Two days can be equally far from the centre but in different directions: one can be a broad fall, while another can be a fall in energy stocks and a rise in technology stocks.

That is the basic idea behind the project.

## 2. What SVD does

SVD looks for the directions in this ten-dimensional space that explain the most movement.

Think of it as rotating the map. The data do not change. The axes change. The first new axis, PC1, is the single combination of stock returns that explains the largest share of variance. PC2 is the next pattern, at a right angle to PC1. PC3 is the next pattern after those two.

Each direction has loadings. A loading shows how strongly each stock belongs to that pattern.

## 3. What a singular value means

Each direction has a singular value. Square it, divide by the sum of all squared singular values, and the result is the share of variance explained by that direction.

In this sample:

- PC1 explains 35.6 percent.
- PC1 and PC2 explain 54.9 percent.
- PC1 to PC3 explain 68.6 percent.
- PC1 to PC5 explain 85.8 percent.

The market is structured, but no one direction is the whole market.

## 4. How to read PC1

Every stock has a positive PC1 loading. When the PC1 score is positive, the stocks generally rose together. When it is negative, they generally fell together.

Shopify's PC1 loading is much larger than the others. That does not mean Shopify is the market. It means Shopify's daily returns vary more, so it contributes more to total raw return variance. The standardized check corrects for this scale difference.

## 5. How to read PC2 and PC3

PC2 places Shopify on one side and Canadian Natural Resources and Cameco on the other. It is a Shopify against energy pattern.

PC3 places Cameco and Barrick Mining on one side and CAE and Canadian Natural Resources on the other. It separates uranium and gold miners from oil and industrial stocks.

These names are readings of the loadings. They are not official factors.

## 6. Distance from the centre

Distance measures how far a day is from the average day. Large distance means the combined size of the ten returns was unusual.

The most extreme day was 16 March 2020. Distance tells size. It does not by itself say whether the move was broad or stock-specific.

## 7. Residual: the part the main patterns miss

A rank-3 reconstruction rebuilds each day using only PC1, PC2 and PC3. The residual is the difference between the real day and the rebuilt day.

If a day has a large distance but a small residual share, it was a large move that followed the main market patterns. That was true on 16 March 2020.

If a day has a large residual share, its mixture of stock moves was unusual even if the total move was not the largest.

## 8. The four trailing states

The project also labels each day with a simple descriptive state based on the benchmark's previous 20 trading days:

- Calm advance
- Calm pullback
- High-volatility advance
- High-volatility decline

High volatility means trailing volatility in the highest quarter of the full sample. Because that cutoff is calculated from the full sample, the labels describe history. They are not a trading rule that was available in real time.

## 9. The main regime finding

High-volatility decline days were farther from the centre than calm advance days. They also had a lower residual share. That means a larger part of their movement followed the first three common directions.

In plain terms: in stress, stocks moved together more. In calm advances, more of the movement belonged to individual stocks.

## 10. Angles between days

The angle compares the pattern of returns on one day with the pattern on the previous day.

- Near 0 degrees: similar pattern
- Near 90 degrees: largely unrelated pattern
- Near 180 degrees: opposite pattern

The average angle is about 90 degrees. Daily return patterns therefore do not persist much from one day to the next.

A large angle alone is not enough. If both days were small, the angle can look dramatic while little happened. The project therefore counts a material transition only when the angle is above 135 degrees and both days were far from the centre. There were 113 large-angle transitions, but only 19 material ones.

## 11. Why the standardized check matters

Raw returns give more weight to stocks that normally move more. Standardized returns divide each stock by its own volatility first, so each stock starts on a more equal scale.

Standardized PC1 is much more even across Brookfield, TD, Enbridge, CAE and Canadian Natural Resources. That shows the common correlation pattern is broad, while the raw PC1 loading on Shopify is mainly a volatility scale effect.

## 12. What this project does not do

It does not forecast tomorrow's return.

It does not say a regime will continue.

It does not replace the earlier hidden Markov model. That model estimated state probabilities through time from weekly data. This project describes the geometry of daily returns across stocks.

## 13. One-minute explanation

Each trading day was converted into a ten-number return vector. SVD found the directions that explain most of the movement in those vectors. Three directions explain 68.6 percent of daily variance. The first is a broad market direction, although Shopify dominates it in raw returns because Shopify is more volatile. The next directions separate Shopify from energy and uranium and gold miners from oil and industrials. Stress days sit farther from the centre and follow the main directions more closely, which means stocks move together more in a crisis. A rank-3 model still misses 31.4 percent of variance, so the market can be compressed for interpretation but not reduced to three numbers without loss.
