"""Vercel Function that validates and stores one completed trial."""

import json
from http.server import BaseHTTPRequestHandler

from backend import build_supabase_record, save_to_supabase


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if size <= 0 or size > 100_000:
                raise ValueError("Invalid request size")
            payload = json.loads(self.rfile.read(size))
            save_to_supabase(build_supabase_record(payload))
            body = json.dumps({"ok": True}).encode()
            status = 201
        except Exception as exc:
            body = json.dumps({"ok": False, "error": str(exc)}).encode()
            status = 502

        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
