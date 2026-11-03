# 🛸 SWOOZ.ETH Mobile DEX & NFT Telemetry Terminal (`v4.0`)

<p align="center">
  <img src="logo.png" alt="SWOOZ.ETH 3D Logo" width="420" />
</p>

<p align="center">
  <a href="https://domswooz.github.io/swooz-dex/"><strong>🚀 OPEN LIVE DASHBOARD: https://domswooz.github.io/swooz-dex/</strong></a>
</p>

---

## ⚡ Quick Links

| Destination | Direct Link |
| :--- | :--- |
| **🌐 Live 24/7 Mobile DEX App (GitHub Pages)** | **[https://domswooz.github.io/swooz-dex/](https://domswooz.github.io/swooz-dex/)** |
| **📦 GitHub Repository** | **[https://github.com/DOMSWOOZ/swooz-dex](https://github.com/DOMSWOOZ/swooz-dex)** |
| **🏠 Local LAN DEX Server (`dex_server.py`)** | `http://localhost:8088` |

---

## 📱 Tailored for Samsung Galaxy Z Fold 8 & Galaxy S26 Ultra

**`SWOOZ.ETH DEX`** is a full-screen Progressive Web App (PWA) and real-time Ethereum Mainnet + Kraken portfolio terminal built specifically for **`swooz.eth`** (`0x6ddAc958d8A54f63B6BD86FB71693fBB493331b4`):

- **📖 Samsung Galaxy Z Fold 8 (Unfolded Inner Display `≥ 720px`)**: Automatically switches into a **Dual-Pane Split View** — keeping your **Kraken Unlock Countdown, Held ETH Gain/Loss (P&L) Tracker, Multi-Wallet Manager, and Bid Allocation Simulator** pinned on the left pane while your **5 Target Snipes (`#1506`, `#1286`, `#140`, `#42`, `BEAST #2313`) and 5 Collection Market Cards** scroll independently on the right pane.
- **📱 Samsung Galaxy S26 Ultra & Fold 8 Cover Screen**: Ergonomic single-thumb portrait terminal with a **5-button glassmorphic Bottom Dock** (`💰 ETH P&L`, `🎯 Targets`, `📊 Markets`, `⚡ Bid Calc`, `📲 Install`) that launches the install guide as a clean pop-up modal instead of cluttering the main dashboard.
- **🎨 Custom 3D `SWOOZ.ETH` Squircle App Icon**: Packaged with custom `192x192` and `512x512` dark-mode icons engineered for Samsung One UI home screens.

---

## 💰 Held ETH Gain / Loss (P&L) Across Wallets & Accounts

The **Held ETH Gain / Loss (P&L)** section tracks both your **Fiat USD P&L** and your **Real NFT Purchasing Power P&L** across every connected account and wallet:

1. **Kraken Main (`Read-Only API`)**:
   - **Held ETH**: `0.37532712 ETH` (includes `+0.00002080 ETH` Auto-Earn staking reward)
   - **Cost Basis**: `$900.00 USD` (`$2,398.04 / ETH` entry on Oct 28, 2026)
   - **Break-Even ETH Price**: `$2,397.91 USD`
   - **Exact 7-Day Plaid ACH Hold Unlock**: **Wednesday, November 4, 2026 at `22:09:09 UTC` (`2:09:09 PM PST`)**
2. **`swooz.eth` Primary On-Chain Wallet (`0x6ddA...31b4`)**:
   - Live Ethereum Mainnet `ETH` + `WETH` balances via direct JSON-RPC (`eth_getBalance` & `balanceOf`)
   - Holds **`132 / 6,969` Mini Supers (`#2 Whale Worldwide`)**
3. **Interactive `+ Add Wallet / Account` Manager**:
   - Add any additional `0x...` wallet (such as your 2nd Mini Supers wallet) or exchange account with optional ETH amount and USD cost basis.
   - Automatically queries Ethereum Mainnet RPC for live `ETH`, `WETH`, and `Mini Supers` balances, merges into your **Total Held ETH & Net USD P&L**, and persists locally on your device.
4. **NFT Purchasing Power Alpha**:
   - Tracks how much cheaper your target NFTs (`Invisible Friends Floor + CloneX Floor`) have become in USD and ETH terms compared to Oct 28 (`0.4750 ETH` / `$1,192.89 USD` then vs. `0.3608 ETH` / `$824.09 USD` now — a **`+31.6%` (`+$368.80 USD`) net purchasing power gain**).

---

## 🎯 Tracked Collections & Specific Target Tokens

| Collection | Contract (`ERC-721`) | Tracked Target Tokens & Holdings |
| :--- | :--- | :--- |
| **Invisible Friends (OG)** | `0x59468516a8259058baD1cA5F8f4BFF190d30E066` | **Primary `#1506`** (Rank #1,621) • **Backups `#1286`, `#140`, `#42`** |
| **CloneX (`RTFKT x Murakami`)** | `0x49cF6f5d44E70224e2E23fDcdd2C053F30aDA28B` | Collection Floor, Top Trait/Collection Bids, 24h Volume & High Sales |
| **a KID called BEAST (`AKCB`)** | `0x77372a4cc66063575b05b44481f059be356964a4` | **Target `BEAST #2313`** (`Beat Street` • `Black Raccoon Balaclava` • `Orange Puffer`) |
| **Mini Supers (`Home Team`)** | `0xe935E764DA0F1a2597F9C1bF13a64515BfF9F7D7` | **`132 Held` by `swooz.eth` (`#2 Holder Worldwide`)** |
| **Invisible Friends: *"The Walk"*** | `0x0905b2277Df5c7dD6C5e3399Ece8a36621aebE85` | Token `#1` (`16,969` locked supply) |

---

## 🛠️ Local Telemetry & Discord Webhook Setup

To run the local Kraken Read-Only API sync and twice-daily Discord webhook reporter:

1. Create `~/.env` (`C:\Users\<user>\.env`) with your read-only keys:
   ```env
   KRAKEN_API_KEY=your_kraken_read_only_key
   KRAKEN_API_SECRET=your_kraken_read_only_secret
   DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
   ```
2. Run a one-shot telemetry sync & Discord report:
   ```bash
   python live_tracker.py
   ```
3. Start the local mobile DEX API server on port `8088`:
   ```bash
   python dex_server.py
   ```
