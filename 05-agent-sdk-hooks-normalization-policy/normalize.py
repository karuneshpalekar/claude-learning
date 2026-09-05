"""Pure normalisation functions — no SDK/hook types here, so they're trivially
unit-testable on their own.

Three heterogeneous formats, one canonical shape:
  Tool A: Unix epoch seconds + numeric status code   (legacy system)
  Tool B: ISO 8601 timestamp + English status string (modern system)
  Tool C: DD/MM/YYYY date + single-character status  (partner feed)

Canonical output: {"order_id": ..., "date": "YYYY-MM-DD", "status": <english word>}
"""

from __future__ import annotations

from datetime import datetime, timezone

STATUS_CODE_MAP = {0: "pending", 1: "processing", 2: "completed", 3: "failed"}
STATUS_CHAR_MAP = {"P": "pending", "C": "completed", "F": "failed", "X": "cancelled"}


def unix_to_iso_date(epoch_seconds: int) -> str:
    return datetime.fromtimestamp(epoch_seconds, tz=timezone.utc).date().isoformat()


def iso_datetime_to_iso_date(iso_string: str) -> str:
    # Accept trailing 'Z' as UTC.
    cleaned = iso_string.replace("Z", "+00:00")
    return datetime.fromisoformat(cleaned).date().isoformat()


def ddmmyyyy_to_iso_date(ddmmyyyy: str) -> str:
    """'01/12/2025' means 1 December 2025, NOT January 12th — this is exactly
    the day/month confusion the exam warns a model can introduce without a
    deterministic converter."""
    day, month, year = ddmmyyyy.split("/")
    return datetime(int(year), int(month), int(day)).date().isoformat()


def numeric_status_to_english(code: int) -> str:
    if code not in STATUS_CODE_MAP:
        raise ValueError(f"unknown numeric status code: {code!r}")
    return STATUS_CODE_MAP[code]


def char_status_to_english(char: str) -> str:
    if char not in STATUS_CHAR_MAP:
        raise ValueError(f"unknown status character: {char!r}")
    return STATUS_CHAR_MAP[char]


def normalize_record_from_tool(tool_name: str, raw: dict) -> dict:
    """Dispatch on which tool produced `raw` and return the canonical shape."""
    if tool_name.endswith("check_order_a"):
        return {
            "order_id": raw["order_id"],
            "date": unix_to_iso_date(raw["timestamp"]),
            "status": numeric_status_to_english(raw["status_code"]),
        }
    if tool_name.endswith("check_order_b"):
        return {
            "order_id": raw["order_id"],
            "date": iso_datetime_to_iso_date(raw["date"]),
            "status": raw["status"].strip().lower(),
        }
    if tool_name.endswith("check_order_c"):
        return {
            "order_id": raw["order_id"],
            "date": ddmmyyyy_to_iso_date(raw["date"]),
            "status": char_status_to_english(raw["status"]),
        }
    raise ValueError(f"no normaliser registered for tool {tool_name!r}")
