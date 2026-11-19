import os
from pathlib import Path

DATA_DIR = Path(os.getenv("DATA_DIR", "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)
INGEST_TOKEN = os.getenv("INGEST_TOKEN", "")
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)

# Signal generation is deliberately disabled until Demo chart calibration is reviewed.
SIGNALS_ENABLED = os.getenv("SIGNALS_ENABLED", "false").strip().lower() in ("1", "true", "yes", "on")
