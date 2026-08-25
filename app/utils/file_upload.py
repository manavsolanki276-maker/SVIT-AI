"""
app/utils/file_upload.py
Secure file upload handling, file type validation, size limits,
and sanitized storage for images and PDF/DOCX documents in SVIT Admin.
Never exposes internal filesystem paths.
"""
import os
import uuid
import mimetypes
from datetime import datetime
from typing import Tuple, Dict, Any, Optional
from werkzeug.utils import secure_filename
from flask import current_app, url_for

# Allowed extensions and MIME types
ALLOWED_IMAGE_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp'}
ALLOWED_DOCUMENT_EXTENSIONS = {'pdf', 'docx'}

# File size limits (in bytes)
MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024       # 5 MB
MAX_DOCUMENT_SIZE_BYTES = 15 * 1024 * 1024   # 15 MB


def get_upload_dir(subfolder: str = 'images') -> str:
    """Returns absolute path to upload directory and ensures it exists."""
    base_static = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'static')
    target_dir = os.path.join(base_static, 'uploads', subfolder)
    os.makedirs(target_dir, exist_ok=True)
    return target_dir


def format_file_size(size_bytes: int) -> str:
    """Formats raw byte count into human-readable size string (KB, MB)."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.2f} MB"


def validate_and_save_file(
    file_storage,
    category: str = 'image',
    uploaded_by: str = 'admin'
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Validates and securely saves an uploaded file.
    
    Args:
        file_storage: Werkzeug FileStorage object from request.files
        category: 'image' or 'document'
        uploaded_by: Username of authenticated admin
        
    Returns:
        (success: bool, message: str, file_info: dict or None)
    """
    if not file_storage or not file_storage.filename:
        return False, "No file provided.", None

    raw_filename = file_storage.filename
    sec_name = secure_filename(raw_filename)
    if not sec_name or '.' not in sec_name:
        return False, "Invalid filename or missing file extension.", None

    ext = sec_name.rsplit('.', 1)[1].lower()

    # 1. Validate Extension
    if category == 'image':
        if ext not in ALLOWED_IMAGE_EXTENSIONS:
            allowed_str = ", ".join(sorted(list(ALLOWED_IMAGE_EXTENSIONS))).upper()
            return False, f"Invalid image format. Supported formats: {allowed_str}.", None
        max_size = MAX_IMAGE_SIZE_BYTES
        subfolder = 'images'
    elif category == 'document':
        if ext not in ALLOWED_DOCUMENT_EXTENSIONS:
            allowed_str = ", ".join(sorted(list(ALLOWED_DOCUMENT_EXTENSIONS))).upper()
            return False, f"Invalid document format. Supported formats: {allowed_str}.", None
        max_size = MAX_DOCUMENT_SIZE_BYTES
        subfolder = 'documents'
    else:
        return False, f"Unsupported upload category: '{category}'.", None

    # 2. Validate File Size
    # Read file content safely or seek to determine length
    file_storage.seek(0, os.SEEK_END)
    file_size = file_storage.tell()
    file_storage.seek(0)

    if file_size <= 0:
        return False, "Uploaded file is empty (0 bytes).", None

    if file_size > max_size:
        max_mb = max_size / (1024 * 1024)
        return False, f"File size ({format_file_size(file_size)}) exceeds the maximum allowed limit of {max_mb:.0f} MB.", None

    # 3. Generate unique safe stored filename
    unique_id = uuid.uuid4().hex[:12]
    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    base_clean = sec_name.rsplit('.', 1)[0][:30]
    safe_stored_name = f"{timestamp}_{unique_id}_{base_clean}.{ext}"

    # 4. Save to Disk
    upload_dir = get_upload_dir(subfolder)
    dest_path = os.path.join(upload_dir, safe_stored_name)

    try:
        file_storage.save(dest_path)
    except Exception as e:
        return False, f"Failed to save file: {str(e)}", None

    # 5. Build Public URL and metadata (never exposing internal filesystem path)
    public_url = f"/static/uploads/{subfolder}/{safe_stored_name}"
    mime_type, _ = mimetypes.guess_type(dest_path)

    file_info = {
        "file_id": unique_id,
        "original_name": raw_filename,
        "stored_filename": safe_stored_name,
        "url": public_url,
        "category": category,
        "file_extension": ext,
        "file_type": mime_type or ('image/' + ext if category == 'image' else 'application/pdf'),
        "file_size": file_size,
        "file_size_formatted": format_file_size(file_size),
        "uploaded_by": uploaded_by,
        "upload_date": datetime.utcnow().isoformat(),
        "upload_date_formatted": datetime.utcnow().strftime('%d %b %Y, %I:%M %p')
    }

    return True, "File uploaded successfully.", file_info


def delete_uploaded_file(file_url_or_filename: str) -> bool:
    """
    Safely deletes a previously uploaded file given its public URL or filename.
    Prevents path traversal.
    """
    if not file_url_or_filename:
        return False

    # Extract filename only
    filename = os.path.basename(file_url_or_filename.strip().split('?')[0])
    if not filename:
        return False

    base_static = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'static')
    
    # Check in both images and documents directories
    for sub in ['images', 'documents']:
        file_path = os.path.join(base_static, 'uploads', sub, filename)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            try:
                os.remove(file_path)
                return True
            except OSError:
                return False

    return False
