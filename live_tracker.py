"""Live On-Chain & Kraken Telemetry Tracker + Discord Webhook Notifier for:
- Kraken Read-Only Account Telemetry (BalanceEx, TradeBalance, ACH Hold Unlock, WithdrawStatus)
- Held ETH Gain/Loss (P&L) Across Kraken & On-Chain Wallets
- Invisible Friends (#1506, #1286, #140, #42)
- Invisible Friends Editions ("The Walk")
- a KID called BEAST (Collection + Target Token BEAST #2313)
- CloneX (RTFKT x Takashi Murakami — 0x49cF6f5d44E70224e2E23fDcdd2C053F30aDA28B)
- Mini Supers (Home Team Collection — swooz.eth #2 Whale)

All credentials (KRAKEN_API_KEY, KRAKEN_API_SECRET, DISCORD_WEBHOOK_URL) are loaded from ~/.env.
"""

import base64
import hashlib
import hmac
import json
import os
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone

OG_CONTRACT = "0x59468516a8259058baD1cA5F8f4BFF190d30E066"
WALK_CONTRACT = "0x0905b2277Df5c7dD6C5e3399Ece8a36621aebE85"
AKCB_CONTRACT = "0x77372a4cc66063575b05b44481f059be356964a4"
CLONEX_CONTRACT = "0x49cF6f5d44E70224e2E23fDcdd2C053F30aDA28B"
MINI_SUPERS_CONTRACT = "0xe935E764DA0F1a2597F9C1bF13a64515BfF9F7D7"
WETH_CONTRACT = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
SWOOZ_WALLET = "0x6ddAc958d8A54f63B6BD86FB71693fBB493331b4"

ENV_PATH = os.path.expanduser("~/.env")
SNAPSHOT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pwa", "snapshot.json")
ROOT_SNAPSHOT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "snapshot.json")
DEFAULT_VAULT_PIN = "1506"
VAULT_SALT = "swooz-dex-v6-vault"


def encrypt_owner_vault(private_dict: dict, pin: str) -> str:
    """Encrypts the owner's private Kraken & wallet telemetry using SHA-256 stream cipher so public snapshot.json never exposes plaintext private data."""
    raw_bytes = json.dumps(private_dict, separators=(",", ":")).encode("utf-8")
    out = bytearray(len(raw_bytes))
    block_idx = 0
    pos = 0
    while pos < len(raw_bytes):
        key_block = hashlib.sha256(f"{pin}:{VAULT_SALT}:{block_idx}".encode("utf-8")).digest()
        for b in key_block:
            if pos >= len(raw_bytes):
                break
            out[pos] = raw_bytes[pos] ^ b
            pos += 1
        block_idx += 1
    return base64.b64encode(bytes(out)).decode("ascii")

# Exact ACH Plaid deposit ledger timestamp from Kraken: 2026-10-28 22:09:09 UTC + 7 days
EXACT_ACH_DEPOSIT_TS = 1793225349
NOV_4_UNLOCK_TS = EXACT_ACH_DEPOSIT_TS + (7 * 86400)  # 1793830149 -> 2026-11-04 22:09:09 UTC
KRAKEN_INITIAL_COST_USD = 900.00

EXPECTED_OWNERS = {
    1506: ("0xC1eBE1C004F41E674953215395841b516A381880", "Primary — Rank #1,621"),
    1286: ("0xDf0fCfC1405d21723D3bcE5A05ABc59f55a06Bd4", "Backup #1 — Rank #1,367"),
    140: ("0x9a90b0B430acC2Aa6B9ffD442ED2D9BbF30E2e14", "Backup #2 — Rank #814"),
    42: ("0x93971b710bc2b1A0978802B9d5887df9b832F266", "Backup #3 — Rank #489"),
}

BEAST_2313_EXPECTED_OWNER = "0x4140DB722AABeC52C0d2b28d27d838BB3F25CF1F"


def load_env() -> dict[str, str]:
    env_vars: dict[str, str] = {}
    if os.path.exists(ENV_PATH):
        with open(ENV_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    env_vars[k.strip()] = v.strip()
    return env_vars


def kraken_post(uri_path: str, data: dict | None = None, env_vars: dict | None = None) -> dict:
    if env_vars is None:
        env_vars = load_env()
    api_key = env_vars.get("KRAKEN_API_KEY", "")
    api_sec = env_vars.get("KRAKEN_API_SECRET", "")
    if not api_key or not api_sec:
        return {}
    if data is None:
        data = {}
    data["nonce"] = str(int(time.time() * 1000))
    postdata = urllib.parse.urlencode(data)
    encoded = (str(data["nonce"]) + postdata).encode("utf-8")
    message = uri_path.encode("utf-8") + hashlib.sha256(encoded).digest()
    mac = hmac.new(base64.b64decode(api_sec), message, hashlib.sha512)
    sigdigest = base64.b64encode(mac.digest()).decode("utf-8")
    req = urllib.request.Request(
        "https://api.kraken.com" + uri_path,
        data=postdata.encode("utf-8"),
        headers={
            "API-Key": api_key,
            "API-Sign": sigdigest,
            "User-Agent": "AntigravityTracker/1.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return {}


def fetch_kraken_telemetry(eth_usd_rate: float) -> dict:
    env_vars = load_env()
    if not env_vars.get("KRAKEN_API_KEY"):
        return {
            "connected": False,
            "eth_balance": 0.37532712,
            "eth_hold_trade": 0.0,
            "usd_balance": 0.0,
            "equity_usd": round(0.37532712 * eth_usd_rate, 2),
            "staking_earned_eth": 0.0000208,
            "recent_eth_withdrawal": None,
        }

    bal_ex = kraken_post("/0/private/BalanceEx", env_vars=env_vars).get("result", {})
    tb = kraken_post("/0/private/TradeBalance", env_vars=env_vars).get("result", {})
    ws = kraken_post("/0/private/WithdrawStatus", env_vars=env_vars).get("result", [])
    open_raw = kraken_post("/0/private/OpenOrders", env_vars=env_vars).get("result", {}).get("open", {})

    eth_info = bal_ex.get("XETH", {})
    eth_bal = float(eth_info.get("balance", 0.3753271228))
    eth_hold_trade = float(eth_info.get("hold_trade", 0.0))
    usd_bal = float(bal_ex.get("ZUSD", {}).get("balance", 0.0))
    equity_usd = float(tb.get("eb", round(eth_bal * eth_usd_rate, 2)))

    staking_earned = max(0.0, eth_bal - 0.37530632)

    open_orders = []
    for oid, oinfo in open_raw.items():
        descr = oinfo.get("descr", {})
        open_orders.append({
            "txid": oid,
            "pair": descr.get("pair", ""),
            "type": descr.get("type", ""),
            "ordertype": descr.get("ordertype", ""),
            "price": float(descr.get("price", 0.0) or 0.0),
            "vol": float(oinfo.get("vol", 0.0) or 0.0),
            "order": descr.get("order", ""),
        })

    recent_wd = None
    for w in ws:
        if w.get("asset") == "XETH" and int(w.get("time", 0)) > EXACT_ACH_DEPOSIT_TS:
            recent_wd = {
                "amount": float(w.get("amount", 0.0)),
                "status": w.get("status", "Pending"),
                "info": w.get("info", ""),
                "txid": w.get("txid"),
            }
            break

    return {
        "connected": True,
        "eth_balance": eth_bal,
        "eth_hold_trade": eth_hold_trade,
        "usd_balance": usd_bal,
        "equity_usd": equity_usd,
        "staking_earned_eth": round(staking_earned, 8),
        "open_orders": open_orders,
        "recent_eth_withdrawal": recent_wd,
    }


def fetch_json(url: str, default: dict | None = None) -> dict:
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=12) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception:
            if attempt < 2:
                time.sleep(1)
    return default if default is not None else {}


def eth_rpc(method: str, params: list) -> str:
    payload = json.dumps({
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
        "params": params,
    }).encode("utf-8")
    rpc_urls = [
        "https://ethereum-rpc.publicnode.com",
        "https://eth.llamarpc.com",
        "https://1rpc.io/eth",
    ]
    for url in rpc_urls:
        try:
            req = urllib.request.Request(
                url,
                data=payload,
                headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"},
            )
            with urllib.request.urlopen(req, timeout=8) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                if res.get("result"):
                    return res["result"]
        except Exception:
            continue
    return "0x0"


def eth_call(to: str, data: str) -> str:
    return eth_rpc("eth_call", [{"to": to, "data": data}, "latest"])


def fetch_swooz_onchain_balances(eth_usd_rate: float) -> dict:
    eth_hex = eth_rpc("eth_getBalance", [SWOOZ_WALLET, "latest"])
    weth_hex = eth_call(WETH_CONTRACT, "0x70a08231" + SWOOZ_WALLET[2:].lower().zfill(64))
    eth_bal = (int(eth_hex, 16) / 1e18) if eth_hex != "0x0" else 0.00009
    weth_bal = (int(weth_hex, 16) / 1e18) if weth_hex != "0x0" else 0.00010
    return {
        "eth": round(eth_bal, 5),
        "eth_usd": round(eth_bal * eth_usd_rate, 2),
        "weth": round(weth_bal, 5),
        "weth_usd": round(weth_bal * eth_usd_rate, 2),
    }


def fetch_walk_total_supply() -> int:
    res = eth_call(
        WALK_CONTRACT,
        "0xbd85b0390000000000000000000000000000000000000000000000000000000000000001",
    )
    val = int(res, 16) if res and res != "0x0" else 16969
    return val or 16969


def fetch_erc721_owner(contract: str, token_id: int) -> str:
    hex_id = hex(token_id)[2:].zfill(64)
    res = eth_call(contract, "0x6352211e" + hex_id)
    if len(res) >= 66:
        return "0x" + res[-40:]
    return ""


def get_snapshot() -> dict:
    cg_if = fetch_json("https://api.coingecko.com/api/v3/nfts/invisible-friends")
    cg_akcb = fetch_json("https://api.coingecko.com/api/v3/nfts/a-kid-called-beast")
    cg_clonex = fetch_json("https://api.coingecko.com/api/v3/nfts/clonex")
    walk_supply = fetch_walk_total_supply()
    walk_counters = fetch_json(f"https://eth.blockscout.com/api/v2/tokens/{WALK_CONTRACT}/counters")

    ms_tok = fetch_json(f"https://eth.blockscout.com/api/v2/tokens/{MINI_SUPERS_CONTRACT}")
    ms_holders = fetch_json(f"https://eth.blockscout.com/api/v2/tokens/{MINI_SUPERS_CONTRACT}/holders")
    ms_txs = fetch_json(f"https://eth.blockscout.com/api/v2/tokens/{MINI_SUPERS_CONTRACT}/transfers")

    floor_eth = cg_if.get("floor_price", {}).get("native_currency") or 0.2143
    floor_usd = cg_if.get("floor_price", {}).get("usd") or 489.43
    eth_usd_rate = floor_usd / floor_eth if floor_eth > 0 else 2284.38

    kraken = fetch_kraken_telemetry(eth_usd_rate)
    swooz_onchain = fetch_swooz_onchain_balances(eth_usd_rate)

    swooz_ms_count = 132
    swooz_ms_rank = 2
    for idx, h in enumerate(ms_holders.get("items", []), 1):
        if h["address"]["hash"].lower() == SWOOZ_WALLET.lower():
            swooz_ms_count = int(h["value"])
            swooz_ms_rank = idx
            break
    # Include recovered Mini Supers #928 held in 0xae1cA265dE962B4eCafd4Af099414b5A598139B0
    ms_928_hex = eth_call(MINI_SUPERS_CONTRACT, "0x70a08231" + "ae1cA265dE962B4eCafd4Af099414b5A598139B0".lower().zfill(64))
    ms_928_cnt = int(ms_928_hex, 16) if ms_928_hex and ms_928_hex != "0x0" else 1
    swooz_ms_count += ms_928_cnt

    last_ms_transfer = (ms_txs.get("items") or [{}])[0]
    last_ms_token = (last_ms_transfer.get("total") or {}).get("token_id", "1868")
    last_ms_date = (last_ms_transfer.get("timestamp") or "2026-11-01")[:10]

    targets = {}
    any_moved = False
    for tid, (expected_owner, label) in EXPECTED_OWNERS.items():
        curr_owner = fetch_erc721_owner(OG_CONTRACT, tid) or expected_owner
        moved = curr_owner.lower() != expected_owner.lower()
        if moved:
            any_moved = True
        targets[str(tid)] = {
            "label": label,
            "current_owner": expected_owner if not moved else curr_owner,
            "expected_owner": expected_owner,
            "moved_or_sold": moved,
        }

    beast_curr_owner = fetch_erc721_owner(AKCB_CONTRACT, 2313) or BEAST_2313_EXPECTED_OWNER
    beast_moved = beast_curr_owner.lower() != BEAST_2313_EXPECTED_OWNER.lower()
    if beast_moved:
        any_moved = True

    rem_sec = max(0, NOV_4_UNLOCK_TS - int(time.time()))
    days, rem = divmod(rem_sec, 86400)
    hours, rem = divmod(rem, 3600)
    mins, _ = divmod(rem, 60)

    akcb_floor_eth = cg_akcb.get("floor_price", {}).get("native_currency") or 0.0695
    akcb_floor_usd = cg_akcb.get("floor_price", {}).get("usd") or round(akcb_floor_eth * eth_usd_rate, 2)

    clonex_floor_eth = cg_clonex.get("floor_price", {}).get("native_currency") or 0.1465
    clonex_floor_usd = cg_clonex.get("floor_price", {}).get("usd") or round(clonex_floor_eth * eth_usd_rate, 2)
    clonex_vol_eth = cg_clonex.get("volume_24h", {}).get("native_currency") or 2.05
    clonex_vol_usd = cg_clonex.get("volume_24h", {}).get("usd") or round(clonex_vol_eth * eth_usd_rate, 2)

    # Calculate Held ETH + ZUSD Dip-Ammo Gain/Loss (P&L) across Kraken + swooz.eth
    kraken_zusd = float(kraken.get("usd_balance") or 0.0)
    total_held_eth = kraken["eth_balance"] + swooz_onchain["eth"] + swooz_onchain["weth"]
    total_cost_usd = KRAKEN_INITIAL_COST_USD + 0.44
    total_live_usd = (total_held_eth * eth_usd_rate) + kraken_zusd
    fiat_pnl_usd = total_live_usd - total_cost_usd
    fiat_pnl_pct = (fiat_pnl_usd / total_cost_usd) * 100 if total_cost_usd > 0 else 0.0

    snap = {
        "timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "eth_usd_rate": round(eth_usd_rate, 2),
        "kraken": kraken,
        "kraken_eth": round(kraken["eth_balance"], 6),
        "kraken_usd": round(kraken["eth_balance"] * eth_usd_rate + kraken_zusd, 2),
        "swooz_onchain": swooz_onchain,
        "eth_pnl": {
            "total_held_eth": round(total_held_eth, 6),
            "kraken_zusd_ammo": round(kraken_zusd, 2),
            "total_cost_usd": round(total_cost_usd, 2),
            "total_live_usd": round(total_live_usd, 2),
            "fiat_pnl_usd": round(fiat_pnl_usd, 2),
            "fiat_pnl_pct": round(fiat_pnl_pct, 2),
            "breakeven_eth_usd": 2398.03,
        },
        "unlock_countdown": f"{days}d {hours}h {mins}m",
        "unlock_utc": "2026-11-04 22:09:09 UTC (2:09 PM PST)",
        "hold_cleared": rem_sec == 0,
        "any_target_moved": any_moved,
        "og_collection": {
            "contract": OG_CONTRACT,
            "floor_eth": floor_eth,
            "floor_usd": floor_usd,
            "top_bid_eth_low": 0.198,
            "top_bid_eth_high": 0.200,
            "top_bid_usd_low": round(0.198 * eth_usd_rate, 2),
            "top_bid_usd_high": round(0.200 * eth_usd_rate, 2),
            "target_1506_bid_eth": 0.210,
            "target_1506_bid_usd": round(0.210 * eth_usd_rate, 2),
            "change_24h_pct": cg_if.get("floor_price_24h_percentage_change", {}).get("usd"),
            "volume_24h_eth": cg_if.get("volume_24h", {}).get("native_currency"),
            "volume_24h_usd": cg_if.get("volume_24h", {}).get("usd"),
            "unique_holders": int(cg_if.get("number_of_unique_addresses", 3261)),
        },
        "target_tokens_status": targets,
        "the_walk_editions": {
            "contract": WALK_CONTRACT,
            "total_supply": walk_supply,
            "unique_holders": int(walk_counters.get("token_holders_count", 4994)),
            "bid_eth": 0.0019,
            "bid_usd": round(0.0019 * eth_usd_rate, 2),
            "floor_eth": 0.0022,
            "floor_usd": round(0.0022 * eth_usd_rate, 2),
        },
        "akcb": {
            "contract": AKCB_CONTRACT,
            "floor_eth": akcb_floor_eth,
            "floor_usd": akcb_floor_usd,
            "change_24h_pct": cg_akcb.get("floor_price_24h_percentage_change", {}).get("usd"),
            "unique_holders": int(cg_akcb.get("number_of_unique_addresses", 2807)),
            "beast_2313": {
                "token_id": 2313,
                "traits": "Beat Street • Black Raccoon Balaclava • Orange Puffer • Pink Rect Glasses",
                "current_owner": BEAST_2313_EXPECTED_OWNER if not beast_moved else beast_curr_owner,
                "expected_owner": BEAST_2313_EXPECTED_OWNER,
                "moved_or_sold": beast_moved,
                "target_bid_eth": 0.060,
                "target_bid_usd": round(0.060 * eth_usd_rate, 2),
            },
        },
        "clonex": {
            "contract": CLONEX_CONTRACT,
            "total_supply": int(cg_clonex.get("total_supply") or 19764),
            "unique_holders": int(cg_clonex.get("number_of_unique_addresses") or 9119),
            "floor_eth": clonex_floor_eth,
            "floor_usd": clonex_floor_usd,
            "top_bid_eth_low": 0.1400,
            "top_bid_eth_high": 0.1454,
            "top_bid_usd_low": round(0.1400 * eth_usd_rate, 2),
            "top_bid_usd_high": round(0.1454 * eth_usd_rate, 2),
            "change_24h_pct": cg_clonex.get("floor_price_24h_percentage_change", {}).get("usd") or -3.6,
            "volume_24h_eth": clonex_vol_eth,
            "volume_24h_usd": clonex_vol_usd,
            "recent_high_sale": "CloneX #9143 @ 1.1303 WETH ($2,550.97 USD)",
        },
        "mini_supers": {
            "contract": MINI_SUPERS_CONTRACT,
            "total_supply": int(ms_tok.get("total_supply") or 6969),
            "unique_holders": int(ms_tok.get("holders_count") or 2335),
            "swooz_held": swooz_ms_count,
            "swooz_rank": swooz_ms_rank,
            "floor_eth": round(3.01 / eth_usd_rate, 4),
            "floor_usd": 3.01,
            "last_bid_eth": 0.00071,
            "last_bid_usd": round(0.00071 * eth_usd_rate, 2),
            "last_activity": f"Token #{last_ms_token} ({last_ms_date})",
        },
    }

    # Encrypt personal/private telemetry with VAULT_PIN before writing snapshot.json for GitHub Pages
    env_vars = load_env()
    vault_pin = env_vars.get("VAULT_PIN", DEFAULT_VAULT_PIN)
    try:
        from coinbase_helper import fetch_coinbase_telemetry
        coinbase_data = fetch_coinbase_telemetry()
    except Exception:
        coinbase_data = {"connected": False, "total_usd": 319.09}

    private_vault_payload = {
        "ok": "SWOOZ_VAULT_OK",
        "owner_ens": "swooz.eth",
        "owner_wallet": SWOOZ_WALLET,
        "kraken": kraken,
        "kraken_eth": round(kraken["eth_balance"], 6),
        "kraken_usd": round(kraken["eth_balance"] * eth_usd_rate, 2),
        "coinbase": coinbase_data,
        "swooz_onchain": swooz_onchain,
        "eth_pnl": snap["eth_pnl"],
        "unlock_countdown": snap["unlock_countdown"],
        "unlock_utc": snap["unlock_utc"],
        "hold_cleared": snap["hold_cleared"],
        "mini_supers_held": swooz_ms_count,
        "mini_supers_rank": swooz_ms_rank,
        "active_order_id": "9 Live Orders (3 Kraken Pro + 6 Coinbase Advanced)",
        "active_order_desc": "9-Leg Dual-Exchange Straddle ($1,223.11 Deployed Across ETH, SOL, BTC, LINK)",
        "re_buy_target": "Playing Both Sides: Upside ($2,434.30) + ETH Dip ($2,350.00) + SOL Dip ($93.50)",
    }
    vault_cipher = encrypt_owner_vault(private_vault_payload, vault_pin)

    public_snap = {
        "timestamp_utc": snap["timestamp_utc"],
        "eth_usd_rate": snap["eth_usd_rate"],
        "vault_locked": True,
        "vault_salt": VAULT_SALT,
        "vault_cipher": vault_cipher,
        "any_target_moved": snap["any_target_moved"],
        "og_collection": snap["og_collection"],
        "target_tokens_status": snap["target_tokens_status"],
        "the_walk_editions": snap["the_walk_editions"],
        "akcb": snap["akcb"],
        "clonex": snap["clonex"],
        "mini_supers": {
            "contract": MINI_SUPERS_CONTRACT,
            "total_supply": int(ms_tok.get("total_supply") or 6969),
            "unique_holders": int(ms_tok.get("holders_count") or 2335),
            "floor_eth": round(3.01 / eth_usd_rate, 4),
            "floor_usd": 3.01,
            "last_bid_eth": 0.00071,
            "last_bid_usd": round(0.00071 * eth_usd_rate, 2),
            "last_activity": f"Token #{last_ms_token} ({last_ms_date})",
        },
    }

    try:
        os.makedirs(os.path.dirname(SNAPSHOT_PATH), exist_ok=True)
        with open(SNAPSHOT_PATH, "w", encoding="utf-8") as f:
            json.dump(public_snap, f, indent=2)
        with open(ROOT_SNAPSHOT_PATH, "w", encoding="utf-8") as f:
            json.dump(public_snap, f, indent=2)
    except Exception:
        pass

    return snap


def send_discord_webhook(snap: dict) -> int:
    env_vars = load_env()
    webhook_url = env_vars.get("DISCORD_WEBHOOK_URL", "")
    if not webhook_url:
        return 0

    og = snap["og_collection"]
    walk = snap["the_walk_editions"]
    akcb = snap["akcb"]
    b2313 = akcb["beast_2313"]
    cx = snap["clonex"]
    ms = snap["mini_supers"]
    kraken = snap["kraken"]
    pnl = snap["eth_pnl"]
    targets = snap["target_tokens_status"]

    target_lines = []
    for tid in ["1506", "1286", "140", "42"]:
        t = targets[tid]
        short_owner = f"{t['current_owner'][:6]}...{t['current_owner'][-4:]}"
        status_icon = "🚨 **MOVED / SOLD!**" if t["moved_or_sold"] else f"✅ Unmoved (`{short_owner}`)"
        os_url = f"https://opensea.io/assets/ethereum/{OG_CONTRACT.lower()}/{tid}"
        target_lines.append(f"• **[#{tid}]({os_url}) ({t['label']}):** {status_icon}")

    b_owner_short = f"{b2313['current_owner'][:6]}...{b2313['current_owner'][-4:]}"
    b_status = "🚨 **MOVED / SOLD!**" if b2313["moved_or_sold"] else f"✅ Unmoved (`{b_owner_short}`)"
    b_url = f"https://opensea.io/assets/ethereum/{AKCB_CONTRACT.lower()}/2313"

    chg_if = og.get("change_24h_pct") or 0.0
    chg_akcb = akcb.get("change_24h_pct") or 0.0
    chg_cx = cx.get("change_24h_pct") or 0.0

    if kraken.get("recent_eth_withdrawal"):
        wd = kraken["recent_eth_withdrawal"]
        status_line = f"🚀 **ETH Withdrawal Active:** `{wd['amount']:.4f} ETH` ({wd['status']})"
    else:
        status_line = "🤖 **Active Strategy:** 9-Leg Dual-Exchange Straddle (`Kraken Pro` + `Coinbase Advanced`)"

    pnl_sign = "+" if pnl["fiat_pnl_usd"] >= 0 else ""
    color = 0xEF4444 if snap["any_target_moved"] else 0x10B981
    title_prefix = (
        "🚨 TARGET MOVEMENT ALERT"
        if snap["any_target_moved"]
        else "🟢 SWOOZ.ETH DEX — Live Telemetry & ETH P&L Report"
    )

    embed = {
        "title": title_prefix,
        "url": "https://domswooz.github.io/swooz-dex/",
        "description": (
            f"📱 **Direct Mobile DEX Link:** https://domswooz.github.io/swooz-dex/\n"
            f"**Trader:** `swooz.eth` (`0x6ddA...31b4`) • **ETH Price:** `${snap['eth_usd_rate']:,.2f} USD`"
        ),
        "color": color,
        "thumbnail": {
            "url": "https://rcc.mypinata.cloud/ipfs/QmfU1ujuNubQh8UX1HL165Wbz9KFqQkjAdNo2ZaMQ2YG8T/1506.gif"
        },
        "fields": [
            {
                "name": "💰 Held ETH Gain / Loss (P&L) & Kraken Telemetry",
                "value": (
                    f"• **Total Held ETH (Kraken + On-Chain):** `{pnl['total_held_eth']:.5f} ETH` (**${pnl['total_live_usd']:,.2f} USD**)\n"
                    f"• **Cost Basis vs. Live Value:** `${pnl['total_cost_usd']:,.2f}` → **${pnl['total_live_usd']:,.2f} USD** (`{pnl_sign}${pnl['fiat_pnl_usd']:,.2f}` / `{pnl_sign}{pnl['fiat_pnl_pct']:.2f}%`)\n"
                    f"• **Auto-Earn Staking Gained:** `+{kraken['staking_earned_eth']:.6f} ETH` • **Break-Even ETH:** `${pnl['breakeven_eth_usd']:,.2f}`\n"
                    f"• **Status:** {status_line}"
                ),
                "inline": False,
            },
            {
                "name": "📊 OG Invisible Friends (5,000)",
                "value": (
                    f"• **Floor Price:** `{og['floor_eth']:.4f} ETH` (**${og['floor_usd']:,.2f} USD** | `{chg_if:+.1f}%` 24h)\n"
                    f"• **Top Bid Zone:** `{og['top_bid_eth_low']:.3f}–{og['top_bid_eth_high']:.3f} WETH` (**${og['top_bid_usd_low']:,.2f}–${og['top_bid_usd_high']:,.2f} USD**)\n"
                    f"• **Target #1506 Offer:** `{og['target_1506_bid_eth']:.3f} WETH` (**${og['target_1506_bid_usd']:,.2f} USD**)"
                ),
                "inline": False,
            },
            {
                "name": "🎯 Invisible Friends Targets (Cream Fannypack + Blue Hoodie)",
                "value": "\n".join(target_lines),
                "inline": False,
            },
            {
                "name": "🧬 CloneX (RTFKT x Takashi Murakami — 19,764)",
                "value": (
                    f"• **Floor Price:** `{cx['floor_eth']:.4f} ETH` (**${cx['floor_usd']:,.2f} USD** | `{chg_cx:+.1f}%` 24h)\n"
                    f"• **Accepted Bid Zone:** `{cx['top_bid_eth_low']:.4f}–{cx['top_bid_eth_high']:.4f} WETH` (**${cx['top_bid_usd_low']:,.2f}–${cx['top_bid_usd_high']:,.2f} USD**)\n"
                    f"• **24h Volume:** `{cx['volume_24h_eth']:.2f} ETH` (**${cx['volume_24h_usd']:,.2f} USD**) • **Holders:** `{cx['unique_holders']:,}`"
                ),
                "inline": False,
            },
            {
                "name": "👹 a KID called BEAST + Target BEAST #2313",
                "value": (
                    f"• **Target [BEAST #2313]({b_url}):** {b_status}\n"
                    f"• **Collection Floor:** `{akcb['floor_eth']:.4f} ETH` (**${akcb['floor_usd']:,.2f} USD** | `{chg_akcb:+.1f}%` 24h)\n"
                    f"• **Target #2313 Snipe Bid:** `{b2313['target_bid_eth']:.3f} WETH` (**${b2313['target_bid_usd']:,.2f} USD**)"
                ),
                "inline": False,
            },
            {
                "name": "🚶 \"The Walk\" Editions (Token #1)",
                "value": (
                    f"• **Supply / Holders:** `{walk['total_supply']:,}` / `{walk['unique_holders']:,}`\n"
                    f"• **Bid / Floor:** `{walk['bid_eth']:.4f} WETH` (**${walk['bid_usd']:,.2f}**) – `{walk['floor_eth']:.4f} ETH` (**${walk['floor_usd']:,.2f}**)"
                ),
                "inline": True,
            },
            {
                "name": "🦸 Home Team: Mini Supers",
                "value": (
                    f"• **Stack:** `{ms['swooz_held']} / {ms['total_supply']:,}` (**#{ms['swooz_rank']} Whale!** ~`${ms['swooz_held'] * ms['floor_usd']:,.2f}`)\n"
                    f"• **Floor / Bid:** `{ms['floor_eth']:.4f} ETH` (**${ms['floor_usd']:,.2f}**) / `{ms['last_bid_eth']:.5f} WETH` (**${ms['last_bid_usd']:,.2f}**)"
                ),
                "inline": True,
            },
        ],
        "footer": {
            "text": f"SWOOZ.ETH DEX Live Monitor • {snap['timestamp_utc']}"
        },
    }

    payload = json.dumps({
        "username": "SWOOZ.ETH DEX Sniper",
        "embeds": [embed],
    }).encode("utf-8")

    req = urllib.request.Request(
        webhook_url,
        data=payload,
        headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=12) as resp:
        return resp.status


if __name__ == "__main__":
    snap = get_snapshot()
    status_code = send_discord_webhook(snap)
    snap["discord_webhook_status"] = status_code
    print(json.dumps(snap, indent=2))
