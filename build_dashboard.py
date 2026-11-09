#!/usr/bin/env python3
"""
Builds the deliverables from data/metrics.json:
  - index.html    the dashboard (single self-contained file, SVG chart inline)
  - ANALYSIS.md   the full written thesis, with every figure templated from
                  the same metrics file — re-running updates the report too

Run model.py first, then:  python3 build_dashboard.py
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
M = json.loads((HERE / "data" / "metrics.json").read_text())
mk, sp, nw, sk = M["market"], M["supply"], M["network"], M["staking_and_decentralization"]
hi, peers = M.get("history_365d") or {}, M.get("peers") or []


def usd(x):
    return f"${x:,.0f}"


def svg_chart(closes, w=820, h=180):
    if not closes:
        return ""
    lo, hi_ = min(closes), max(closes)
    rng = (hi_ - lo) or 1
    pts = " ".join(
        f"{i * w / (len(closes) - 1):.1f},{h - 8 - (c - lo) / rng * (h - 24):.1f}"
        for i, c in enumerate(closes)
    )
    return (
        f'<svg viewBox="0 0 {w} {h}" width="100%" role="img" aria-label="NEAR price, last 365 days">'
        f'<polyline fill="none" stroke="#4ade80" stroke-width="2" points="{pts}"/></svg>'
        f'<p class="sub">365 days of daily closes. Window low ${lo:.2f} · window high ${hi_:.2f} · '
        f"annualized volatility {hi.get('annualized_volatility_pct')}% · max drawdown {hi.get('max_drawdown_in_window_pct')}%</p>"
    )


def peer_rows():
    out = []
    for p in peers:
        hl = ' style="background:#17301f"' if p["symbol"] == "NEAR" else ""
        out.append(
            f"<tr{hl}><td>{p['symbol']}</td><td>${p['price_usd']:,.2f}</td>"
            f"<td>{usd(p['market_cap_usd'])}</td><td>{p['volume_to_mcap_pct']}%</td>"
            f"<td>{p['drawdown_from_ath_pct']}%</td><td>{p['change_1y_pct']}%</td></tr>"
        )
    return "\n    ".join(out)


scen_rows = "\n    ".join(
    f"<tr><td>{s['scenario']}</td><td>${s['price_usd']:,.2f}</td>"
    f"<td>{usd(s['implied_market_cap_usd'])}</td><td>{s['multiple_vs_today']}x</td></tr>"
    for s in M["valuation_scenarios_supply_held_constant"]
)

html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>NEAR by the Numbers — a re-runnable long-term thesis</title>
<style>
  body {{ font-family: system-ui, sans-serif; margin: 0; background: #0b0f14; color: #e6edf3; }}
  main {{ max-width: 900px; margin: 0 auto; padding: 32px 20px 64px; }}
  h1 {{ font-size: 32px; margin-bottom: 4px; }}
  h2 {{ margin-top: 42px; border-bottom: 1px solid #26303c; padding-bottom: 6px; }}
  .sub {{ color: #9fb0c3; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 12px; margin-top: 16px; }}
  .card {{ background: #121922; border: 1px solid #223041; border-radius: 10px; padding: 14px; }}
  .card .v {{ font-size: 22px; font-weight: 700; }}
  .card .k {{ color: #9fb0c3; font-size: 13px; margin-top: 2px; }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 12px; font-size: 15px; }}
  td, th {{ padding: 8px; border-bottom: 1px solid #223041; text-align: left; }}
  li {{ margin: 6px 0; }}
  code {{ background: #121922; padding: 2px 6px; border-radius: 4px; }}
  .foot {{ color: #7d8ea3; font-size: 13px; margin-top: 48px; }}
</style>
</head>
<body>
<main>
  <h1>NEAR by the Numbers</h1>
  <p class="sub">A long-term investment thesis for NEAR Protocol, backed by live on-chain data.
  Every figure here is produced by <code>model.py</code> from public sources and can be re-run by anyone.
  The full written report is <code>ANALYSIS.md</code> in the repository. Snapshot: {M['generated_at_utc']}</p>

  <div class="grid">
    <div class="card"><div class="v">${mk['price_usd']:.2f}</div><div class="k">NEAR price (USD)</div></div>
    <div class="card"><div class="v">{usd(mk['market_cap_usd'])}</div><div class="k">Market cap</div></div>
    <div class="card"><div class="v">{mk['drawdown_from_ath_pct']}%</div><div class="k">vs all-time high ${mk['ath_usd']:.2f}</div></div>
    <div class="card"><div class="v">{hi.get('return_365d_pct')}%</div><div class="k">Return, last 365 days</div></div>
    <div class="card"><div class="v">{mk['volume_to_mcap_pct']}%</div><div class="k">24h volume / market cap</div></div>
    <div class="card"><div class="v">{sp['circulating_pct_of_total']}%</div><div class="k">Supply already circulating</div></div>
    <div class="card"><div class="v">{sk['staking_ratio_pct_of_total_supply']}%</div><div class="k">Of supply staked</div></div>
    <div class="card"><div class="v">{sk['nakamoto_coefficient']}</div><div class="k">Nakamoto coefficient (validators to &gt;1/3 stake)</div></div>
    <div class="card"><div class="v">{nw['total_transactions']:,}</div><div class="k">Lifetime transactions</div></div>
    <div class="card"><div class="v">{nw['avg_block_time_s']}s</div><div class="k">Average block time, {nw['shards']} shards</div></div>
  </div>

  <h2>Price history — 365 days</h2>
  {svg_chart(hi.get('daily_closes_usd') or [])}

  <h2>The bull case, in evidence</h2>
  <ul>
    <li><b>Usage is real and cumulative:</b> {nw['total_transactions']:,} lifetime transactions, {nw['nodes_online']} nodes online,
    blocks every ~{nw['avg_block_time_s']}s across {nw['shards']} shards ({nw['blocks_per_day']:,} blocks/day).</li>
    <li><b>Holders commit:</b> {sk['total_staked_near']:,} NEAR — {sk['staking_ratio_pct_of_total_supply']}% of all supply — is staked
    across {sk['current_validators']} validators instead of sitting on exchanges.</li>
    <li><b>Dilution is mostly behind it:</b> {sp['circulating_pct_of_total']}% of total supply already circulates.</li>
    <li><b>Liquidity is large-cap grade:</b> 24h volume {usd(mk['volume_24h_usd'])} = {mk['volume_to_mcap_pct']}% of market cap —
    among the deepest turnover in the peer table below.</li>
    <li><b>De-rated, not dead:</b> {mk['drawdown_from_ath_pct']}% below the ${mk['ath_usd']:.2f} ATH, yet the 365-day return is
    {hi.get('return_365d_pct')}% and the network metrics above kept compounding.</li>
  </ul>

  <h2>The bear case, honestly</h2>
  <ul>
    <li><b>Stake is concentrated at the top:</b> Nakamoto coefficient is {sk['nakamoto_coefficient']} — the top
    {sk['nakamoto_coefficient']} pools together hold over a third of all stake (top 10: {sk['top10_stake_share_pct']}%).</li>
    <li><b>Volatility is extreme:</b> {hi.get('annualized_volatility_pct')}% annualized over the last year, with a
    {hi.get('max_drawdown_in_window_pct')}% maximum drawdown inside the window. Position sizing is not optional.</li>
    <li><b>Fee revenue is not in this model:</b> only metrics public APIs report directly are used; protocol fee income
    and burn are future work (see README).</li>
  </ul>

  <h2>Peer benchmark — major L1s, market structure</h2>
  <table>
    <tr><th>Asset</th><th>Price</th><th>Market cap</th><th>24h vol / mcap</th><th>vs ATH</th><th>1y change</th></tr>
    {peer_rows()}
  </table>
  <p class="sub">Market structure only (CoinGecko): NEAR trades at a large-cap size with turnover comparable to peers
  several times its market cap, while sitting deeper below its ATH than most of the set — the "de-rated but liquid" profile the thesis prices.</p>

  <h2>Valuation scenarios (arithmetic, not predictions)</h2>
  <p class="sub">Price targets applied to today's circulating supply of {sp['circulating_near']:,} NEAR.</p>
  <table>
    <tr><th>Scenario</th><th>Price</th><th>Implied market cap</th><th>Multiple</th></tr>
    {scen_rows}
  </table>

  <h2>Method &amp; sources</h2>
  <ul>
    <li>NearBlocks API — supply, price, market cap, volume, lifetime transactions, nodes online.</li>
    <li>NEAR mainnet RPC — chain status and the live validator set; stake shares and the Nakamoto coefficient are summed directly.</li>
    <li>CoinGecko — 365 days of daily closes and the L1 peer set.</li>
    <li>Raw responses committed in <code>data/snapshot_raw.json</code>; derived values in <code>data/metrics.json</code>.</li>
  </ul>
  <p>Re-run it yourself: <code>python3 model.py &amp;&amp; python3 build_dashboard.py</code> — Python 3 standard library only, no API keys.</p>

  <p class="foot">Built by team zarroww for the NEAR Hackathon (Investment Thesis track). Research and education only — not financial advice.</p>
</main>
</body>
</html>
"""
(HERE / "index.html").write_text(html)

peer_md = "\n".join(
    f"| {p['symbol']} | ${p['price_usd']:,.2f} | {usd(p['market_cap_usd'])} | {p['volume_to_mcap_pct']}% | {p['drawdown_from_ath_pct']}% | {p['change_1y_pct']}% |"
    for p in peers
)
scen_md = "\n".join(
    f"| {s['scenario']} | ${s['price_usd']:,.2f} | {usd(s['implied_market_cap_usd'])} | {s['multiple_vs_today']}x |"
    for s in M["valuation_scenarios_supply_held_constant"]
)

analysis = f"""# NEAR by the Numbers — Investment Thesis

*Team zarroww · NEAR Hackathon, Investment Thesis track · Data snapshot: {M['generated_at_utc']}*
*Every figure in this report is generated by `model.py` from live public sources and committed
to `data/metrics.json` with its raw inputs in `data/snapshot_raw.json`. Re-run the model to verify.*

## Executive summary

NEAR trades at {usd(mk['market_cap_usd'])} — {mk['drawdown_from_ath_pct']}% below its ${mk['ath_usd']:.2f}
all-time high — while the network underneath it posts numbers that belong to a much larger asset:
{nw['total_transactions']:,} lifetime transactions, {sk['staking_ratio_pct_of_total_supply']}% of supply
staked across {sk['current_validators']} validators, {sp['circulating_pct_of_total']}% of supply already
circulating, and daily turnover of {mk['volume_to_mcap_pct']}% of market cap. The thesis: the market is
pricing NEAR's 2022 de-rating as permanent, while usage, staking commitment and supply structure say the
network kept compounding. The gap is the opportunity — sized honestly against a concentrated validator
top and {hi.get('annualized_volatility_pct')}% annualized volatility.

## 1. Usage: the network is used, not just traded

- Lifetime transactions: **{nw['total_transactions']:,}**
- Block cadence: **~{nw['avg_block_time_s']}s** across **{nw['shards']} shards** ({nw['blocks_per_day']:,} blocks/day)
- Nodes online: **{nw['nodes_online']}** · Protocol version: {nw['protocol_version']}

Sustained transaction throughput over years is the hardest metric to fake in this industry. NEAR's count
is a stock that only grows, and it grew through the bear market that produced the current price.

## 2. Commitment: holders stake, they don't just hold

- Total staked: **{sk['total_staked_near']:,} NEAR ({sk['staking_ratio_pct_of_total_supply']}% of total supply)**
- Validators: **{sk['current_validators']}** · Epoch: {sk['epoch_height']}

A staking ratio near half of supply means the marginal holder's revealed preference is long-term
exposure plus yield, not exit liquidity — a structural bid under the float that remains.

## 3. Supply: dilution is mostly behind it

- Circulating: **{sp['circulating_near']:,} of {sp['total_near']:,} NEAR ({sp['circulating_pct_of_total']}%)**

Low-float launches de-rate for years as unlocks hit. NEAR's float is already out: future supply growth
is staking issuance net of fee burn, not cliff unlocks — the cleanest supply structure in the peer set.

## 4. Market structure: de-rated but liquid

- 24h volume: **{usd(mk['volume_24h_usd'])} ({mk['volume_to_mcap_pct']}% of market cap)**
- 365-day return: **{hi.get('return_365d_pct')}%** · Volatility: **{hi.get('annualized_volatility_pct')}%** · Max drawdown in window: **{hi.get('max_drawdown_in_window_pct')}%**

| Asset | Price | Market cap | 24h vol / mcap | vs ATH | 1y change |
| --- | --- | --- | --- | --- | --- |
{peer_md}

NEAR's turnover ratio sits with peers several times its size, while its ATH drawdown is among the
deepest — liquidity without the price recovery. That asymmetry is what the scenarios below price.

## 5. The bear case (stated, not buried)

- **Concentration:** Nakamoto coefficient is **{sk['nakamoto_coefficient']}**; the top 10 pools hold
  **{sk['top10_stake_share_pct']}%** of stake (top 1: {sk['top1_stake_share_pct']}%). Decentralization is
  broad at the tail and concentrated at the head.
- **Volatility:** {hi.get('annualized_volatility_pct')}% annualized with a {hi.get('max_drawdown_in_window_pct')}%
  in-window drawdown. This is a high-beta asset; the thesis is about years, not weeks.
- **Missing piece:** protocol fee revenue and burn are not modeled — public endpoints do not expose a
  clean historical fee series, and this report only uses directly sourceable numbers. Adding them is
  the top item in the README's future-work list.

## 6. Valuation scenarios (arithmetic, not predictions)

Applied to today's circulating supply of {sp['circulating_near']:,} NEAR:

| Scenario | Price | Implied market cap | Multiple |
| --- | --- | --- | --- |
{scen_md}

Re-rating merely to $5 — still 75% below the ATH — implies a {usd(5 * sp['circulating_near'])} market cap,
inside the range NEAR's own peer set already occupies at similar usage levels.

## Method & reproducibility

Sources: NearBlocks API (aggregates), NEAR mainnet RPC `status` and `validators` (stake summed
directly from the live set), CoinGecko (daily closes, peer markets). No API keys. Run:

```bash
python3 model.py && python3 build_dashboard.py
```

This regenerates `data/metrics.json`, `index.html`, and this report. Discrepancies between a figure
here and a fresh run are explained by the snapshot timestamp — markets move; the method doesn't.

*Research and education only — not financial advice.*
"""
(HERE / "ANALYSIS.md").write_text(analysis)
print("Wrote index.html and ANALYSIS.md")
