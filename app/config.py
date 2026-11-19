import os
from pathlib import Path

DATA_DIR = Path(os.getenv("DATA_DIR", "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)
INGEST_TOKEN = os.getenv("INGEST_TOKEN", "")
