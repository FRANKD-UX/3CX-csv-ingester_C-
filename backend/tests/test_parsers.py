import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from parsers import detect_parser


def test_detects_and_parses_3cx_row():
    parser = detect_parser(["Call ID", "Ring Duration", "Dialed Number", "Reason", "Start Time"])

    record = parser.parse_row(
        {
            "Call ID": "1",
            "Ring Duration": "00:00:05",
            "Talk Duration": "00:02:00",
            "Dialed Number": "200",
            "Calling Party": "100",
            "Reason": "Answered",
            "Start Time": "2026-05-17 09:15:00",
            "Answered By Ext": "200",
            "Answered By Name": "Agent A",
        }
    )

    assert parser.name == "3CX"
    assert record is not None
    assert record["caller_number"] == "100"
    assert record["callee_number"] == "200"
    assert record["duration_secs"] == 120
    assert record["ring_secs"] == 5
    assert record["outcome"] == "answered"
    assert record["pbx_source"] == "3CX"
    assert record["row_hash"]


def test_detects_and_parses_yeastar_row():
    parser = detect_parser(["CallFrom", "CallTo", "Talk Duration", "Disposition", "Date"])

    record = parser.parse_row(
        {
            "CallFrom": "<101>",
            "CallTo": "<202>",
            "Talk Duration": "03:15",
            "Ring Duration": "00:10",
            "Disposition": "ANSWERED",
            "Date": "2026-05-17 10:00:00",
            "Agent Ext": "202",
        }
    )

    assert parser.name == "Yeastar"
    assert record is not None
    assert record["caller_number"] == "101"
    assert record["callee_number"] == "202"
    assert record["duration_secs"] == 195
    assert record["outcome"] == "answered"


def test_detects_and_parses_freepbx_row():
    parser = detect_parser(["src", "dst", "duration", "disposition", "accountcode", "calldate"])

    record = parser.parse_row(
        {
            "src": "100",
            "dst": "200",
            "duration": "90",
            "billsec": "60",
            "disposition": "ANSWERED",
            "accountcode": "SIP/200-00001",
            "calldate": "2026-05-17 11:30:00",
            "dcontext": "from-internal",
        }
    )

    assert parser.name == "FreePBX"
    assert record is not None
    assert record["agent_ext"] == "200"
    assert record["duration_secs"] == 60
    assert record["ring_secs"] == 30
    assert record["direction"] == "outbound"


def test_rejects_unsupported_headers():
    with pytest.raises(ValueError, match="No supported PBX format detected"):
        detect_parser(["foo", "bar"])
