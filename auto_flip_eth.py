"""Automated Kraken Pro Dual-Bucket Auto-Flipper Daemon (Scenario A: $900 ETH + $10 SOL).

Watches the active Full-Stack Profit-Lock Sell Order (OV57WW-IWDWQ-D5XSSX @ $2,434.30).
The exact moment it fills and Kraken ZUSD balance reaches >= $900.00:
  1. BUCKET 1 ($900.00 ZUSD Core Principal -> ETH/USD Dip Re-Buy):
     Places a Post-Only Limit Buy (0.40% Maker fee) using $900.00 ($896.41 order + $3.59 fee)
     at $2,365.00 / ETH -> buying back 0.37903171 ETH (+0.00370 Free ETH gain!).
  2. BUCKET 2 (+$10.00 ZUSD House-Money Profit -> SOL/USD Perpetual Range Scraper):
     Takes the remaining ~$10.00 ZUSD locked profit and places a Post-Only Limit Buy on
     SOLUSD at $93.50 / SOL (~0.1065 SOL, >2x Kraken's 0.05 SOL minimum).
     Whenever the SOL Dip Buy fills, it automatically places a Post-Only Limit Sell on
     SOLUSD at $97.80 / SOL (near the $98.01 24h high) and compounds in a continuous loop!
  3. Sends instant Discord webhook notifications and syncs snapshot.json on every fill.
"""

import json
import time
import urllib.request
from live_tracker import get_snapshot, kraken_post, load_env

SELL_TXID = "OV57WW-IWDWQ-D5XSSX"
PROTECTED_PRINCIPAL_USD = 900.00
MAKER_FEE_RATE = 0.004  # 0.40% Kraken Pro Maker Fee

# Bucket 1: ETH Core Stack Dip Re-Buy Target
ETH_DIP_BUY_PRICE = 2365.00

# Bucket 2: SOL House-Money Range Scraper Targets
SOL_DIP_BUY_PRICE = 93.50
SOL_TOP_SELL_PRICE = 97.80


def send_discord_alert(webhook_url: str, title: str, description: str, color: int = 0x00F5A0) -> None:
    if not webhook_url:
        return
    payload = {
        "username": "SWOOZ.ETH Dual Auto-Flipper (ETH + SOL)",
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
            headers={"Content-Type": "application/json", "User-Agent": "SwoozAutoFlip/2.0"},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print("Discord alert error:", e, flush=True)


def main() -> None:
    env = load_env()
    webhook = env.get("DISCORD_WEBHOOK_URL", "")
    eth_rebuy_placed = False
    eth_rebuy_txid = None
    eth_rebuy_done = False

    sol_state = "IDLE"  # IDLE -> BUYING_DIP -> SELLING_TOP
    sol_order_txid = None

    print(
        f"[Dual Auto-Flipper Started] Watching {SELL_TXID} ($2,434.30 -> $900 ETH Re-Buy + $10 SOL Scraper)...",
        flush=True,
    )

    while True:
        try:
            env = load_env()
            oo = kraken_post("/0/private/OpenOrders", env_vars=env).get("result", {}).get("open", {})
            bal = kraken_post("/0/private/BalanceEx", env_vars=env).get("result", {})

            zusd_total = float(bal.get("ZUSD", {}).get("balance", 0.0) or 0.0)
            zusd_hold = float(bal.get("ZUSD", {}).get("hold_trade", 0.0) or 0.0)
            zusd_avail = max(0.0, zusd_total - zusd_hold)

            xeth_total = float(bal.get("XETH", {}).get("balance", 0.0) or 0.0)
            sol_total = float(bal.get("SOL", {}).get("balance", 0.0) or 0.0)
            sol_hold = float(bal.get("SOL", {}).get("hold_trade", 0.0) or 0.0)
            sol_avail = max(0.0, sol_total - sol_hold)

            # STEP 1 -> STEP 2A & 2B: When $2,434.30 ETH Sell fills and ~$910 ZUSD lands
            if not eth_rebuy_placed and (SELL_TXID not in oo) and zusd_avail >= 895.0:
                profit_bucket_usd = max(0.0, zusd_avail - PROTECTED_PRINCIPAL_USD)
                eth_deploy_usd = min(zusd_avail, PROTECTED_PRINCIPAL_USD)

                # 2A. Place $900.00 ETH Dip Re-Buy @ $2,365.00
                net_eth_order_usd = eth_deploy_usd / (1.0 + MAKER_FEE_RATE)
                buy_vol_eth = round(net_eth_order_usd / ETH_DIP_BUY_PRICE, 8)

                res_eth = kraken_post(
                    "/0/private/AddOrder",
                    {
                        "pair": "XETHZUSD",
                        "type": "buy",
                        "ordertype": "limit",
                        "price": f"{ETH_DIP_BUY_PRICE:.2f}",
                        "volume": f"{buy_vol_eth:.8f}",
                        "oflags": "post,fciq",
                    },
                    env_vars=env,
                )
                if not res_eth.get("error"):
                    txids = res_eth.get("result", {}).get("txid", [])
                    eth_rebuy_txid = txids[0] if txids else "PLACED"
                    eth_rebuy_placed = True

                time.sleep(0.5)

                # 2B. Place +$10.00 House-Money Profit Bucket into SOL/USD Dip Buy @ $93.50
                sol_msg_line = "⏳ Waiting for >= $5.00 ZUSD surplus for SOL order."
                if profit_bucket_usd >= 5.0:
                    net_sol_order_usd = profit_bucket_usd / (1.0 + MAKER_FEE_RATE)
                    buy_vol_sol = round(net_sol_order_usd / SOL_DIP_BUY_PRICE, 6)
                    if buy_vol_sol >= 0.05:
                        res_sol = kraken_post(
                            "/0/private/AddOrder",
                            {
                                "pair": "SOLUSD",
                                "type": "buy",
                                "ordertype": "limit",
                                "price": f"{SOL_DIP_BUY_PRICE:.2f}",
                                "volume": f"{buy_vol_sol:.6f}",
                                "oflags": "post,fciq",
                            },
                            env_vars=env,
                        )
                        if not res_sol.get("error"):
                            s_txids = res_sol.get("result", {}).get("txid", [])
                            sol_order_txid = s_txids[0] if s_txids else "PLACED"
                            sol_state = "BUYING_DIP"
                            sol_msg_line = (
                                f"🟢 **Bucket 2 (`SOL/USD` House-Money Scraper Placed — `{sol_order_txid}`)**:\n"
                                f"• `buy {buy_vol_sol:.5f} SOLUSD @ limit ${SOL_DIP_BUY_PRICE:.2f}` (`${profit_bucket_usd:.2f} USD` profit deployed)\n"
                                f"• Auto-flips to `sell @ ${SOL_TOP_SELL_PRICE:.2f}` once filled!"
                            )

                msg = (
                    f"✅ **Step 1 Full-Stack ETH Sell Filled (`{SELL_TXID}`) at `$2,434.30 / ETH`!**\n"
                    f"💰 **Total Cash Locked**: **`${zusd_total:.2f} USD`** (`$900.00` Principal + **`+${profit_bucket_usd:.2f} USD` Profit!**)\n\n"
                    f"🟢 **Bucket 1 (`ETH/USD` Core Dip Re-Buy Placed — `{eth_rebuy_txid}`)**:\n"
                    f"• `buy {buy_vol_eth:.6f} ETHUSD @ limit ${ETH_DIP_BUY_PRICE:.2f}` (`$900.00 USD` deployed → **`+{buy_vol_eth - 0.37532712:.5f} Free ETH`**)\n\n"
                    f"{sol_msg_line}"
                )
                print(msg, flush=True)
                send_discord_alert(
                    webhook,
                    "💰 $910 LOCKED! Auto-Deployed $900 ETH Re-Buy + $10 SOL Scraper!",
                    msg,
                )
                get_snapshot()

            # Check if Bucket 1 ($900 ETH Re-Buy) filled
            if eth_rebuy_placed and not eth_rebuy_done and eth_rebuy_txid and (eth_rebuy_txid not in oo) and xeth_total >= 0.375:
                eth_rebuy_done = True
                msg = (
                    f"🎉 **Bucket 1 (`$900 ETH Dip Re-Buy`) FILLED at `${ETH_DIP_BUY_PRICE:.2f}`!**\n"
                    f"• **New Kraken ETH Stack**: **`{xeth_total:.6f} ETH`** (**`+{xeth_total - 0.37532712:.6f} Free ETH` gained!**)"
                )
                print(msg, flush=True)
                send_discord_alert(webhook, "🎉 $900 ETH DIP RE-BUY FILLED (+0.0037 Free ETH)!", msg)
                get_snapshot()

            # Check Bucket 2 (SOL/USD Perpetual Range Scraper Loop)
            if sol_state == "BUYING_DIP" and sol_order_txid and (sol_order_txid not in oo) and sol_avail >= 0.05:
                # SOL Dip Buy filled! Automatically flip to Top Sell @ $97.80
                sell_vol_sol = round(sol_avail, 6)
                res_sol_sell = kraken_post(
                    "/0/private/AddOrder",
                    {
                        "pair": "SOLUSD",
                        "type": "sell",
                        "ordertype": "limit",
                        "price": f"{SOL_TOP_SELL_PRICE:.2f}",
                        "volume": f"{sell_vol_sol:.6f}",
                        "oflags": "post,fciq",
                    },
                    env_vars=env,
                )
                if not res_sol_sell.get("error"):
                    s_txids = res_sol_sell.get("result", {}).get("txid", [])
                    sol_order_txid = s_txids[0] if s_txids else "PLACED"
                    sol_state = "SELLING_TOP"
                    est_usd = sell_vol_sol * SOL_TOP_SELL_PRICE * (1.0 - MAKER_FEE_RATE)
                    msg = (
                        f"⚡ **SOL Dip Buy Filled (`@ ${SOL_DIP_BUY_PRICE:.2f}`)!**\n"
                        f"• Auto-placed Top Sell (`{sol_order_txid}`): `sell {sell_vol_sol:.5f} SOLUSD @ limit ${SOL_TOP_SELL_PRICE:.2f}`\n"
                        f"• Target Payout: **`${est_usd:.2f} USD` Net Cash**"
                    )
                    print(msg, flush=True)
                    send_discord_alert(webhook, f"⚡ SOL Dip Bought! Auto-Set Sell @ ${SOL_TOP_SELL_PRICE:.2f}", msg)
                    get_snapshot()

            elif sol_state == "SELLING_TOP" and sol_order_txid and (sol_order_txid not in oo) and zusd_avail >= 9.50:
                # SOL Top Sell filled! Re-deploy compounded SOL profit back into $93.50 Dip Buy!
                sol_budget_usd = zusd_avail if eth_rebuy_placed else max(0.0, zusd_avail - PROTECTED_PRINCIPAL_USD)
                if sol_budget_usd >= 5.0:
                    net_sol_usd = sol_budget_usd / (1.0 + MAKER_FEE_RATE)
                    buy_vol_sol = round(net_sol_usd / SOL_DIP_BUY_PRICE, 6)
                    res_sol_rebuy = kraken_post(
                        "/0/private/AddOrder",
                        {
                            "pair": "SOLUSD",
                            "type": "buy",
                            "ordertype": "limit",
                            "price": f"{SOL_DIP_BUY_PRICE:.2f}",
                            "volume": f"{buy_vol_sol:.6f}",
                            "oflags": "post,fciq",
                        },
                        env_vars=env,
                    )
                    if not res_sol_rebuy.get("error"):
                        s_txids = res_sol_rebuy.get("result", {}).get("txid", [])
                        sol_order_txid = s_txids[0] if s_txids else "PLACED"
                        sol_state = "BUYING_DIP"
                        msg = (
                            f"💰 **SOL Top Sell Filled (`@ ${SOL_TOP_SELL_PRICE:.2f}`)! Profit Compounded to `${sol_budget_usd:.2f} USD`!**\n"
                            f"• Auto-placed next Dip Buy (`{sol_order_txid}`): `buy {buy_vol_sol:.5f} SOLUSD @ limit ${SOL_DIP_BUY_PRICE:.2f}`"
                        )
                        print(msg, flush=True)
                        send_discord_alert(webhook, f"💰 SOL Top Scraped (${sol_budget_usd:.2f})! Re-Set Buy @ ${SOL_DIP_BUY_PRICE:.2f}", msg)
                        get_snapshot()

        except Exception as e:
            print("Watcher loop error:", e, flush=True)

        time.sleep(20)


if __name__ == "__main__":
    main()
