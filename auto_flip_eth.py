"""Automated Kraken Pro 3-Leg Dual-Sided Straddle Daemon (Option 1 — Playing Both Sides!).

Watches all 3 live Post-Only Maker (0.40%) orders on the Kraken book:
  1. LEG 1 (85% Upside Profit-Lock — OQZFZ5-JE7VA-XL4ICG):
     `sell 0.32000000 ETHUSD @ limit $2,434.30` (~$775.86 Net USD).
     When filled -> auto-places Post-Only Limit Buy at $2,365.00/ETH (~0.32675 ETH, +0.00675 Free ETH!).
  2. LEG 2 (ETH Dip-Catcher — O2M55I-TTRGZ-JHPZLG):
     `buy 0.05085957 ETHUSD @ limit $2,350.00` ($120.00 USD deployed).
     When filled -> auto-places Post-Only Limit Sell at $2,434.30/ETH (compounding back into top sell!).
  3. LEG 3 (SOL/USD Perpetual Range Scraper — OXHR5G-7XDXV-JDJ77G):
     `buy 0.13324064 SOLUSD @ limit $93.50` ($12.51 USD deployed).
     When filled -> auto-places Post-Only Limit Sell at $97.80/SOL (~$12.98 Net USD) and loops continuously!
"""

import json
import time
import urllib.request
from live_tracker import get_snapshot, kraken_post, load_env

MAKER_FEE_RATE = 0.004  # 0.40% Kraken Pro Maker Fee

# Leg 1: 85% Core ETH Upside -> Dip Re-Buy
LEG1_SELL_TXID = "OQZFZ5-JE7VA-XL4ICG"
LEG1_SELL_PRICE = 2434.30
LEG1_REBUY_PRICE = 2365.00

# Leg 2: $120 ETH Dip-Catcher -> Bounce Sell
LEG2_BUY_TXID = "O2M55I-TTRGZ-JHPZLG"
LEG2_BUY_PRICE = 2350.00
LEG2_SELL_PRICE = 2434.30

# Leg 3: $12.51 SOL/USD Range Scraper Loop
LEG3_SOL_BUY_TXID = "OXHR5G-7XDXV-JDJ77G"
SOL_DIP_BUY_PRICE = 93.50
SOL_TOP_SELL_PRICE = 97.80


def send_discord_alert(webhook_url: str, title: str, description: str, color: int = 0x10B981) -> None:
    if not webhook_url:
        return
    payload = {
        "username": "SWOOZ.ETH Straddle Auto-Flipper",
        "content": f"🚨 **{title}**",
        "embeds": [{"title": title, "description": description, "color": color}],
    }
    try:
        req = urllib.request.Request(
            webhook_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "User-Agent": "SwoozAutoFlip/3.0"},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print("Discord alert error:", e, flush=True)


def main() -> None:
    env = load_env()
    webhook = env.get("DISCORD_WEBHOOK_URL", "")

    leg1_state = "SELLING_TOP"  # SELLING_TOP -> BUYING_DIP -> DONE
    leg1_txid = LEG1_SELL_TXID

    leg2_state = "BUYING_DIP"   # BUYING_DIP -> SELLING_TOP -> DONE
    leg2_txid = LEG2_BUY_TXID

    sol_state = "BUYING_DIP"    # BUYING_DIP <-> SELLING_TOP
    sol_txid = LEG3_SOL_BUY_TXID

    print(
        f"[3-Leg Straddle Daemon Live] Watching:\n"
        f"  • Leg 1 (ETH Upside Sell @ $2,434.30): {leg1_txid}\n"
        f"  • Leg 2 (ETH Dip Buy @ $2,350.00):     {leg2_txid}\n"
        f"  • Leg 3 (SOL Dip Buy @ $93.50):        {sol_txid}",
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
            xeth_hold = float(bal.get("XETH", {}).get("hold_trade", 0.0) or 0.0)
            xeth_avail = max(0.0, xeth_total - xeth_hold)

            sol_total = float(bal.get("SOL", {}).get("balance", 0.0) or 0.0)
            sol_hold = float(bal.get("SOL", {}).get("hold_trade", 0.0) or 0.0)
            sol_avail = max(0.0, sol_total - sol_hold)

            # ================= LEG 1: 0.3200 ETH @ $2,434.30 =================
            if leg1_state == "SELLING_TOP" and leg1_txid and (leg1_txid not in oo) and zusd_avail >= 750.0:
                deploy_usd = min(zusd_avail, 775.86)
                net_order_usd = deploy_usd / (1.0 + MAKER_FEE_RATE)
                buy_vol_eth = round(net_order_usd / LEG1_REBUY_PRICE, 8)
                res = kraken_post(
                    "/0/private/AddOrder",
                    {
                        "pair": "XETHZUSD",
                        "type": "buy",
                        "ordertype": "limit",
                        "price": f"{LEG1_REBUY_PRICE:.2f}",
                        "volume": f"{buy_vol_eth:.8f}",
                        "oflags": "post,fciq",
                    },
                    env_vars=env,
                )
                if not res.get("error"):
                    txids = res.get("result", {}).get("txid", [])
                    leg1_txid = txids[0] if txids else "PLACED"
                    leg1_state = "BUYING_DIP"
                    msg = (
                        f"✅ **Leg 1 Upside ETH Sell Filled (`0.3200 ETH @ $2,434.30`)!**\n"
                        f"• Auto-placed Dip Re-Buy (`{leg1_txid}`): `buy {buy_vol_eth:.6f} ETHUSD @ limit ${LEG1_REBUY_PRICE:.2f}`\n"
                        f"• Gains **`+{buy_vol_eth - 0.32:.5f} Free ETH`** when filled!"
                    )
                    print(msg, flush=True)
                    send_discord_alert(webhook, "💰 Leg 1 ($2,434.30) Filled! Auto-Set Re-Buy @ $2,365", msg)
                    get_snapshot()

            # ================= LEG 2: 0.05086 ETH Dip Buy @ $2,350.00 =================
            if leg2_state == "BUYING_DIP" and leg2_txid and (leg2_txid not in oo) and xeth_avail >= 0.050:
                sell_vol_eth = round(xeth_avail, 8)
                res = kraken_post(
                    "/0/private/AddOrder",
                    {
                        "pair": "XETHZUSD",
                        "type": "sell",
                        "ordertype": "limit",
                        "price": f"{LEG2_SELL_PRICE:.2f}",
                        "volume": f"{sell_vol_eth:.8f}",
                        "oflags": "post,fciq",
                    },
                    env_vars=env,
                )
                if not res.get("error"):
                    txids = res.get("result", {}).get("txid", [])
                    leg2_txid = txids[0] if txids else "PLACED"
                    leg2_state = "SELLING_TOP"
                    msg = (
                        f"🎯 **Leg 2 ETH Dip Buy Filled (`{sell_vol_eth:.5f} ETH @ $2,350.00`)!**\n"
                        f"• Auto-placed Top Sell (`{leg2_txid}`): `sell {sell_vol_eth:.6f} ETHUSD @ limit ${LEG2_SELL_PRICE:.2f}`"
                    )
                    print(msg, flush=True)
                    send_discord_alert(webhook, "🎯 ETH Dip Caught @ $2,350! Auto-Set Sell @ $2,434.30", msg)
                    get_snapshot()

            # ================= LEG 3: SOL/USD Perpetual Scraper ($93.50 <-> $97.80) =================
            if sol_state == "BUYING_DIP" and sol_txid and (sol_txid not in oo) and sol_avail >= 0.05:
                sell_vol_sol = round(sol_avail, 6)
                res = kraken_post(
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
                if not res.get("error"):
                    txids = res.get("result", {}).get("txid", [])
                    sol_txid = txids[0] if txids else "PLACED"
                    sol_state = "SELLING_TOP"
                    est_usd = sell_vol_sol * SOL_TOP_SELL_PRICE * (1.0 - MAKER_FEE_RATE)
                    msg = (
                        f"⚡ **Leg 3 SOL Dip Buy Filled (`{sell_vol_sol:.5f} SOL @ ${SOL_DIP_BUY_PRICE:.2f}`)!**\n"
                        f"• Auto-placed Top Sell (`{sol_txid}`): `sell {sell_vol_sol:.5f} SOLUSD @ limit ${SOL_TOP_SELL_PRICE:.2f}`\n"
                        f"• Target Payout: **`${est_usd:.2f} USD` Net Cash**"
                    )
                    print(msg, flush=True)
                    send_discord_alert(webhook, f"⚡ SOL Dip Bought @ $93.50! Auto-Set Sell @ ${SOL_TOP_SELL_PRICE:.2f}", msg)
                    get_snapshot()

            elif sol_state == "SELLING_TOP" and sol_txid and (sol_txid not in oo) and zusd_avail >= 11.0:
                sol_budget_usd = min(zusd_avail, 25.0)
                net_sol_usd = sol_budget_usd / (1.0 + MAKER_FEE_RATE)
                buy_vol_sol = round(net_sol_usd / SOL_DIP_BUY_PRICE, 6)
                if buy_vol_sol >= 0.05:
                    res = kraken_post(
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
                    if not res.get("error"):
                        txids = res.get("result", {}).get("txid", [])
                        sol_txid = txids[0] if txids else "PLACED"
                        sol_state = "BUYING_DIP"
                        msg = (
                            f"💰 **SOL Top Sell Filled (`@ ${SOL_TOP_SELL_PRICE:.2f}`)! Compounded to `${sol_budget_usd:.2f} USD`!**\n"
                            f"• Auto-placed next Dip Buy (`{sol_txid}`): `buy {buy_vol_sol:.5f} SOLUSD @ limit ${SOL_DIP_BUY_PRICE:.2f}`"
                        )
                        print(msg, flush=True)
                        send_discord_alert(webhook, f"💰 SOL Top Scraped (${sol_budget_usd:.2f})! Re-Set Buy @ ${SOL_DIP_BUY_PRICE:.2f}", msg)
                        get_snapshot()

        except Exception as e:
            print("Watcher loop error:", e, flush=True)

        time.sleep(20)


if __name__ == "__main__":
    main()
