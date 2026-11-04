"""Automated Kraken Pro ETH 'Scrape the Top' Limit Sell Ladder (Post-Only Maker Orders).

Places 4 Post-Only (0.40% Maker fee) Limit Sell rungs on XETHZUSD that skim profit
into USD cash every time ETH pumps higher, while keeping 0.36003 ETH untouched for
Invisible Friends #1506 (0.210 WETH) + CloneX (0.1447 ETH) = 0.3547 ETH!

Usage:
  python place_eth_ladder.py            # Places all 4 Post-Only Limit Sell orders on Kraken
  python place_eth_ladder.py --dry-run  # Validates orders without placing them
"""

import sys
import time
from live_tracker import kraken_post, load_env

# 4-Rung Top-Scraper Ladder (Total = 0.01530 ETH -> $37.75 USD Gross / $37.60 Net Cash)
# Leaves 0.360027 ETH untouched (covers IF #1506 0.210 + CloneX 0.1447 = 0.3547 ETH + Gas!)
LADDER_RUNGS = [
    {
        "rung": 1,
        "label": "Rung 1 — Immediate Top Skim (Lock Current Profit > $900)",
        "price": "2435.00",
        "volume": "0.00520",
    },
    {
        "rung": 2,
        "label": "Rung 2 — 24h High Breakout Skim (+$20/ETH Leg)",
        "price": "2455.00",
        "volume": "0.00300",
    },
    {
        "rung": 3,
        "label": "Rung 3 — Momentum Extension Skim (+$45/ETH Leg)",
        "price": "2480.00",
        "volume": "0.00350",
    },
    {
        "rung": 4,
        "label": "Rung 4 — $2,500+ Psychological Breakout Skim",
        "price": "2510.00",
        "volume": "0.00360",
    },
]


def main() -> None:
    dry_run = "--dry-run" in sys.argv
    env = load_env()

    print("=" * 72)
    print("  SWOOZ.ETH KRAKEN PRO 'SCRAPE THE TOP' LIMIT SELL LADDER (XETHZUSD)")
    print("=" * 72)

    total_eth = 0.0
    total_usd = 0.0

    for r in LADDER_RUNGS:
        p = float(r["price"])
        v = float(r["volume"])
        usd = p * v
        fee = usd * 0.004  # 0.40% Maker fee
        net = usd - fee
        total_eth += v
        total_usd += net

        payload = {
            "pair": "XETHZUSD",
            "type": "sell",
            "ordertype": "limit",
            "price": r["price"],
            "volume": r["volume"],
            "oflags": "post",  # Guarantees 0.40% Maker fee (never 0.80% Taker)
        }
        if dry_run:
            payload["validate"] = "true"

        res = kraken_post("/0/private/AddOrder", payload, env_vars=env)
        errs = res.get("error", [])
        if errs:
            print(f"[!] {r['label']}:")
            print(f"    Sell {r['volume']} ETH @ ${r['price']} (${usd:.2f} USD | Net +${net:.2f} after $0.05 fee)")
            print(f"    Kraken API Response: {errs[0]}")
            if "Permission denied" in str(errs):
                print("    -> NOTE: Your API key is currently Read-Only. Either enter the 4 rungs")
                print("       manually in your open Kraken Pro window, or check 'Create & modify orders'")
                print("       in Kraken -> Settings -> API for this key and re-run this script!")
        else:
            txids = res.get("result", {}).get("txid", [])
            descr = res.get("result", {}).get("descr", {}).get("order", "")
            print(f"[OK] {r['label']} PLACED: {descr} (txid: {txids})")
        time.sleep(0.4)

    print("-" * 72)
    print(f"Total ETH in Top-Scraper Ladder : {total_eth:.5f} ETH")
    print(f"Total Locked Cash if All 4 Fill : +${total_usd:.2f} USD (Net of 0.40% Maker Fees)")
    print(f"Protected ETH Left for NFTs     : {0.37532712 - total_eth:.5f} ETH (Covers IF #1506 + CloneX + Gas!)")
    print("=" * 72)


if __name__ == "__main__":
    main()
