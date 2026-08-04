"""Launch the human experiment as a local browser GUI."""

from __future__ import annotations

import csv
from datetime import datetime
import json
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import threading
import webbrowser


ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
SEQUENCE_FILE = DATA / ".participant_sequence"
SEQUENCE_LOCK = threading.Lock()
CSV_FIELDS = [
    "participant_id", "trial_number", "block", "reversed", "left_orientation",
    "right_orientation", "horizontal_base_probability", "vertical_base_probability",
    "horizontal_unchosen_before", "vertical_unchosen_before", "horizontal_baited",
    "vertical_baited", "choice_side", "chosen_orientation", "reaction_time_ms",
    "reward", "cumulative_score", "timestamp",
]


def reserve_participant_id(data_dir=DATA) -> str:
    """Atomically reserve the next persistent, sequential participant ID."""
    data_dir = Path(data_dir)
    sequence_file = data_dir / ".participant_sequence"
    with SEQUENCE_LOCK:
        data_dir.mkdir(exist_ok=True)
        try:
            current = int(sequence_file.read_text(encoding="utf-8").strip())
        except (OSError, ValueError):
            current = 0
        number = current + 1
        sequence_file.write_text(str(number), encoding="utf-8")
    return f"participant_{number:03d}"


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
        super().do_GET()

    def do_POST(self):
        if self.path != "/save":
            self.send_error(404)
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(size))
            participant = str(payload["participant_id"])
            safe_id = "".join(c if c.isalnum() or c in "-_" else "_" for c in participant)
            session_id = str(payload["session_id"])
            DATA.mkdir(exist_ok=True)
            path = DATA / f"{safe_id}_{session_id}.csv"
            new_file = not path.exists()
            with path.open("a", newline="", encoding="utf-8") as output:
                writer = csv.DictWriter(output, fieldnames=CSV_FIELDS)
                if new_file:
                    writer.writeheader()
                writer.writerow({key: payload.get(key, "") for key in CSV_FIELDS})
            body = json.dumps({"ok": True, "path": str(path)}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except Exception as exc:
            body = json.dumps({"ok": False, "error": str(exc)}).encode()
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)


def main():
    server = ThreadingHTTPServer(("127.0.0.1", 8765), Handler)
    url = "http://127.0.0.1:8765/"
    print(f"Human experiment running at {url}", flush=True)
    print("Keep this terminal open during the experiment. Press Ctrl+C to stop.", flush=True)
    threading.Timer(0.4, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
