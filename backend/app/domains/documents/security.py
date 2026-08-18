"""
=============================================================================
VeriField Nexus — Document Security & Binary Validator
=============================================================================
Provides strict validation of uploaded files:
- MIME & extension validation
- Magic bytes / binary signature verification
- Path traversal & filename sanitization
- Executable rejection (MZ, ELF, Mach-O, Shebangs)
- SHA-256 hashing
=============================================================================
"""

import hashlib
import io
import os
import re
import zipfile
from typing import Tuple
from fastapi import HTTPException, UploadFile, status

MAX_DOCUMENT_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".xlsx", ".csv", ".txt"}

EXECUTABLE_SIGNATURES = [
    b"MZ",              # DOS / Windows PE Executable
    b"\x7fELF",         # Linux / Unix ELF Binary
    b"\xca\xfe\xba\xbe", # Java Class / Mach-O Fat Binary
    b"\xfe\xed\xfa\xce", # Mach-O 32-bit
    b"\xfe\xed\xfa\xcf", # Mach-O 64-bit
    b"#!\n", b"#!/",    # Script shebangs
]


class DocumentSecurityValidator:
    """Validates binary signatures and file safety before persistence."""

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitizes filename and strips path traversal characters."""
        if not filename:
            return "unnamed_document"
        # Take basename only
        clean_name = os.path.basename(filename)
        # Remove path traversal, control chars, null bytes
        clean_name = re.sub(r'[\x00-\x1f\x7f/\\]', '', clean_name)
        # Replace multiple dots or dangerous chars
        clean_name = re.sub(r'\.+', '.', clean_name)
        return clean_name.strip()

    @classmethod
    async def validate_and_read(cls, file: UploadFile) -> Tuple[bytes, str, str, str]:
        """
        Reads, validates, and computes the SHA-256 hash for an uploaded document.
        Returns: (file_bytes, clean_filename, mime_type, sha256_hash)
        """
        clean_filename = cls.sanitize_filename(file.filename or "")
        ext = os.path.splitext(clean_filename)[1].lower()

        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file type '{ext}'. Allowed extensions: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
            )

        # Read content with bounded chunk streaming to prevent memory exhaustion
        CHUNK_SIZE = 64 * 1024
        buffer = bytearray()
        while True:
            chunk = await file.read(CHUNK_SIZE)
            if not chunk:
                break
            buffer.extend(chunk)
            if len(buffer) > MAX_DOCUMENT_SIZE_BYTES:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"Document exceeds maximum allowed size of {MAX_DOCUMENT_SIZE_BYTES // (1024 * 1024)} MB.",
                )

        content = bytes(buffer)
        file_size = len(content)

        if file_size == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Empty file uploaded. Document size must be greater than 0 bytes.",
            )

        # Check for executable signatures

        for sig in EXECUTABLE_SIGNATURES:
            if content.startswith(sig):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Security violation: Executable or binary script files are strictly prohibited.",
                )

        mime_type = file.content_type or "application/octet-stream"

        # Validate magic bytes by extension
        if ext == ".pdf":
            if not content.startswith(b"%PDF-"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid PDF signature: File content does not start with standard '%PDF-' magic bytes.",
                )
            mime_type = "application/pdf"

        elif ext in (".docx", ".xlsx"):
            if not content.startswith(b"PK\x03\x04"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid {ext.upper()} signature: File is not a valid Office Open XML zip archive.",
                )
            # Verify internal package structure
            try:
                with zipfile.ZipFile(io.BytesIO(content)) as zf:
                    names = zf.namelist()
                    if "[Content_Types].xml" not in names:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Corrupted or invalid {ext.upper()} package: Missing '[Content_Types].xml'.",
                        )
            except zipfile.BadZipFile:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Corrupted {ext.upper()} archive file.",
                )
            mime_type = (
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                if ext == ".docx"
                else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        elif ext in (".csv", ".txt"):
            try:
                content.decode("utf-8")
            except UnicodeDecodeError:
                try:
                    content.decode("latin-1")
                except Exception:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid text encoding. File must be valid UTF-8 or ASCII text.",
                    )
            mime_type = "text/csv" if ext == ".csv" else "text/plain"

        sha256_hash = hashlib.sha256(content).hexdigest()

        return content, clean_filename, mime_type, sha256_hash
