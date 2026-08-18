"""
=============================================================================
VeriField Nexus — OCR Engine & Scanned Document Handler
=============================================================================
Detects scanned / image-only PDFs and performs OCR when the system environment
supports it. If OCR binary is unavailable, reports explicit OCR_REQUIRED state.
=============================================================================
"""

import io
import logging
import shutil
from typing import Any, Dict, List
import pytesseract
from pdf2image import convert_from_bytes

logger = logging.getLogger("verifield.documents.ocr")


class OCREngineService:
    """Executes OCR extraction for image-based PDFs when native OCR is configured."""

    @staticmethod
    def is_ocr_available() -> bool:
        """Checks if both Tesseract and Poppler (pdftoppm) binaries are available on system PATH."""
        return shutil.which("tesseract") is not None and shutil.which("pdftoppm") is not None


    @classmethod
    def process_scanned_pdf(cls, file_bytes: bytes, max_pages: int = 20) -> Dict[str, Any]:
        """
        Executes OCR on scanned PDF pages.
        Returns: {
            "ocr_performed": bool,
            "status": "EXTRACTED" | "OCR_REQUIRED" | "OCR_FAILED",
            "pages": [...],
            "full_text": str,
            "error_reason": Optional[str]
        }
        """
        if not cls.is_ocr_available():
            logger.info("Tesseract binary not installed on host. Marking document as OCR_REQUIRED.")
            return {
                "ocr_performed": False,
                "status": "OCR_REQUIRED",
                "pages": [],
                "full_text": "",
                "error_reason": "Tesseract OCR binary is not installed in the deployment environment.",
            }

        try:
            images = convert_from_bytes(file_bytes, first_page=1, last_page=max_pages)
            pages_data: List[Dict[str, Any]] = []
            full_text_chunks: List[str] = []

            for idx, img in enumerate(images):
                page_num = idx + 1
                extracted_text = pytesseract.image_to_string(img) or ""
                clean_text = extracted_text.strip()
                pages_data.append({
                    "page_number": page_num,
                    "text": clean_text,
                    "char_count": len(clean_text),
                    "is_scanned": False,
                })
                if clean_text:
                    full_text_chunks.append(clean_text)

            return {
                "ocr_performed": True,
                "status": "EXTRACTED",
                "pages": pages_data,
                "full_text": "\n\n".join(full_text_chunks),
                "error_reason": None,
            }
        except Exception as e:
            logger.error(f"OCR processing failed: {e}")
            return {
                "ocr_performed": False,
                "status": "OCR_FAILED",
                "pages": [],
                "full_text": "",
                "error_reason": f"OCR processing encountered an internal error: {str(e)}",
            }
