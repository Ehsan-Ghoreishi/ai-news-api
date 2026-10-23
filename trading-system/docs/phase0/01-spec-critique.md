# 01 — Spec Critique

Each item is labelled **C** (contradiction), **G** (gap) or **U** (unrealistic expectation) and carries a proposed resolution. Items marked *decision* are repeated in [08-decisions-needed.md](08-decisions-needed.md).

## Contradictions

### C1. Two undefined haircuts and two gates (decision D1)
- §1 requires each family to reach "net OOS Sharpe >= 1 after haircut". §4 defines the haircut as 50% of the OOS estimate. §7 requires the *combined* portfolio to reach >= 1.0 after haircut.
- Read literally, every family needs a raw OOS Sharpe >= 2.0. If every family clears 2.0, the portfolio gate in §7 is redundant: two families at 2.0 with ρ = 0.2 already combine to ~2.6.
- **Proposed resolution:** two levels.
  - Family gate: statistical significance (DSR >= 0.95 with the full trial count) plus raw OOS net Sharpe >= 0.5, plus every robustness check in §3.
  - Portfolio gate: haircut combined Sharpe >= 1.0, i.e. raw combined OOS >= 2.0. Keep this one as written. It is the one that matters for leverage.
  - Alternative: keep the spec literally and accept that the expected outcome is "no family passes".

### C2. Family C needs the regime classifier, which is scheduled for Phase 4
- C is defined as "only in range regime", but the classifier arrives in Phase 4, after 3C.
- **Resolution:** Phase 2 ships `RuleRegimeV0`, a fixed, pre-registered, untuned rule set (04, §R). 3C is validated with V0. Phase 4 evaluates any learned or tuned classifier as additional trials.

### C3. Regime gating after validation is rescue tuning
- §3 says "never tune to rescue". Adding a regime gate to a family that failed ungated is exactly that.
- **Resolution:** a gating hypothesis counts only if it is written into the family's hypothesis file *before* the family's first run. Phase 4 may apply gating only to families that already passed ungated (its effect is reported), or to families whose gating was pre-registered (C only, as specified). Every gating variant is counted as a trial.

### C4. "Intraday flat before high-impact news" vs. families A2, A3 and F
- US data at 08:30 ET falls inside the NY-open window. ISM at 10:00 ET lands exactly at the entry of a 30-minute index ORB. Applied naively, the news-flat rule removes a large share of A2/A3 trading days.
- **Resolution:** a tiered calendar (02, §4).
  - Tier 1 (NFP, CPI, FOMC, ECB/BoE/SNB/BoC/RBA/RBNZ decisions): every intraday family is flat from T−5 min until the settle condition (04, F) is met.
  - Tier 2 (ISM, retail sales, GDP advance, PCE, PMIs): no *new entries* in [T−5, T+10] min, existing positions may be held.
  - Events are mapped to instruments by currency and index.

### C5. Kelly target vs. hard limits (see 06, §3)
- At half Kelly on a haircut Sharpe of 1.0, the target volatility is 50% per year, so daily σ ≈ 3.15%. The 5% daily halt is 1.6σ and fires on ~5.6% of days.
- The 6% total-open-risk cap, defined as the sum of losses at stop, limits family D to ~14–29% annual volatility depending on stop width. It can never reach the Kelly target.
- **Resolution (decision D3):** define open risk per family type.
  - Intraday families: sum of loss-at-stop, as written.
  - D: 1-day 99% expected shortfall of the D book, counted against the same 6% budget. At 6% ES99 the cap allows ~36% annual volatility.
  - The Monte Carlo reports how often each limit binds.

### C6. 35% breaker vs. "accept large drawdowns" vs. P(50%/70% drawdown)
- With a breaker that stops trading at 35%, a 50% or 70% drawdown is reachable only through gaps or a manual restart. At half Kelly the breaker trips on average every ~1.2 years if the true Sharpe equals the haircut Sharpe (06, §2). A terminal breaker plus half Kelly therefore means the system is usually stopped.
- **Resolution (decision D4):** replace the cliff with a drawdown taper (06, §4). Risk scales by (D_max − DD)/D_max, which makes reaching D_max asymptotically impossible in continuous markets. The 35% breaker stays as a backstop for gaps. The Monte Carlo reports both "breaker terminal" and "breaker → review → resume at 0.5x".

### C7. ">= 300 trades" does not apply to family D
- D holds continuous positions on 11 instruments. "Trades" there is a rebalance count, not independent bets.
- **Resolution:** for D, require >= 300 rebalance trades *and* >= 10 years of OOS history, with Sharpe inference on monthly returns. The statistical bar is years, not trade count.

### C8. Pyramiding vs. 2% per-trade cap
- **Resolution:** the 2% cap applies to the aggregate position per instrument per family (all units, loss measured at each unit's stop). Adds are allowed only when the existing units' stops have reached breakeven or better.

### C9. Hold-out "used once" vs. a go/no-go that depends on it
- If the hold-out fails, the project stops. No re-run on modified strategies, because a second look makes it in-sample.
- The researcher (human and model) also knows what happened in 2024–2026 (August 2024 yen carry unwind, April 2025 tariff shock), so hypotheses are not fully blind to the hold-out.
- **Resolution:** accept both. Freeze every hypothesis file before Phase 3. Record the contamination as a known limitation.

### C10. MT5 option vs. Docker/Linux VPS
- The MetaTrader5 Python package is Windows-only, so choosing MT5 means a Windows VPS and no Linux container for the adapter.
- **Resolution:** exclude MT5 unless the broker offers nothing else.

### C11. ESMA leverage vs. tight intraday stops
- 2% risk on a 15-pip EURUSD stop is 13.3x notional/equity per trade. Three concurrent positions on majors reach 40x, above the 30:1 cap. AUD and NZD pairs are non-major (20:1).
- **Resolution:** `RiskOverlay` checks the margin requirement before every order. A rejected or downsized order is logged with its reason, and its frequency is reported per family.

### C12. Paper trading cannot validate execution costs
- Broker demo environments fill without realistic slippage and queue position. The §6 auto-disable rule ("live costs exceed backtest costs") cannot be calibrated on paper.
- **Resolution:** paper validates plumbing, latency and reconciliation. Cost validation happens in the "small live" stage with a minimum-size account.

## Gaps

| # | Gap | Resolution |
|---|---|---|
| G1 | Placeholders `<EUR amount>`, `<EUR floor>` and the broker are not filled in | Decisions D2 and D5. Sizing granularity and fixed-cost drag depend on them. |
| G2 | "FX majors" not enumerated | EURUSD, GBPUSD, USDJPY, USDCHF, USDCAD, AUDUSD, NZDUSD. AUDUSD and NZDUSD are ESMA non-major (20:1). |
| G3 | "High-impact" not defined | Tiered calendar, C4. |
| G4 | No rule for several families on one instrument | Internal virtual sub-positions per family, each with its own stop. Requires a broker with trade-level stops on a netting account (OANDA v20 supports per-trade SL; IBKR via OCA brackets). |
| G5 | "Trial" not defined | One trial = one distinct (family, config hash, instrument set, timeframe, data split) evaluated on any development data, including abandoned ideas. 05, §6. |
| G6 | "Uncorrelated" not quantified | |ρ| <= 0.3 on daily OOS P&L, and on the worst-decile days of the portfolio (tail correlation). |
| G7 | Live re-fitting cadence not specified | Parameters frozen at the hold-out decision. Re-selection at most yearly, by the same walk-forward rule, logged as trials. |
| G8 | Index CFD dividend adjustments | US500/NAS100 cash CFDs debit or credit dividends on ex-dates. Historical dividend points are not in the free data, so they are modelled from annual yield (assumed data, flagged). GER40 tracks the DAX performance (total return) index, so it has no adjustment. |
| G9 | EUR conversion of P&L | Realized P&L converted at the broker rate in live trading. Backtest uses the mid of the EURxxx rate at trade close. The tax export uses ECB reference rates (D8). |
| G10 | Unscheduled events (SNB 2015, emergency cuts 2020) | Not in any calendar. Covered only by catastrophe stops, the weekend policy and the jump model in the Monte Carlo. |
| G11 | Fixed costs | VPS (~EUR 10–30/month), data and broker fees are deducted in the Monte Carlo. On a EUR 2,000 account, EUR 20/month is a 12%/year drag. |
| G12 | Holiday and half-day sessions | Exchange calendars for US500/NAS100 (NYSE) and GER40 (Xetra), and FX liquidity holidays (Dec 25, Jan 1). Thin-liquidity days excluded from intraday families. |
| G13 | Coverage >= 80% with numba | JIT-compiled code is invisible to coverage. A CI job runs the suite with `NUMBA_DISABLE_JIT=1`. |
| G14 | Compute budget | 1000 random-benchmark runs × families × configs × CPCV paths is too slow event-driven. The random benchmark uses a vectorised exit-outcome kernel (05, §4), O(n) per run. |
| G15 | Tax residence | Determines the export format and loss rules (D8). |

## Unrealistic expectations

### U1. Per-family Sharpe >= 2 raw
- Literature reference points (gross, institutional costs):
  - Time-series momentum per asset: ~0.3–0.5.
  - Diversified across ~50 futures: ~1.0 before 2010, materially weaker in the 2010s.
  - G10 FX carry: ~0.5–0.8, with crash skew.
- With 11 instruments and retail costs, D should be expected at a raw Sharpe of 0.3–0.7.
- Session breakouts and ORB are widely published and heavily traded. Liquidity-sweep (ICT-style) concepts have no peer-reviewed support. The closest academic basis is the stop-loss clustering and price cascades documented by Osler (2003, 2005).

### U2. Multiple testing
- ~500 trials over 14 years: the expected best Sharpe of pure noise is ~0.82. Over 240 trials it is ~0.76 (06, §5).

### U3. Hold-out power
- Over 2.75 years, SE(SR) ≈ 0.75 at SR = 1. Two standard deviations either side cover −0.5 to 2.5. The hold-out catches only gross failure.

### U4. Three months of paper
- SE(SR) ≈ 2.0 over a quarter. It is an operational test only.

### U5. 10+ years of tick data on index CFDs
- Free CFD index tick history begins around 2012–2013 at the earliest (verify). Micro futures exist only since May 2019 (MES/MNQ). 10 years is available for FX and gold only.

### U6. Carry on retail CFDs
- Broker financing is benchmark rate ± a markup (typically 1–3% per year per side, verify with the broker). The markup can turn positive carry negative on both legs. Historical broker swap rates are not available, so the carry P&L is modelled (assumed data, flagged).

### U7. Intraday M5 costs
- On a 15-pip stop, a 0.8-pip round-trip spread plus commission plus slippage costs ~6–8% of the risked amount per trade before any edge. M5 families need high hit-rate times payoff just to break even.

## Expected outcome, stated in advance
Base rate for this kind of programme: most families fail after costs and multiple-testing correction. The likely result is one or two families passing at a raw Sharpe of 0.5–1.0 and a combined haircut Sharpe below 1.0. The §7 "no combination reaches 1.0" branch should be treated as the probable path, not the exception.
