# 03 — Architecture

## 1. Principles
- **One code path.** Strategy, risk and cost code is identical in backtest, paper and live trading. Only `DataFeed` and `ExecutionAdapter` implementations differ.
- **Pure strategies.** A strategy is a deterministic step function `(state, closed bars, calendar view) -> (new state, order intents)`. It does no I/O, reads no clock and calls no broker. Features are precomputed in vectorised numba kernels. Order management is event-driven.
- **Limits live in `risk/`.** Strategies never size positions. They emit intents with a stop price. Sizing, caps and halts are applied in `RiskOverlay`.
- **Every artifact is reproducible.** Each run records its config hash, data version, git commit and seed in the experiment registry.
- **The hold-out is locked in code.** `DataFeed` refuses any timestamp >= `holdout_start` unless the call presents a one-time unlock token. The token is minted once, is logged, and makes every later request fail.

## 2. File tree (planned, dedicated repository)

```
trading-system/
├── pyproject.toml                 # py3.12, deps, ruff, mypy strict, pytest config
├── .pre-commit-config.yaml        # ruff, ruff-format, mypy, no-secrets hook
├── .env.example                   # broker + telegram placeholders only
├── .github/workflows/ci.yml       # lint, mypy, tests (JIT on), coverage (JIT off)
├── config/
│   ├── instruments.yaml           # contract spec, pip, min size, ESMA leverage class, sessions, tz
│   ├── calendar_tiers.yaml        # event -> tier -> instruments
│   ├── costs/{dukascopy_base,oanda_eu,ibkr_ie}.yaml
│   ├── risk.yaml                  # hard limits, taper, breaker, kill switch, fat-finger
│   ├── regime_v0.yaml
│   ├── families/{a1,a2,a3,b,c,d,e,f}.yaml   # parameter grids, pre-registered
│   ├── portfolio.yaml             # allocator, Kelly fraction, haircut
│   ├── validation.yaml            # splits, CPCV, gates, trial budget
│   └── prop/<firm>.yaml
├── research/
│   ├── hypotheses/{A1,A2,A3,B,C,D,E,F,REGIME}.md   # frozen before first run
│   └── reports/                   # generated family and portfolio reports (md + html)
├── src/tsys/
│   ├── core/       types.py  config.py  clock.py  sessions.py  events.py  interfaces.py
│   │               logging.py (JSON)  journal.py (SQLite)  errors.py
│   ├── data/       dukascopy.py  truefx.py  rates_bis.py  store.py  bars.py
│   │               validate.py  manifest.py  feed.py  calendar/{sources.py,build.py,validate.py}
│   ├── features/   kernels.py (numba)  indicators.py  swings.py  levels.py
│   ├── regime/     rule_v0.py  evaluate.py
│   ├── strategies/ base.py  a1_asian_breakout.py  a2_ny_momentum.py  a3_index_orb.py
│   │               b_liquidity_sweep.py  c_mean_reversion.py  d_tsmom_carry.py
│   │               e_compression_breakout.py  f_post_news_drift.py
│   ├── costs/      model.py  financing.py  profiles.py
│   ├── backtest/   engine.py  broker_sim.py  fills.py  margin.py  outcome_kernel.py
│   ├── validation/ splits.py (CPCV, purge, embargo, walk-forward)  selection.py
│   │               random_benchmark.py  sharpe.py (SE, PSR, DSR)  pbo.py  gates.py
│   ├── portfolio/  hrp.py  risk_parity.py  allocator.py  correlation.py
│   ├── sizing/     kelly.py  taper.py  montecarlo.py
│   ├── risk/       overlay.py  limits.py  news_guard.py  weekend.py  kill_switch.py  checks.py
│   ├── execution/  adapter.py  paper.py  <broker>.py  reconcile.py  quality.py
│   ├── live/       engine.py  state.py  scheduler.py  heartbeat.py  alerts.py  shadow.py
│   ├── prop/       rules.py  simulator.py  optimizer.py  enforcer.py
│   ├── registry/   experiments.py  hypotheses.py
│   ├── reporting/  family.py  portfolio.py  exits.py  tax_export.py
│   └── cli.py
├── tests/          unit/  property/  integration/  fixtures/ (small synthetic + sampled real)
├── docker/         Dockerfile  compose.yaml
└── docs/           phase0/  runbook.md  install.md
```

## 3. Interfaces (spec §10)

| Interface | Responsibility | Key operations (inputs → outputs) |
|---|---|---|
| `DataFeed` | Serve closed bars and ticks in time order, enforce the hold-out lock | `bars(instrument, tf, start, end)` → bar frame. `ticks(instrument, start, end)` → tick frame. `stream()` → event iterator (live and backtest). |
| `RegimeClassifier` | Label trend / range / high-vol per instrument per day using data up to the previous close | `label(daily_bars)` → regime series |
| `StrategyFamily` | Pure signal and order-intent logic | `features(bars)` → feature frame (vectorised). `on_bar(state, bar, features, calendar)` → (state, intents). `params_grid()`. `hypothesis_id`. |
| `CostModel` | Spread, commission, slippage, financing per fill and per rollover | `fill_cost(order, quote, context)`. `financing(position, rollover_ts)`. `scaled(k)` for stress tests. |
| `Validator` | CPCV, walk-forward, random benchmark, DSR, PBO, gates | `run(family, grid, data)` → validation report, gate verdict |
| `PortfolioAllocator` | Weights across validated families | `weights(oos_returns)` → family weights (HRP / ERC) |
| `KellySizer` | Portfolio scale from haircut Sharpe and Kelly fraction | `scale(oos_returns, weights, fraction)` → risk multiplier |
| `RiskOverlay` | Final sizing and every hard limit | `size(intent, account, positions)` → order or rejection with reason. `on_fill`. `on_equity`. Halts, breaker, kill switch. |
| `ExecutionAdapter` | Broker abstraction: sim, paper, live | `submit`, `cancel`, `positions`, `orders`, `account`, `stream_fills`, `stream_quotes` |
| `PropRules` | Prop firm rule set and evaluation | `check(account_state)` → breaches. `buffer(limit)`. |
| `Reporter` | Metrics tables, exit audit, per year / session / instrument, correlation | `family_report`, `portfolio_report`, `risk_report` |
| `ExperimentRegistry` | Append-only trial log | `record(trial)`. `count(family=None)`. `trial_sharpes()` for DSR. `assert_hypothesis_frozen(family)`. |

## 4. Data flow

```
raw ticks (bi5) ──► validate ──► parquet ticks (partitioned instrument/year/month)
                                   │
                                   ├──► M1 bid/ask OHLC + spread stats + t_high/t_low per side
                                   │        └──► M5/M15/H1/D (17:00 NY) by resampling from M1
                                   ▼
policy rates, calendar ──► DataFeed (holdout lock) ──► features (numba, vectorised)
                                   │
                                   ▼
               StrategyFamily.on_bar ──► OrderIntent(instrument, side, type, entry, stop, target, tags)
                                   │
           PortfolioAllocator + KellySizer ──► family risk budget
                                   │
                                   ▼
                    RiskOverlay ──► sized Order | Rejection(reason)
                                   │
              BrokerSim (backtest) │ PaperAdapter │ LiveAdapter
                                   ▼
                    Fill ──► Journal (SQLite) ──► Reporter / Registry / Alerts
```

## 5. Backtest engine and fill resolution
- **Event loop at M1 granularity.** Higher-timeframe strategies receive bar events only when their bar closes. Pending orders are checked on every M1 bar.
- **Intra-bar resolution.**
  - Buy stops trigger on ask ≥ trigger, sell stops on bid ≤ trigger.
  - Limits fill only when price trades *through* the limit by at least 1 tick (queue conservatism).
  - If one M1 bar can trigger several orders (stop and target, or entry and stop), the engine loads that minute's ticks and replays them in order. If ticks are missing, the worst case (stop first) is assumed and counted.
  - Gaps: a stop fills at the first tick beyond the trigger, which includes weekend and news gaps.
- **Cost of the method.** M1 bars cost O(n) over ~3.7M bars per instrument per decade. Tick loads are O(k) for ambiguous minutes only (k ≪ n).
- **Margin.** ESMA leverage per instrument class. Margin close-out at 50% of required margin. Negative balance protection: the account floors at 0, and equity paths are not otherwise clipped.
- **Determinism.** Fixed seeds for any randomness (random benchmark, Monte Carlo). The engine itself is deterministic.

## 6. Persistence
- SQLite journal tables: `orders`, `fills`, `positions`, `equity`, `risk_events` (halts, breaker, kill switch with timestamp and reason), `alerts`, `reconciliations`.
- Experiment registry: `trials(id, family, hypothesis_id, config_hash, data_version, git_commit, seed, split, period, n_trades, metrics_json, created_at, is_holdout)`. Append-only, enforced by a trigger that rejects UPDATE and DELETE.

## 7. Test plan
- **Unit tests**: indicators vs. reference implementations, session and DST conversion (including US/EU DST mismatch weeks), bar building from ticks, cost model arithmetic, financing including triple Wednesday, margin and close-out, every hard limit and halt, Kelly and taper math, DSR/PSR against published worked examples, HRP against a reference.
- **Property tests (hypothesis)**:
  - Truncation invariance (no look-ahead): for a random cut t, signals computed on data[:t] equal the full-data signals up to t, for every strategy and feature.
  - Resampling: M1→M5→H1 equals M1→H1.
  - The fill engine never fills a buy below the ask or a limit without trade-through.
  - Equity identity: Σ fills P&L + financing − costs = Δequity.
  - Position size × stop distance ≤ the risk cap for any equity and stop.
- **Integration tests**: synthetic markets with planted edges (the validator must detect them) and with no edge (the validator must reject at the nominal rate). A full backtest on a sampled real month with a golden-file comparison.
- **Delay test**: every family is re-run with +1 bar signal delay.
- **Coverage**: ≥ 80% on `core, data, features, costs, backtest, validation, sizing, risk, portfolio`, measured with the JIT disabled.

## 8. Live operations (summary, detailed in Phase 8–9)
- **Start-up.** Idempotent: restore state from SQLite, reconcile broker positions and orders against the journal, refuse to trade on mismatch, alert.
- **Scheduler.** UTC, with session events computed from tz rules.
- **Resilience.** 30 s heartbeat and a watchdog. Retries use exponential backoff with a cap. Every order has a client ID for idempotency.
- **Telegram alerts.** Fills, risk triggers, reconciliation mismatch, abnormal slippage, family auto-disable, heartbeat loss.
- **Shadow backtest.** Daily, on the broker's own recorded quotes. Alert on any signal mismatch, and on fill-price divergence above a threshold.
- **Deployment.** Docker on a Linux VPS. Secrets from `.env` only. API keys trade-only, with an IP whitelist where supported. `LIVE_TRADING=true` plus an interactive confirmation are required to enable live order submission.
- **Tax export.** Yearly CSV of trades and P&L in EUR (format per D8).
