"""
app/admin/routes.py
Re-exports and proxies the main admin routes to ensure consistency across imports.
"""
from app.routes.admin import admin_bp

__all__ = ['admin_bp']