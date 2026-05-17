# backend/threecx_poller.py

"""
Two scheduled jobs that use the 3CX client:

  1. poll_live_calls   — runs every THREECX_POLL_INTERVAL_SECONDS
                         fetches active calls and caches them in memory
                         (no DB write — this is the live call wall)

  2. poll_call_history — runs every 5 minutes
                         fetches completed calls since last run
                         and writes them to the database via ingest logic

Both jobs are registered into the existing APScheduler instance
from scheduler.py — they don't create a second scheduler.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import text

from config import THREECX_ENABLED, THREECX_POLL_INTERVAL_SECONDS
from database import SessionLocal
from models import IngestLog
from threecx_client import ThreeCXClient
from threecx_normaliser import normalise_api_record

logger = logging.getLogger(__name__)

# In-memory cache of active calls — the live call wall reads from this.
# This is intentionally not in the database — it's ephemeral state.
_active_calls_cache: list[dict] = []
_active_calls_updated_at: datetime | None = None

# Tracks the last time we successfully pulled CDR history.
# On first run we pull the last 24 hours.
_last_history_poll: datetime | None = None


def get_cached_active_calls() -> dict[str, Any]:
    """
    Returns the in-memory active calls cache with its timestamp.
    Called by the /api/v1/live/activecalls endpoint.
    """
    return {
        "calls": _active_calls_cache,
        "updated_at": _active_calls_updated_at.isoformat() if _active_calls_updated_at else None,
        "count": len(_active_calls_cache),
    }


def poll_live_calls():
    """
    Fetches currently active calls from 3CX and updates the in-memory cache.

    This does NOT write to the database — active calls are transient.
    The frontend polls /api/v1/live/activecalls every 10-15 seconds
    to show the live call wall.
    """
    global _active_calls_cache, _active_calls_updated_at

    if not THREECX_ENABLED:
        return

    client = ThreeCXClient()
    try:
        calls = client.get_active_calls()
        _active_calls_cache = calls
        _active_calls_updated_at = datetime.utcnow()
        logger.debug("Active calls refreshed: %d in progress", len(calls))
    except Exception as exc:
        logger.error("poll_live_calls failed: %s", exc)
    finally:
        client.close()


def poll_call_history():
    """
    Fetches completed call records from 3CX since the last successful poll
    and writes them to the database.

    This is how live API data flows into the leaderboard — same pipeline
    as CSV ingestion, just a different source.
    """
    global _last_history_poll

    if not THREECX_ENABLED:
        return

    since = _last_history_poll or (datetime.utcnow() - timedelta(hours=24))
    until = datetime.utcnow()

    client = ThreeCXClient()
    db = SessionLocal()
    rows_imported = 0
    rows_skipped = 0

    try:
        records = client.get_call_history(since=since, until=until)

        if not records:
            logger.debug("No new CDR records from 3CX since %s", since.isoformat())
            _last_history_poll = until
            return

        for raw in records:
            normalised = normalise_api_record(raw)
            if normalised is None:
                rows_skipped += 1
                continue

            # Same INSERT IGNORE pattern as CSV ingest — deduplication
            # via row_hash means re-processing overlapping time windows is safe.
            result = db.execute(
                text("""
                    INSERT IGNORE INTO call_records (
                        id, caller_number, caller_name, callee_number, callee_name,
                        start_time, answer_time, end_time, duration_secs, ring_secs,
                        direction, outcome, queue_name, agent_ext, agent_name,
                        did_number, pbx_source, row_hash
                    ) VALUES (
                        :id, :caller_number, :caller_name, :callee_number, :callee_name,
                        :start_time, :answer_time, :end_time, :duration_secs, :ring_secs,
                        :direction, :outcome, :queue_name, :agent_ext, :agent_name,
                        :did_number, :pbx_source, :row_hash
                    )
                """),
                normalised,
            )
            if result.rowcount > 0:
                rows_imported += 1
            else:
                rows_skipped += 1

        db.commit()
        _last_history_poll = until

        logger.info(
            "3CX API poll: %d imported, %d skipped (window: %s → %s)",
            rows_imported, rows_skipped,
            since.isoformat(), until.isoformat(),
        )

        # Write a synthetic ingest log entry so Import History page shows API polls
        log = IngestLog(
            filename=f"3cx-api-poll-{until.strftime('%Y%m%d-%H%M%S')}",
            file_hash=f"api-{until.isoformat()}",
            pbx_source="3CX-API",
            rows_imported=rows_imported,
            rows_skipped=rows_skipped,
            status="success",
            processed_at=until,
        )
        db.add(log)
        db.commit()

    except Exception as exc:
        logger.error("poll_call_history failed: %s", exc)
        db.rollback()
    finally:
        client.close()
        db.close()