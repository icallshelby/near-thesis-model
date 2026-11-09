# NEAR by the Numbers — a re-runnable long-term thesis

**NEAR Hackathon submission — Investment Thesis track.** Team: **zarroww**.

An investment thesis is only worth reading if its numbers can be checked.
This repository is a small, fully re-runnable model that pulls **live** NEAR
mainnet data from public sources, computes the metrics the thesis stands on,
and publishes them as a static dashboard. No API keys, no spreadsheets that
only the author can reproduce: if a figure on the dashboard is wrong, anyone
can re-run the model and show it.

## What it does

`model.py` (Python 3, standard library only) queries:

| Source | Data used |
| --- | --- |
| NearBlocks API (`api.nearblocks.io/v1/stats`) | supply, price, market cap, 24h volume, ATH, lifetime transactions, nodes online, block time |
| NEAR mainnet RPC (`rpc.mainnet.near.org`) | chain status, and the **live validator set** — total stake, top-1/5/10 concentration, and the **Nakamoto coefficient** are computed directly from the RPC response |
| CoinGecko public API | 365 days of daily closes (returns, annualized volatility, max drawdown) and a **peer benchmark** of major L1s (market cap, turnover, ATH drawdown, 1y change) |

and writes:

- `data/metrics.json` — every derived metric, with its sources
- `data/snapshot_raw.json` — the raw API responses behind them (audit trail)
- `index.html` — the dashboard (via `build_dashboard.py`): metric cards, a 365-day
  price chart, bull and bear cases, the peer table, valuation scenarios
- `ANALYSIS.md` — the full written thesis, regenerated from the same metrics,
  so the report can never drift from the data

A GitHub Actions workflow (`.github/workflows/refresh-data.yml`) re-runs the
model daily and commits the refreshed data and report — the thesis stays
current on its own, and the commit history is the proof.

## Run it

```bash
python3 model.py            # fetch live data -> data/metrics.json
python3 build_dashboard.py  # render index.html from the metrics
```

Then open `index.html` in any browser. That is the whole setup.

## The thesis (short version)

1. **Usage compounds.** Billions of lifetime transactions, sub-second blocks,
   hundreds of nodes online — the network is used, not just traded.
2. **Holders commit capital.** A large share of supply is staked across
   hundreds of validators (the model measures the exact figure live).
3. **Dilution is mostly behind it.** Nearly all supply already circulates,
   limiting future unlock overhang.
4. **The market de-rated it anyway.** The price sits far below its all-time
   high while the usage and staking metrics kept growing — the gap between
   network fundamentals and price is the opportunity the thesis prices.

The dashboard also states the bear case (stake concentration in the top
pools, negative short-term momentum, and the fact that protocol fee revenue
is *not* yet in the model) — a thesis that hides its weak points is marketing,
not research.

Valuation scenarios are simple arithmetic — target price × current
circulating supply — and are labelled as such. They are not predictions.

## Limitations & future work

- Protocol fee revenue and fee burn are not yet modeled; public endpoints do
  not expose a clean historical fee series, and this model only uses numbers
  it can source directly. Adding a fee/burn series from an indexer is the
  natural next step.
- Metrics are snapshots. Running the model on a schedule produces a time
  series; the JSON schema is designed for that.
- Scenario multiples ignore future supply change (staking issuance net of
  burns).

## Hackathon notes

- Built during the NEAR Hackathon window (November 2026), with AI assistance,
  for the **Investment Thesis** track.
- Data sources and partner docs were verified against the live endpoints
  above; nothing in this repo requires a NEAR wallet or spends funds.
- Not financial advice. Research and education only.

## License

MIT
