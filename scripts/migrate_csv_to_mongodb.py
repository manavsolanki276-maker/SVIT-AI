"""
scripts/migrate_csv_to_mongodb.py
Production CSV & SQLite to MongoDB Atlas Migration Script for SVIT-AI.
Idempotent and safe to run multiple times without duplicating data.
Never deletes source CSV or SQLite database files.
"""
import os
import sys
import sqlite3
import pandas as pd
from datetime import datetime
from typing import Dict, Any, List

# Ensure utf-8 stdout
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Ensure project root is on sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

from app.database.mongodb import get_mongodb_db, is_mongodb_connected, get_mongodb_uri


def migrate_csv_files(db) -> Dict[str, Dict[str, int]]:
    """Migrates all CSV files in knowledge_base/ and subfolders to MongoDB collections."""
    kb_dir = os.path.join(PROJECT_ROOT, "knowledge_base")
    csv_files: List[str] = []

    for root, _, files in os.walk(kb_dir):
        for f in files:
            if f.lower().endswith(".csv"):
                csv_files.append(os.path.join(root, f))

    stats: Dict[str, Dict[str, int]] = {}
    print("\n========================================================")
    print(f"[PHASE 1] MIGRATING KNOWLEDGE BASE CSVs ({len(csv_files)} files)")
    print("========================================================")

    for file_path in sorted(csv_files):
        filename = os.path.basename(file_path)
        base_name = filename.replace(".csv", "").lower().replace(" ", "_")
        collection_name = "subjects" if base_name in ("subject", "subjects") else base_name
        coll = db[collection_name]

        try:
            df = pd.read_csv(file_path, sep=None, engine='python', dtype=str).fillna("")
            records = df.to_dict(orient="records")

            inserted = 0
            updated = 0
            errors = 0

            # Clean and normalize records
            for idx, raw_row in enumerate(records):
                try:
                    clean_row = {str(k).strip().lower(): str(v).strip() for k, v in raw_row.items()}
                    clean_row["_source_file"] = filename
                    clean_row["_row_number"] = idx + 1
                    clean_row["_migrated_at"] = datetime.utcnow()

                    # Deduplication key: build a signature from significant columns
                    sig_parts = [f"{k}={v}" for k, v in sorted(clean_row.items()) if not k.startswith("_") and v]
                    sig = "|".join(sig_parts) if sig_parts else f"row_{idx+1}"
                    clean_row["_record_signature"] = sig

                    res = coll.update_one(
                        {"_record_signature": sig},
                        {"$set": clean_row},
                        upsert=True
                    )
                    if res.upserted_id is not None:
                        inserted += 1
                    else:
                        updated += 1
                except Exception as row_err:
                    errors += 1

            stats[collection_name] = {"inserted": inserted, "updated": updated, "errors": errors, "total": len(records)}
            print(f"  * [{collection_name}] Source: {filename} -> {len(records)} rows ({inserted} new, {updated} updated, {errors} errors)")

        except Exception as file_err:
            print(f"  [ERROR] reading {filename}: {file_err}")
            stats[collection_name] = {"inserted": 0, "updated": 0, "errors": 1, "total": 0}

    return stats


def migrate_sqlite_data(db) -> Dict[str, Dict[str, int]]:
    """Migrates existing users, chat history, and messages from SQLite to MongoDB."""
    sqlite_paths = [
        os.path.join(PROJECT_ROOT, "app", "svit_assistant.db"),
        os.path.join(PROJECT_ROOT, "instance", "database.db"),
    ]

    sqlite_db_path = None
    for p in sqlite_paths:
        if os.path.exists(p) and os.path.getsize(p) > 0:
            sqlite_db_path = p
            break

    stats: Dict[str, Dict[str, int]] = {}
    print("\n========================================================")
    print("[PHASE 2] MIGRATING SQLITE PERSISTENT APPLICATION DATA")
    print("========================================================")

    if not sqlite_db_path:
        print("  [NOTE] No local SQLite database file found with data. Skipping SQLite migration.")
        return stats

    print(f"  [SOURCE] Reading from SQLite database: {sqlite_db_path}")

    conn = sqlite3.connect(sqlite_db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 1. Migrate Students
    try:
        cursor.execute("SELECT * FROM students")
        rows = cursor.fetchall()
        coll = db["students"]
        ins, upd, err = 0, 0, 0
        for r in rows:
            try:
                row_dict = dict(r)
                row_dict["is_profile_complete"] = bool(row_dict.get("is_profile_complete", False))
                row_dict["is_profile_completed"] = row_dict["is_profile_complete"]
                enroll = row_dict.get("enrollment_no", "").strip()
                if not enroll:
                    continue

                res = coll.update_one(
                    {"enrollment_no": enroll},
                    {"$set": row_dict},
                    upsert=True
                )
                if res.upserted_id is not None:
                    ins += 1
                else:
                    upd += 1
            except Exception:
                err += 1

        stats["students"] = {"inserted": ins, "updated": upd, "errors": err, "total": len(rows)}
        print(f"  * [students] {len(rows)} records ({ins} new, {upd} updated, {err} errors)")
    except Exception as e:
        print(f"  [NOTE] students table: {e}")

    # 2. Migrate Admins
    try:
        cursor.execute("SELECT * FROM admins")
        rows = cursor.fetchall()
        coll = db["admins"]
        ins, upd, err = 0, 0, 0
        for r in rows:
            try:
                row_dict = dict(r)
                uname = row_dict.get("username", "").strip()
                if not uname:
                    continue
                res = coll.update_one(
                    {"username": uname},
                    {"$set": row_dict},
                    upsert=True
                )
                if res.upserted_id is not None:
                    ins += 1
                else:
                    upd += 1
            except Exception:
                err += 1

        stats["admins"] = {"inserted": ins, "updated": upd, "errors": err, "total": len(rows)}
        print(f"  * [admins] {len(rows)} records ({ins} new, {upd} updated, {err} errors)")
    except Exception as e:
        pass

    # 3. Migrate Chat Conversations
    try:
        cursor.execute("SELECT * FROM chat_conversations")
        rows = cursor.fetchall()
        coll = db["chat_conversations"]
        ins, upd, err = 0, 0, 0
        for r in rows:
            try:
                row_dict = dict(r)
                conv_id = str(row_dict.get("id"))
                row_dict["is_pinned"] = bool(row_dict.get("is_pinned", False))
                res = coll.update_one(
                    {"id": conv_id},
                    {"$set": row_dict},
                    upsert=True
                )
                if res.upserted_id is not None:
                    ins += 1
                else:
                    upd += 1
            except Exception:
                err += 1

        stats["chat_conversations"] = {"inserted": ins, "updated": upd, "errors": err, "total": len(rows)}
        print(f"  * [chat_conversations] {len(rows)} records ({ins} new, {upd} updated, {err} errors)")
    except Exception as e:
        print(f"  [NOTE] chat_conversations table: {e}")

    # 4. Migrate Chat Messages
    try:
        cursor.execute("SELECT * FROM chat_messages")
        rows = cursor.fetchall()
        coll = db["chat_messages"]
        ins, upd, err = 0, 0, 0
        for r in rows:
            try:
                row_dict = dict(r)
                msg_id = row_dict.get("id")
                res = coll.update_one(
                    {"id": msg_id, "conversation_id": row_dict.get("conversation_id")},
                    {"$set": row_dict},
                    upsert=True
                )
                if res.upserted_id is not None:
                    ins += 1
                else:
                    upd += 1
            except Exception:
                err += 1

        stats["chat_messages"] = {"inserted": ins, "updated": upd, "errors": err, "total": len(rows)}
        print(f"  * [chat_messages] {len(rows)} records ({ins} new, {upd} updated, {err} errors)")
    except Exception as e:
        print(f"  [NOTE] chat_messages table: {e}")

    # 5. Migrate Chat Feedbacks
    try:
        cursor.execute("SELECT * FROM chat_feedbacks")
        rows = cursor.fetchall()
        coll = db["chat_feedbacks"]
        ins, upd, err = 0, 0, 0
        for r in rows:
            try:
                row_dict = dict(r)
                fb_id = row_dict.get("id")
                res = coll.update_one(
                    {"id": fb_id},
                    {"$set": row_dict},
                    upsert=True
                )
                if res.upserted_id is not None:
                    ins += 1
                else:
                    upd += 1
            except Exception:
                err += 1

        stats["chat_feedbacks"] = {"inserted": ins, "updated": upd, "errors": err, "total": len(rows)}
        print(f"  * [chat_feedbacks] {len(rows)} records ({ins} new, {upd} updated, {err} errors)")
    except Exception as e:
        pass

    conn.close()
    return stats


def main():
    print("========================================================")
    print("SVIT-AI MONGODB ATLAS MIGRATION RUNNER")
    print("========================================================")

    uri = get_mongodb_uri()
    if not uri:
        print("\n[NOTE] MONGODB_URI environment variable is not configured in local environment.")
        print("To run migration to your MongoDB Atlas cluster, set MONGODB_URI in .env or as environment variable.")
        print("Example: MONGODB_URI=mongodb+srv://<username>:<password>@cluster0.xxxxx.mongodb.net/svit_ai?retryWrites=true&w=majority")
        return False

    db = get_mongodb_db()
    if db is None or not is_mongodb_connected():
        print("\n[ERROR] Unable to connect to MongoDB Atlas.")
        print("Please check network connectivity, credentials, and Atlas IP Access List.")
        return False

    print(f"[CONNECTED] Successfully connected to MongoDB database: {db.name}\n")

    csv_stats = migrate_csv_files(db)
    sqlite_stats = migrate_sqlite_data(db)

    print("\n========================================================")
    print("MIGRATION COMPLETE SUMMARY")
    print("========================================================")
    total_docs = 0
    for coll_name, s in {**csv_stats, **sqlite_stats}.items():
        count = db[coll_name].count_documents({})
        total_docs += count
        print(f"  Collection '{coll_name}': {count} total documents in MongoDB Atlas")

    print(f"\nGrand Total: {total_docs} documents across {len(csv_stats) + len(sqlite_stats)} collections in MongoDB Atlas.")
    print("All source CSV files and SQLite databases preserved unchanged.")
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
