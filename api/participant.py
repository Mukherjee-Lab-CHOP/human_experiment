"""Vercel Function that creates a participant ID."""

import json
from http.server import BaseHTTPRequestHandler

from backend import reserve_participant_id


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = json.dumps({"participant_id": reserve_participant_id()}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
