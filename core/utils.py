import hashlib
import mimetypes
import os
import uuid
from pathlib import Path
from typing import Optional
import bleach
from django.core.exceptions import ValidationError
from django.conf import settings


def generate_vehicle_image_path(instance, filename: str) -> str:
    """
    Generate a safe, non-guessable storage path for vehicle images.
    Never trust the original filename.
    """
    ext = Path(filename).suffix.lower()
    safe_name = f"{uuid.uuid4().hex}{ext}"
    vehicle_id = instance.vehicle.pk if hasattr(instance, "vehicle") else "tmp"
    return f"vehicles/{vehicle_id}/{safe_name}"


def validate_image_upload(file) -> None:
    """
    Validate uploaded image files.
    Check: extension, MIME type, file signature, size.
    """
    max_size = settings.MAX_UPLOAD_SIZE
    allowed_extensions = settings.ALLOWED_IMAGE_EXTENSIONS

    # Size check
    if file.size > max_size:
        raise ValidationError(
            f"Image file too large. Maximum allowed size is "
            f"{max_size // (1024 * 1024)}MB."
        )

    # Extension check
    ext = Path(file.name).suffix.lower()
    if ext not in allowed_extensions:
        raise ValidationError(
            f"Unsupported image format '{ext}'. "
            f"Allowed formats: {', '.join(allowed_extensions)}"
        )

    # File signature (magic bytes) check
    file.seek(0)
    header = file.read(12)
    file.seek(0)

    signatures = {
        b"\xff\xd8\xff": "image/jpeg",
        b"\x89PNG\r\n\x1a\n": "image/png",
        b"RIFF": "image/webp",  # further check needed
        b"GIF87a": "image/gif",
        b"GIF89a": "image/gif",
    }

    detected = None
    for sig, mime in signatures.items():
        if header.startswith(sig):
            detected = mime
            break

    # WebP: RIFF....WEBP
    if header.startswith(b"RIFF") and header[8:12] == b"WEBP":
        detected = "image/webp"
    elif header.startswith(b"RIFF"):
        detected = None  # Not WebP

    if detected is None:
        raise ValidationError("File does not appear to be a valid image.")

    # Reject SVG entirely (XSS risk)
    if ext == ".svg" or detected == "image/svg+xml":
        raise ValidationError(
            "SVG files are not permitted for security reasons.")


def sanitize_html(html: str) -> str:
    """
    Sanitize HTML description input — strip dangerous tags.
    Only allow safe formatting.
    """
    allowed_tags = [
        "p", "br", "strong", "em", "b", "i", "u",
        "ul", "ol", "li", "h2", "h3", "h4",
        "blockquote", "a",
    ]
    allowed_attrs = {
        "a": ["href", "title", "rel"],
    }
    return bleach.clean(
        html,
        tags=allowed_tags,
        attributes=allowed_attrs,
        strip=True,
    )


def format_price(amount, currency_code: str = "KES", symbol: str = "KSh") -> str:
    """Format a price for display."""
    if amount is None:
        return "Price on Request"
    return f"{symbol} {amount:,.0f}"
