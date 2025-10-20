#!/usr/bin/env python3
"""
PAXECT Demo 04 – Metrics & Health Endpoints
-------------------------------------------
Lightweight developer version of the observability service.

Endpoints:
  /ping    -> 200 OK (alive)
  /ready   -> 200 OK if last run OK, else 503
  /metrics -> simple counters
  /last    -> JSON of last run
"""

from http.server import BaseHTTPRequestHandler, HTTPServer
import threading, json, random, time, tempfile
from pathlib import Path

PORT = 8081
STATE_PATH = Path(tempfile.gettempdir()) / "paxect_demo_04_last.json"
_last = {}
_lock = threading.Lock()

def run_health_cycle():
    """Simulate plugin health & write result."""
    data = {
        "timestamp": int(time.time()),
        "modules_ok": 5,
        "epsilon": 0.1,
        "mode": "exploit" if random.random() > 0.1 else "explore"
    }
    with _lock:
        _last.update(data)
    STATE_PATH.write_text(json.dumps(data))

class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json"):
        b = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        path = self.path.split("?",1)[0]
        if path == "/ping":
            self._send(200, json.dumps({"status":"pong"})); return
        if path == "/ready":
            ready = _last.get("modules_ok",0) == 5
            self._send(200 if ready else 503, json.dumps({"ready": ready})); return
        if path == "/metrics":
            metrics = [
                "# HELP paxect_demo04_ok Gauge of OK modules",
                "# TYPE paxect_demo04_ok gauge",
                f"paxect_demo04_ok {_last.get('modules_ok',0)}",
                "# HELP paxect_demo04_last_mode Last selftune mode",
                f"paxect_demo04_last_mode{{mode=\"{_last.get('mode','n/a')}\"}} 1"
            ]
            self._send(200, "\n".join(metrics), "text/plain; version=0.0.4"); return
        if path == "/last":
            self._send(200, json.dumps(_last)); return
        self._send(404, json.dumps({"error":"not found"}))

    def log_message(self, *a, **kw): pass

def background_loop():
    while True:
        run_health_cycle()
        time.sleep(10)

def main():
    print("=== PAXECT Demo 04 – Metrics & Health Endpoints ===")
    run_health_cycle()
    t = threading.Thread(target=background_loop, daemon=True)
    t.start()
    httpd = HTTPServer(("127.0.0.1", PORT), Handler)
    print(f"[listening] http://127.0.0.1:{PORT} (/ping /ready /metrics /last)")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        httpd.server_close()
        print("\n[OK] Demo 04 stopped")

if __name__ == "__main__":
    main()
