"""Application configuration loaded from environment variables."""
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    "mysql+pymysql://calluser:callpass@mysql:3306/callreports",
)
WATCHED_FOLDER: str = os.getenv("WATCHED_FOLDER", "./watched_folder")
POLL_INTERVAL_SECONDS: int = int(os.getenv("POLL_INTERVAL_SECONDS", "60"))
RETENTION_DAYS: int = int(os.getenv("RETENTION_DAYS", "365"))
OUTPUT_MODE: str = os.getenv("OUTPUT_MODE", "superset")
MAX_UPLOAD_BYTES: int = int(os.getenv("MAX_UPLOAD_BYTES", str(25 * 1024 * 1024)))
CORS_ORIGINS: list[str] = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "*").split(",")
    if origin.strip()
]

if not DATABASE_URL.startswith("mysql"):
    raise EnvironmentError(
        "DATABASE_URL must be a valid MySQL SQLAlchemy connection string. "
        f"Got: '{DATABASE_URL}'"
    )

if POLL_INTERVAL_SECONDS < 10:
    raise EnvironmentError("POLL_INTERVAL_SECONDS must be at least 10.")

if RETENTION_DAYS < 1:
    raise EnvironmentError("RETENTION_DAYS must be at least 1.")

if MAX_UPLOAD_BYTES < 1024:
    raise EnvironmentError("MAX_UPLOAD_BYTES must be at least 1024.")

# Power BI — read but not used in v1
POWERBI_TENANT_ID: str = os.getenv("POWERBI_TENANT_ID", "")
POWERBI_CLIENT_ID: str = os.getenv("POWERBI_CLIENT_ID", "")
POWERBI_CLIENT_SECRET: str = os.getenv("POWERBI_CLIENT_SECRET", "")
POWERBI_WORKSPACE_ID: str = os.getenv("POWERBI_WORKSPACE_ID", "")
POWERBI_DATASET_ID: str = os.getenv("POWERBI_DATASET_ID", "")
