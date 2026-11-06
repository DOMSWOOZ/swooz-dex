"""Unified Kraken Pro (3 Legs) + Coinbase Advanced Trade (6 Legs) Bidirectional Auto-Flipper & Trade Logger.

Watches all 9 live Post-Only Maker limit orders across BOTH exchanges 24/7 and logs every executed leg
to `trade_history.json` for quantitative performance analysis:

KRAKEN PRO (0.40% Maker Fee):
  1. K-Leg 1 (ETH Core Ping-Pong — OB3VUY-7XHEE-EISY6C): BUY 0.32675219 ETH @ $2,365.00 <-> SELL @ $2,434.30
  2. K-Leg 2 (ETH Dip Catcher — O2M55I-TTRGZ-JHPZLG):    BUY 0.05085957 ETH @ $2,350.00 <-> SELL @ $2,434.30
  3. K-Leg 3 (SOL Dip Scraper — OXHR5G-7XDXV-JDJ77G):    BUY 0.13324064 SOL @ $93.50    <-> SELL @ $97.80

COINBASE ADVANCED TRADE (0.50% Maker Fee):
  4. CB-Leg 1 (ETH Core Ping-Pong — 1b4768d6-07e7-4ecd-afc0-c19e77a8732a): BUY 0.04719500 ETH @ $2,360.00 <-> SELL @ $2,435.00
  5. CB-Leg 2 (SOL Upside Sell — af8d6809-13cc-4270-aaf1-ed293aedd88e):    SELL 0.28494619 SOL @ $97.80   <-> BUY @ $93.50
  6. CB-Leg 3 (BTC Upside Sell — 245c48b9-9ff8-403c-89ae-a999ad3868a0):    SELL 0.00087620 BTC @ $81,800  <-> BUY @ $78,800
  7. CB-Leg 4 (LINK Upside Sell — 21abdc51-4595-4432-948e-6885eb412b77):   SELL 2.37 LINK @ $11.85       <-> BUY @ $11.05
  8. CB-Leg 5 (ETH Dip Catcher — 6f967d19-e0f9-4c03-ab8e-7cb6c21d6b5b):    BUY 0.02328000 ETH @ $2,350.00 <-> SELL @ $2,435.00
  9. CB-Leg 6 (SOL Dip Catcher — 76e7ed73-8732-4cc2-b35b-4accb2bd62bb):    BUY 0.30250000 SOL @ $93.40    <-> SELL @ $97.80
"""

from datetime import datetime, timezone
import json
import os
import time
import urllib.request
import uuid
from coinbase_helper import cb_request
from speak import speak_text
from live_tracker import get_snapshot, kraken_post, load_env

KRAKEN_MAKER_FEE = 0.004
CB_MAKER_FEE = 0.005
HISTORY_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "trade_history.json")


def log_trade_event(event: dict) -> None:
    try:
        history = []
        if os.path.exists(HISTORY_PATH):
            with open(HISTORY_PATH, "r", encoding="utf-8") as f:
                history = json.load(f)
        event["timestamp_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        history.append(event)
        with open(HISTORY_PATH, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2)
    except Exception as e:
        print("Trade history log error:", e, flush=True)


def send_discord_alert(webhook_url: str, title: str, description: str, color: int = 0x10B981) -> None:
    try:
        speak_text(title.replace("🎯", "").replace("💰", "").replace("🔵", ""))
    except Exception:
        pass
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
            headers={"Content-Type": "application/json", "User-Agent": "SwoozAutoFlip/5.0"},
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

    # Kraken Pro 4 Bidirectional Reverse-Grid + Breakout Legs (Plays BOTH sides of the live $2,216-$2,284 range + $2,385 breakout!)
    k_legs = [
        {
            "name": "Kraken Leg 2 (Local Range Short/Reload)",
            "txid": "OUUDZ7-CBKWI-EQDF5F",
            "pair": "XETHZUSD",
            "state": "SELL",
            "vol": 0.05085957,
            "buy_px": 2216.00,
            "sell_px": 2262.00,
            "decimals": 8,
        },
        {
            "name": "Kraken Leg 1A (Channel Top Short/Reload)",
            "txid": "OL4VXF-ZQFX3-Y4ZWSA",
            "pair": "XETHZUSD",
            "state": "SELL",
            "vol": 0.16337609,
            "buy_px": 2234.00,
            "sell_px": 2284.00,
            "decimals": 8,
        },
        {
            "name": "Kraken Leg 1B (Mid-Breakout Rally Wall)",
            "txid": "OUZWVK-5LAOQ-JK2OHZ",
            "pair": "XETHZUSD",
            "state": "SELL",
            "vol": 0.16337610,
            "buy_px": 2330.00,
            "sell_px": 2385.00,
            "decimals": 8,
        },
        {
            "name": "Kraken Leg 3 (Local SOL Range Scalper)",
            "txid": "OFFIKV-FPECK-TBSP3W",
            "pair": "SOLUSD",
            "state": "SELL",
            "vol": 0.13324100,
            "buy_px": 88.90,
            "sell_px": 91.80,
            "decimals": 6,
        },
    ]

    # Coinbase Advanced 5 Bidirectional Reverse-Grid + Breakout Legs (Total = 9 Active Legs!)
    cb_legs = [
        {
            "name": "CB Leg 4 (ETH Upper Breakout Wall)",
            "order_id": "cc4b1d80-4b1c-427b-be6e-8a91424d65ce",
            "product_id": "ETH-USDC",
            "state": "SELL",
            "buy_px": 2388.00,
            "sell_px": 2448.00,
            "decimals": 6,
        },
        {
            "name": "CB Leg 9 (Local SOL Range Scalper)",
            "order_id": "a3ca66c6-22a4-48f9-ac17-93fe26e85641",
            "product_id": "SOL-USDC",
            "state": "SELL",
            "buy_px": 89.20,
            "sell_px": 92.40,
            "decimals": 6,
        },
        {
            "name": "CB Leg 5 (SOL Breakout Runner)",
            "order_id": "a272dcf4-9e7e-4e4b-819c-1101ca4cc0ad",
            "product_id": "SOL-USDC",
            "state": "SELL",
            "buy_px": 95.20,
            "sell_px": 99.40,
            "decimals": 6,
        },
        {
            "name": "CB Leg 6 (BTC Upside Wall)",
            "order_id": "245c48b9-9ff8-403c-89ae-a999ad3868a0",
            "product_id": "BTC-USDC",
            "state": "SELL",
            "buy_px": 79200.00,
            "sell_px": 81800.00,
            "decimals": 7,
        },
        {
            "name": "CB Leg 7 (LINK Upside Wall)",
            "order_id": "21abdc51-4595-4432-948e-6885eb412b77",
            "product_id": "LINK-USDC",
            "state": "SELL",
            "buy_px": 11.20,
            "sell_px": 11.85,
            "decimals": 2,
        },
    ]

    print(
        "[9-Leg Aggressive Auto-Compounding Recovery Bot v6 Live] Watching 4 Kraken Pro + 5 Coinbase Advanced Orders!",
        flush=True,
    )

    while True:
        try:
            env = load_env()
            oo = kraken_post("/0/private/OpenOrders", env_vars=env).get("result", {}).get("open", {})
            co = kraken_post("/0/private/ClosedOrders", env_vars=env).get("result", {}).get("closed", {})

            for kleg in k_legs:
                txid = kleg["txid"]
                if not txid or txid in oo:
                    continue
                c_info = co.get(txid, {})
                if c_info.get("status") != "closed":
                    continue
                exec_vol = float(c_info.get("vol_exec", 0.0) or kleg["vol"])
                cost_usd = float(c_info.get("cost", 0.0) or 0.0)
                fee_usd = float(c_info.get("fee", 0.0) or 0.0)
                dec = kleg["decimals"]

                if kleg["state"] == "BUY" and exec_vol > 0:
                    # Flip to SELL at sell_px
                    sell_vol = round(exec_vol, dec)
                    res = kraken_post(
                        "/0/private/AddOrder",
                        {
                            "pair": kleg["pair"],
                            "type": "sell",
                            "ordertype": "limit",
                            "price": f"{kleg['sell_px']:.2f}",
                            "volume": f"{sell_vol:.{dec}f}",
                            "oflags": "post,fciq",
                        },
                        env_vars=env,
                    )
                    if not res.get("error"):
                        new_txid = (res.get("result", {}).get("txid") or ["PLACED"])[0]
                        log_trade_event({
                            "exchange": "Kraken Pro",
                            "leg": kleg["name"],
                            "filled_order_id": txid,
                            "filled_side": "BUY",
                            "pair": kleg["pair"],
                            "filled_size": exec_vol,
                            "filled_price_usd": kleg["buy_px"],
                            "gross_usd": cost_usd,
                            "fee_usd": fee_usd,
                            "flipped_order_id": new_txid,
                            "flipped_side": "SELL",
                            "flipped_size": sell_vol,
                            "flipped_price_usd": kleg["sell_px"],
                        })
                        kleg["txid"] = new_txid
                        kleg["state"] = "SELL"
                        kleg["vol"] = sell_vol
                        send_discord_alert(
                            webhook,
                            f"🎯 {kleg['name']} Dip Buy FILLED @ ${kleg['buy_px']:.2f}! Auto-Set Sell @ ${kleg['sell_px']:.2f}",
                            f"Placed `{new_txid}` to SELL `{sell_vol:.{dec}f}` @ `${kleg['sell_px']:.2f}`!",
                        )
                        get_snapshot()

                elif kleg["state"] == "SELL" and cost_usd > 5.0:
                    # Flip to BUY at buy_px using net USD proceeds
                    net_usd = cost_usd - fee_usd
                    buy_vol = round((net_usd / (1.0 + KRAKEN_MAKER_FEE)) / kleg["buy_px"], dec)
                    res = kraken_post(
                        "/0/private/AddOrder",
                        {
                            "pair": kleg["pair"],
                            "type": "buy",
                            "ordertype": "limit",
                            "price": f"{kleg['buy_px']:.2f}",
                            "volume": f"{buy_vol:.{dec}f}",
                            "oflags": "post,fciq",
                        },
                        env_vars=env,
                    )
                    if not res.get("error"):
                        new_txid = (res.get("result", {}).get("txid") or ["PLACED"])[0]
                        log_trade_event({
                            "exchange": "Kraken Pro",
                            "leg": kleg["name"],
                            "filled_order_id": txid,
                            "filled_side": "SELL",
                            "pair": kleg["pair"],
                            "filled_size": exec_vol,
                            "filled_price_usd": kleg["sell_px"],
                            "gross_usd": cost_usd,
                            "fee_usd": fee_usd,
                            "flipped_order_id": new_txid,
                            "flipped_side": "BUY",
                            "flipped_size": buy_vol,
                            "flipped_price_usd": kleg["buy_px"],
                        })
                        kleg["txid"] = new_txid
                        kleg["state"] = "BUY"
                        kleg["vol"] = buy_vol
                        send_discord_alert(
                            webhook,
                            f"💰 {kleg['name']} Top Sell FILLED @ ${kleg['sell_px']:.2f}! Auto-Set Buy @ ${kleg['buy_px']:.2f}",
                            f"Placed `{new_txid}` to BUY `{buy_vol:.{dec}f}` @ `${kleg['buy_px']:.2f}`!",
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
                    fee_val = float(o_info.get("total_fees", 0.0) or 0.0)
                    dec = leg["decimals"]
                    if leg["state"] == "SELL" and filled_val > 5.0:
                        net_usdc = (filled_val - fee_val) / (1.0 + CB_MAKER_FEE)

                        new_sz = round(net_usdc / leg["buy_px"], dec)
                        new_oid = place_cb_post_only(
                            leg["product_id"], "BUY", f"{new_sz:.{dec}f}", f"{leg['buy_px']:.2f}"
                        )
                        if new_oid:
                            log_trade_event({
                                "exchange": "Coinbase Advanced",
                                "leg": leg["name"],
                                "filled_order_id": oid,
                                "filled_side": "SELL",
                                "pair": leg["product_id"],
                                "filled_size": filled_sz,
                                "filled_price_usd": leg["sell_px"],
                                "gross_usd": filled_val,
                                "fee_usd": fee_val,
                                "flipped_order_id": new_oid,
                                "flipped_side": "BUY",
                                "flipped_size": new_sz,
                                "flipped_price_usd": leg["buy_px"],
                            })
                            leg["order_id"] = new_oid
                            leg["state"] = "BUY"
                            send_discord_alert(
                                webhook,
                                f"🔵 {leg['name']} Top Sell FILLED! Auto-Set Dip Buy @ ${leg['buy_px']:.2f}",
                                f"Placed Coinbase Post-Only BUY `{new_oid[:8]}` for `{new_sz}` `{leg['product_id']}` @ `${leg['buy_px']:.2f}`!",
                            )
                            get_snapshot()
                    elif leg["state"] == "BUY" and filled_sz > 0:
                        new_sz = round(filled_sz, dec)
                        new_oid = place_cb_post_only(
                            leg["product_id"], "SELL", f"{new_sz:.{dec}f}", f"{leg['sell_px']:.2f}"
                        )
                        if new_oid:
                            log_trade_event({
                                "exchange": "Coinbase Advanced",
                                "leg": leg["name"],
                                "filled_order_id": oid,
                                "filled_side": "BUY",
                                "pair": leg["product_id"],
                                "filled_size": filled_sz,
                                "filled_price_usd": leg["buy_px"],
                                "gross_usd": filled_val,
                                "fee_usd": fee_val,
                                "flipped_order_id": new_oid,
                                "flipped_side": "SELL",
                                "flipped_size": new_sz,
                                "flipped_price_usd": leg["sell_px"],
                            })
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
