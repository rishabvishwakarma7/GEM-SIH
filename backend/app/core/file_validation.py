"""
Secure file validation for tender/bidder document uploads.

Checks (in order): filename present, extension allowlist, declared
content-type allowlist, non-empty, size limit, and magic-byte signature —
so a renamed .exe or empty file can't slip through just because the client
claimed it was a PDF/image.
"""
import os
from typing import Optional

from fastapi import HTTPException, status

# ---- PDF-only validation (used by tender document upload — unchanged) ----
ALLOWED_EXTENSIONS = {".pdf"}
ALLOWED_CONTENT_TYPES = {"application/pdf"}
PDF_MAGIC_BYTES = b"%PDF"


def validate_pdf_bytes(
    filename: Optional[str],
    content_type: Optional[str],
    contents: bytes,
    max_size_mb: int,
) -> None:
    """Raises HTTPException(400) if the upload fails any validation check."""
    if not filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No filename provided")

    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are allowed",
        )

    if content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid content type '{content_type}'; expected application/pdf",
        )

    if not contents:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty")

    max_bytes = max_size_mb * 1024 * 1024
    if len(contents) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File exceeds maximum size of {max_size_mb}MB",
        )

    if not contents.startswith(PDF_MAGIC_BYTES):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File does not appear to be a valid PDF (signature check failed)",
        )


# ---- PDF + image validation (used by bidder document upload, Day 3) ----
ALLOWED_DOCUMENT_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}
ALLOWED_DOCUMENT_CONTENT_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
}
# (magic bytes, content-type prefix) — checked as "starts with"
IMAGE_MAGIC_SIGNATURES = {
    b"\xff\xd8\xff": "image/jpeg",       # JPEG
    b"\x89PNG\r\n\x1a\n": "image/png",   # PNG
}


def validate_document_bytes(
    filename: Optional[str],
    content_type: Optional[str],
    contents: bytes,
    max_size_mb: int,
) -> str:
    """
    Validates a bidder document upload (PDF or image). Raises
    HTTPException(400) on any failed check. Returns "pdf" or "image" so the
    caller knows which extraction path to use — determined from the actual
    file signature, not the (spoofable) declared extension/content-type.
    """
    if not filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No filename provided")

    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_DOCUMENT_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF, JPG, and PNG files are allowed",
        )

    if content_type not in ALLOWED_DOCUMENT_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid content type '{content_type}'; expected PDF, JPEG, or PNG",
        )

    if not contents:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty")

    max_bytes = max_size_mb * 1024 * 1024
    if len(contents) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File exceeds maximum size of {max_size_mb}MB",
        )

    if contents.startswith(PDF_MAGIC_BYTES):
        return "pdf"

    for magic, _ in IMAGE_MAGIC_SIGNATURES.items():
        if contents.startswith(magic):
            return "image"

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="File does not appear to be a valid PDF, JPEG, or PNG (signature check failed)",
    )


def safe_stored_filename(original_filename: str) -> str:
    """Builds a collision-safe filename for disk storage, stripping any path components."""
    import uuid
    base = os.path.basename(original_filename)
    return f"{uuid.uuid4().hex}_{base}"
