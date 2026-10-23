# 05 — Validation Protocol

## 1. Data splits (fixed now)

| Segment | Period | Use |
|---|---|---|
| Development | 2010-01-01 → 2023-12-31 (indices: first verified month → 2023-12-31) | CPCV, walk-forward, every family decision |
| Hold-out | 2024-01-01 → last available date (~2026-09-30) | One evaluation in Phase 6, unlocked by token |

D may extend development back to 2003 for daily bars if the data passes validation. That extension is pre-declared, not chosen after seeing results.

## 2. Combinatorial purged cross-validation (parameter selection)
- **Split.** N = 10 contiguous groups, k = 2 test groups. That gives C(10,2) = 45 splits and φ = 9 backtest paths.
- **Purging.** Drop every training trade whose [entry, exit] interval overlaps a test group.
- **Embargo.** Drop training trades starting within h after a test group, where h = max(1 trading day, the family's maximum holding period). For D, h = 20 trading days.
- **Selection rule (robust region, not argmax).**
  1. For each config, compute the median Sharpe across the 9 paths.
  2. A config is eligible if every immediate grid neighbour has a median ≥ 0.7 × its own median.
  3. Pick the eligible config with the highest median. If none is eligible, the family fails selection.
- **PBO.** Probability of backtest overfitting via CSCV (Bailey, Borwein, López de Prado, Zhu 2017) on the config × time-block matrix of returns. Gate: PBO ≤ 0.25.

## 3. Walk-forward (deployment emulation)
- Rolling window: 4 years train, 1 year test, 1 year step.
- Each step applies the §2 selection rule to the train window only.
- The concatenated test years form the **WF OOS series**, the series used for every gate and for portfolio construction.

## 4. Random-entry benchmark
- **Per family, 1000 runs, seed fixed.** Each run uses:
  - the same number of trades per instrument and per year as the strategy;
  - entry timestamps sampled uniformly from the family's *allowed* entry windows (same sessions, same news and rollover exclusions);
  - direction 50/50 random;
  - identical exit rules, stop/target geometry in ATR units, sizing and costs.
- **Implementation.** `outcome_kernel.py` precomputes, for each candidate entry bar and direction, the exit time and P&L under the family's exit rules. That costs O(n) once per family-config. Each random run is then O(trades).
- **Gate.** Strategy net Sharpe and net expectancy both above the 95th percentile of the random distribution.

## 5. Sharpe statistics
- Standard error: SE(SR) = √((1 − γ₃·SR + (γ₄ − 1)/4·SR²)/T), where γ₃ is skewness, γ₄ is kurtosis and T is the number of periods (Lo 2002, Mertens 2002). It is annualised consistently.
- PSR (Bailey & López de Prado 2012) against SR* = 0.
- DSR (Bailey & López de Prado 2014). SR* = √V[SR_trials] · ((1 − γ)·Φ⁻¹(1 − 1/N) + γ·Φ⁻¹(1 − 1/(N·e))), where:
  - N is the effective trial count (registry count, clustered by correlation of trial returns per López de Prado 2018);
  - V[SR_trials] is the variance of trial Sharpes from the registry;
  - γ is the Euler–Mascheroni constant.
- **Gate:** DSR ≥ 0.95.

## 6. Experiment registry rules
- A trial is a distinct (family, config_hash, instrument set, timeframe, split) evaluated on any development data. Every trial is written before its results are read. Failed and abandoned runs count.
- `config_hash` is the SHA-256 of canonical YAML (sorted keys, normalised numbers). `data_version` is the SHA-256 of the data manifest. `git_commit` is HEAD, and a dirty tree is refused for registry runs.
- The hypothesis file `research/hypotheses/<FAMILY>.md` must exist in a commit older than the trial's commit. The registry verifies this through git.

## 7. Family gates (all must pass on WF OOS, base costs unless stated)

| # | Check | Pass condition |
|---|---|---|
| G1 | Net Sharpe | Per decision D1 (proposed: raw ≥ 0.5; spec literal: haircut ≥ 1.0, i.e. raw ≥ 2.0) |
| G2 | Cost stress 1.5× (spread, commission, slippage, financing markup) | Sharpe > 0 and ≥ 0.6 × base Sharpe |
| G3 | +1 bar delay | Sharpe > 0 and ≥ 0.5 × base Sharpe |
| G4 | Random benchmark | > 95th percentile (Sharpe and expectancy) |
| G5 | DSR | ≥ 0.95 with full trial count |
| G6 | PBO | ≤ 0.25 |
| G7 | Trade count | ≥ 300 OOS (D: ≥ 300 rebalance trades and ≥ 10 OOS years) |
| G8 | Stability | Net P&L positive in ≥ 60% of calendar years. No single year > 40% of P&L. No single instrument > 50% of P&L. |
| G9 | Exit audit | For every exit type, report count, win rate, average P&L and share of total loss. A disproportionate loss share must be explained before the verdict. It cannot be tuned away. |
| G10 | Correlation report | Daily OOS P&L correlation and tail (worst-decile) correlation to every already-passed family |

A family that fails any gate is reported with every metric and dropped. It is never re-parameterised.

## 8. Family report content
- Metrics table first (OOS, net):
  - total return, CAGR, Sharpe, Sortino, max drawdown and its duration;
  - win rate, profit factor, expectancy (R and EUR), average win and loss, trade count, exposure time;
  - results by exit type, and the comparison against buy-and-hold and against the random-benchmark percentile.
- Breakdowns: per year, per session, per instrument, per regime (V0 labels, informational only).
- In-sample (CPCV train) and out-of-sample are reported separately and labelled.
- Parameter sensitivity table across the whole grid.
- Gate table with the verdict.

## 9. Portfolio and hold-out (Phases 5–6)
- **Portfolio.** HRP weights estimated walk-forward on the WF OOS series of passed families. The combined OOS Sharpe uses only weights known at each step.
- **Hold-out (single run).** The frozen portfolio (families, configs, weights, Kelly fraction, limits) runs once over the hold-out. Pass criteria:
  - Sharpe, max drawdown and trade counts all inside the Monte Carlo 5–95% band for a period of that length;
  - realised costs inside the 1.0–1.5× band.
- The result is final.
