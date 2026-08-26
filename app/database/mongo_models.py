"""
app/database/mongo_models.py
MongoDB document models and database access layer for SVIT AI Assistant.
Provides seamless user authentication, chat history, settings, notifications,
and academic dataset management via MongoDB Atlas with connection pooling.
"""
import re
import uuid
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Set
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app.database.mongodb import get_collection


# =========================================================================
# 1. USER & AUTH MODELS (FLASK-LOGIN COMPATIBLE)
# =========================================================================

class MongoStudent(UserMixin):
    """Flask-Login compatible Student user model backed by MongoDB."""
    def __init__(self, doc: Dict[str, Any]):
        self._doc = doc
        self.id = doc.get('id') or str(doc.get('_id', ''))
        self.enrollment_no = doc.get('enrollment_no', '')
        self.email = doc.get('email', '')
        self.password_hash = doc.get('password_hash', '')
        self.full_name = doc.get('full_name') or doc.get('name', 'Student')
        self.name = self.full_name
        self.program = doc.get('program', 'BE')
        self.department = doc.get('department', 'Computer Engineering')
        self.semester = doc.get('semester', 3)
        self.division = doc.get('division', 'A')
        self.batch = doc.get('batch', 'A1')
        self.phone = doc.get('phone', '')
        self.gender = doc.get('gender', '')
        self.dob = doc.get('dob', '')
        self.address = doc.get('address', '')
        self.is_profile_complete = bool(doc.get('is_profile_complete', doc.get('is_profile_completed', False)))
        self.is_profile_completed = self.is_profile_complete

        # Approval workflow fields (defaulting to 'active' for existing students)
        self.status = doc.get('status', 'active')
        self.request_id = doc.get('request_id', '')
        self.approved_by = doc.get('approved_by')
        self.approved_at = doc.get('approved_at')
        self.rejected_by = doc.get('rejected_by')
        self.rejected_at = doc.get('rejected_at')
        self.rejection_reason = doc.get('rejection_reason')
        self.created_at = doc.get('created_at')
        self.updated_at = doc.get('updated_at')

    def get_id(self) -> str:
        return f"student_{self.id}"

    @property
    def is_admin(self) -> bool:
        return False

    def check_password(self, password: str) -> bool:
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)
        self._doc['password_hash'] = self.password_hash

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "enrollment_no": self.enrollment_no,
            "email": self.email,
            "full_name": self.full_name,
            "name": self.name,
            "program": self.program,
            "department": self.department,
            "semester": self.semester,
            "division": self.division,
            "batch": self.batch,
            "phone": self.phone,
            "gender": self.gender,
            "dob": self.dob,
            "address": self.address,
            "is_profile_complete": self.is_profile_complete,
            "is_profile_completed": self.is_profile_completed,
            "status": self.status,
            "request_id": self.request_id,
            "approved_by": self.approved_by,
            "approved_at": self.approved_at.isoformat() if hasattr(self.approved_at, 'isoformat') else str(self.approved_at) if self.approved_at else None,
            "rejected_by": self.rejected_by,
            "rejected_at": self.rejected_at.isoformat() if hasattr(self.rejected_at, 'isoformat') else str(self.rejected_at) if self.rejected_at else None,
            "rejection_reason": self.rejection_reason,
            "created_at": self.created_at.isoformat() if hasattr(self.created_at, 'isoformat') else str(self.created_at) if self.created_at else None,
        }

    @classmethod
    def get_by_id(cls, user_id: Any) -> Optional['MongoStudent']:
        coll = get_collection('students')
        if coll is None:
            return None
        try:
            # Try integer id, string id, or enrollment_no
            query = {"$or": [{"id": user_id}, {"id": int(user_id) if str(user_id).isdigit() else -1}, {"enrollment_no": str(user_id)}]}
            doc = coll.find_one(query)
            if doc:
                return cls(doc)
        except Exception:
            pass
        return None

    @classmethod
    def find_by_identifier(cls, identifier: str) -> Optional['MongoStudent']:
        coll = get_collection('students')
        if coll is None or not identifier:
            return None
        ident = identifier.strip()
        doc = coll.find_one({
            "$or": [
                {"email": ident},
                {"enrollment_no": ident},
                {"enrollment_number": ident}
            ]
        })
        if doc:
            return cls(doc)
        return None

    @classmethod
    def save_or_update(cls, data: Dict[str, Any]) -> Optional['MongoStudent']:
        coll = get_collection('students')
        if coll is None:
            return None
        enrollment = data.get('enrollment_no', '').strip()
        email = data.get('email', '').strip()
        
        query = {}
        if enrollment:
            query['enrollment_no'] = enrollment
        elif email:
            query['email'] = email
        else:
            query['id'] = data.get('id')

        data['updated_at'] = datetime.utcnow()
        if 'created_at' not in data:
            data['created_at'] = datetime.utcnow()

        coll.update_one(query, {"$set": data}, upsert=True)
        doc = coll.find_one(query)
        return cls(doc) if doc else None


class MongoAdmin(UserMixin):
    """Flask-Login compatible Admin user model backed by MongoDB with full RBAC."""
    def __init__(self, doc: Dict[str, Any]):
        from app.auth.rbac import (
            ROLE_SUPER_ADMIN,
            ROLE_DISPLAY_NAMES,
            normalize_role,
            get_role_permissions,
            has_permission as rbac_has_permission,
            has_role as rbac_has_role,
        )
        self._doc = doc
        self.id = str(doc.get('id') or doc.get('_id', ''))
        self.admin_id = doc.get('admin_id') or doc.get('id') or self.id
        self.name = doc.get('name') or doc.get('full_name') or 'Administrator'
        self.full_name = self.name
        self.username = str(doc.get('username', '')).strip()
        self.email = str(doc.get('email', '')).strip().lower()
        self.password_hash = str(doc.get('password_hash', ''))
        self.role = normalize_role(doc.get('role', ROLE_SUPER_ADMIN))
        self.department = doc.get('department', '')
        self._is_active = bool(doc.get('is_active', True))
        self.created_at = doc.get('created_at')
        self.updated_at = doc.get('updated_at')
        self.last_login = doc.get('last_login')

    def get_id(self) -> str:
        return f"admin_{self.id}"

    @property
    def is_active(self) -> bool:
        return self._is_active

    @property
    def is_admin(self) -> bool:
        return True

    @property
    def role_display(self) -> str:
        from app.auth.rbac import ROLE_DISPLAY_NAMES, normalize_role
        norm = normalize_role(self.role)
        return ROLE_DISPLAY_NAMES.get(norm, norm.replace('_', ' ').title())

    @property
    def permissions(self) -> Set[str]:
        from app.auth.rbac import get_role_permissions
        return get_role_permissions(self.role)

    def check_password(self, password: str) -> bool:
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)
        self._doc['password_hash'] = self.password_hash

    def has_permission(self, permission: str) -> bool:
        from app.auth.rbac import has_permission as rbac_has_permission
        return rbac_has_permission(self, permission)

    def has_role(self, *roles: str) -> bool:
        from app.auth.rbac import has_role as rbac_has_role
        return rbac_has_role(self, *roles)

    def update_last_login(self):
        coll = get_collection('admins')
        now = datetime.utcnow()
        self.last_login = now
        self.updated_at = now
        if coll is not None:
            from bson import ObjectId
            try:
                coll.update_one(
                    {"$or": [{"id": self.id}, {"_id": ObjectId(self.id) if ObjectId.is_valid(self.id) else None}, {"username": self.username}]},
                    {"$set": {"last_login": now, "updated_at": now}}
                )
            except Exception:
                pass

    def to_dict(self) -> Dict[str, Any]:
        """CRITICAL: Never exposes password or password_hash."""
        return {
            "id": self.id,
            "admin_id": self.admin_id,
            "name": self.name,
            "full_name": self.full_name,
            "username": self.username,
            "email": self.email,
            "role": self.role,
            "role_display": self.role_display,
            "department": self.department,
            "is_active": self.is_active,
            "permissions": sorted(list(self.permissions)),
            "created_at": self.created_at.isoformat() if hasattr(self.created_at, 'isoformat') else str(self.created_at) if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if hasattr(self.updated_at, 'isoformat') else str(self.updated_at) if self.updated_at else None,
            "last_login": self.last_login.isoformat() if hasattr(self.last_login, 'isoformat') else str(self.last_login) if self.last_login else None,
        }

    @classmethod
    def get_by_id(cls, user_id: Any) -> Optional['MongoAdmin']:
        coll = get_collection('admins')
        if coll is None:
            return None
        try:
            from bson import ObjectId
            query = {
                "$or": [
                    {"id": user_id},
                    {"id": int(user_id) if str(user_id).isdigit() else -1},
                    {"admin_id": str(user_id)},
                    {"username": str(user_id)},
                    {"_id": ObjectId(str(user_id)) if ObjectId.is_valid(str(user_id)) else None}
                ]
            }
            doc = coll.find_one(query)
            if doc:
                return cls(doc)
        except Exception:
            pass
        return None

    @classmethod
    def find_by_identifier(cls, identifier: str) -> Optional['MongoAdmin']:
        coll = get_collection('admins')
        if coll is None or not identifier:
            return None
        ident = identifier.strip()
        ident_lower = ident.lower()
        doc = coll.find_one({
            "$or": [
                {"username": {"$regex": f"^{re.escape(ident)}$", "$options": "i"}},
                {"email": ident_lower}
            ]
        }) if 're' in globals() else coll.find_one({
            "$or": [
                {"username": ident},
                {"email": ident_lower},
                {"email": ident}
            ]
        })
        if doc:
            return cls(doc)
        return None

    @classmethod
    def save_or_update(cls, data: Dict[str, Any]) -> Optional['MongoAdmin']:
        coll = get_collection('admins')
        if coll is None:
            return None

        uname = str(data.get('username', '')).strip()
        email = str(data.get('email', '')).strip().lower()

        query = {}
        if uname:
            query['username'] = uname
        elif email:
            query['email'] = email
        else:
            query['id'] = data.get('id')

        clean_data = dict(data)
        clean_data['updated_at'] = datetime.utcnow()
        if 'created_at' not in clean_data:
            clean_data['created_at'] = datetime.utcnow()

        if 'password' in clean_data:
            clean_data['password_hash'] = generate_password_hash(clean_data.pop('password'))

        coll.update_one(query, {"$set": clean_data}, upsert=True)
        doc = coll.find_one(query)
        return cls(doc) if doc else None

    @classmethod
    def get_all(cls) -> List['MongoAdmin']:
        coll = get_collection('admins')
        if coll is None:
            return []
        return [cls(doc) for doc in coll.find().sort("created_at", -1)]


# =========================================================================
# 2. CHAT & CONVERSATION DATA SERVICES
# =========================================================================

class MongoChatService:
    """MongoDB service for chat history, messages, bookmarks, and feedback."""

    @staticmethod
    def get_conversations(student_id: Any, search_query: str = "") -> Dict[str, List[Dict[str, Any]]]:
        coll = get_collection('chat_conversations')
        saved_coll = get_collection('saved_conversations')
        
        grouped = {
            "today": [],
            "yesterday": [],
            "last_7_days": [],
            "last_month": [],
            "older": []
        }

        if coll is None:
            return grouped

        query: Dict[str, Any] = {"student_id": student_id}
        if search_query:
            query["title"] = {"$regex": search_query.strip(), "$options": "i"}

        saved_ids = set()
        if saved_coll is not None:
            try:
                for s in saved_coll.find({"student_id": student_id}):
                    saved_ids.add(s.get("conversation_id"))
            except Exception:
                pass

        now = datetime.utcnow()
        today_start = datetime(now.year, now.month, now.day)
        yesterday_start = today_start - timedelta(days=1)
        week_start = today_start - timedelta(days=7)
        month_start = today_start - timedelta(days=30)

        cursor = coll.find(query).sort([("is_pinned", -1), ("updated_at", -1)])
        for doc in cursor:
            conv_id = str(doc.get("id") or doc.get("_id"))
            updated = doc.get("updated_at") or doc.get("created_at") or now
            if isinstance(updated, str):
                try:
                    updated = datetime.fromisoformat(updated)
                except Exception:
                    updated = now

            item = {
                "id": conv_id,
                "student_id": doc.get("student_id"),
                "title": doc.get("title", "New Conversation"),
                "is_pinned": bool(doc.get("is_pinned", False)),
                "is_saved": conv_id in saved_ids,
                "created_at": doc.get("created_at", now).isoformat() if hasattr(doc.get("created_at"), "isoformat") else str(doc.get("created_at")),
                "updated_at": updated.isoformat() if hasattr(updated, "isoformat") else str(updated)
            }

            if updated >= today_start:
                grouped["today"].append(item)
            elif updated >= yesterday_start:
                grouped["yesterday"].append(item)
            elif updated >= week_start:
                grouped["last_7_days"].append(item)
            elif updated >= month_start:
                grouped["last_month"].append(item)
            else:
                grouped["older"].append(item)

        return grouped

    @staticmethod
    def get_saved_conversations(student_id: Any, search_query: str = "") -> List[Dict[str, Any]]:
        saved_coll = get_collection('saved_conversations')
        conv_coll = get_collection('chat_conversations')
        if saved_coll is None or conv_coll is None:
            return []

        saved_docs = list(saved_coll.find({"student_id": student_id}).sort("saved_at", -1))
        conv_ids = [s.get("conversation_id") for s in saved_docs]

        if not conv_ids:
            return []

        query: Dict[str, Any] = {"id": {"$in": conv_ids}}
        if search_query:
            query["title"] = {"$regex": search_query.strip(), "$options": "i"}

        conversations = {c.get("id"): c for c in conv_coll.find(query)}
        results = []
        for s in saved_docs:
            cid = s.get("conversation_id")
            if cid in conversations:
                c = conversations[cid]
                results.append({
                    "id": cid,
                    "title": c.get("title", "New Conversation"),
                    "is_saved": True,
                    "is_pinned": bool(c.get("is_pinned", False)),
                    "updated_at": str(c.get("updated_at", ""))
                })
        return results

    @staticmethod
    def get_conversation_thread(conversation_id: str, student_id: Any = None) -> Optional[Dict[str, Any]]:
        conv_coll = get_collection('chat_conversations')
        msg_coll = get_collection('chat_messages')
        if conv_coll is None:
            return None

        query = {"id": conversation_id}
        if student_id is not None:
            query["student_id"] = student_id

        conv = conv_coll.find_one(query)
        if not conv:
            return None

        messages = []
        if msg_coll is not None:
            cursor = msg_coll.find({"conversation_id": conversation_id}).sort("created_at", 1)
            for m in cursor:
                sources = m.get("sources", [])
                if isinstance(sources, str):
                    try:
                        import json
                        sources = json.loads(sources)
                    except Exception:
                        sources = [sources]

                messages.append({
                    "id": m.get("id") or str(m.get("_id")),
                    "conversation_id": conversation_id,
                    "sender": m.get("sender", "user"),
                    "content": m.get("content", ""),
                    "text": m.get("content", ""),
                    "image_path": m.get("image_path"),
                    "sources": sources,
                    "feedback": m.get("feedback"),
                    "created_at": str(m.get("created_at", ""))
                })

        return {
            "conversation": {
                "id": conv.get("id"),
                "title": conv.get("title", "New Conversation"),
                "is_pinned": bool(conv.get("is_pinned", False)),
                "created_at": str(conv.get("created_at", "")),
                "updated_at": str(conv.get("updated_at", ""))
            },
            "messages": messages
        }

    @staticmethod
    def save_or_update_conversation(conversation_id: str, student_id: Any, title: str) -> str:
        coll = get_collection('chat_conversations')
        now = datetime.utcnow()
        if coll is not None:
            coll.update_one(
                {"id": conversation_id},
                {
                    "$set": {
                        "id": conversation_id,
                        "student_id": student_id,
                        "title": title,
                        "updated_at": now
                    },
                    "$setOnInsert": {
                        "created_at": now,
                        "is_pinned": False
                    }
                },
                upsert=True
            )
        return conversation_id

    @staticmethod
    def save_message(conversation_id: str, sender: str, content: str, image_path: str = None, sources: List[str] = None) -> Any:
        coll = get_collection('chat_messages')
        conv_coll = get_collection('chat_conversations')
        now = datetime.utcnow()
        msg_id = None
        if coll is not None:
            res = coll.insert_one({
                "conversation_id": conversation_id,
                "sender": sender,
                "content": content,
                "image_path": image_path,
                "sources": sources or [],
                "feedback": None,
                "created_at": now
            })
            msg_id = str(res.inserted_id)

        if conv_coll is not None:
            conv_coll.update_one({"id": conversation_id}, {"$set": {"updated_at": now}})

        return msg_id

    @staticmethod
    def toggle_pin(conversation_id: str, student_id: Any) -> Optional[bool]:
        coll = get_collection('chat_conversations')
        if coll is None:
            return None
        conv = coll.find_one({"id": conversation_id, "student_id": student_id})
        if not conv:
            return None
        new_state = not bool(conv.get("is_pinned", False))
        coll.update_one({"id": conversation_id}, {"$set": {"is_pinned": new_state}})
        return new_state

    @staticmethod
    def toggle_save(conversation_id: str, student_id: Any) -> bool:
        saved_coll = get_collection('saved_conversations')
        if saved_coll is None:
            return False
        existing = saved_coll.find_one({"conversation_id": conversation_id, "student_id": student_id})
        if existing:
            saved_coll.delete_one({"conversation_id": conversation_id, "student_id": student_id})
            return False
        else:
            saved_coll.insert_one({
                "conversation_id": conversation_id,
                "student_id": student_id,
                "saved_at": datetime.utcnow()
            })
            return True

    @staticmethod
    def rename_conversation(conversation_id: str, student_id: Any, new_title: str) -> bool:
        coll = get_collection('chat_conversations')
        if coll is None:
            return False
        res = coll.update_one(
            {"id": conversation_id, "student_id": student_id},
            {"$set": {"title": new_title, "updated_at": datetime.utcnow()}}
        )
        return res.modified_count > 0

    @staticmethod
    def delete_conversation(conversation_id: str, student_id: Any) -> bool:
        conv_coll = get_collection('chat_conversations')
        msg_coll = get_collection('chat_messages')
        saved_coll = get_collection('saved_conversations')
        if conv_coll is not None:
            conv_coll.delete_one({"id": conversation_id, "student_id": student_id})
        if msg_coll is not None:
            msg_coll.delete_many({"conversation_id": conversation_id})
        if saved_coll is not None:
            saved_coll.delete_many({"conversation_id": conversation_id})
        return True

    @staticmethod
    def clear_history_range(student_id: Any, range_type: str = 'all') -> int:
        conv_coll = get_collection('chat_conversations')
        msg_coll = get_collection('chat_messages')
        saved_coll = get_collection('saved_conversations')
        if conv_coll is None:
            return 0

        now = datetime.utcnow()
        query: Dict[str, Any] = {"student_id": student_id}

        if range_type == '1hour':
            query["updated_at"] = {"$gte": now - timedelta(hours=1)}
        elif range_type == '5hours':
            query["updated_at"] = {"$gte": now - timedelta(hours=5)}
        elif range_type == 'today':
            query["updated_at"] = {"$gte": datetime(now.year, now.month, now.day)}
        elif range_type == '24hours':
            query["updated_at"] = {"$gte": now - timedelta(hours=24)}
        elif range_type == '7days':
            query["updated_at"] = {"$gte": now - timedelta(days=7)}

        matching_convs = list(conv_coll.find(query, {"id": 1}))
        matching_ids = [c["id"] for c in matching_convs if "id" in c]

        if matching_ids:
            conv_coll.delete_many({"id": {"$in": matching_ids}})
            if msg_coll is not None:
                msg_coll.delete_many({"conversation_id": {"$in": matching_ids}})
            if saved_coll is not None:
                saved_coll.delete_many({"conversation_id": {"$in": matching_ids}})

        return len(matching_ids)

    @staticmethod
    def save_feedback(conversation_id: str, message_id: Any, student_id: Any, rating: str, query_text: str = "", response_text: str = "", comment: str = "") -> Optional[str]:
        fb_coll = get_collection('chat_feedbacks')
        msg_coll = get_collection('chat_messages')

        if msg_coll is not None and conversation_id and response_text:
            try:
                msg_coll.update_one(
                    {"conversation_id": conversation_id, "sender": "assistant"},
                    {"$set": {"feedback": rating}}
                )
            except Exception:
                pass

        if fb_coll is not None:
            res = fb_coll.insert_one({
                "conversation_id": conversation_id,
                "message_id": message_id,
                "student_id": student_id,
                "rating": rating,
                "query_text": query_text,
                "response_text": response_text,
                "comment": comment,
                "created_at": datetime.utcnow()
            })
            return str(res.inserted_id)

        return None


# =========================================================================
# 3. SETTINGS & NOTIFICATIONS SERVICES
# =========================================================================

class MongoUserSettingsService:
    @staticmethod
    def get_settings(user_id: Any) -> Dict[str, Any]:
        coll = get_collection('user_settings')
        if coll is not None:
            doc = coll.find_one({"user_id": user_id})
            if doc:
                return {
                    "id": str(doc.get("_id")),
                    "user_id": user_id,
                    "theme": doc.get("theme", "dark"),
                    "notifications_enabled": doc.get("notifications_enabled", True),
                    "email_alerts": doc.get("email_alerts", False),
                    "language": doc.get("language", "en"),
                    "font_size": doc.get("font_size", "medium"),
                    "voice_output": doc.get("voice_output", False),
                    "auto_read_response": doc.get("auto_read_response", False),
                }
        return {
            "user_id": user_id,
            "theme": "dark",
            "notifications_enabled": True,
            "email_alerts": False,
            "language": "en",
            "font_size": "medium",
            "voice_output": False,
            "auto_read_response": False,
        }

    @staticmethod
    def save_settings(user_id: Any, data: Dict[str, Any]) -> Dict[str, Any]:
        coll = get_collection('user_settings')
        if coll is not None:
            update_fields = {k: v for k, v in data.items() if k not in ('_id', 'id')}
            update_fields["updated_at"] = datetime.utcnow()
            coll.update_one(
                {"user_id": user_id},
                {"$set": update_fields, "$setOnInsert": {"user_id": user_id}},
                upsert=True
            )
        return MongoUserSettingsService.get_settings(user_id)


class MongoNotificationService:
    @staticmethod
    def create_notification(user_id: Any, title: str, message: str, category: str = "general", data: Optional[Dict[str, Any]] = None, is_admin: bool = False) -> Optional[str]:
        coll = get_collection('notifications')
        if coll is None:
            return None
        doc = {
            "user_id": str(user_id),
            "title": title,
            "message": message,
            "category": category,
            "data": data or {},
            "is_admin": is_admin,
            "is_read": False,
            "created_at": datetime.utcnow()
        }
        res = coll.insert_one(doc)
        return str(res.inserted_id)

    @staticmethod
    def notify_admins(title: str, message: str, category: str = "registration", data: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """Creates a broadcast/admin notification for pending registrations or alerts."""
        return MongoNotificationService.create_notification(
            user_id="admin",
            title=title,
            message=message,
            category=category,
            data=data,
            is_admin=True
        )

    @staticmethod
    def notify_student(student_id: Any, title: str, message: str, category: str = "registration", data: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """Creates a targeted notification for a student."""
        return MongoNotificationService.create_notification(
            user_id=str(student_id),
            title=title,
            message=message,
            category=category,
            data=data,
            is_admin=False
        )

    @staticmethod
    def get_notifications(user_id: Any, limit: int = 30) -> Dict[str, Any]:
        coll = get_collection('notifications')
        if coll is None:
            return {"status": "success", "unread_count": 0, "notifications": []}

        uid_str = str(user_id)
        # Also support numeric / enrollment ID variants
        query = {"$or": [{"user_id": uid_str}, {"user_id": user_id}]}
        cursor = coll.find(query).sort("created_at", -1).limit(limit)
        notifs = []
        unread = 0
        for doc in cursor:
            is_read = bool(doc.get("is_read", False))
            if not is_read:
                unread += 1
            notifs.append({
                "id": str(doc.get("_id")),
                "user_id": str(user_id),
                "title": doc.get("title", ""),
                "message": doc.get("message", ""),
                "category": doc.get("category", "general"),
                "data": doc.get("data", {}),
                "is_read": is_read,
                "created_at": doc.get("created_at").isoformat() if hasattr(doc.get("created_at"), 'isoformat') else str(doc.get("created_at", ""))
            })

        return {"status": "success", "unread_count": unread, "notifications": notifs}

    @staticmethod
    def get_admin_notifications(limit: int = 30) -> Dict[str, Any]:
        coll = get_collection('notifications')
        if coll is None:
            return {"status": "success", "unread_count": 0, "notifications": []}

        query = {"$or": [{"is_admin": True}, {"user_id": "admin"}, {"category": "registration"}]}
        cursor = coll.find(query).sort("created_at", -1).limit(limit)
        notifs = []
        unread = 0
        for doc in cursor:
            is_read = bool(doc.get("is_read", False))
            if not is_read:
                unread += 1
            notifs.append({
                "id": str(doc.get("_id")),
                "user_id": str(doc.get("user_id", "admin")),
                "title": doc.get("title", ""),
                "message": doc.get("message", ""),
                "category": doc.get("category", "general"),
                "data": doc.get("data", {}),
                "is_admin": True,
                "is_read": is_read,
                "created_at": doc.get("created_at").isoformat() if hasattr(doc.get("created_at"), 'isoformat') else str(doc.get("created_at", ""))
            })

        return {"status": "success", "unread_count": unread, "notifications": notifs}

    @staticmethod
    def mark_read(notification_id: str, user_id: Any = None) -> bool:
        coll = get_collection('notifications')
        if coll is not None:
            from bson import ObjectId
            query: Dict[str, Any] = {}
            if ObjectId.is_valid(notification_id):
                query["_id"] = ObjectId(notification_id)
            else:
                query["id"] = notification_id

            if user_id is not None and user_id != "admin":
                query["user_id"] = {"$in": [str(user_id), user_id]}

            try:
                coll.update_one(query, {"$set": {"is_read": True}})
                return True
            except Exception:
                pass
        return False

    @staticmethod
    def mark_admin_notification_read(notification_id: str) -> bool:
        return MongoNotificationService.mark_read(notification_id, user_id="admin")

    @staticmethod
    def mark_all_read(user_id: Any) -> bool:
        coll = get_collection('notifications')
        if coll is not None:
            query = {"$or": [{"user_id": str(user_id)}, {"user_id": user_id}], "is_read": False}
            coll.update_many(query, {"$set": {"is_read": True}})
            return True
        return False

    @staticmethod
    def mark_all_admin_notifications_read() -> bool:
        coll = get_collection('notifications')
        if coll is not None:
            query = {"$or": [{"is_admin": True}, {"user_id": "admin"}, {"category": "registration"}], "is_read": False}
            coll.update_many(query, {"$set": {"is_read": True}})
            return True
        return False

    @staticmethod
    def delete_notification(notification_id: str, user_id: Any = None) -> bool:
        coll = get_collection('notifications')
        if coll is not None:
            from bson import ObjectId
            query: Dict[str, Any] = {}
            if ObjectId.is_valid(notification_id):
                query["_id"] = ObjectId(notification_id)
            else:
                query["id"] = notification_id

            if user_id is not None and user_id != "admin":
                query["user_id"] = {"$in": [str(user_id), user_id]}

            try:
                coll.delete_one(query)
                return True
            except Exception:
                pass
        return False
