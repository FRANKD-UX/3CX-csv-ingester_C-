"""
Core ingestion function.

Called by both the upload API endpoint and the folder scanner.
Accepts raw CSV bytes, detects the parser, normalises every row,
and bulk-upserts into MySQL using INSERT IGNORE for deduplication.
"""

from __future__ import annotations

import csv
import hashlib
import io
import logging
from datetime import datetime
from typing import Any

from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models import CallRecord, IngestLog
from parsers import detect_parser

logger = logging.getLogger(__name__)
MAX_ERROR_SAMPLES = 5


def _file_hash(content: bytes) -> str:
    """SHA-256 of the raw file bytes, used to detect duplicate file uploads."""
    return hashlib.sha256(content).hexdigest()[:64]


def _read_csv(content: bytes) -> tuple[list[str], list[dict[str, str]]]:
    """
    Decode the CSV bytes and return (headers, rows).

    We strip the BOM that Windows-exported CSVs prepend, and strip
    whitespace from every key and value so parsers don't need to
    worry about it.
    """
    text_content = content.decode("utf-8-sig").strip()
    reader = csv.DictReader(io.StringIO(text_content))
    headers = [h.strip() for h in (reader.fieldnames or [])]
    rows = [
        {k.strip(): (v.strip() if v else "") for k, v in row.items() if k}
        for row in reader
    ]
    return headers, rows


def _record_values(record: dict[str, Any], parser_name: str) -> dict[str, Any]:
    return {
        "id": record.get("id"),
        "caller_number": record.get("caller_number") or "unknown",
        "caller_name": record.get("caller_name") or None,
        "callee_number": record.get("callee_number") or "unknown",
        "callee_name": record.get("callee_name") or None,
        "start_time": record.get("start_time"),
        "answer_time": record.get("answer_time"),
        "end_time": record.get("end_time"),
        "duration_secs": record.get("duration_secs"),
        "ring_secs": record.get("ring_secs"),
        "direction": record.get("direction") or "unknown",
        "outcome": record.get("outcome") or "unknown",
        "queue_name": record.get("queue_name") or None,
        "agent_ext": record.get("agent_ext") or None,
        "agent_name": record.get("agent_name") or None,
        "did_number": record.get("did_number") or None,
        "pbx_source": record.get("pbx_source") or parser_name,
        "row_hash": record.get("row_hash"),
    }


def _insert_call_record_ignore_duplicates(
    db: Session,
    record: dict[str, Any],
    parser_name: str,
) -> int:
    """Insert a call record with MySQL INSERT IGNORE semantics."""
    stmt = mysql_insert(CallRecord).values(**_record_values(record, parser_name)).prefix_with("IGNORE")
    result = db.execute(stmt)
    return result.rowcount or 0


def ingest_csv(content: bytes, filename: str, db: Session) -> dict[str, Any]:
    """
    Parse, normalise, deduplicate, and store a CSV file.

    Returns a summary dict:
      { pbx_detected, rows_imported, rows_skipped, filename }

    Raises ValueError for unrecognised formats or empty files.
    This function is intentionally synchronous — both the FastAPI
    upload endpoint (called with await) and the background scheduler
    call it the same way.
    """
    fhash = _file_hash(content)

    # Check whether this exact file has already been successfully imported
    existing = (
        db.query(IngestLog)
        .filter(IngestLog.file_hash == fhash, IngestLog.status == "success")
        .first()
    )
    if existing:
        logger.info("File %s already imported (hash match), skipping.", filename)
        return {
            "pbx_detected": existing.pbx_source or "unknown",
            "rows_imported": 0,
            "rows_skipped": existing.rows_imported or 0,
            "filename": filename,
        }

    headers, rows = _read_csv(content)
    if not headers:
        raise ValueError("CSV file appears to be empty or has no headers.")

    parser = detect_parser(headers)  # raises ValueError if no match

    log_entry = IngestLog(
        filename=filename,
        file_hash=fhash,
        pbx_source=parser.name,
        status="pending",
        processed_at=datetime.utcnow(),
    )
    db.add(log_entry)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        existing = db.query(IngestLog).filter(IngestLog.file_hash == fhash).first()
        if existing:
            return {
                "pbx_detected": existing.pbx_source or "unknown",
                "rows_imported": 0,
                "rows_skipped": existing.rows_imported or 0,
                "filename": filename,
            }
        raise

    rows_imported = 0
    rows_skipped = 0
    error_samples: list[str] = []

    try:
        for row_number, raw_row in enumerate(rows, start=2):
            try:
                record_dict = parser.parse_row(raw_row)
            except Exception as exc:
                logger.warning("parse_row raised on row %s: %s", raw_row, exc)
                rows_skipped += 1
                if len(error_samples) < MAX_ERROR_SAMPLES:
                    error_samples.append(f"row {row_number}: {exc}")
                continue

            if record_dict is None:
                rows_skipped += 1
                continue

            try:
                with db.begin_nested():
                    inserted = _insert_call_record_ignore_duplicates(db, record_dict, parser.name)
                if inserted > 0:
                    rows_imported += 1
                else:
                    rows_skipped += 1
            except Exception as exc:
                logger.error("DB insert failed for row %s: %s", raw_row, exc)
                rows_skipped += 1
                if len(error_samples) < MAX_ERROR_SAMPLES:
                    error_samples.append(f"row {row_number}: {exc}")

        log_entry.rows_imported = rows_imported
        log_entry.rows_skipped = rows_skipped
        log_entry.status = "success"
        if error_samples:
            log_entry.error_message = "; ".join(error_samples)[:1024]
        log_entry.processed_at = datetime.utcnow()
        db.commit()

    except Exception as exc:
        db.rollback()
        try:
            log_entry.status = "error"
            log_entry.error_message = str(exc)[:1024]
            log_entry.processed_at = datetime.utcnow()
            db.add(log_entry)
            db.commit()
        except Exception:
            db.rollback()
        raise

    logger.info(
        "Ingested %s via %s: %d imported, %d skipped",
        filename, parser.name, rows_imported, rows_skipped,
    )

    return {
        "pbx_detected": parser.name,
        "rows_imported": rows_imported,
        "rows_skipped": rows_skipped,
        "filename": filename,
    }
