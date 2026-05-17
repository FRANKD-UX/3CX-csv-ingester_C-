from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import CORS_ORIGINS
from scheduler import start_scheduler
from database import engine, get_db, Base, verify_connection

_scheduler = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _scheduler
    verify_connection()
    Base.metadata.create_all(bind=engine)
    _scheduler = start_scheduler()
    yield
    if _scheduler:
        _scheduler.shutdown(wait=False)


app = FastAPI(title="Call Dashboard Reporter API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/v1/health")
def health():
    return {"status": "ok"}

