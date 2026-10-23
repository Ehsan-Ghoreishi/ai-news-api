# 04 — Exact Strategy Definitions

## Conventions (apply to every family)

### Prices and bars
- Signals are computed on mid = (bid + ask) / 2. Fills use bid/ask from the fill engine (03, §5).
- A bar is stamped with its open time. A bar's values are usable only after it closes.
- An order decided at the close of bar t can execute no earlier than the open of bar t+1. Resting stop and limit orders become active from t+1.

### Indicators
- `ATR_D(n)`: ATR on daily bars (17:00 NY close), up to and including the previous completed day.
- `ATR_tf(n)`: Wilder ATR on timeframe tf, using closed bars only.
- `σ_x(n)`: standard deviation of the log return of the window x over the last n occurrences of that window, excluding today.

### Sessions (local time → UTC per date)
- Asia window: 00:00–07:00 Europe/London.
- London open: 07:00 Europe/London (FX); 08:00 Europe/London is the cash-equity open.
- NY: US cash open at 09:30 America/New_York; FX "NY open" reference at 08:00 America/New_York.
- GER40 cash open: 09:00 Europe/Berlin.

### News, rollover, weekend
- News guard (01, C4):
  - Tier-1 event at T: flat by T−5 min. No entry until the F settle condition holds, or T+30 min, whichever comes later.
  - Tier-2 event: no new entries in [T−5, T+10].
- Rollover guard: no intraday entries between 16:45 and 18:15 New York time, when spreads widen.
- Weekend: every intraday family is flat by Friday 16:00 NY.

### Spread filter
- Skip an entry if the current spread exceeds the max of:
  - the p90 spread for that instrument and hour of week (computed from development data);
  - 1.5 × the median spread for the same slot.

### Stop rule
- Every intent carries a stop. Size is derived from the stop distance in `RiskOverlay`, never fixed.

### Parameter scope and grids
- Parameters are **pooled across instruments**: one parameter set per family, not per instrument. This cuts trials and overfitting.
- Grids are fixed here and frozen in `config/families/*.yaml`. Expanding a grid later counts as new trials and needs a hypothesis amendment committed before the run.

---

## A1. Asian range breakout at London open
- **Hypothesis.** The Asian session accumulates resting orders beyond a narrow range. London-open order flow breaks the range and continues far enough to pay costs, beating random entries with the same exits.
- **Instruments.** The 7 FX majors and XAUUSD. **Timeframe:** M5.
- **Range.**
  - H = max(mid high), L = min(mid low) over the M5 bars in the Asia window. W = H − L.
  - The day is valid only if w_min·ATR_D(20) ≤ W ≤ w_max·ATR_D(20).
- **Orders.** At 07:00 London, place an OCO pair:
  - buy stop at H + b·W, with stop at L and target at entry + k·W;
  - sell stop at L − b·W, with stop at H and target at entry − k·W.
  - A fill cancels the other leg. At most one trade per instrument per day.
- **Expiry and exit.** Unfilled orders are cancelled at 10:00 London. Open positions close at 16:00 London.
- **Grid.** b ∈ {0.0, 0.1}, k ∈ {1.0, 1.5, 2.0}, (w_min, w_max) ∈ {(0.15, 0.6), (0.1, 0.8)} → **12 configs**.

## A2. New York open momentum
- **Hypothesis.** Intraday momentum. Gao, Han, Li & Zhou (2018) document that the return from the prior close through the first half hour predicts the return in the last half hour for US equity index ETFs. For FX, the London-to-NY-open move carries into the US morning.
- **A2-idx (US500, NAS100).**
  - r1 = log(mid at 10:00 NY / mid at the previous 16:00 NY).
  - At 15:30 NY, enter in the sign of r1 if |r1| ≥ θ·σ_r1(60).
  - Exit at 15:59 NY.
  - Stop: entry ∓ 2·σ_last30(60), where σ_last30 is the standard deviation of the 15:30–16:00 return.
- **A2-fx (FX majors, XAUUSD).**
  - r1 = log(mid at 09:00 NY / mid at 03:00 NY), covering the London morning and the 08:30 releases.
  - Enter at the next M5 open after 09:00 NY in the sign of r1 if |r1| ≥ θ·σ_r1(60).
  - Exit at 12:00 NY.
  - Stop: entry ∓ 2·σ_hold(60), where σ_hold is the standard deviation of the 09:00–12:00 return.
- **Grid.** θ ∈ {0.0, 0.5, 1.0} → **3 configs per variant, 6 total**.

## A3. Opening range breakout (indices)
- **Hypothesis.** Order imbalance at the cash open makes a break of the first N minutes' range continue more often than chance.
- **Instruments.** US500 and NAS100 (cash open 09:30 NY), GER40 (09:00 Berlin). **Timeframe:** M1 for the range, M5 for management.
- **Range.** OR_H and OR_L are the mid high and low over the first N minutes after the open. Valid only if OR width ≤ 0.6·ATR_D(14).
- **Orders.** At open + N, place an OCO pair:
  - buy stop at OR_H + 0.05·ATR_D(14);
  - sell stop at OR_L − 0.05·ATR_D(14).
  - Stop at the opposite OR boundary (variant `opp`) or at the OR midpoint (variant `mid`).
- **Expiry and exit.** Orders valid until 12:00 local. Exit at target entry ± k·OR width, or at 15:55 NY / 17:25 Berlin.
- **Grid.** N ∈ {15, 30}, stop ∈ {opp, mid}, k ∈ {1.0, 2.0, ∞ (time exit only)} → **12 configs**.

## B. Liquidity sweep reversal
- **Hypothesis.** Stop-loss orders cluster just beyond obvious levels (Osler 2003/2005). A brief run through a level that triggers those stops but finds no follow-through reverts, because the cascade's liquidity is absorbed.
- **Instruments.** FX majors, XAUUSD, US500, NAS100, GER40. **Execution timeframe:** M5.

### Level set at time t
Only levels known and confirmed at t are used.
1. PDH and PDL: previous 17:00-NY day's high and low. For indices, the previous cash session's high and low.
2. Asia high and low: from 07:00 London onward.
3. London session high and low (08:00–16:30 London): from 16:30 London onward.
4. Equal highs and lows on H1:
   - Swing high at bar i if high_i > max(high over i−3..i−1 and i+1..i+3). It is confirmed only at the close of bar i+3.
   - Two confirmed swing highs p1 and p2 within the last 48 H1 bars, at least 6 bars apart, with |p1 − p2| ≤ 0.1·ATR_H1(14), form level ℓ = max(p1, p2).
   - Equal lows are the mirror image.
5. A level is **consumed** once a sweep trade has been taken on it.
6. A level is **broken**, and removed, if any M5 bar closes beyond it by more than 0.25·ATR_H1(14).

### Bearish sweep at upper level ℓ (bullish is the mirror)
1. **Sweep bar s (M5).**
   - Penetration: high_s ≥ ℓ + 0.1·ATR_M5(14).
   - Depth cap: high_s ≤ ℓ + 1.0·ATR_H1(14). A deeper move is a breakout, not a sweep.
2. **Close back inside.** The close of bar s, s+1 or s+2 is below ℓ. Call the first such bar c.
3. **Displacement.** Within bars c..c+3, a bar e satisfies all of:
   - bearish;
   - body |close − open| ≥ 1.5·ATR_M5(14);
   - close_e < low_s.
4. **Entry.**
   - Variant `mkt`: sell at the open of e+1.
   - Variant `lim50`: sell limit at the midpoint of bar e's body, valid for 6 bars.
5. **Stop.** max(high over s..e) + 0.1·ATR_M5(14).
6. **Target.** entry − k·(stop − entry).
7. **Time stop.** 24 bars (2 h).
8. **Windows.** Sweep bar s must fall in 07:00–11:00 London or 08:00–11:00 NY. At most 2 trades per instrument per day. No sweep bar is accepted within ±15 min of a tier-1 event, because news spikes belong to F.

- **Grid.** entry ∈ {mkt, lim50}, k ∈ {1.5, 2.0, 3.0} → **6 configs**. The level-definition constants above are fixed, not tuned. Each one is a researcher degree of freedom, disclosed here.

## C. Mean reversion after overextension (range regime only)
- **Hypothesis.** In non-trending, normal-volatility regimes, short-horizon overextensions from a moving mean revert partially within hours.
- **Instruments.** FX majors, US500, NAS100, GER40. **Timeframe:** M15.
- **Signal.** z_t = (close_t − SMA_20(close)_t) / ATR_M15(20)_t.
- **Entry.** Long when z_t ≤ −z_e, short when z_t ≥ +z_e, and only if `RuleRegimeV0` labels the instrument "range" for the current day. Enter at the open of t+1.
- **Exit.**
  - z crosses 0: exit at the next open.
  - Stop: entry ∓ s·ATR_M15(20).
  - Time stop: 40 bars (10 h). Every position also closes 15 min before the rollover guard.
- **Grid.** z_e ∈ {2.0, 2.5, 3.0}, s ∈ {1.5, 2.5} → **6 configs**.

## D. Daily time-series momentum + carry (portfolio core)
- **Hypothesis.** Moskowitz, Ooi & Pedersen (2012) document time-series momentum. Lustig, Roussanov & Verdelhan (2011) and Koijen et al. (2018) document FX carry. Both persist net of retail costs at weekly rebalancing on a vol-targeted book.
- **Instruments.** 7 FX majors, XAUUSD, US500, NAS100, GER40. **Timeframe:** daily, 17:00 NY.
- **Momentum.** m_i = mean over L ∈ {21, 63, 126, 252} of sign(log P_t − log P_{t−L}), so m_i ∈ [−1, 1]. Fixed, not tuned.
- **Carry (FX only).**
  - c_i = policy rate(base) − policy rate(quote), using BIS policy rates known at t.
  - Rank c_i across the 7 pairs, then map linearly to [−1, 1].
  - Gold, indices: carry term = 0 (index dividend data unavailable, 01 G8).
- **Combined signal.** FX: s_i = 0.5·m_i + 0.5·c_i. Others: s_i = m_i.
- **Position.** Target risk weight w_i = s_i · (σ_tgt,asset / σ̂_i).
  - σ̂_i: EWMA volatility of daily returns, half-life 30 days, using data to t.
  - σ_tgt,asset is set so that the unit book runs at 10% annual volatility, rescaled later by `KellySizer`.
- **Rebalance.** Weekly, at Wednesday 15:00 London (liquid hours). Trade an instrument only if |target − current| > 0.25·|target|, or if the sign changes.
- **Catastrophe stop.** Every position carries a stop at entry ∓ 4·ATR_D(20), re-anchored at each rebalance. A stop-out keeps the position flat until the next rebalance.
- **Grid.** None. **1 config** (hard-coded, pre-registered blend). The momentum-only and carry-only sub-books are reported for attribution and are not selectable.

## E. Volatility compression → breakout
- **Hypothesis.** Volatility clusters and mean-reverts. Low-volatility states are followed by expansion, and the breakout direction predicts continuation (Mandelbrot 1963, Engle 1982; practitioner "squeeze").
- **Instruments.** FX majors, XAUUSD, indices. **Timeframes:** H1 and D, each a separate trial set.
- **Compression state at bar t.**
  - RR_t = (max high − min low over the last 20 bars) / ATR(100)_t.
  - Compression holds if RR_t ≤ the q-quantile of RR over the previous 500 bars.
  - The box is the high/low of those 20 bars.
- **Orders.** On the first compression bar, place an OCO pair at box high + 0.1·ATR(100) and box low − 0.1·ATR(100). Valid for 24 bars (H1) or 10 bars (D).
- **Stop.** Box midpoint.
- **Exit.**
  - Chandelier trailing stop: highest close since entry − 3·ATR(22) (longs, mirrored for shorts).
  - Time stop: 120 bars (H1) or 40 bars (D).
- **Pyramiding.** Add 1 unit at +1R and +2R (max 3 units). Earlier units' stops move to breakeven before an add. Aggregate risk ≤ the per-trade cap (01, C8).
- **Grid.** q ∈ {0.05, 0.10, 0.20}, pyramiding ∈ {off, on} → **6 configs per timeframe, 12 total**.

## F. Post-news drift
- **Hypothesis.** After tier-1 releases, the initial price reaction under-adjusts. Once spreads normalise, the move continues in the reaction's direction over the following hours. Evidence is mixed: Andersen et al. (2003) show fast adjustment. This hypothesis is weaker than A2 or D.
- **Events.** Tier 1 only, mapped to instruments (02, §4). FOMC is anchored at the press conference end, estimated at T_statement + 90 min. BoJ is excluded (no fixed time).
- **Settle condition at time u ≥ T + τ.**
  - Current spread ≤ 2 × the median spread for that hour of week.
  - Mean M1 range over the last 5 minutes ≤ 2 × the median M1 range over [T−65, T−5] min.
  - If the condition never holds before T + 120 min, skip the event.
- **Signal.**
  - r = log(mid_u / mid_{T−1min}).
  - z = r / σ_event, where σ_event is the standard deviation of r for the same event type over its previous 20 occurrences. At least 8 occurrences are required.
- **Entry.** Market at the next M1 open after u, in the sign of r, if |z| ≥ z_min.
- **Stop.** Beyond the extreme of [T, u] against the trade, + 0.25·ATR_M5(14).
- **Exit.** Time exit at u + H.
- **Grid.** τ ∈ {15, 30} min, z_min ∈ {0.5, 1.0}, H ∈ {2 h, end of NY session at 16:00 NY} → **8 configs**.
- **Hard rule.** No order exists before T. The engine asserts this.

---

## R. Regime classifier `RuleRegimeV0` (fixed, pre-registered, untuned)
Computed per instrument on daily bars up to the previous close. The label applies to the whole next trading day.

| Quantity | Definition |
|---|---|
| ER(20) | Kaufman efficiency ratio = abs(C_t − C_{t−20}) / Σ abs(C_k − C_{k−1}) over 20 days |
| ADX(14) | Wilder ADX on daily bars |
| RVpct | Percentile of the 20-day realized volatility within the previous 500 days |

**Labels**, checked in order:
1. **high-vol** if RVpct ≥ 0.90;
2. **trend** if ER(20) ≥ 0.35 or ADX(14) ≥ 25;
3. **range** otherwise.

**Gating matrix** (pre-registered; only C is gated in Phase 3, the rest are evaluated in Phase 4 as reported effects, never as rescue):

| Family | trend | range | high-vol |
|---|---|---|---|
| A1/A2/A3 | Phase 4 eval | Phase 4 eval | Phase 4 eval |
| B | Phase 4 eval | Phase 4 eval | Phase 4 eval |
| C | off | **on** | off |
| D | on | on | on (vol targeting handles it) |
| E | Phase 4 eval | Phase 4 eval | Phase 4 eval |
| F | on | on | on |

## Trial budget (pre-registered)

| Family | Configs | Instrument sets | Trials |
|---|---|---|---|
| A1 | 12 | 1 | 12 |
| A2 | 6 | 2 | 6 |
| A3 | 12 | 1 | 12 |
| B | 6 | 1 | 6 |
| C | 6 | 1 | 6 |
| D | 1 | 1 | 1 |
| E | 12 | 1 | 12 |
| F | 8 | 1 | 8 |
| **Total Phase 3** | | | **63** |

- Phase 4 regime evaluation adds up to 7 × 3 = 21 trials. Delay tests, cost stress and random benchmarks are diagnostics, not selection, so they are not counted.
- The DSR uses the registry's actual count, which also includes every exploratory run.
- The cap is 500 total. Exceeding it requires a written amendment.
