---
title: Hindsight Taiwan Stock Backtest
emoji: 📈
colorFrom: blue
colorTo: gray
sdk: docker
app_port: 8050
pinned: false
---

# hindsight

Taiwan stock backtesting system: per-ticker strategy assignment with shared capital pool, retroactive split adjustment, multi-source data quality flags, Dash UI.

## Quick start

```bash
pip install -r requirements.txt
export FINMIND_TOKEN=your_token_here   # optional; falls back to yfinance
python3 -m ui.app                       # http://localhost:8050
```

Or with Docker:

```bash
docker compose up
```

## Strategies

- `dip_and_take_profit` — buys on drop ≥ dip_pct, sells on take-profit or max-hold-days
- `infinite_average_v0` — continuous averaging-down; unconditional re-entry the day after a sell (no price gate); avg_cost fully resets per round

## Architecture

Five-layer monolith (one-way deps top → bottom): `ui/` → `backtest/` → `strategy/` → `selection/` → `data/`.

Data layer applies retroactive split adjustment at read time using `data/splits_manual.json` (authoritative) plus heuristic detection on big consecutive-close ratios.

See [DEVELOPMENT.md](DEVELOPMENT.md) for the full architecture, design decisions, test breakdown, and known limitations.

## Tests

```bash
python3 -m pytest -q
```

105 tests covering data layer (cache, gap-fill, splits), strategy layer (PnL, base, two strategies), backtest engine, UI charts/layout, and end-to-end smoke.
