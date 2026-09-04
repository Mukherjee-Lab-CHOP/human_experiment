"""Shared validation and Supabase persistence for local and Vercel backends."""

from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4


ROOT = Path(__file__).resolve().parent
SUPABASE_FIELDS = [
    "participant_id", "session_id", "phase", "trial_number", "block_number",
    "block_trial_number", "block_length", "total_scheduled_main_trials",
    "schedule_id", "block_type", "probability_condition", "favored_fruit", "favored_fruit_switched",
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
    "block_number", "block_trial_number", "block_length", "schedule_id",
    "block_type", "favored_fruit",
    "favored_fruit_switched", "chosen_stimulus", "choice_clicked_at",
    "reaction_time_ms",
}


def load_env_file(path=ROOT / ".env") -> None:
    """Load simple KEY=VALUE settings for local development."""
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


def reserve_participant_id() -> str:
    """Create a globally unique participant ID without persistent local state."""
    return f"participant_{uuid4().hex}"


def build_supabase_record(payload: dict) -> dict:
    """Allow only known fields and normalize browser values for Postgres."""
    if not isinstance(payload, dict):
        raise ValueError("The request body must be a JSON object")
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


def supabase_settings() -> tuple[str, str]:
    """Read settings at request time so Vercel environment variables are used."""
    url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    key = os.environ.get("SUPABASE_PUBLISHABLE_KEY", "")
    if not url or not key:
        raise RuntimeError("Supabase backend is not configured")
    return url, key


def save_to_supabase(record: dict, timeout=10) -> None:
    """Insert one trial using the server-held low-privilege API key."""
    url, key = supabase_settings()
    request = Request(
        f"{url}/rest/v1/experiment_trials",
        data=json.dumps(record).encode("utf-8"),
        method="POST",
        headers={
            "apikey": key,
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
