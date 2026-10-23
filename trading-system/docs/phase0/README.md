# Phase 0 — Design and Spec Review

Status: **awaiting approval**. Phase 0 contains no code by design.

| File | Content |
|---|---|
| [01-spec-critique.md](01-spec-critique.md) | Contradictions, gaps, unrealistic expectations, proposed resolutions |
| [02-data-sources.md](02-data-sources.md) | Concrete data sources, coverage, licensing, timezone, known issues, assumed data |
| [03-architecture.md](03-architecture.md) | File tree, module responsibilities, interfaces, data flow, test plan |
| [04-strategy-definitions.md](04-strategy-definitions.md) | Exact algorithmic definitions for families A–F and the regime classifier |
| [05-validation-protocol.md](05-validation-protocol.md) | Splits, CPCV, walk-forward, random benchmark, deflated Sharpe, gates, registry |
| [06-kelly-and-risk-math.md](06-kelly-and-risk-math.md) | Kelly sizing, haircut, drawdown math, limit interactions, Monte Carlo design |
| [07-risks.md](07-risks.md) | Project, model, market, operational, regulatory risks |
| [08-decisions-needed.md](08-decisions-needed.md) | Decisions required before Phase 1 |

## Key conclusions

1. **The per-family gate is the binding constraint and is probably unreachable.** "Net OOS Sharpe >= 1 after haircut" with a 50% haircut means a raw OOS Sharpe >= 2.0 per family. Published, retail-accessible edges in this universe are mostly in the 0.3–0.8 range before haircut. Expected result under the spec as written: zero or one family passes. A two-level gate is proposed (01, D1).
2. **Multiple testing sets a high floor.** With ~500 trials over 14 years of development data, the expected maximum Sharpe of pure-noise strategies is ~0.8 per year. Any result below that is indistinguishable from luck (06, §5).
3. **Half Kelly and the hard limits are not consistent.** At true Sharpe 1.0, half Kelly runs at ~50% annual volatility: the 5% daily halt fires on ~5.6% of days, the 10% weekly halt on ~7.5% of weeks, and the 35% circuit breaker trips on average every **~1.2 years**. The 6% total-open-risk cap, defined as the sum of losses at stop, limits the daily-swing family D to ~15–29% annual volatility. In practice the hard limits, not Kelly, set the leverage (06, §3).
4. **The hold-out has almost no statistical power.** For 2.75 years at Sharpe 1, the standard error is ~0.75, so the hold-out works only as a gross-failure detector. Three months of paper trading says nothing about Sharpe; paper trading is only an operational test (01, U4).
5. **This container cannot reach any data source.** Dukascopy, FRED, TrueFX and OANDA were all refused by the environment network policy. Phase 1 needs an allowlist change or must download on the user's machine (02, §0).
6. **Broker choice changes the cost model enough to change verdicts.** The IBKR FX minimum commission of USD 2 per order is ~2 bp of a EUR 10k notional, which is prohibitive for small intraday trades. MT5 conflicts with the Linux Docker target. OANDA (EU entity) is the default recommendation if its v20 API is confirmed for EU retail accounts (08).
7. **The repository is wrong.** This work currently sits in `ai-news-api`. Use a dedicated repository before Phase 1 (08, D0).
