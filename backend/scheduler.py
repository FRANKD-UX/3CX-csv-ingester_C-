"""APScheduler jobs: folder_scanner and retention_purge."""
from __future__ import annotations

import hashlib
import logging
import os
import shutil
from datetime import datetime, timedelta

from apscheduler.schedulers.background import BackgroundScheduler

from config import (
    WATCHED_FOLDER,
    POLL_INTERVAL_SECONDS,
    RETENTION_DAYS,
    THREECX_ENABLED,
    THREECX_POLL_INTERVAL_SECONDS,
)
from database import SessionLocal
from ingest import ingest_csv
from models import IngestLog, CallRecord
from threecx_poller import poll_live_calls, poll_call_history

logger = logging.getLogger(__name__)


def _file_hash(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()[:64]


def _unique_dest(folder: str, filename: str) -> str:
    base, ext = os.path.splitext(filename)
    dest = os.path.join(folder, filename)
    counter = 1
    while os.path.exists(dest):
        dest = os.path.join(folder, f"{base}_{counter}{ext}")
        counter += 1
    return dest


def _write_failure_log(db, filename: str, file_hash: str, error: Exception) -> None:
    existing = db.query(IngestLog).filter(IngestLog.file_hash == file_hash).first()
    if existing:
        existing.status = "error"
        existing.error_message = str(error)[:1024]
        existing.processed_at = datetime.utcnow()
    else:
        db.add(
            IngestLog(
                filename=filename,
                file_hash=file_hash,
                pbx_source=None,
                rows_imported=0,
                rows_skipped=0,
                status="error",
                error_message=str(error)[:1024],
                processed_at=datetime.utcnow(),
            )
        )
    db.commit()


def folder_scanner():
    """Scan WATCHED_FOLDER for new *.csv files and import them."""
    folder = WATCHED_FOLDER
    processed_dir = os.path.join(folder, "processed")
    failed_dir = os.path.join(folder, "failed")
    os.makedirs(processed_dir, exist_ok=True)
    os.makedirs(failed_dir, exist_ok=True)

    db = SessionLocal()
    try:
        for fname in os.listdir(folder):
            if not fname.lower().endswith(".csv"):
                continue
            fpath = os.path.join(folder, fname)
            if not os.path.isfile(fpath):
                continue
            with open(fpath, "rb") as f:
                content = f.read()
            fhash = _file_hash(content)

            # Skip already-processed files
            if (
                db.query(IngestLog)
                .filter(IngestLog.file_hash == fhash, IngestLog.status == "success")
                .first()
            ):
                # Move it to processed anyway so it's cleaned up
                dest = _unique_dest(processed_dir, fname)
                try:
                    shutil.move(fpath, dest)
                except Exception:
                    logger.exception("[scanner] Could not move duplicate file %s", fname)
                continue

            imported = False
            try:
                ingest_csv(content, fname, db)
                imported = True
            except Exception as exc:
                db.rollback()
                _write_failure_log(db, fname, fhash, exc)
                logger.error("[scanner] Failed to import %s: %s", fname, exc)

            dest_dir = processed_dir if imported else failed_dir
            dest = _unique_dest(dest_dir, fname)
            try:
                shutil.move(fpath, dest)
            except Exception as move_err:
                logger.error("[scanner] Could not move %s: %s", fname, move_err)
    finally:
        db.close()


def retention_purge():
    """Delete call_records older than RETENTION_DAYS days."""
    cutoff = datetime.utcnow() - timedelta(days=RETENTION_DAYS)
    db = SessionLocal()
    try:
        deleted = db.query(CallRecord).filter(CallRecord.start_time < cutoff).delete()
        db.commit()
        if deleted:
            logger.info("[purge] Deleted %d call records older than %d days.", deleted, RETENTION_DAYS)
    finally:
        db.close()


def start_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        folder_scanner,
        "interval",
        seconds=POLL_INTERVAL_SECONDS,
        id="folder_scanner",
        replace_existing=True,
    )
    scheduler.add_job(
        retention_purge,
        "cron",
        hour=2,
        minute=0,
        id="retention_purge",
        replace_existing=True,
    )

    # 3CX live jobs are only scheduled when API credentials are configured.
    if THREECX_ENABLED:
        scheduler.add_job(
            poll_live_calls,
            "interval",
            seconds=THREECX_POLL_INTERVAL_SECONDS,
            id="threecx_live",
            replace_existing=True,
        )
        scheduler.add_job(
            poll_call_history,
            "interval",
            minutes=5,
            id="threecx_history",
            replace_existing=True,
        )

    scheduler.start()
    logger.info(
        "[scheduler] folder_scanner every %ds, retention_purge at 02:00 daily.",
        POLL_INTERVAL_SECONDS,
    )
    if THREECX_ENABLED:
        logger.info(
            "[scheduler] 3CX API polling enabled - live calls every %ds, CDR every 5min.",
            THREECX_POLL_INTERVAL_SECONDS,
        )
    return scheduler
