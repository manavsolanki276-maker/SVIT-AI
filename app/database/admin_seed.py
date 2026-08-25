"""
app/database/admin_seed.py
Database schema migration and seed accounts for SVIT Admin RBAC system.
Supports both SQLite and MongoDB with idempotent operations and secure password hashing.
"""
import sqlite3
import os
import logging
from datetime import datetime
from typing import Dict, Any, List
from werkzeug.security import generate_password_hash

from app.auth.rbac import (
    ROLE_SUPER_ADMIN,
    ROLE_ACADEMIC_ADMIN,
    ROLE_ADMISSION_ADMIN,
    ROLE_NOTICE_ADMIN,
    ROLE_EVENT_ADMIN,
    ROLE_BUS_ADMIN,
    ROLE_LIBRARY_ADMIN,
    ROLE_CANTEEN_ADMIN,
    ROLE_SPORTS_ADMIN,
)

logger = logging.getLogger(__name__)

# Predefined standard admin seed accounts
DEFAULT_ADMIN_ACCOUNTS: List[Dict[str, Any]] = [
    {
        "admin_id": "ADM-0001",
        "username": "superadmin",
        "email": "superadmin@svit.ac.in",
        "password": "Admin@123",
        "role": ROLE_SUPER_ADMIN,
        "name": "Super Administrator",
        "department": "Executive Administration",
        "is_active": True,
    },
    {
        "admin_id": "ADM-0002",
        "username": "academic_admin",
        "email": "academic@svit.ac.in",
        "password": "Academic@123",
        "role": ROLE_ACADEMIC_ADMIN,
        "name": "Academic Administrator",
        "department": "Academic Cell",
        "is_active": True,
    },
    {
        "admin_id": "ADM-0003",
        "username": "admission_admin",
        "email": "admission@svit.ac.in",
        "password": "Admission@123",
        "role": ROLE_ADMISSION_ADMIN,
        "name": "Admission Incharge",
        "department": "Admission Cell",
        "is_active": True,
    },
    {
        "admin_id": "ADM-0004",
        "username": "notice_admin",
        "email": "notice@svit.ac.in",
        "password": "Notice@123",
        "role": ROLE_NOTICE_ADMIN,
        "name": "Notice & Announcements Admin",
        "department": "Public Relations",
        "is_active": True,
    },
    {
        "admin_id": "ADM-0005",
        "username": "event_admin",
        "email": "event@svit.ac.in",
        "password": "Event@123",
        "role": ROLE_EVENT_ADMIN,
        "name": "College Events Coordinator",
        "department": "Student Affairs",
        "is_active": True,
    },
    {
        "admin_id": "ADM-0006",
        "username": "bus_admin",
        "email": "bus@svit.ac.in",
        "password": "Bus@123",
        "role": ROLE_BUS_ADMIN,
        "name": "Transport Coordinator",
        "department": "Transportation Section",
        "is_active": True,
    },
    {
        "admin_id": "ADM-0007",
        "username": "library_admin",
        "email": "library@svit.ac.in",
        "password": "Library@123",
        "role": ROLE_LIBRARY_ADMIN,
        "name": "Chief Librarian",
        "department": "Central Library",
        "is_active": True,
    },
    {
        "admin_id": "ADM-0008",
        "username": "canteen_admin",
        "email": "canteen@svit.ac.in",
        "password": "Canteen@123",
        "role": ROLE_CANTEEN_ADMIN,
        "name": "Canteen Manager",
        "department": "Campus Amenities",
        "is_active": True,
    },
    {
        "admin_id": "ADM-0009",
        "username": "sports_admin",
        "email": "sports@svit.ac.in",
        "password": "Sports@123",
        "role": ROLE_SPORTS_ADMIN,
        "name": "Sports Officer",
        "department": "Physical Education & Sports",
        "is_active": True,
    },
    {
        "admin_id": "ADM-0010",
        "username": "disabled_admin",
        "email": "disabled@svit.ac.in",
        "password": "Disabled@123",
        "role": ROLE_ACADEMIC_ADMIN,
        "name": "Inactive Admin Account",
        "department": "Deactivated",
        "is_active": False,
    },
]


def migrate_sqlite_admin_columns(db_path: str = None):
    """Safely adds any missing columns to SQLite 'admins' table using engine connection."""
    from app.extensions import db
    from sqlalchemy import text, inspect

    try:
        engine = db.engine
        inspector = inspect(engine)
        if 'admins' not in inspector.get_table_names():
            return

        existing_cols = {col['name'] for col in inspector.get_columns('admins')}

        new_columns = [
            ("admin_id", "VARCHAR(64)"),
            ("name", "VARCHAR(100) DEFAULT 'Administrator'"),
            ("role", "VARCHAR(50) DEFAULT 'super_admin'"),
            ("department", "VARCHAR(100)"),
            ("is_active", "BOOLEAN DEFAULT 1"),
            ("created_at", "DATETIME"),
            ("updated_at", "DATETIME"),
            ("last_login", "DATETIME"),
        ]

        with engine.begin() as conn:
            for col_name, col_type in new_columns:
                if col_name not in existing_cols:
                    logger.info(f"[DB Migration] Adding missing column '{col_name}' to admins table...")
                    try:
                        conn.execute(text(f"ALTER TABLE admins ADD COLUMN {col_name} {col_type};"))
                    except Exception as col_err:
                        logger.warning(f"[DB Migration] Column '{col_name}' migration notice: {col_err}")
    except Exception as e:
        logger.warning(f"[DB Migration] Column inspection notice: {e}")


def seed_admin_accounts(app=None) -> Dict[str, int]:
    """
    Seeds all default admin accounts into SQLite and MongoDB if not present.
    Idempotent: updates existing accounts or creates missing accounts.
    """
    stats = {"sqlite_created": 0, "sqlite_updated": 0, "mongo_created": 0, "mongo_updated": 0}

    # 1. Migrate SQLite columns first
    from app.database.models.admin import Admin
    from app.extensions import db

    try:
        migrate_sqlite_admin_columns()
    except Exception as e:
        logger.warning(f"[Seed] Column check notice: {e}")

    # 2. Seed SQLite Admins
    try:
        for acc in DEFAULT_ADMIN_ACCOUNTS:
            uname = acc["username"]
            admin = Admin.query.filter(
                (Admin.username == uname) | (Admin.email == acc["email"])
            ).first()

            if not admin:
                admin = Admin(
                    admin_id=acc.get("admin_id"),
                    username=uname,
                    email=acc["email"],
                    name=acc.get("name", "Administrator"),
                    role=acc.get("role", ROLE_SUPER_ADMIN),
                    department=acc.get("department", ""),
                    is_active=acc.get("is_active", True),
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                admin.set_password(acc["password"])
                db.session.add(admin)
                stats["sqlite_created"] += 1
            else:
                # Update attributes while keeping password secure
                admin.name = acc.get("name", admin.name)
                admin.role = acc.get("role", admin.role)
                admin.department = acc.get("department", admin.department)
                admin.is_active = acc.get("is_active", admin.is_active)
                if not admin.admin_id:
                    admin.admin_id = acc.get("admin_id")
                # Refresh password hash if needed
                admin.set_password(acc["password"])
                admin.updated_at = datetime.utcnow()
                stats["sqlite_updated"] += 1

        db.session.commit()
    except Exception as e:
        try:
            db.session.rollback()
        except Exception:
            pass
        logger.warning(f"[Seed] SQLite admin seeding notice: {e}")

    # 3. Seed MongoDB Admins (if Mongo is connected)
    try:
        from app.database.mongodb import get_collection, is_mongodb_connected
        if is_mongodb_connected():
            coll = get_collection('admins')
            if coll is not None:
                for acc in DEFAULT_ADMIN_ACCOUNTS:
                    doc = dict(acc)
                    pwd = doc.pop("password")
                    doc["password_hash"] = generate_password_hash(pwd)
                    doc["updated_at"] = datetime.utcnow()

                    res = coll.update_one(
                        {"$or": [{"username": acc["username"]}, {"email": acc["email"]}]},
                        {"$set": doc, "$setOnInsert": {"created_at": datetime.utcnow()}},
                        upsert=True
                    )
                    if res.upserted_id:
                        stats["mongo_created"] += 1
                    else:
                        stats["mongo_updated"] += 1
    except Exception as e:
        logger.warning(f"[Seed] MongoDB admin seeding notice: {e}")

    return stats
