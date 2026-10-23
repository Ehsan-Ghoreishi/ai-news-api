# 08 — Decisions Needed Before Phase 1

| ID | Decision | Options | Recommendation |
|---|---|---|---|
| D0 | Repository | (a) dedicated new repository; (b) keep `trading-system/` inside `ai-news-api` | (a). Separate CI, dependencies and history; the two codebases are unrelated. |
| D1 | Family pass threshold (01, C1) | (a) literal: haircut ≥ 1.0, i.e. raw ≥ 2.0 per family; (b) two-level: family raw ≥ 0.5 plus DSR ≥ 0.95 and every robustness gate, portfolio haircut ≥ 1.0 | (b). Under (a) the expected number of passing families is ~0. |
| D2 | Account size and floor | Fill `<EUR amount>`, `<EUR floor>` | Required. Determines size granularity, broker feasibility and fixed-cost drag. |
| D3 | Open-risk definition for D (01, C5) | (a) sum of loss-at-stop for all families, as written (D capped near 14–29% vol); (b) ES99 for D, loss-at-stop for intraday | (b). |
| D4 | Circuit breaker (01, C6) | (a) terminal at 35%; (b) linear drawdown taper to 35% plus breaker as gap backstop, resume at 0.5× after written review | (b). |
| D5 | Broker | OANDA v20 (EU entity) / Interactive Brokers Ireland / MT5 | OANDA if account < ~EUR 10k and the v20 API is confirmed for EU retail. IBKR if larger or micro futures are wanted (USD 2 FX minimum commission). MT5 excluded (Windows-only). |
| D6 | Data download location (02, §0) | (a) allowlist `datafeed.dukascopy.com`, `data.bis.org`, official calendar hosts and `www.truefx.com` in this environment; (b) download on own machine/VPS, transfer derived bars | (b) for the raw tick archive (size, persistence). (a) additionally for small datasets and tests. |
| D7 | Economic calendar source | (a) reconstruct from official publishers (free, laborious); (b) paid historical calendar | (a), with automated validation against volatility spikes. Fall back to (b) if validation fails. |
| D8 | Tax residence | Country | Required for the export format and loss rules. |
| D9 | Hold-out boundary | 2024-01-01 → end of data (proposed) | Accept. Any later change after Phase 3 starts is forbidden. |
| D10 | Trial cap | 500 total (proposed) | Accept. |
