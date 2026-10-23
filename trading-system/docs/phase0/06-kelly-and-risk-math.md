# 06 — Kelly, Leverage and Risk Math

Notation:
- S: annualised Sharpe of the combined portfolio (excess return over volatility).
- σ: annualised portfolio volatility.
- c: Kelly fraction.
- The risk-free rate is ignored. The model is continuous-time with i.i.d. returns unless stated otherwise.

## 1. Kelly for a portfolio
- Log-growth rate at volatility σ: g(σ) = S·σ − σ²/2. It is maximised at σ* = S (full Kelly), where g* = S²/2.
- For several strategies with mean vector μ and covariance Σ, the Kelly weights are f* = Σ⁻¹μ, and S² = μ'Σ⁻¹μ.
  - Σ⁻¹μ is unstable, so the allocator uses HRP weights w.
  - The book is then scaled to volatility c·S_h, where S_h = h·Ŝ_OOS.
  - h = 0.5 is the haircut, and Ŝ_OOS is the WF OOS Sharpe of the w-weighted combination.
- Scale factor on unit-risk family budgets: k = c·S_h / σ̂_p(w). Here σ̂_p(w) is the annualised volatility of the w-weighted unit-risk OOS series.
- Fractional Kelly c, *if the true Sharpe equals S_h*:
  - σ = c·S_h;
  - log growth g = (c − c²/2)·S_h²;
  - 2g/σ² = 2/c − 1.

## 2. Closed-form reference table (S_true = S_h = 1.0)

| c | Annual vol | Log growth | ≈ Annual growth | P(ever losing 30% from now) | 50% | 70% | E[time to first 35% DD] | P(day ≤ −5%) | P(week ≤ −10%) |
|---|---|---|---|---|---|---|---|---|---|
| 0.25 | 25% | 0.219 | 24.5% | 8.2% | 0.8% | 0.02% | 10.7 y | 0.07% | 0.2% |
| 0.50 | 50% | 0.375 | 45.5% | 34.3% | 12.5% | 2.7% | 1.2 y | 5.6% | 7.5% |
| 0.75 | 75% | 0.469 | 59.8% | 55.2% | 31.5% | 13.4% | 0.43 y | 14.5% | 16.8% |
| 1.00 | 100% | 0.500 | 64.9% | 70.0% | 50.0% | 30.0% | 0.22 y | 21.4% | 23.5% |

Formulas:
- **Probability of ever falling to fraction y of current wealth:** P = y^(2/c − 1). This does not depend on S. With certainty some drawdown of every size eventually occurs from *some* peak, so this measures "from a given point".
- **Expected time to a drawdown of log-size a** (here a = −ln 0.65) for drifted Brownian motion with drift m = g and volatility σ (Taylor 1975):
  E[τ_a] = (σ²/(2m²))·(e^{2ma/σ²} − 1 − 2ma/σ²).
- **Daily and weekly halt probabilities:** normal approximation, mean ignored. Fat tails make them higher.
- **These are not forecasts.** They show the shape of the trade-off and assume S_true = 1.0.

### Consequence
- At the default c = 0.5, the 35% circuit breaker is reached on average every ~1.2 years, and the daily halt fires about once a month.
- "Half Kelly + terminal 35% breaker" means the strategy spends most of its life stopped. Decision D4.

## 3. Interaction with the hard limits
Annual volatility each limit permits:

| Limit (spec) | Implied max annual vol | Note |
|---|---|---|
| 6% open risk, D, stops at 4·ATR_D, 11 positions, ρ̄ = 0.3 | ~14% | Sum-of-stop definition, sized at 0.55% per position |
| same, stops at 2·ATR_D | ~29% | |
| 6% 1-day ES99 (proposed for D) | ~36% | ES99 = 2.665σ_daily under normality |
| 2% per intraday trade, R std ≈ 1, n trades/year | 2%·√n | n = 250 → 32%; n = 500 → 45% |

ESMA notional per intraday trade at 2% risk:

| Stop distance | Notional / equity |
|---|---|
| 0.10% (EURUSD ~11 pips) | 20× |
| 0.15% | 13.3× |
| 0.30% | 6.7× |

Two concurrent tight-stop trades on majors reach the 30:1 cap. On AUD, NZD, gold and indices (20:1), one trade can.

**Conclusion.** Unless open risk is redefined for D, the effective portfolio volatility is capped near quarter Kelly by the hard limits. The Kelly fraction then acts as an upper bound, not a target. The Monte Carlo reports the realised fraction.

## 4. Drawdown taper and anti-martingale compounding
- **Sizing base.** Current equity E_t, recomputed at every order. This alone is proportional, anti-martingale compounding.
- **Taper.** Risk multiplier τ(DD) = max(0, (D_max − DD_t)/D_max)^p, with DD_t = 1 − E_t/HWM_t, D_max = 0.35, p = 1.
  - This is the Grossman–Zhou (1993) drawdown-constrained Kelly policy in simplified form.
  - In continuous markets it makes DD = D_max unreachable; only gaps can cross it.
  - Recovery above the previous high water mark scales size back up automatically.
- **Final risk per trade.** min(2%, k·w_family·r_unit·τ(DD)). The total-open-risk cap (6%) and the ESMA margin check are applied afterwards.
- **Breaker.** 35% stays as a backstop for gap events: flat, trading halted, manual review required.
  - Resume requires a signed review entry in the journal.
  - Proposed resume level: 0.5 × previous risk until a new HWM.
- **Forbidden and asserted in code:** martingale sizing, averaging down, grid orders, stop removal or widening after entry.

## 5. Multiple-testing floor
Expected maximum Sharpe of N zero-edge trials over T years, with SE ≈ 1/√T:

| N | E[max z] | T = 14 y → SR floor |
|---|---|---|
| 63 (Phase 3 budget) | 2.36 | 0.63 |
| 240 | 2.83 | 0.76 |
| 500 | 3.05 | 0.82 |
| 1000 | 3.26 | 0.87 |

A family's raw OOS Sharpe must clearly exceed this floor before the DSR can reach 0.95.

## 6. Sharpe misestimation
Log growth when sizing on S_h = 1.0 but the true Sharpe differs:

| True S | c = 0.25 | c = 0.50 | c = 0.75 |
|---|---|---|---|
| 0.00 | −0.031 | −0.125 | −0.281 |
| 0.25 | +0.031 | 0.000 | −0.094 |
| 0.50 | +0.094 | +0.125 | +0.094 |
| 0.75 | +0.156 | +0.250 | +0.281 |
| 1.00 | +0.219 | +0.375 | +0.469 |

- At c = 0.75, the true Sharpe must exceed ~0.375 × S_h (i.e. ~19% of the raw OOS Sharpe) just to grow at all.
- The 50% haircut plus a ≤ 0.5 fraction is the minimum sensible protection. The hard cap at 0.75 is retained.

## 7. Monte Carlo risk report (Phase 5)

### Paths
- 10,000 paths, horizon 5 years, daily steps, fixed seed.
- Returns: stationary block bootstrap (mean block 20 days) of the combined WF OOS daily return series of the unit-risk portfolio.

### Sharpe uncertainty
- Per path, draw S_path ~ N(S_h, SE(Ŝ_OOS)²), not truncated.
- Shift the path's bootstrap returns so their mean matches S_path × the target volatility.

### Fat tails and gaps
- The empirical tails are kept by the bootstrap.
- A Poisson jump overlay is added:
  - rate λ = 1/year;
  - jump size drawn from the empirical distribution of the worst weekend and event gaps across instruments, in units of stop distance;
  - stops fill at the gap price, so losses can exceed the stop. Examples: CHF 2015-01-15, GBP 2016-10-07, JPY 2024-08-05.

### Rules applied inside each path
Taper, per-trade and open-risk caps (as realised in the backtest), daily and weekly halts, the breaker (variants: terminal; review → resume at 0.5×), ESMA margin close-out at 50%, negative balance floor at 0, monthly fixed costs in EUR.

### Outputs per c ∈ {0.25, 0.375, 0.5, 0.625, 0.75}
- Median and 5/25/75/95 percentiles of annual geometric growth.
- P(max DD ≥ 30%, 50%, 70%).
- Median time to recovery from max DD.
- P(equity < EUR floor at any time).
- Breaker trips per path.
- Halt frequency.
- Fraction of time the limits bind.

Equity paths are never clipped or floored, other than the broker's negative-balance protection, which is the real rule.

## 8. Prop-firm sizing (Phase 7)
- **Objective.** Maximise EV = P(pass)·E[funded payout | pass] − fee over risk-per-trade r. Expected attempts until a pass are 1/P(pass), and breakeven needs E[payout | pass] ≥ fee / P(pass).
- **Simulation.**
  - Same bootstrap engine, with the firm's rules: daily-loss and max-loss definitions (balance vs. equity, static vs. trailing), minimum trading days, time limit, news and weekend rules.
  - Live enforcement halts at 80% of every loss limit.
- **Character of the optimum.** Without a time limit and with a positive edge, P(pass) rises as r falls (gambler's ruin with drift). With a time limit, an interior optimum appears. The optimiser reports the whole curve, not one point.
