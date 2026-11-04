"""Automated Kraken Pro ETH Profit-Lock & Dip Re-Buy Watcher Daemon.

Watches the active Full-Stack Profit-Lock Sell Order (OV57WW-IWDWQ-D5XSSX @ $2,434.30).
The moment it fills and Kraken ZUSD balance reaches >= $900.00:
  1. Keeps all profit above $900.00 (~+$10.00 USD) permanently locked in ZUSD cash.
  2. Automatically places a Post-Only Limit Buy (0.40% Maker fee) using only the
     $900.00 principal ($896.41 order value + $3.59 Maker fee = $900.00 total)
     at $2,365.00 / ETH -> buying back 0.37903171 ETH (+0.00370 Free ETH gain!).
  3. Sends an instant Discord webhook notification and updates snapshot.json.
"""

import json
import time
import urllib.request
from live_tracker import get_snapshot, kraken_post, load_env

SELL_TXID = "OV57WW-IWDWQ-D5XSSX"
PROTECTED_PRINCIPAL_USD = 900.00
MAKER_FEE_RATE = 0.004  # 0.40% Kraken Pro Maker Fee
DIP_REBUY_PRICE_USD = 2365.00  # Yields 0.37903 ETH (+0.00370 Free ETH) while keeping +$10.00 USD cash!


def send_discord_alert(webhook_url: str, title: str, description: str, color: int = 0x00F5A0) -> None:
    if not webhook_url:
        return
    payload = {
        "username": "SWOOZ.ETH Auto-Flipper",
        "content": f"🚨 **{title}**",
        "embeds": [
            {
                "title": title,
                "description": description,
                "color": color,
            }
        ],
    }
    try:
        req = urllib.request.Request(
            webhook_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "User-Agent": "SwoozAutoFlip/1.0"},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print("Discord alert error:", e, flush=True)


def main() -> None:
    env = load_env()
    webhook = env.get("DISCORD_WEBHOOK_URL", "")
    rebuy_placed = False
    rebuy_txid = None

    print(
        f"[Auto-Flipper Started] Watching Sell Order {SELL_TXID} ($2,434.30 -> $910.00 Net Cash)...",
        flush=True,
    )

    while True:
        try:
            env = load_env()
            oo = kraken_post("/0/private/OpenOrders", env_vars=env).get("result", {}).get("open", {})
            bal = kraken_post("/0/private/BalanceEx", env_vars=env).get("result", {})

            zusd_total = float(bal.get("ZUSD", {}).get("balance", 0.0) or 0.0)
            zusd_hold = float(bal.get("ZUSD", {}).get("hold_trade", 0.0) or 0.0)
            zusd_avail = zusd_total - zusd_hold
            xeth_total = float(bal.get("XETH", {}).get("balance", 0.0) or 0.0)

            # Check if Sell Order filled and ZUSD is available for the $900 Re-Buy
            if not rebuy_placed and (SELL_TXID not in oo) and zusd_avail >= 895.0:
                locked_profit = max(0.0, zusd_total - PROTECTED_PRINCIPAL_USD)
                deploy_usd = min(zusd_avail, PROTECTED_PRINCIPAL_USD)
                # Account for 0.40% Maker fee so total cost (order value + fee) <= $900.00
                net_order_usd = deploy_usd / (1.0 + MAKER_FEE_RATE)
                buy_vol_eth = round(net_order_usd / DIP_REBUY_PRICE_USD, 8)

                res = kraken_post(
                    "/0/private/AddOrder",
                    {
                        "pair": "XETHZUSD",
                        "type": "buy",
                        "ordertype": "limit",
                        "price": f"{DIP_REBUY_PRICE_USD:.2f}",
                        "volume": f"{buy_vol_eth:.8f}",
                        "oflags": "post,fciq",
                    },
                    env_vars=env,
                )
                errs = res.get("error", [])
                if not errs:
                    txids = res.get("result", {}).get("txid", [])
                    rebuy_txid = txids[0] if txids else "PLACED"
                    rebuy_placed = True
                    msg = (
                        f"✅ **Step 1 Sell Filled (`{SELL_TXID}`)**: Your `0.37532712 ETH` sold at **`$2,434.30 / ETH`**!\n"
                        f"💰 **Total Cash Received**: **`${zusd_total:.2f} USD`** (**`+${locked_profit:.2f} USD` profit permanently locked in cash!**)\n\n"
                        f"🎯 **Step 2 Auto-Placed (`{rebuy_txid}`)**:\n"
                        f"• **Order**: `buy {buy_vol_eth:.6f} ETHUSD @ limit ${DIP_REBUY_PRICE_USD:.2f}` (`Post-Only` 0.40% Maker)\n"
                        f"• **Capital Deployed**: **`${deploy_usd:.2f} USD`** (leaving **`+${locked_profit:.2f} USD`** untouched in cash!)\n"
                        f"• **Result When Filled**: **`{buy_vol_eth:.5f} ETH`** (**`+{buy_vol_eth - 0.37532712:.5f} Free ETH`** + **`+${locked_profit:.2f} USD`** cash!)"
                    )
                    print(msg, flush=True)
                    send_discord_alert(
                        webhook,
                        f"💰 $910.00 PROFIT LOCKED! Auto-Placed $900 Dip Re-Buy @ ${DIP_REBUY_PRICE_USD:.2f}",
                        msg,
                    )
                    get_snapshot()
                else:
                    print("Re-buy AddOrder error:", errs, flush=True)

            # If Step 2 Re-Buy was placed and has now filled
            elif rebuy_placed and rebuy_txid and (rebuy_txid not in oo) and xeth_total >= 0.375:
                msg = (
                    f"🎉 **Step 2 Dip Re-Buy (`{rebuy_txid}`) FILLED at `${DIP_REBUY_PRICE_USD:.2f}`!**\n"
                    f"• **New Kraken ETH Stack**: **`{xeth_total:.6f} ETH`** (`+{xeth_total - 0.37532712:.6f} Free ETH` gained!)\n"
                    f"• **Locked Cash Profit Remaining**: **`${zusd_total:.2f} USD`**"
                )
                print(msg, flush=True)
                send_discord_alert(webhook, "🎉 FULL CYCLE COMPLETE: Free ETH + Locked USD Profit!", msg)
                get_snapshot()
                break

        except Exception as e:
            print("Watcher loop error:", e, flush=True)

        time.sleep(20)


if __name__ == "__main__":
    main()
