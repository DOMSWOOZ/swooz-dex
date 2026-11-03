"""Live Mobile DEX PWA Server for swooz.eth (Galaxy Z Fold 8 & S26 Ultra).

Serves the installable PWA on 0.0.0.0:8088 and exposes:
- GET /api/snapshot (cached 20s live Kraken + Ethereum Mainnet + CoinGecko + Blockscout snapshot)
- POST /api/push-discord (pushes an instant live report to #invisible on Discord)
"""

import json
import os
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import live_tracker

PWA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pwa")
CACHE_TTL = 20
_cached_snap: dict | None = None
_cached_ts: float = 0.0


def get_cached_snapshot() -> dict:
    global _cached_snap, _cached_ts
    now = time.time()
    if _cached_snap is None or (now - _cached_ts) > CACHE_TTL:
        _cached_snap = live_tracker.get_snapshot()
        _cached_ts = now
    return _cached_snap


class DexHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, format: str, *args) -> None:
        pass

    def _send(self, code: int, body: bytes, content_type: str, head_only: bool = False) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.end_headers()
        if not head_only:
            self.wfile.write(body)

    def do_HEAD(self) -> None:
        self._handle_get(head_only=True)

    def do_GET(self) -> None:
        self._handle_get(head_only=False)

    def _handle_get(self, head_only: bool = False) -> None:
        path = self.path.split("?")[0]
        if path == "/api/snapshot":
            snap = get_cached_snapshot()
            self._send(200, json.dumps(snap).encode("utf-8"), "application/json; charset=utf-8", head_only)
            return

        file_map = {
            "/": ("index.html", "text/html; charset=utf-8"),
            "/index.html": ("index.html", "text/html; charset=utf-8"),
            "/manifest.json": ("manifest.json", "application/manifest+json; charset=utf-8"),
            "/sw.js": ("sw.js", "application/javascript; charset=utf-8"),
            "/icon.svg": ("icon.svg", "image/svg+xml; charset=utf-8"),
            "/logo.png": ("logo.png", "image/png"),
            "/icon-192.png": ("icon-192.png", "image/png"),
            "/icon-512.png": ("icon-512.png", "image/png"),
        }
        if path in file_map:
            fname, ctype = file_map[path]
            fpath = os.path.join(PWA_DIR, fname)
            if os.path.exists(fpath):
                with open(fpath, "rb") as f:
                    self._send(200, f.read(), ctype, head_only)
                return

        self._send(404, b"Not Found", "text/plain; charset=utf-8", head_only)

    def do_POST(self) -> None:
        if self.path.startswith("/api/push-discord"):
            snap = live_tracker.get_snapshot()
            status = live_tracker.send_discord_webhook(snap)
            self._send(200, json.dumps({"status": status}).encode("utf-8"), "application/json")
            return
        self._send(404, b"Not Found", "text/plain; charset=utf-8")


if __name__ == "__main__":
    server = ThreadingHTTPServer(("0.0.0.0", 8088), DexHandler)
    print("SWOOZ DEX Mobile PWA Server listening on http://0.0.0.0:8088 (LAN: http://192.168.1.166:8088)", flush=True)
    server.serve_forever()
