# backend/threecx_normaliser.py

"""
Maps raw 3CX API call history records to the normalised CallRecord dict
format — the same format that parsers.py produces from CSVs.

This means the ingest pipeline is identical whether data comes from
a CSV or from the live API. The database doesn't know the difference.
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime
from typing import Any


def _parse_3cx_dt(value: str | None) -> datetime | None:
    """
    3CX API returns datetimes in ISO 8601 format:
    '2024-03-15T09:42:11.000Z' or '2024-03-15T09:42:11'
    """
    if not value:
        return None
    for fmt in (
            "%Y-%m-%dT%H:%M:%S.%fZ",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%S",
    ):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def _map_call_type(raw: str | None) -> str:
    """
    3CX CallType values: Inbound, Outbound, Internal, Unknown
    """
    mapping = {
        "inbound": "inbound",
        "outbound": "outbound",
        "internal": "internal",
    }
    return mapping.get((raw or "").strip().lower(), "unknown")


def _map_reason(raw: str | None) -> str:
    """
    3CX call end reason → our outcome enum.

    Common values from the API: Answered, NoAnswer, Busy,
    Abandoned, Voicemail, Rejected, TransferredToVoicemail
    """
    mapping = {
        "answered": "answered",
        "noanswer": "missed",
        "no answer": "missed",
        "abandoned": "abandoned",
        "busy": "busy",
        "voicemail": "voicemail",
        "transferredtovoicemail": "voicemail",
        "rejected": "missed",
    }
    return mapping.get((raw or "").strip().lower().replace(" ", ""), "unknown")


def _compute_hash(*fields) -> str:
    raw = "|".join(str(f) if f is not None else "" for f in fields)
    return hashlib.sha256(raw.encode()).hexdigest()[:64]


def normalise_api_record(record: dict[str, Any]) -> dict | None:
    """
    Convert a single 3CX API CDR record into the normalised dict
    that ingest.py expects.

    Returns None if the record is missing critical fields (no caller,
    no start time) — those rows are silently skipped.

    3CX CDR API record shape (v18):
    {
      "Id": "abc-123",
      "StartTime": "2024-03-15T09:42:11Z",
      "TalkingDuration": 125,        # seconds
      "RingDuration": 8,             # seconds
      "CallType": "Inbound",
      "Reason": "Answered",
      "FromDisplayName": "John Smith",
      "FromNo": "0211234567",
      "ToDisplayName": "Sales Queue",
      "ToNo": "200",
      "AgentExt": "101",
      "AgentName": "Jane Doe",
      "QueueName": "Sales",
      "DID": "0211234567",
    }

    Note: field names vary slightly between 3CX versions. We use .get()
    everywhere and never assume a field exists.
    """
    caller = record.get("FromNo") or record.get("CallerNumber") or ""
    callee = record.get("ToNo") or record.get("CalleeNumber") or ""
    start_str = record.get("StartTime") or record.get("start_time") or ""

    caller = caller.strip()
    callee = callee.strip()
    start_time = _parse_3cx_dt(start_str)

    if not caller or not callee or not start_time:
        return None

    talk_secs = record.get("TalkingDuration") or record.get("duration_secs") or 0
    ring_secs = record.get("RingDuration") or record.get("ring_secs") or 0

    try:
        talk_secs = int(talk_secs)
        ring_secs = int(ring_secs)
    except (ValueError, TypeError):
        talk_secs = 0
        ring_secs = 0

    direction = _map_call_type(record.get("CallType"))
    outcome = _map_reason(record.get("Reason"))

    agent_ext = str(record.get("AgentExt") or "").strip()
    agent_name = str(record.get("AgentName") or "").strip()
    queue_name = str(record.get("QueueName") or "").strip() or None
    did_number = str(record.get("DID") or "").strip() or None

    row_hash = _compute_hash(caller, callee, start_str, agent_ext, talk_secs)

    return {
        "id": str(uuid.uuid4()),
        "caller_number": caller,
        "caller_name": str(record.get("FromDisplayName") or "").strip() or None,
        "callee_number": callee,
        "callee_name": str(record.get("ToDisplayName") or "").strip() or None,
        "start_time": start_time,
        "answer_time": None,  # not in CDR, derive if needed
        "end_time": None,
        "duration_secs": talk_secs or None,
        "ring_secs": ring_secs or None,
        "direction": direction,
        "outcome": outcome,
        "queue_name": queue_name,
        "agent_ext": agent_ext or None,
        "agent_name": agent_name or None,
        "did_number": did_number,
        "pbx_source": "3CX-API",
        "row_hash": row_hash,
    }