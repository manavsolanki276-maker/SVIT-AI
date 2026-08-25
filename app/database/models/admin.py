"""
app/database/models/admin.py
SQLAlchemy Admin User Model with RBAC support, secure password hashing,
active status tracking, and permission resolution.
"""
from datetime import datetime
from typing import Dict, Any, Set, Optional
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from app.extensions import db
from app.auth.rbac import (
    ROLE_SUPER_ADMIN,
    ROLE_DISPLAY_NAMES,
    normalize_role,
    get_role_permissions,
    has_permission as rbac_has_permission,
    has_role as rbac_has_role,
)


class Admin(UserMixin, db.Model):
    __tablename__ = 'admins'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.String(64), unique=True, nullable=True)
    name = db.Column(db.String(100), default='Administrator', nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(50), default=ROLE_SUPER_ADMIN, nullable=False)
    department = db.Column(db.String(100), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)

    @property
    def full_name(self) -> str:
        return self.name or "Administrator"

    @full_name.setter
    def full_name(self, val: str):
        self.name = val

    @property
    def role_display(self) -> str:
        norm = normalize_role(self.role)
        return ROLE_DISPLAY_NAMES.get(norm, norm.replace('_', ' ').title())

    @property
    def permissions(self) -> Set[str]:
        return get_role_permissions(self.role)

    def set_password(self, password: str):
        """Hashes and sets password securely."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Verifies candidate plaintext against stored hash."""
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    # Overrides Flask-Login's get_id to prevent ID collisions with Student
    def get_id(self) -> str:
        return f"admin_{self.id}"

    @property
    def is_admin(self) -> bool:
        return True

    def has_permission(self, permission: str) -> bool:
        return rbac_has_permission(self, permission)

    def has_role(self, *roles: str) -> bool:
        return rbac_has_role(self, *roles)

    def update_last_login(self):
        """Updates last_login timestamp."""
        self.last_login = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()

    def to_dict(self) -> Dict[str, Any]:
        """
        Serializes admin model for safe API responses.
        CRITICAL: Never exposes password or password_hash.
        """
        return {
            "id": self.id,
            "admin_id": self.admin_id or f"ADM-{self.id:04d}" if self.id else None,
            "name": self.name,
            "full_name": self.full_name,
            "username": self.username,
            "email": self.email,
            "role": normalize_role(self.role),
            "role_display": self.role_display,
            "department": self.department or "",
            "is_active": bool(self.is_active),
            "permissions": sorted(list(self.permissions)),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None,
        }

    def __repr__(self):
        return f"<Admin id={self.id} username='{self.username}' role='{self.role}' active={self.is_active}>"