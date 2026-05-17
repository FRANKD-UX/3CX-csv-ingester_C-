"""Parser registry — abstract base class and concrete PBX parsers."""
from __future__ import annotations

import hashlib
import re
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Optional


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_dt(value: str | None, fmts: list[str]) -> Optional[datetime]:
    """Try each format in order; return None if nothing matches."""
    if not value:
        return None
    value = value.strip()
    for fmt in fmts:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            pass
    return None


def _to_int(value: str | None) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(str(value).strip())
    except (ValueError, TypeError):
        return None


def _duration_to_secs(value: str | None) -> Optional[int]:
    """Accept hh:mm:ss, mm:ss, or bare integer seconds."""
    if not value:
        return None
    value = str(value).strip()
    parts = value.split(":")
    try:
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        if len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        return int(float(value))
    except (ValueError, TypeError):
        return None


def _compute_hash(fields: list) -> str:
    raw = "|".join(str(f) if f is not None else "" for f in fields)
    return hashlib.sha256(raw.encode()).hexdigest()[:64]


def _normalise_direction(value: str | None) -> str:
    if not value:
        return "unknown"
    v = value.strip().lower()
    if v in ("inbound", "in"):
        return "inbound"
    if v in ("outbound", "out"):
        return "outbound"
    if v in ("internal",):
        return "internal"
    return "unknown"


def _normalise_outcome(value: str | None) -> str:
    if not value:
        return "unknown"
    v = value.strip().lower()
    mapping = {
        "answered": "answered",
        "answer": "answered",
        "no answer": "missed",
        "no_answer": "missed",
        "noanswer": "missed",
        "missed": "missed",
        "abandoned": "abandoned",
        "abandon": "abandoned",
        "busy": "busy",
        "voicemail": "voicemail",
        "vm": "voicemail",
        "hangup": "answered",
        "answered|no answer": "missed",
        "completed": "answered",
        "cancel": "abandoned",
        "congestion": "busy",
        "chanunavail": "busy",
    }
    return mapping.get(v, "unknown")


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------

class BaseParser(ABC):
    name: str = "Unknown"

    @abstractmethod
    def can_parse(self, headers: list[str]) -> bool:
        """Return True if this parser understands the given CSV headers."""

    @abstractmethod
    def parse_row(self, row: dict) -> Optional[dict]:
        """Return a dict ready to become a CallRecord, or None to skip the row."""

    def _build_record(self, **kwargs) -> dict:
        fields = [
            kwargs.get("caller_number", ""),
            kwargs.get("callee_number", ""),
            str(kwargs.get("start_time", "")),
            kwargs.get("pbx_source", ""),
            kwargs.get("agent_ext", ""),
            kwargs.get("duration_secs", ""),
        ]
        kwargs.setdefault("id", str(uuid.uuid4()))
        kwargs["row_hash"] = _compute_hash(fields)
        return kwargs


# ---------------------------------------------------------------------------
# 3CX Parser
# ---------------------------------------------------------------------------

_3CX_REQUIRED = {"Call ID", "Ring Duration", "Dialed Number", "Reason"}

_3CX_DT_FMTS = [
    "%Y/%m/%d %H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
    "%m/%d/%Y %H:%M:%S",
    "%d/%m/%Y %H:%M:%S",
    "%m/%d/%Y %I:%M:%S %p",
]


class ThreeCXParser(BaseParser):
    name = "3CX"

    def can_parse(self, headers: list[str]) -> bool:
        return _3CX_REQUIRED.issubset(set(headers))

    def parse_row(self, row: dict) -> Optional[dict]:
        caller = row.get("Calling Party", "") or ""
        callee = row.get("Dialed Number", "") or ""
        start_str = row.get("Start Time") or row.get("Date/Time") or ""
        start_time = _parse_dt(start_str, _3CX_DT_FMTS)
        if not start_time or not caller or not callee:
            return None

        ring = _duration_to_secs(row.get("Ring Duration"))
        talk = _duration_to_secs(row.get("Talk Duration") or row.get("Duration"))
        reason = (row.get("Reason") or "").strip().lower()
        outcome = "answered" if reason in ("", "answered", "hangup") else "missed"
        if "busy" in reason:
            outcome = "busy"
        elif "voicemail" in reason:
            outcome = "voicemail"
        elif "no answer" in reason or "noanswer" in reason:
            outcome = "missed"

        direction_raw = row.get("Direction") or row.get("Call Direction") or ""
        direction = _normalise_direction(direction_raw)

        agent_ext = row.get("Answered By Ext") or row.get("Agent Ext") or row.get("Answered By") or ""
        agent_name = row.get("Answered By Name") or row.get("Agent Name") or ""

        answer_time = None
        if outcome == "answered" and ring is not None and start_time:
            answer_time = start_time + timedelta(seconds=ring)

        end_time = None
        if start_time and talk is not None:
            end_time = start_time + timedelta(seconds=(ring or 0) + talk)

        return self._build_record(
            caller_number=caller,
            caller_name=row.get("Calling Party Name", ""),
            callee_number=callee,
            callee_name=row.get("Callee Name", ""),
            start_time=start_time,
            answer_time=answer_time,
            end_time=end_time,
            duration_secs=talk,
            ring_secs=ring,
            direction=direction,
            outcome=outcome,
            queue_name=row.get("Queue", "") or row.get("Call Queue", ""),
            agent_ext=agent_ext.strip(),
            agent_name=agent_name.strip(),
            did_number=row.get("DID", "") or row.get("DID Number", ""),
            pbx_source="3CX",
        )


# ---------------------------------------------------------------------------
# Yeastar Parser
# ---------------------------------------------------------------------------

_YEASTAR_REQUIRED = {"CallFrom", "CallTo", "Talk Duration", "Disposition"}

_YS_DT_FMTS = [
    "%Y-%m-%d %H:%M:%S",
    "%m/%d/%Y %H:%M:%S",
    "%d-%m-%Y %H:%M:%S",
]


class YeastarParser(BaseParser):
    name = "Yeastar"

    def can_parse(self, headers: list[str]) -> bool:
        return _YEASTAR_REQUIRED.issubset(set(headers))

    def parse_row(self, row: dict) -> Optional[dict]:
        caller = row.get("CallFrom", "") or ""
        callee = row.get("CallTo", "") or ""
        # Strip angle brackets common in Yeastar exports e.g. <100>
        caller = re.sub(r"[<>]", "", caller).strip()
        callee = re.sub(r"[<>]", "", callee).strip()
        if not caller or not callee:
            return None

        start_str = row.get("Date") or row.get("Start Time") or row.get("DateTime") or ""
        start_time = _parse_dt(start_str, _YS_DT_FMTS)
        if not start_time:
            return None

        talk = _duration_to_secs(row.get("Talk Duration"))
        ring = _duration_to_secs(row.get("Ring Duration") or row.get("Wait Duration"))
        outcome = _normalise_outcome(row.get("Disposition"))

        answer_time = None
        end_time = None
        if outcome == "answered" and ring is not None and start_time:
            answer_time = start_time + timedelta(seconds=ring)
        if start_time and talk is not None:
            end_time = start_time + timedelta(seconds=(ring or 0) + talk)

        direction = _normalise_direction(row.get("Call Direction") or row.get("Direction"))
        agent_ext = row.get("Agent Ext") or row.get("Agent") or row.get("Answered By") or ""
        agent_name = row.get("Agent Name") or row.get("Answered By Name") or ""

        return self._build_record(
            caller_number=caller,
            caller_name=row.get("Caller Name", ""),
            callee_number=callee,
            callee_name=row.get("Callee Name", ""),
            start_time=start_time,
            answer_time=answer_time,
            end_time=end_time,
            duration_secs=talk,
            ring_secs=ring,
            direction=direction,
            outcome=outcome,
            queue_name=row.get("Queue", "") or row.get("Queue Name", ""),
            agent_ext=agent_ext.strip(),
            agent_name=agent_name.strip(),
            did_number=row.get("DID", ""),
            pbx_source="Yeastar",
        )


# ---------------------------------------------------------------------------
# FreePBX Parser
# ---------------------------------------------------------------------------

_FREEPBX_REQUIRED = {"src", "dst", "duration", "disposition", "accountcode"}

_FP_DT_FMTS = [
    "%Y-%m-%d %H:%M:%S",
    "%m/%d/%Y %H:%M:%S",
]


class FreePBXParser(BaseParser):
    name = "FreePBX"

    def can_parse(self, headers: list[str]) -> bool:
        return _FREEPBX_REQUIRED.issubset(set(headers))

    def parse_row(self, row: dict) -> Optional[dict]:
        caller = row.get("src", "") or ""
        callee = row.get("dst", "") or ""
        if not caller or not callee:
            return None

        start_str = row.get("calldate") or row.get("start") or row.get("date") or ""
        start_time = _parse_dt(start_str, _FP_DT_FMTS)
        if not start_time:
            return None

        duration = _duration_to_secs(row.get("duration"))
        billsec = _duration_to_secs(row.get("billsec"))
        ring = (duration - billsec) if (duration and billsec) else None
        talk = billsec

        disposition = row.get("disposition", "")
        outcome = _normalise_outcome(disposition)

        answer_time = None
        end_time = None
        if outcome == "answered" and ring is not None and start_time:
            answer_time = start_time + timedelta(seconds=ring)
        if start_time and duration is not None:
            end_time = start_time + timedelta(seconds=duration)

        channel = row.get("channel", "")
        direction = "inbound" if callee.startswith("s") or row.get("dcontext", "").lower() in ("from-trunk",) else "outbound"

        agent_ext = row.get("accountcode", "") or row.get("dstchannel", "") or ""
        # Extract extension number from SIP/100-xxxx style strings
        match = re.search(r"[\\/](\d+)", agent_ext)
        if match:
            agent_ext = match.group(1)

        return self._build_record(
            caller_number=caller,
            caller_name=row.get("cnam", ""),
            callee_number=callee,
            callee_name="",
            start_time=start_time,
            answer_time=answer_time,
            end_time=end_time,
            duration_secs=talk,
            ring_secs=ring,
            direction=direction,
            outcome=outcome,
            queue_name=row.get("dcontext", ""),
            agent_ext=agent_ext.strip(),
            agent_name="",
            did_number=row.get("did", ""),
            pbx_source="FreePBX",
        )


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

PARSERS: list[BaseParser] = [
    ThreeCXParser(),
    YeastarParser(),
    FreePBXParser(),
]


def detect_parser(headers: list[str]) -> BaseParser:
    """Return the first parser that claims ownership, or raise ValueError."""
    for parser in PARSERS:
        if parser.can_parse(headers):
            return parser
    found = ", ".join(f'"{h}"' for h in headers)
    raise ValueError(
        f"No supported PBX format detected. "
        f"Headers found: [{found}]. "
        f"Supported formats: 3CX (needs 'Call ID', 'Ring Duration', 'Dialed Number', 'Reason'), "
        f"Yeastar (needs 'CallFrom', 'CallTo', 'Talk Duration', 'Disposition'), "
        f"FreePBX (needs 'src', 'dst', 'duration', 'disposition', 'accountcode')."
    )
