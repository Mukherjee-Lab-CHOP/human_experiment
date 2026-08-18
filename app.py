"""Local development server for the Vercel-compatible experiment."""

from __future__ import annotations

import json
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import threading
import webbrowser

from backend import (
    build_supabase_record,
    reserve_participant_id,
    save_to_supabase,
    supabase_settings,
)


ROOT = Path(__file__).resolve().parent


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def log_message(self, format, *args):
        return

    def do_GET(self):
        if self.path in ("/api/participant", "/next-participant"):
            body = json.dumps({"participant_id": reserve_participant_id()}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path == "/data" or self.path.startswith("/data/"):
            self.send_error(404)
            return
        super().do_GET()

    def do_POST(self):
        if self.path not in ("/api/save", "/save"):
            self.send_error(404)
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if size <= 0 or size > 100_000:
                raise ValueError("Invalid request size")
            payload = json.loads(self.rfile.read(size))
            save_to_supabase(build_supabase_record(payload))
            body = json.dumps({"ok": True}).encode()
            self.send_response(201)
        except Exception as exc:
            body = json.dumps({"ok": False, "error": str(exc)}).encode()
            self.send_response(502)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main():
    supabase_settings()
    server = ThreadingHTTPServer(("127.0.0.1", 8765), Handler)
    url = "http://127.0.0.1:8765/"
    print(f"Human experiment running at {url}", flush=True)
    print("Trial data will be saved to Supabase. Press Ctrl+C to stop.", flush=True)
    threading.Timer(0.4, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
