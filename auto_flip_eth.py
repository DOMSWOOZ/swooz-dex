"""Unified Kraken Pro (3 Legs) + Coinbase Advanced Trade (6 Legs) Auto-Flipper Daemon.

Watches all 9 live Post-Only Maker limit orders across BOTH exchanges 24/7:

KRAKEN PRO (0.40% Maker Fee):
  1. K-Leg 1 (ETH Upside Sell — OQZFZ5-JE7VA-XL4ICG): 0.32000000 ETH @ $2,434.30 <-> Auto-Buy @ $2,365.00
  2. K-Leg 2 (ETH Dip Buy — O2M55I-TTRGZ-JHPZLG):     0.05085957 ETH @ $2,350.00 <-> Auto-Sell @ $2,434.30
  3. K-Leg 3 (SOL Dip Scraper — OXHR5G-7XDXV-JDJ77G): 0.13324064 SOL @ $93.50    <-> Auto-Sell @ $97.80

COINBASE ADVANCED TRADE (0.50% Maker Fee):
  4. CB-Leg 1 (ETH Upside Sell — 6ccbc4fb-fdd1-4cac-a168-045eba43851d): 0.04620134 ETH @ $2,435.00 <-> Auto-Buy @ $2,360.00
  5. CB-Leg 2 (SOL Upside Sell — af8d6809-13cc-4270-aaf1-ed293aedd88e): 0.28494619 SOL @ $97.80    <-> Auto-Buy @ $93.50
  6. CB-Leg 3 (BTC Upside Sell — 245c48b9-9ff8-403c-89ae-a999ad3868a0): 0.00087620 BTC @ $81,800   <-> Auto-Buy @ $78,800
  7. CB-Leg 4 (LINK Upside Sell — 21abdc51-4595-4432-948e-6885eb412b77): 2.37 LINK @ $11.85        <-> Auto-Buy @ $11.05
  8. CB-Leg 5 (ETH Dip Buy — 6f967d19-e0f9-4c03-ab8e-7cb6c21d6b5b):     0.02328000 ETH @ $2,350.00 <-> Auto-Sell @ $2,435.00
  9. CB-Leg 6 (SOL Dip Buy — 76e7ed73-8732-4cc2-b35b-4accb2bd62bb):     0.30250000 SOL @ $93.40    <-> Auto-Sell @ $97.80
"""

import json
import time
import urllib.request
import uuid
from coinbase_helper import cb_request
from live_tracker import get_snapshot, kraken_post, load_env

KRAKEN_MAKER_FEE = 0.004
CB_MAKER_FEE = 0.005


def send_discord_alert(webhook_url: str, title: str, description: str, color: int = 0x10B981) -> None:
    if not webhook_url:
        return
    payload = {
        "username": "SWOOZ.ETH 9-Leg Dual-Exchange Bot",
        "content": f"🚨 **{title}**",
        "embeds": [{"title": title, "description": description, "color": color}],
    }
    try:
        req = urllib.request.Request(
            webhook_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "User-Agent": "SwoozAutoFlip/4.0"},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print("Discord alert error:", e, flush=True)


def place_cb_post_only(product_id: str, side: str, base_size: str, limit_price: str) -> str | None:
    body = {
        "client_order_id": str(uuid.uuid4()),
        "product_id": product_id,
        "side": side.upper(),
        "order_configuration": {
            "limit_limit_gtc": {
                "base_size": base_size,
                "limit_price": limit_price,
                "post_only": True,
            }
        },
    }
    res = cb_request("POST", "/api/v3/brokerage/orders", body=body)
    if res.get("success"):
        return res.get("success_response", {}).get("order_id")
    return None


def main() -> None:
    env = load_env()
    webhook = env.get("DISCORD_WEBHOOK_URL", "")

    # Kraken 3 Legs
    k_leg1_txid = "OQZFZ5-JE7VA-XL4ICG"
    k_leg1_state = "SELLING_TOP"

    k_leg2_txid = "O2M55I-TTRGZ-JHPZLG"
    k_leg2_state = "BUYING_DIP"

    k_sol_txid = "OXHR5G-7XDXV-JDJ77G"
    k_sol_state = "BUYING_DIP"

    # Coinbase 6 Legs
    cb_legs = [
        {
            "name": "CB ETH Upside",
            "order_id": "6ccbc4fb-fdd1-4cac-a168-045eba43851d",
            "product_id": "ETH-USDC",
            "state": "SELL",
            "buy_px": 2360.00,
            "sell_px": 2435.00,
            "decimals": 6,
        },
        {
            "name": "CB SOL Upside",
            "order_id": "af8d6809-13cc-4270-aaf1-ed293aedd88e",
            "product_id": "SOL-USDC",
            "state": "SELL",
            "buy_px": 93.50,
            "sell_px": 97.80,
            "decimals": 6,
        },
        {
            "name": "CB BTC Upside",
            "order_id": "245c48b9-9ff8-403c-89ae-a999ad3868a0",
            "product_id": "BTC-USDC",
            "state": "SELL",
            "buy_px": 78800.00,
            "sell_px": 81800.00,
            "decimals": 7,
        },
        {
            "name": "CB LINK Upside",
            "order_id": "21abdc51-4595-4432-948e-6885eb412b77",
            "product_id": "LINK-USDC",
            "state": "SELL",
            "buy_px": 11.05,
            "sell_px": 11.85,
            "decimals": 2,
        },
        {
            "name": "CB ETH Dip-Catcher",
            "order_id": "6f967d19-e0f9-4c03-ab8e-7cb6c21d6b5b",
            "product_id": "ETH-USDC",
            "state": "BUY",
            "buy_px": 2350.00,
            "sell_px": 2435.00,
            "decimals": 6,
        },
        {
            "name": "CB SOL Dip-Catcher",
            "order_id": "76e7ed73-8732-4cc2-b35b-4accb2bd62bb",
            "product_id": "SOL-USDC",
            "state": "BUY",
            "buy_px": 93.40,
            "sell_px": 97.80,
            "decimals": 6,
        },
    ]

    print(
        "[9-Leg Dual-Exchange Auto-Flipper Live] Watching 3 Kraken Pro Orders + 6 Coinbase Advanced Orders!",
        flush=True,
    )

    while True:
        try:
            env = load_env()
            # 1. Check Kraken Pro 3 Legs
            oo = kraken_post("/0/private/OpenOrders", env_vars=env).get("result", {}).get("open", {})
            bal = kraken_post("/0/private/BalanceEx", env_vars=env).get("result", {})

            zusd_avail = max(
                0.0,
                float(bal.get("ZUSD", {}).get("balance", 0.0) or 0.0)
                - float(bal.get("ZUSD", {}).get("hold_trade", 0.0) or 0.0),
            )
            xeth_avail = max(
                0.0,
                float(bal.get("XETH", {}).get("balance", 0.0) or 0.0)
                - float(bal.get("XETH", {}).get("hold_trade", 0.0) or 0.0),
            )
            sol_avail = max(
                0.0,
                float(bal.get("SOL", {}).get("balance", 0.0) or 0.0)
                - float(bal.get("SOL", {}).get("hold_trade", 0.0) or 0.0),
            )

            if k_leg1_state == "SELLING_TOP" and k_leg1_txid and (k_leg1_txid not in oo) and zusd_avail >= 750.0:
                deploy_usd = min(zusd_avail, 775.86)
                buy_vol = round((deploy_usd / (1.0 + KRAKEN_MAKER_FEE)) / 2365.00, 8)
                res = kraken_post(
                    "/0/private/AddOrder",
                    {
                        "pair": "XETHZUSD",
                        "type": "buy",
                        "ordertype": "limit",
                        "price": "2365.00",
                        "volume": f"{buy_vol:.8f}",
                        "oflags": "post,fciq",
                    },
                    env_vars=env,
                )
                if not res.get("error"):
                    k_leg1_txid = (res.get("result", {}).get("txid") or ["PLACED"])[0]
                    k_leg1_state = "BUYING_DIP"
                    send_discord_alert(
                        webhook,
                        "💰 Kraken Leg 1 ($2,434.30) Filled! Auto-Set Re-Buy @ $2,365",
                        f"Placed `{k_leg1_txid}` for `{buy_vol:.6f} ETH` @ `$2,365.00`!",
                    )
                    get_snapshot()

            if k_leg2_state == "BUYING_DIP" and k_leg2_txid and (k_leg2_txid not in oo) and xeth_avail >= 0.050:
                sell_vol = round(xeth_avail, 8)
                res = kraken_post(
                    "/0/private/AddOrder",
                    {
                        "pair": "XETHZUSD",
                        "type": "sell",
                        "ordertype": "limit",
                        "price": "2434.30",
                        "volume": f"{sell_vol:.8f}",
                        "oflags": "post,fciq",
                    },
                    env_vars=env,
                )
                if not res.get("error"):
                    k_leg2_txid = (res.get("result", {}).get("txid") or ["PLACED"])[0]
                    k_leg2_state = "SELLING_TOP"
                    send_discord_alert(
                        webhook,
                        "🎯 Kraken ETH Dip Caught @ $2,350! Auto-Set Sell @ $2,434.30",
                        f"Placed `{k_leg2_txid}` for `{sell_vol:.6f} ETH` @ `$2,434.30`!",
                    )
                    get_snapshot()

            if k_sol_state == "BUYING_DIP" and k_sol_txid and (k_sol_txid not in oo) and sol_avail >= 0.05:
                sell_vol = round(sol_avail, 6)
                res = kraken_post(
                    "/0/private/AddOrder",
                    {
                        "pair": "SOLUSD",
                        "type": "sell",
                        "ordertype": "limit",
                        "price": "97.80",
                        "volume": f"{sell_vol:.6f}",
                        "oflags": "post,fciq",
                    },
                    env_vars=env,
                )
                if not res.get("error"):
                    k_sol_txid = (res.get("result", {}).get("txid") or ["PLACED"])[0]
                    k_sol_state = "SELLING_TOP"
                    send_discord_alert(
                        webhook,
                        "⚡ Kraken SOL Dip Caught @ $93.50! Auto-Set Sell @ $97.80",
                        f"Placed `{k_sol_txid}` for `{sell_vol:.5f} SOL` @ `$97.80`!",
                    )
                    get_snapshot()

            # 2. Check Coinbase Advanced Trade 6 Legs
            for leg in cb_legs:
                oid = leg["order_id"]
                if not oid:
                    continue
                o_info = cb_request("GET", f"/api/v3/brokerage/orders/historical/{oid}").get("order", {})
                status = o_info.get("status", "")
                if status == "FILLED":
                    filled_sz = float(o_info.get("filled_size", 0.0) or 0.0)
                    filled_val = float(o_info.get("filled_value", 0.0) or 0.0)
                    dec = leg["decimals"]
                    if leg["state"] == "SELL" and filled_val > 5.0:
                        # Flip to BUY at buy_px
                        net_usdc = filled_val * (1.0 - CB_MAKER_FEE) / (1.0 + CB_MAKER_FEE)
                        new_sz = round(net_usdc / leg["buy_px"], dec)
                        new_oid = place_cb_post_only(
                            leg["product_id"], "BUY", f"{new_sz:.{dec}f}", f"{leg['buy_px']:.2f}"
                        )
                        if new_oid:
                            leg["order_id"] = new_oid
                            leg["state"] = "BUY"
                            send_discord_alert(
                                webhook,
                                f"🔵 {leg['name']} Top Sell FILLED! Auto-Set Dip Buy @ ${leg['buy_px']:.2f}",
                                f"Placed Coinbase Post-Only BUY `{new_oid[:8]}` for `{new_sz}` `{leg['product_id']}` @ `${leg['buy_px']:.2f}`!",
                            )
                            get_snapshot()
                    elif leg["state"] == "BUY" and filled_sz > 0:
                        # Flip to SELL at sell_px
                        new_sz = round(filled_sz, dec)
                        new_oid = place_cb_post_only(
                            leg["product_id"], "SELL", f"{new_sz:.{dec}f}", f"{leg['sell_px']:.2f}"
                        )
                        if new_oid:
                            leg["order_id"] = new_oid
                            leg["state"] = "SELL"
                            send_discord_alert(
                                webhook,
                                f"🔵 {leg['name']} Dip Buy FILLED! Auto-Set Top Sell @ ${leg['sell_px']:.2f}",
                                f"Placed Coinbase Post-Only SELL `{new_oid[:8]}` for `{new_sz}` `{leg['product_id']}` @ `${leg['sell_px']:.2f}`!",
                            )
                            get_snapshot()

        except Exception as e:
            print("Watcher loop error:", e, flush=True)

        time.sleep(20)


if __name__ == "__main__":
    main()
