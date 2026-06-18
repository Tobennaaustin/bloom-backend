"""
Bloom Database — MongoDB Atlas connection
Set MONGO_URI in .env to your Atlas connection string
"""

from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
import os

_client = None
_db = None


def get_db():
    global _client, _db
    if _db is not None:
        return _db

    mongo_uri = os.getenv("MONGO_URI")

    try:
        _client = MongoClient(
            mongo_uri,
            serverSelectionTimeoutMS=8000,
            connectTimeoutMS=8000,
            socketTimeoutMS=20000,
        )
        _client.admin.command("ping")

        # Determine DB name from URI or default
        if "mongodb.net" in mongo_uri or "mongodb+srv" in mongo_uri:
            db_name = mongo_uri.split("/")[-1].split("?")[0] or "bloom_db"
            if not db_name:
                db_name = "bloom_db"
            _db = _client[db_name]
        else:
            _db = _client["bloom_db"]

        print(f"[Bloom DB] Connected to MongoDB — '{_db.name}'")
        _ensure_indexes()

    except (ConnectionFailure, ServerSelectionTimeoutError) as e:
        print(f"[Bloom DB] MongoDB connection failed: {e}")
        print("[Bloom DB] Falling back to demo mode")
        _db = None

    return _db


def _ensure_indexes():
    if _db is None:
        return
    try:
        _db["vendors"].create_index([("email", ASCENDING)], unique=True)
        _db["vendors"].create_index([("storeType", ASCENDING)])
        _db["vendors"].create_index([("createdAt", DESCENDING)])
        _db["budget_plans"].create_index([("vendorId", ASCENDING)])
        _db["budget_plans"].create_index([("createdAt", DESCENDING)])
    except Exception as e:
        print(f"[Bloom DB] Index warning: {e}")


def get_collection(name: str):
    db = get_db()
    if db is None:
        return None
    return db[name]


def is_connected() -> bool:
    return _db is not None
