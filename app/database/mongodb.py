"""
app/database/mongodb.py
Centralized MongoDB Atlas Connection and Collection Access Module.
Designed for serverless execution with connection pooling, lazy client initialization,
and graceful fallback when MONGODB_URI is not set.
"""
import os
import logging
from typing import Optional
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.collection import Collection

load_dotenv()

logger = logging.getLogger(__name__)

# Global singleton client and database instances
_mongo_client: Optional[MongoClient] = None
_mongo_db: Optional[Database] = None


def get_mongodb_uri() -> str:
    """Retrieves MongoDB connection URI from environment variables."""
    uri = (
        os.environ.get('MONGODB_URI', '').strip() or
        os.environ.get('MONGO_URI', '').strip()
    )
    if not uri:
        db_url = os.environ.get('DATABASE_URL', '').strip()
        if db_url.startswith(('mongodb://', 'mongodb+srv://')):
            uri = db_url
    return uri


def get_mongodb_client() -> Optional[MongoClient]:
    """
    Returns a pooled, reusable MongoClient singleton suitable for serverless functions.
    Reuses the existing connection across warm function invocations.
    """
    global _mongo_client
    uri = get_mongodb_uri()

    if not uri:
        return None

    if _mongo_client is None:
        try:
            logger.info("[MongoDB] Initializing pooled MongoClient for serverless execution...")
            _mongo_client = MongoClient(
                uri,
                maxPoolSize=10,
                minPoolSize=0,
                maxIdleTimeMS=30000,
                serverSelectionTimeoutMS=4000,
                connectTimeoutMS=4000,
                socketTimeoutMS=10000,
                retryWrites=True,
                appname="SVIT-AI-Assistant"
            )
            # Quick ping to verify connectivity
            _mongo_client.admin.command('ping')
            logger.info("[MongoDB] Successfully connected to MongoDB Atlas.")
        except Exception as e:
            logger.warning(f"[MongoDB] Connection failed: {e}")
            _mongo_client = None
            return None

    return _mongo_client


def get_mongodb_db(db_name: str = "svit_ai") -> Optional[Database]:
    """Returns the application MongoDB database instance."""
    global _mongo_db
    if _mongo_db is not None:
        return _mongo_db

    client = get_mongodb_client()
    if client is not None:
        try:
            default_db = client.get_default_database()
            if default_db is not None and default_db.name not in ("admin", "test", "local"):
                _mongo_db = default_db
                return _mongo_db
        except Exception:
            pass

        _mongo_db = client[db_name]
        return _mongo_db

    return None


def get_collection(collection_name: str) -> Optional[Collection]:
    """Helper to get a specific MongoDB collection."""
    db = get_mongodb_db()
    if db is not None:
        return db[collection_name]
    return None


def is_mongodb_connected() -> bool:
    """Checks whether MongoDB is currently reachable."""
    client = get_mongodb_client()
    if client is None:
        return False
    try:
        client.admin.command('ping')
        return True
    except Exception:
        return False
