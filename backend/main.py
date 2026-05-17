"""FastAPI application — entry point."""
from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timedelta, date
from typing import Optional, List

from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import case as sa_case, func
from sqlalchemy.orm import Session

from database import engine, get_db, Base, verify_connection
from models import CallRecord, IngestLog
from ingest import ingest_csv
from scheduler import start_scheduler
from config import CORS_ORIGINS, MAX_UPLOAD_BYTES
from threecx_poller import get_cached_active_calls


# ---------------------------------------------------------------------------
# DB init
# ---------------------------------------------------------------------------

def init_db():
    verify_connection()
    Base.metadata.create_all(bind=engine)


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------

_scheduler = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _scheduler
    init_db()
    _scheduler = start_scheduler()
    yield
    if _scheduler:
        _scheduler.shutdown(wait=False)


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(title="Call Dashboard Reporter API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class UploadResponse(BaseModel):
    pbx_detected: str
    rows_imported: int
    rows_skipped: int
    filename: str


class AgentLeaderboardEntry(BaseModel):
    rank: int
    agent_ext: str
    agent_name: Optional[str]
    total_calls: int
    answered_calls: int
    missed_calls: int
    total_talk_mins: float
    avg_talk_mins: float
    answer_rate_pct: float


class ImportLogEntry(BaseModel):
    id: int
    filename: Optional[str]
    pbx_source: Optional[str]
    rows_imported: int
    rows_skipped: int
    status: Optional[str]
    error_message: Optional[str]
    processed_at: Optional[datetime]


class TopAgent(BaseModel):
    name: Optional[str]
    count: int


class OverviewStats(BaseModel):
    total_calls_today: int
    total_calls_week: int
    total_calls_month: int
    top_agent_today: Optional[TopAgent]
    active_agents_today: int


class HourlyBucket(BaseModel):
    hour: int
    calls: int


def _count_outcome(outcome: str):
    return func.sum(sa_case((CallRecord.outcome == outcome, 1), else_=0))


def _sum_duration_for_outcome(outcome: str):
    return func.sum(sa_case((CallRecord.outcome == outcome, CallRecord.duration_secs), else_=0))


# ---------------------------------------------------------------------------
# Helper — date windows
# ---------------------------------------------------------------------------

def _period_window(period: str):
    today = date.today()
    if period == "daily":
        start = datetime.combine(today, datetime.min.time())
        end = datetime.combine(today, datetime.max.time())
    elif period == "weekly":
        monday = today - timedelta(days=today.weekday())
        sunday = monday + timedelta(days=6)
        start = datetime.combine(monday, datetime.min.time())
        end = datetime.combine(sunday, datetime.max.time())
    elif period == "monthly":
        first = today.replace(day=1)
        if today.month == 12:
            last = today.replace(day=31)
        else:
            last = (today.replace(month=today.month + 1, day=1) - timedelta(days=1))
        start = datetime.combine(first, datetime.min.time())
        end = datetime.combine(last, datetime.max.time())
    else:
        raise HTTPException(status_code=400, detail=f"Invalid period '{period}'. Use daily|weekly|monthly.")
    return start, end


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/api/v1/health")
def health():
    return {"status": "ok"}


@app.get("/api/v1/live/activecalls")
def live_active_calls():
    """
    Returns the in-memory cache of currently active calls.

    The cache is updated every THREECX_POLL_INTERVAL_SECONDS by the
    scheduler. If 3CX API is not configured, returns an empty list.
    The frontend polls this every 10-15 seconds to drive the live wall.
    """
    return get_cached_active_calls()


@app.post("/api/v1/upload", response_model=UploadResponse)
async def upload_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only .csv files are accepted.")
    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="CSV file is too large.")
    try:
        result = ingest_csv(content, file.filename, db)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Import failed: {exc}")
    return UploadResponse(**{k: result[k] for k in UploadResponse.model_fields})


@app.get("/api/v1/leaderboard/{period}", response_model=List[AgentLeaderboardEntry])
def leaderboard(period: str, db: Session = Depends(get_db)):
    start, end = _period_window(period)

    rows = (
        db.query(
            CallRecord.agent_ext,
            func.max(CallRecord.agent_name).label("agent_name"),
            func.count(CallRecord.id).label("total_calls"),
            _count_outcome("answered").label("answered_calls"),
            _count_outcome("missed").label("missed_calls"),
            _sum_duration_for_outcome("answered").label("total_talk_secs"),
        )
        .filter(
            CallRecord.start_time >= start,
            CallRecord.start_time <= end,
            CallRecord.agent_ext.isnot(None),
            CallRecord.agent_ext != "",
        )
        .group_by(CallRecord.agent_ext)
        .order_by(
            _count_outcome("answered").desc(),
            _sum_duration_for_outcome("answered").desc(),
        )
        .limit(50)
        .all()
    )

    result = []
    for rank, row in enumerate(rows, start=1):
        total_talk_secs = row.total_talk_secs or 0
        answered = row.answered_calls or 0
        total = row.total_calls or 0
        total_talk_mins = round(total_talk_secs / 60, 2)
        avg_talk_mins = round(total_talk_secs / 60 / answered, 2) if answered > 0 else 0.0
        answer_rate = round(answered / total * 100, 1) if total > 0 else 0.0
        result.append(
            AgentLeaderboardEntry(
                rank=rank,
                agent_ext=row.agent_ext,
                agent_name=row.agent_name or "",
                total_calls=total,
                answered_calls=answered,
                missed_calls=row.missed_calls or 0,
                total_talk_mins=total_talk_mins,
                avg_talk_mins=avg_talk_mins,
                answer_rate_pct=answer_rate,
            )
        )
    return result


@app.get("/api/v1/imports", response_model=List[ImportLogEntry])
def imports(db: Session = Depends(get_db)):
    logs = (
        db.query(IngestLog)
        .order_by(IngestLog.processed_at.desc())
        .limit(20)
        .all()
    )
    return [
        ImportLogEntry(
            id=log.id,
            filename=log.filename,
            pbx_source=log.pbx_source,
            rows_imported=log.rows_imported or 0,
            rows_skipped=log.rows_skipped or 0,
            status=log.status,
            error_message=log.error_message,
            processed_at=log.processed_at,
        )
        for log in logs
    ]


@app.get("/api/v1/stats/overview", response_model=OverviewStats)
def stats_overview(db: Session = Depends(get_db)):
    today = date.today()
    today_start = datetime.combine(today, datetime.min.time())
    today_end = datetime.combine(today, datetime.max.time())

    monday = today - timedelta(days=today.weekday())
    week_start = datetime.combine(monday, datetime.min.time())
    week_end = datetime.combine(monday + timedelta(days=6), datetime.max.time())

    month_start = datetime.combine(today.replace(day=1), datetime.min.time())
    if today.month == 12:
        month_end = datetime.combine(today.replace(day=31), datetime.max.time())
    else:
        last_day = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
        month_end = datetime.combine(last_day, datetime.max.time())

    total_today = db.query(func.count(CallRecord.id)).filter(
        CallRecord.start_time >= today_start,
        CallRecord.start_time <= today_end,
    ).scalar() or 0

    total_week = db.query(func.count(CallRecord.id)).filter(
        CallRecord.start_time >= week_start,
        CallRecord.start_time <= week_end,
    ).scalar() or 0

    total_month = db.query(func.count(CallRecord.id)).filter(
        CallRecord.start_time >= month_start,
        CallRecord.start_time <= month_end,
    ).scalar() or 0

    # Top agent today by answered calls
    top_row = (
        db.query(
            CallRecord.agent_name,
            CallRecord.agent_ext,
            func.count(CallRecord.id).label("cnt"),
        )
        .filter(
            CallRecord.start_time >= today_start,
            CallRecord.start_time <= today_end,
            CallRecord.outcome == "answered",
            CallRecord.agent_ext.isnot(None),
            CallRecord.agent_ext != "",
        )
        .group_by(CallRecord.agent_ext, CallRecord.agent_name)
        .order_by(func.count(CallRecord.id).desc())
        .first()
    )

    top_agent = None
    if top_row:
        name = top_row.agent_name or top_row.agent_ext or "Unknown"
        top_agent = TopAgent(name=name, count=top_row.cnt)

    active_agents = (
        db.query(func.count(func.distinct(CallRecord.agent_ext)))
        .filter(
            CallRecord.start_time >= today_start,
            CallRecord.start_time <= today_end,
            CallRecord.agent_ext.isnot(None),
            CallRecord.agent_ext != "",
        )
        .scalar()
        or 0
    )

    return OverviewStats(
        total_calls_today=total_today,
        total_calls_week=total_week,
        total_calls_month=total_month,
        top_agent_today=top_agent,
        active_agents_today=active_agents,
    )


@app.get("/api/v1/stats/hourly", response_model=List[HourlyBucket])
def stats_hourly(db: Session = Depends(get_db)):
    """Calls per hour for today (0-23)."""
    today = date.today()
    today_start = datetime.combine(today, datetime.min.time())
    today_end = datetime.combine(today, datetime.max.time())

    rows = (
        db.query(
            func.hour(CallRecord.start_time).label("hour"),
            func.count(CallRecord.id).label("calls"),
        )
        .filter(
            CallRecord.start_time >= today_start,
            CallRecord.start_time <= today_end,
        )
        .group_by(func.hour(CallRecord.start_time))
        .all()
    )

    bucket_map = {row.hour: row.calls for row in rows}
    return [HourlyBucket(hour=h, calls=bucket_map.get(h, 0)) for h in range(24)]


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
