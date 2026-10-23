# 02 — Data Sources

Every row marked **(verify)** is an assumption that Phase 1 confirms or refutes with a coverage report. Nothing below has been downloaded yet.

## 0. Environment constraint (blocking for Phase 1)
- Probed from this cloud container on 2026-10-23. The network policy refused every host: `datafeed.dukascopy.com`, `fred.stlouisfed.org`, `www.truefx.com`, `api-fxpractice.oanda.com`.
- Phase 1 needs either the hosts added under the environment's allowed domains (https://code.claude.com/docs/en/cloud-environments#network-access) or downloads run on the user's machine or VPS with only derived artifacts moved into the container.
- Storage: compressed FX tick history is roughly 2–6 GB per instrument per decade (estimate, measured in Phase 1). The container has ~31 GB and is ephemeral. Raw ticks belong on persistent storage (user machine or VPS). The repository stores only manifests and hashes; `data/` stays gitignored.

## 1. Intraday price data

| Use | Source | Coverage (expected) | Format | Licensing | Known issues |
|---|---|---|---|---|---|
| Primary: FX majors, XAUUSD ticks | Dukascopy historical datafeed (`bi5`, LZMA, hourly files) | FX majors ~2003+, XAUUSD ~2003+ (verify) | bid, ask, bid vol, ask vol, ms timestamp | Free; personal use; redistribution prohibited (verify terms, record them in the manifest) | Spreads are Dukascopy ECN spreads, not the target broker's. Missing hours. Spike ticks. Weekend stray ticks. Pre-2008 sparse. Volume is Dukascopy liquidity, not market volume. |
| Primary: index CFDs | Dukascopy `USA500.IDX/USD`, `USATECH.IDX/USD`, `DEU.IDX/EUR` | ~2012–2013+ (verify) | as above | as above | Short history (U5). CFD tracks futures-derived price. Session hours and holiday breaks differ from the cash index. |
| Cross-check: FX | TrueFX (Integral) tick bid/ask | ~2009+, majors (verify) | CSV monthly | Free with registration, non-commercial (verify) | Different liquidity pool; used only to validate Dukascopy on sampled months. |
| Optional: index futures | Databento CME Globex (ES, NQ; MES/MNQ since 2019-05) | ES/NQ ~2010+ | MBP-1 / OHLCV-1m | Paid, per-GB | Needed only if the broker is IBKR and micro futures are traded. Eurex FDAX coverage (verify). |
| Rejected | HistData.com M1 | — | bid only | — | No ask, so no spread; violates §2. |
| Rejected | Forex Factory / Investing.com price or calendar scraping | — | — | ToS prohibit scraping | Legal risk. |

### Instrument list
- FX: EURUSD, GBPUSD, USDJPY, USDCHF, USDCAD, AUDUSD, NZDUSD.
- Metal: XAUUSD.
- Indices: US500, NAS100, GER40.
- Oil and BTC are excluded until the core passes (§1).

### Development data start
- 2010-01-01 for intraday families. Post-2008, fully electronic regime, at least 14 development years for FX and gold.
- Indices from the first verified month.
- D may use daily history from 2003 where available.

## 2. Daily data
- Daily bars are built from M1, with the day ending at 17:00 America/New_York. That gives 5 bars per week and no Sunday bar.
- No external daily source is mixed in, so the data stays single-source and aligned.

## 3. Interest rates

| Use | Source | Notes |
|---|---|---|
| Carry signal and financing model | BIS central bank policy rates (daily, all G10) | Free with attribution (verify licence). A policy rate is known on announcement day, so it has no revision or publication-lag look-ahead. |
| Cross-check | OECD 3-month interbank (via FRED, monthly) | Published with a lag. Used only as a sanity check and shifted one month. |
| Broker financing | Model: policy-rate differential ± broker markup | Markup per broker in `config/costs/<broker>.yaml`. **Assumed data**, flagged in every D report. |

## 4. Economic calendar
Scheduled release times are built from official publishers. No consensus or actual values are needed, because F uses the price reaction, not the surprise.

| Event | Tier | Instruments | Source |
|---|---|---|---|
| US Employment Situation (NFP) | 1 | USD pairs, XAUUSD, US500, NAS100 | BLS release schedule archive |
| US CPI | 1 | same | BLS |
| FOMC statement (14:00 ET) + press conference | 1 | same | federalreserve.gov meeting calendars |
| ECB decision + press conference | 1 | EUR pairs, GER40 | ecb.europa.eu |
| BoE MPC | 1 | GBP pairs | bankofengland.co.uk |
| SNB, BoC, RBA, RBNZ decisions | 1 | CHF, CAD, AUD, NZD pairs | respective central banks |
| BoJ decision | 1 (no fixed time) | JPY pairs | boj.or.jp. Release time varies, so the whole morning window is blocked for JPY on BoJ days. |
| US retail sales, ISM manufacturing, GDP advance, PCE | 2 | USD pairs, XAUUSD, US indices | Census, ISM, BEA |
| Euro area / German flash PMIs, German Ifo | 2 | EUR pairs, GER40 | S&P Global, ifo |

Calendar facts:
- Historical release *times* for US statistical releases are standardised (08:30 or 10:00 ET).
- Dates come from archived schedules.
- Every event row stores: `event_id, name, tier, currencies, instruments, scheduled_local, tz, scheduled_utc, source_url, retrieved_at`.
- Coverage risk: assembling 14 years from official archives is manual work and probably has errors. Phase 1 validates the calendar against price: each tier-1 event should show a volatility spike at its timestamp, and events without one are flagged.
- Fallback: a paid calendar (e.g. Trading Economics API) if the official reconstruction fails validation (decision D7).

## 5. Time handling
- All storage is in UTC, at millisecond resolution for ticks and bar-open timestamps for bars.
- Sessions are defined in local zones (Asia/Tokyo, Europe/London, Europe/Berlin, America/New_York) and converted per date with the IANA tz database. That covers the 2–3 weeks each year when US and EU daylight saving times differ.
- FX day boundary and rollover: 17:00 America/New_York. Financing is charged at rollover, triple on Wednesday for FX (T+2). Index CFD weekend financing follows the broker convention (verify).
- Weekend: from Friday 17:00 NY to Sunday 17:00 NY there is no trading. The first Sunday tick is the gap open, and stops are filled at the first available price.

## 6. Validation applied in Phase 1
For every instrument and month the coverage report contains:
- duplicates, out-of-order rows, zero or negative prices, crossed quotes (bid >= ask);
- spread outliers (> p99.9 for that hour of week), spikes (|Δmid| > 10 × rolling MAD that revert within 3 ticks);
- missing minutes inside session hours, missing hours, weekend leakage;
- tick-count distribution and spread distribution by hour of week;
- a Dukascopy vs. TrueFX mid-price comparison on sampled months (median |Δ|, max |Δ|).

Other Phase 1 rules:
- Rows are flagged, never silently dropped. The cleaning rules are versioned, and the data version is the SHA-256 of the manifest (files, row counts, rule version).
- Gap count and coverage are reported before any backtest, as the skill requires.
