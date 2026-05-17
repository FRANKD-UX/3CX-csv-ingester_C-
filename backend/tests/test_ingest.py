import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ingest import _read_csv


def test_read_csv_sniffs_tab_delimited_exports():
    content = (
        "Call ID\tStart Time\tCalling Party\tDialed Number\tRing Duration\tReason\n"
        "1\t2026-05-17 09:00:00\t100\t200\t00:00:05\tAnswered\n"
    ).encode()

    headers, rows = _read_csv(content)

    assert headers == [
        "Call ID",
        "Start Time",
        "Calling Party",
        "Dialed Number",
        "Ring Duration",
        "Reason",
    ]
    assert rows[0]["Calling Party"] == "100"
    assert rows[0]["Dialed Number"] == "200"
