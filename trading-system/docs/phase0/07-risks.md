# 07 — Risks

Ranked by expected impact on the mandate.

| # | Risk | Impact | Mitigation |
|---|---|---|---|
| R1 | No family has a real edge after costs and multiple testing | Project ends at Phase 3 or 6 with no portfolio | Accepted as the probable outcome (01, "Expected outcome"). Report plainly. A conservative configuration of whatever passes, if anything. |
| R2 | Overfitting through researcher degrees of freedom (level definitions, windows, filters) | Inflated OOS Sharpe and leveraged losses live | Pre-registered definitions (04). Registry with full trial count. DSR, PBO, random benchmark. Pooled parameters. Hold-out used once. |
| R3 | Backtest/live cost mismatch: Dukascopy spreads vs. broker, demo vs. live fills | Intraday edges vanish live | Broker spread profile ≥ data spread. 1.5× stress gate. Small live stage before scaling. Auto-disable on cost drift. |
| R4 | Gap risk: SNB-type events, weekend gaps, flash crashes | Losses far beyond stops, possibly the whole account (negative balance protection caps it at equity) | Weekend policy. Tier-1 news flat. Jump overlay in the Monte Carlo. Breaker as backstop. Size against gap-adjusted risk for overnight positions. |
| R5 | Kelly on an overestimated Sharpe | Negative growth at high fractions (06, §6) | 50% haircut. c ≤ 0.5 default. Hard cap 0.75. Hard limits bind first. |
| R6 | Carry book destroyed by broker financing markup | D underperforms the backtest | Markup modelled from the broker's published rates. Carry-only attribution reported. D also reported with momentum only. |
| R7 | Data defects (missing hours, spikes, calendar errors) | False signals, wrong fills | Phase 1 validation report. Calendar validated against volatility spikes. Flag, never silently drop. |
| R8 | Look-ahead bugs (swing confirmation, daily ATR, rate data, calendar revisions) | Fictitious edge | Truncation-invariance property tests on every feature. +1 bar delay gate. Policy rates (no revisions). |
| R9 | Operational: disconnects, duplicate orders, state loss on restart | Unintended exposure | Idempotent client order IDs. Reconcile before trading. Heartbeat and watchdog. Kill switch. Max orders/day. Fat-finger checks. Runbook. |
| R10 | Regulatory and broker: leverage changes, product withdrawal, API restrictions for EU retail | Strategy infeasible | Verify limits with the broker before Phase 8. Instrument config per broker. Margin check in `RiskOverlay`. |
| R11 | Small-account frictions: min lot size, IBKR USD 2 min commission, fixed monthly costs | Realised risk ≠ model risk, cost drag | Size rounding modelled in the backtest. Broker choice (D5). Fixed costs in the Monte Carlo. |
| R12 | Prop firm counterparty risk: rule changes, denied payouts, firm closures (2023–2024 precedent) | Fees lost | EV calculation treats the payout as probabilistic. Optional module only. |
| R13 | Hold-out contamination by known 2024–2026 history | Optimistic hold-out | Hypotheses frozen before Phase 3. Contamination disclosed in the verdict. |
| R14 | Psychological override: manual intervention during drawdowns | Breaks the system's statistics | Every manual action is journaled. Breaker resume needs a written review. |
| R15 | Tax and reporting errors | Fines | Yearly EUR export using ECB reference rates. Format chosen per tax residence (D8). |
| R16 | Secrets leakage | Account compromise | `.env` only, never logged. Trade-only keys without withdrawal, IP whitelist. Pre-commit secret scan. |

## Statement on expected returns
No number in these documents is a forecast. Section 06, §2 shows what Kelly sizing implies *if* the true Sharpe equals the haircut estimate. Backtest results, when they exist, will be labelled in-sample, OOS, hold-out, paper or live. They are never to be read as expected future returns.
