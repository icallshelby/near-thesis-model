#!/usr/bin/env python3
"""
NEAR by the Numbers — a re-runnable long-term investment thesis model.

Pulls live public data (no API keys) from:
  - NEAR mainnet RPC        https://rpc.mainnet.near.org
  - NearBlocks API          https://api.nearblocks.io/v1/stats
  - CoinGecko public API    https://api.coingecko.com/api/v3

Computes, from those raw responses only:
  - market snapshot (price, market cap, liquidity, drawdown from ATH)
  - supply structure (circulating vs total)
  - network usage (lifetime transactions, block cadence, nodes)
  - staking & decentralization from the LIVE validator set: total stake,
    staking ratio, top-1/5/10 pool concentration, Nakamoto coefficient
  - 365-day price history: returns, annualized volatility, max drawdown
  - peer benchmarking against other major L1s (market structure only)
  - valuation scenarios (supply held constant; arithmetic, not predictions)

Writes:
  - data/metrics.json        every metric + derivation + sources
  - data/snapshot_raw.json   the raw API responses, for full auditability

Run:  python3 model.py
Stdlib only. Anyone can re-run this and check every number.
"""

import json
import math
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

UA = {"User-Agent": "near-thesis-model/2.0 (+https://nearhackathon.com)"}
HERE = Path(__file__).resolve().parent
YOCTO = 10**24
PEERS = "ethereum,solana,avalanche-2,cardano,polkadot,cosmos,sui,aptos,near"


def fetch_json(url, payload=None, timeout=40):
    """urllib first; fall back to curl, which tolerates proxies that
    truncate responses mid-stream."""
    import subprocess

    body = json.dumps(payload) if payload is not None else None
    for _ in range(3):
        try:
            headers = dict(UA)
            data = body.encode() if body else None
            if data:
                headers["Content-Type"] = "application/json"
            req = urllib.request.Request(url, data=data, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode())
        except Exception:
            time.sleep(1)
    cmd = ["curl", "-s", "-m", str(timeout), "-A", UA["User-Agent"]]
    if body:
        cmd += ["-H", "Content-Type: application/json", "-d", body]
    cmd.append(url)
    out = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def rpc(method, params):
    return fetch_json(
        "https://rpc.mainnet.near.org",
        {"jsonrpc": "2.0", "id": "model", "method": method, "params": params},
    )["result"]


def pct(a, b, nd=2):
    return round(100.0 * a / b, nd) if b else None


def history_stats(prices):
    """prices: list of [ts_ms, price] daily points, oldest first."""
    closes = [p for _, p in prices if p > 0]
    if len(closes) < 30:
        return None
    def ret(days):
        if len(closes) <= days:
            return None
        return pct(closes[-1] - closes[-1 - days], closes[-1 - days])
    logs = [math.log(closes[i] / closes[i - 1]) for i in range(1, len(closes))]
    mean = sum(logs) / len(logs)
    var = sum((x - mean) ** 2 for x in logs) / (len(logs) - 1)
    vol_annual = round(math.sqrt(var) * math.sqrt(365) * 100, 1)
    peak, max_dd = closes[0], 0.0
    for c in closes:
        peak = max(peak, c)
        max_dd = min(max_dd, (c - peak) / peak)
    return {
        "points": len(closes),
        "daily_closes_usd": [round(c, 4) for c in closes],
        "return_30d_pct": ret(30),
        "return_90d_pct": ret(90),
        "return_365d_pct": ret(len(closes) - 1),
        "annualized_volatility_pct": vol_annual,
        "max_drawdown_in_window_pct": round(max_dd * 100, 1),
    }


def main():
    raw = {}

    # --- NearBlocks aggregate stats --------------------------------------
    nb = fetch_json("https://api.nearblocks.io/v1/stats")["stats"][0]
    raw["nearblocks_stats"] = nb

    # --- NEAR RPC: status + live validator set ---------------------------
    status = rpc("status", [])
    raw["rpc_status"] = {
        "chain_id": status["chain_id"],
        "latest_block_height": status["sync_info"]["latest_block_height"],
        "latest_protocol_version": status["latest_protocol_version"],
    }
    validators = rpc("validators", [None])
    vals = validators["current_validators"]
    stakes = sorted((int(v["stake"]) for v in vals), reverse=True)
    total_stake_yocto = sum(stakes)
    raw["rpc_validators_meta"] = {
        "epoch_height": validators["epoch_height"],
        "current_validators": len(vals),
        "shards": len(vals[0].get("num_expected_chunks_per_shard", [])) or None,
    }

    def top_share(n):
        return pct(sum(stakes[:n]) / YOCTO, total_stake_yocto / YOCTO)

    # Nakamoto coefficient: smallest number of validators whose combined
    # stake exceeds 1/3 of total stake (the BFT safety threshold).
    acc, nc = 0, 0
    for s in stakes:
        acc += s
        nc += 1
        if acc > total_stake_yocto / 3:
            break

    # --- CoinGecko: NEAR history + L1 peer markets ------------------------
    history, peers = None, []
    try:
        time.sleep(2)
        chart = fetch_json(
            "https://api.coingecko.com/api/v3/coins/near/market_chart"
            "?vs_currency=usd&days=365"
        )
        history = history_stats(chart["prices"])
        raw["coingecko_market_chart_meta"] = {
            "price_points": len(chart["prices"]),
        }
        time.sleep(2)
        markets = fetch_json(
            "https://api.coingecko.com/api/v3/coins/markets"
            f"?ids={PEERS}&vs_currency=usd"
            "&price_change_percentage=24h,7d,30d,1y"
        )
        raw["coingecko_markets"] = markets
        for c in markets:
            peers.append(
                {
                    "id": c["id"],
                    "symbol": c["symbol"].upper(),
                    "price_usd": c["current_price"],
                    "market_cap_usd": c["market_cap"],
                    "volume_24h_usd": c["total_volume"],
                    "volume_to_mcap_pct": pct(c["total_volume"], c["market_cap"]),
                    "ath_usd": c["ath"],
                    "drawdown_from_ath_pct": round(c["ath_change_percentage"], 1),
                    "change_1y_pct": (
                        round(c["price_change_percentage_1y_in_currency"], 1)
                        if c.get("price_change_percentage_1y_in_currency") is not None
                        else None
                    ),
                }
            )
        peers.sort(key=lambda x: -x["market_cap_usd"])
    except Exception as e:  # peer/history sections degrade gracefully
        raw["coingecko_error"] = str(e)

    # --- Derived snapshot metrics -----------------------------------------
    total_supply = int(nb["total_supply"]) / YOCTO
    circulating = int(nb["circulating_supply"]) / YOCTO
    price = float(nb["near_price"])
    mcap = float(nb["market_cap"])
    volume24 = float(nb["volume"])
    ath = float(nb["high_all"])
    total_stake = total_stake_yocto / YOCTO

    scenarios = []
    for label, target_price in [
        ("Re-rate to $5", 5.0),
        ("Re-rate to $10", 10.0),
        ("Back to all-time high", ath),
        ("2x all-time high", 2 * ath),
    ]:
        scenarios.append(
            {
                "scenario": label,
                "price_usd": target_price,
                "implied_market_cap_usd": round(target_price * circulating),
                "multiple_vs_today": round(target_price / price, 2),
            }
        )

    metrics = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "sources": [
            "https://api.nearblocks.io/v1/stats",
            "https://rpc.mainnet.near.org (status, validators)",
            "https://api.coingecko.com/api/v3/coins/near/market_chart?days=365",
            "https://api.coingecko.com/api/v3/coins/markets (L1 peer set)",
        ],
        "market": {
            "price_usd": price,
            "market_cap_usd": mcap,
            "fully_diluted_usd": round(price * total_supply),
            "volume_24h_usd": volume24,
            "volume_to_mcap_pct": pct(volume24, mcap),
            "change_24h_pct": float(nb["change_24"]),
            "ath_usd": ath,
            "drawdown_from_ath_pct": pct(price - ath, ath),
        },
        "supply": {
            "total_near": round(total_supply),
            "circulating_near": round(circulating),
            "circulating_pct_of_total": pct(circulating, total_supply),
        },
        "network": {
            "latest_block_height": status["sync_info"]["latest_block_height"],
            "avg_block_time_s": float(nb["avg_block_time"]),
            "blocks_per_day": round(86400 / float(nb["avg_block_time"])),
            "total_transactions": int(nb["total_txns"]),
            "reported_tps": nb["tps"],
            "nodes_online": nb["nodes_online"],
            "protocol_version": status["latest_protocol_version"],
            "shards": raw["rpc_validators_meta"]["shards"],
        },
        "staking_and_decentralization": {
            "current_validators": len(vals),
            "epoch_height": validators["epoch_height"],
            "total_staked_near": round(total_stake),
            "staking_ratio_pct_of_total_supply": pct(total_stake, total_supply),
            "top1_stake_share_pct": top_share(1),
            "top5_stake_share_pct": top_share(5),
            "top10_stake_share_pct": top_share(10),
            "nakamoto_coefficient": nc,
        },
        "history_365d": history,
        "peers": peers,
        "valuation_scenarios_supply_held_constant": scenarios,
        "notes": [
            "Scenarios are arithmetic (price x current circulating supply), not predictions.",
            "Nakamoto coefficient = fewest validators controlling >1/3 of stake, from the live RPC validator set.",
            "History statistics come from CoinGecko daily closes (365d); see snapshot_raw.json for provenance.",
            "Every input response is preserved in data/snapshot_raw.json.",
        ],
    }

    (HERE / "data").mkdir(exist_ok=True)
    (HERE / "data" / "metrics.json").write_text(json.dumps(metrics, indent=2))
    (HERE / "data" / "snapshot_raw.json").write_text(json.dumps(raw, indent=2))

    m, s, n, st = metrics["market"], metrics["supply"], metrics["network"], metrics["staking_and_decentralization"]
    print(f"NEAR thesis model v2 — {metrics['generated_at_utc']}")
    print(f"  Price ${m['price_usd']:.2f} | MCap ${m['market_cap_usd']:,.0f} | 24h vol {m['volume_to_mcap_pct']}% of mcap | ATH drawdown {m['drawdown_from_ath_pct']}%")
    print(f"  Validators {st['current_validators']} | Staked {st['staking_ratio_pct_of_total_supply']}% of supply | NC {st['nakamoto_coefficient']} | top10 {st['top10_stake_share_pct']}%")
    if history:
        print(f"  365d: return {history['return_365d_pct']}% | vol {history['annualized_volatility_pct']}% | maxDD {history['max_drawdown_in_window_pct']}%")
    print(f"  Peers benchmarked: {len(peers)}")
    print("  Wrote data/metrics.json and data/snapshot_raw.json")


if __name__ == "__main__":
    main()
