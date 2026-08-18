"""Serve the experiment and save trial data through a Supabase backend."""

from __future__ import annotations

from datetime import datetime
import json
import os
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import threading
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4
import webbrowser


ROOT = Path(__file__).resolve().parent

SUPABASE_FIELDS = [
    "participant_id", "session_id", "phase", "trial_number", "block_number",
    "block_trial_number", "block_length", "total_scheduled_main_trials",
    "probability_condition", "favored_fruit", "favored_fruit_switched",
    "left_stimulus", "right_stimulus", "apple_base_probability",
    "banana_base_probability", "apple_unchosen_before", "banana_unchosen_before",
    "apple_baited", "banana_baited", "choice_side", "chosen_stimulus",
    "choice_clicked_at", "response_recorded_at", "next_clicked_at",
    "reaction_time_ms", "reward", "cumulative_score", "saved_at",
]
BOOLEAN_FIELDS = {
    "favored_fruit_switched", "apple_baited", "banana_baited", "reward"
}
NULLABLE_FIELDS = {
    "block_number", "block_trial_number", "block_length", "favored_fruit",
    "favored_fruit_switched", "chosen_stimulus", "choice_clicked_at",
    "reaction_time_ms",
}


def load_env_file(path=ROOT / ".env") -> None:
    """Load simple KEY=VALUE settings without adding a dependency."""
    try:
        lines = Path(path).read_text(encoding="utf-8").splitlines()
    except OSError:
        return
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


load_env_file()
SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_PUBLISHABLE_KEY = os.environ.get("SUPABASE_PUBLISHABLE_KEY", "")


def reserve_participant_id() -> str:
    """Create a unique ID without storing any local participant state."""
    return f"participant_{uuid4().hex}"


def build_supabase_record(payload: dict) -> dict:
    """Allow only known fields and normalize browser values for Postgres."""
    missing = [field for field in SUPABASE_FIELDS if field not in payload]
    if missing:
        raise ValueError(f"Missing required fields: {', '.join(missing)}")

    record = {}
    for field in SUPABASE_FIELDS:
        value = payload[field]
        if field in NULLABLE_FIELDS and value == "":
            value = None
        if field in BOOLEAN_FIELDS and value is not None:
            if value not in (0, 1, False, True):
                raise ValueError(f"Invalid boolean value for {field}")
            value = bool(value)
        record[field] = value
    return record


def save_to_supabase(record: dict, timeout=10) -> None:
    """Insert one trial using the server-held low-privilege API key."""
    if not SUPABASE_URL or not SUPABASE_PUBLISHABLE_KEY:
        raise RuntimeError("Supabase backend is not configured")

    request = Request(
        f"{SUPABASE_URL}/rest/v1/experiment_trials",
        data=json.dumps(record).encode("utf-8"),
        method="POST",
        headers={
            "apikey": SUPABASE_PUBLISHABLE_KEY,
            "Content-Type": "application/json",
            "Prefer": "return=minimal",
        },
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            if not 200 <= response.status < 300:
                raise RuntimeError(f"Supabase returned HTTP {response.status}")
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Supabase rejected the trial: {detail}") from error
    except URLError as error:
        raise RuntimeError(f"Could not reach Supabase: {error.reason}") from error


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def log_message(self, format, *args):
        return

    def do_GET(self):
        if self.path == "/next-participant":
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
        if self.path != "/save":
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
    if not SUPABASE_URL or not SUPABASE_PUBLISHABLE_KEY:
        raise RuntimeError("Set SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY in .env")
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
