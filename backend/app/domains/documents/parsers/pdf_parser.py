"""
=============================================================================
VeriField Nexus — PDF Parser Service
=============================================================================
Extracts text page-by-page, preserves page boundaries, extracts document metadata,
and detects scanned / image-only pages.
=============================================================================
"""

import io
import logging
from typing import Any, Dict, List, Optional
from pypdf import PdfReader

logger = logging.getLogger("verifield.documents.pdf_parser")


class PDFParserService:
    """Extracts text, metadata, and page structures from PDF documents."""

    @staticmethod
    def parse_pdf(file_bytes: bytes) -> Dict[str, Any]:
        """
        Parses a PDF file buffer and returns structured page contents and metadata.
        """
        reader = PdfReader(io.BytesIO(file_bytes))
        total_pages = len(reader.pages)

        metadata: Dict[str, Any] = {}
        if reader.metadata:
            for key, val in reader.metadata.items():
                clean_key = key.lstrip("/").lower()
                metadata[clean_key] = str(val) if val is not None else None

        pages_data: List[Dict[str, Any]] = []
        full_text_chunks: List[str] = []
        scanned_pages_count = 0

        for page_idx, page in enumerate(reader.pages):
            page_num = page_idx + 1
            text = page.extract_text() or ""
            clean_text = text.strip()

            is_scanned = len(clean_text) < 50
            if is_scanned:
                scanned_pages_count += 1

            pages_data.append({
                "page_number": page_num,
                "text": clean_text,
                "char_count": len(clean_text),
                "is_scanned": is_scanned,
            })
            if clean_text:
                full_text_chunks.append(clean_text)

        full_text = "\n\n".join(full_text_chunks)
        overall_is_scanned = (scanned_pages_count / total_pages > 0.5) if total_pages > 0 else False

        return {
            "total_pages": total_pages,
            "metadata": metadata,
            "pages": pages_data,
            "full_text": full_text,
            "is_scanned": overall_is_scanned,
            "scanned_pages_count": scanned_pages_count,
        }
