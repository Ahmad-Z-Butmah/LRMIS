import os
from pymongo import MongoClient

MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "lrmis_db")

_client = MongoClient(MONGO_URL)
db = _client[DB_NAME]
