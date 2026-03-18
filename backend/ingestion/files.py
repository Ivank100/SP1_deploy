# src/file_utils.py
import os
import shutil
import uuid
from pathlib import Path
from typing import Optional
from ..core.config import UPLOAD_DIR

def ensure_upload_dir(subdir: Optional[str] = None) -> Path:
    """Ensure uploads directory (and optional subdir) exists, return Path object."""
    upload_path = Path(UPLOAD_DIR)
    if subdir:
        upload_path = upload_path / subdir
    upload_path.mkdir(parents=True, exist_ok=True)
    return upload_path

def save_uploaded_file(source_path: str, original_name: str, subdir: Optional[str] = None) -> str:
    """
    Save uploaded file to uploads/ directory with unique name.
    
    Args:
        source_path: Path to source file
        original_name: Original filename
        
    Returns:
        New file path relative to project root
    """
    upload_dir = ensure_upload_dir(subdir=subdir)
    
    # Generate unique filename: {uuid}_{original_name}
    file_ext = Path(original_name).suffix
    unique_name = f"{uuid.uuid4()}{file_ext}"
    dest_path = upload_dir / unique_name
    
    # Copy file
    shutil.copy2(source_path, dest_path)
    
    # Return path as string (relative to project root)
    return str(dest_path)

def get_file_path(stored_path: str) -> Path:
    """Get full Path object for a stored file path."""
    return Path(stored_path)


def delete_stored_file(stored_path: Optional[str]) -> bool:
    """
    Delete a stored upload file only if it lives under the configured uploads directory.

    Returns True when a file was removed, False otherwise.
    """
    if not stored_path:
        return False

    try:
        candidate = Path(stored_path).expanduser().resolve()
        uploads_root = Path(UPLOAD_DIR).expanduser().resolve()
    except OSError:
        return False

    try:
        candidate.relative_to(uploads_root)
    except ValueError:
        return False

    if not candidate.exists() or not candidate.is_file():
        return False

    try:
        candidate.unlink()
        return True
    except OSError:
        return False
