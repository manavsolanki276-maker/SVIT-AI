"""
app/database/mongodb.py
Centralized MongoDB Atlas Connection and Collection Access Module.
Designed for serverless execution with connection pooling, lazy client initialization,
and graceful fallback when MONGODB_URI is not set.
"""
import os
import re
import logging
from typing import Optional
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.collection import Collection

load_dotenv()

logger = logging.getLogger(__name__)

try:
    import certifi
    CA_FILE = certifi.where()
except Exception:
    CA_FILE = None

# Global singleton client and database instances
_mongo_client: Optional[MongoClient] = None
_mongo_db: Optional[Database] = None


_last_mongo_error: Optional[str] = None
_last_failed_time: float = 0.0


def get_last_error() -> Optional[str]:
    """Returns the sanitized last connection error message."""
    global _last_mongo_error
    return _last_mongo_error


import urllib.parse


def format_mongo_uri(raw_uri: str) -> str:
    """
    Safely sanitizes and URL-encodes raw username and password in a MongoDB URI
    to ensure compliance with RFC 3986 and prevent ConfigurationError.
    """
    if not raw_uri:
        return ''
    uri = raw_uri.strip().strip('\'"')
    for prefix in ('mongodb+srv://', 'mongodb://'):
        if uri.startswith(prefix):
            scheme = prefix
            rest = uri[len(prefix):]
            if '@' in rest:
                creds, host = rest.rsplit('@', 1)
                if ':' in creds:
                    u, p = creds.split(':', 1)
                    clean_u = urllib.parse.quote_plus(urllib.parse.unquote(u))
                    clean_p = urllib.parse.quote_plus(urllib.parse.unquote(p))
                    return f"{scheme}{clean_u}:{clean_p}@{host}"
                else:
                    clean_u = urllib.parse.quote_plus(urllib.parse.unquote(creds))
                    return f"{scheme}{clean_u}@{host}"
    return uri


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
    if uri:
        uri = format_mongo_uri(uri)
    return uri


def get_mongodb_client() -> Optional[MongoClient]:
    """
    Returns a pooled, reusable MongoClient singleton suitable for serverless functions.
    Reuses the existing connection across warm function invocations.
    """
    global _mongo_client, _last_mongo_error, _last_failed_time
    import time
    uri = get_mongodb_uri()

    if not uri:
        _last_mongo_error = "No MONGODB_URI or MONGO_URI environment variable found."
        return None

    if _mongo_client is not None:
        try:
            _mongo_client.admin.command('ping')
            _last_mongo_error = None
            return _mongo_client
        except Exception:
            _mongo_client = None

    # Do not hammer failing connection within 10 seconds in the same function invocation
    if (time.time() - _last_failed_time) < 10.0:
        return None

    client_kwargs = {
        "maxPoolSize": 5,
        "minPoolSize": 0,
        "maxIdleTimeMS": 30000,
        "serverSelectionTimeoutMS": 3000,
        "connectTimeoutMS": 3000,
        "socketTimeoutMS": 5000,
        "retryWrites": True,
        "appname": "SVIT-AI-Assistant"
    }

    if CA_FILE and os.path.exists(CA_FILE):
        client_kwargs["tlsCAFile"] = CA_FILE

    # Attempt 1: Standard connection with certifi CA bundle
    try:
        logger.info("[MongoDB] Initializing pooled MongoClient for serverless execution...")
        client = MongoClient(uri, **client_kwargs)
        client.admin.command('ping')
        _mongo_client = client
        _last_mongo_error = None
        logger.info("[MongoDB] Successfully connected to MongoDB Atlas.")
        return _mongo_client
    except Exception as e:
        safe_err = re.sub(r'mongodb(\+srv)?://[^@]+@', 'mongodb://***:***@', str(e))
        _last_mongo_error = f"Attempt 1 failed: {safe_err}"
        logger.warning(f"[MongoDB] Initial connection attempt failed: {safe_err}")

    # Attempt 2: Fallback with tlsAllowInvalidCertificates if environment certificate store fails
    try:
        logger.info("[MongoDB] Retrying connection with fallback TLS options...")
        fallback_kwargs = dict(client_kwargs)
        fallback_kwargs.pop("tlsCAFile", None)
        fallback_kwargs["tlsAllowInvalidCertificates"] = True
        client = MongoClient(uri, **fallback_kwargs)
        client.admin.command('ping')
        _mongo_client = client
        _last_mongo_error = None
        logger.info("[MongoDB] Connected to MongoDB Atlas with fallback TLS.")
        return _mongo_client
    except Exception as e:
        safe_err = re.sub(r'mongodb(\+srv)?://[^@]+@', 'mongodb://***:***@', str(e))
        _last_mongo_error = f"{_last_mongo_error} | Fallback failed: {safe_err}"
        logger.error(f"[MongoDB] All connection attempts failed: {safe_err}")
        _mongo_client = None
        _last_failed_time = time.time()
        return None


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
