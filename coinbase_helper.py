"""Coinbase Advanced Trade v3 (Ed25519 JWT) Telemetry & Automated Trading Helper."""

import base64
import json
import os
import secrets
import time
import urllib.request
import jwt
from cryptography.hazmat.primitives.asymmetric import ed25519

CB_KEY_PATH = os.path.expanduser("~/.coinbase_cdp_key.json")


def cb_request(method: str, path: str, query: str = "", body: dict | None = None) -> dict:
    if not os.path.exists(CB_KEY_PATH):
        return {}
    with open(CB_KEY_PATH, "r", encoding="utf-8") as f:
        d = json.load(f)
    key_id = d["id"]
    raw_priv = base64.b64decode(d["privateKey"])
    priv_key = ed25519.Ed25519PrivateKey.from_private_bytes(raw_priv[:32])

    now = int(time.time())
    uri = f"{method.upper()} api.coinbase.com{path}"
    token = jwt.encode(
        {"sub": key_id, "iss": "cdp", "nbf": now, "exp": now + 120, "uri": uri},
        priv_key,
        algorithm="EdDSA",
        headers={"kid": key_id, "nonce": secrets.token_hex()},
    )
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(
        f"https://api.coinbase.com{path}{query}",
        data=data,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "SwoozDEX/1.0",
        },
        method=method.upper(),
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            return {"error": e.code, "detail": json.loads(e.read().decode("utf-8"))}
        except Exception:
            return {"error": e.code}
    except Exception as e:
        return {"error": str(e)}


def fetch_coinbase_telemetry() -> dict:
    if not os.path.exists(CB_KEY_PATH):
        return {"connected": False, "total_usd": 0.0, "assets": [], "open_orders": []}

    accts = cb_request("GET", "/api/v3/brokerage/accounts", "?limit=250").get("accounts", [])
    orders_res = cb_request("GET", "/api/v3/brokerage/orders/historical/batch", "?order_status=OPEN")
    open_orders = orders_res.get("orders", [])

    assets = []
    total_usd = 0.0
    eth_balance = 0.0
    usdc_balance = 0.0
    sol_balance = 0.0

    for a in accts:
        avail = float(a.get("available_balance", {}).get("value", 0.0) or 0.0)
        hold = float(a.get("hold", {}).get("value", 0.0) or 0.0)
        qty = avail + hold
        if qty <= 0.00005:
            continue
        cur = a.get("currency", "")
        if cur in ("USD", "USDC"):
            px = 1.0
        else:
            prod = cb_request("GET", f"/api/v3/brokerage/products/{cur}-USD")
            px = float(prod.get("price", 0.0) or 0.0)
        usd_val = qty * px
        if usd_val >= 0.01:
            total_usd += usd_val
            if cur == "ETH":
                eth_balance += qty
            elif cur in ("USDC", "USD"):
                usdc_balance += qty
            elif cur == "SOL":
                sol_balance += qty
            assets.append({
                "currency": cur,
                "available": round(avail, 8),
                "hold": round(hold, 8),
                "total": round(qty, 8),
                "price_usd": round(px, 4),
                "value_usd": round(usd_val, 2),
            })

    assets.sort(key=lambda x: x["value_usd"], reverse=True)
    return {
        "connected": True,
        "total_usd": round(total_usd, 2),
        "eth_balance": round(eth_balance, 8),
        "usdc_balance": round(usdc_balance, 2),
        "sol_balance": round(sol_balance, 6),
        "assets": assets,
        "open_orders": [
            {
                "order_id": o.get("order_id"),
                "product_id": o.get("product_id"),
                "side": o.get("side"),
                "status": o.get("status"),
                "configuration": o.get("order_configuration"),
            }
            for o in open_orders
        ],
    }


if __name__ == "__main__":
    print(json.dumps(fetch_coinbase_telemetry(), indent=2))
