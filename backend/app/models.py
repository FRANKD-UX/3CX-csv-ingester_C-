import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, DateTime, Text,
    Enum as SAEnum, Index, text,
)
from sqlalchemy.dialects.mysql import CHAR
from database import Base

class CallRecord(Base):
    __tablename__ = "call_records"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    caller_number = Column(String(64), nullable=False)
    caller_name = Column(String(128))
    callee_number = Column(String(64), nullable=False)
    callee_name = Column(String(128))
    start_time = Column(DateTime, nullable=False)
    answer_time = Column(DateTime)
    end_time = Column(DateTime)
    duration_secs = Column(Integer)
    ring_secs = Column(Integer)
    direction = Column(
        SAEnum("inbound", "outbound", "internal", "unknown"),
        nullable=False,
        server_default="unknown",
    )
    outcome = Column(
        SAEnum("answered", "missed", "abandoned", "busy", "voicemail", "unknown"),
        nullable=False,
        server_default="unknown",
    )
    queue_name = Column(String(128))
    agent_ext = Column(String(64))
    agent_name = Column(String(128))
    did_number = Column(String(64))
    pbx_source = Column(String(64), nullable=False)
    row_hash = Column(String(64), unique=True)
    imported_at = Column(DateTime, server_default=text("NOW()"))

    __table_args__ = (
        Index("ix_call_records_start_time", "start_time"),
        Index("ix_call_records_agent_ext", "agent_ext"),
        Index("ix_call_records_queue_name", "queue_name"),
        Index("ix_call_records_outcome", "outcome"),
    )

class IngestLog(Base):
    __tablename__ = "ingest_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String(512))
    file_hash = Column(String(64), unique=True, index=True)
    pbx_source = Column(String(64))
    rows_imported = Column(Integer, default=0)
    rows_skipped = Column(Integer, default=0)
    status = Column(String(32))
    error_message = Column(Text)
    processed_at = Column(DateTime, server_default=text("NOW()"))

