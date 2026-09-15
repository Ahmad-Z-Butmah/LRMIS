import os

from pymongo import MongoClient

try:
    import mongomock
except Exception:  # pragma: no cover - only needed in local dev fallback
    mongomock = None

MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "lrmis_db")


def _build_client():
    client = MongoClient(MONGO_URL, serverSelectionTimeoutMS=1500)
    try:
        client.admin.command("ping")
        return client
    except Exception:
        if mongomock is not None:
            return mongomock.MongoClient()
        return client


_client = _build_client()
db = _client[DB_NAME]
