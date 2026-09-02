"""
Modular document processing service.

Uses PyMuPDF (fitz) for direct text-layer extraction, and falls back to
Tesseract OCR (via pytesseract) per-page when a PDF is scanned/image-based
and PyMuPDF pulls out little or no text.

Pages are concatenated with explicit "[PAGE n]" markers so downstream
consumers (the AI service) can report which page a requirement came from.
"""
from typing import Dict, Any, List

import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import io

from app.core.logging_config import logger

# If the average extracted characters per page falls below this, the PDF is
# treated as scanned/image-based and OCR is used instead.
MIN_AVG_CHARS_PER_PAGE = 20

# DPI used when rendering pages to images for OCR — balances OCR accuracy
# against processing time for a hackathon-scale document.
OCR_RENDER_DPI = 200


class DocumentProcessingError(Exception):
    pass


class DocumentProcessor:
    def extract_text_pymupdf(self, file_path: str) -> List[str]:
        """Returns a list of per-page text strings using PyMuPDF's text layer."""
        try:
            doc = fitz.open(file_path)
        except Exception as e:
            raise DocumentProcessingError(f"Could not open PDF: {e}") from e

        try:
            pages_text = [page.get_text("text") for page in doc]
        finally:
            doc.close()

        return pages_text

    def extract_text_ocr(self, file_path: str) -> List[str]:
        """Returns a list of per-page text strings via Tesseract OCR (for scanned PDFs)."""
        try:
            doc = fitz.open(file_path)
        except Exception as e:
            raise DocumentProcessingError(f"Could not open PDF for OCR: {e}") from e

        pages_text: List[str] = []
        try:
            for page_index, page in enumerate(doc):
                try:
                    pix = page.get_pixmap(dpi=OCR_RENDER_DPI)
                    image = Image.open(io.BytesIO(pix.tobytes("png")))
                    text = pytesseract.image_to_string(image)
                except Exception as e:
                    logger.warning(f"OCR failed on page {page_index + 1}: {e}")
                    text = ""
                pages_text.append(text)
        finally:
            doc.close()

        return pages_text

    def process_document(self, file_path: str) -> Dict[str, Any]:
        """
        Orchestrates extraction: try PyMuPDF first; if the average text per
        page is too sparse (likely a scanned document), fall back to OCR.

        Returns: {"raw_text": str, "method": "pymupdf"|"ocr", "page_count": int}
        """
        pages_text = self.extract_text_pymupdf(file_path)
        page_count = len(pages_text)

        if page_count == 0:
            raise DocumentProcessingError("PDF has no pages")

        total_chars = sum(len(p.strip()) for p in pages_text)
        avg_chars_per_page = total_chars / page_count
        method = "pymupdf"

        if avg_chars_per_page < MIN_AVG_CHARS_PER_PAGE:
            logger.info(
                f"{file_path}: avg {avg_chars_per_page:.1f} chars/page from PyMuPDF — "
                f"falling back to OCR"
            )
            pages_text = self.extract_text_ocr(file_path)
            method = "ocr"

        combined_parts = []
        for i, text in enumerate(pages_text, start=1):
            combined_parts.append(f"\n\n[PAGE {i}]\n{text.strip()}\n")
        raw_text = "".join(combined_parts).strip()

        return {
            "raw_text": raw_text,
            "method": method,
            "page_count": page_count,
        }

    # -----------------------------------------------------------------
    # Image documents (bidder uploads: photographed/scanned JPG/PNG docs)
    # -----------------------------------------------------------------
    def extract_text_from_image(self, file_path: str) -> str:
        """OCRs a single standalone image file (not a PDF page) via Tesseract."""
        try:
            image = Image.open(file_path)
            return pytesseract.image_to_string(image)
        except Exception as e:
            raise DocumentProcessingError(f"Could not OCR image: {e}") from e

    def process_image(self, file_path: str) -> Dict[str, Any]:
        """
        Same return shape as process_document(), for a single-page image
        document. Always uses OCR — images have no embedded text layer.
        """
        text = self.extract_text_from_image(file_path)
        raw_text = f"\n\n[PAGE 1]\n{text.strip()}\n".strip()
        return {
            "raw_text": raw_text,
            "method": "image_ocr",
            "page_count": 1,
        }

    def process_bidder_document(self, file_path: str, file_kind: str) -> Dict[str, Any]:
        """
        Entry point for the bidder document pipeline: dispatches to the PDF
        pipeline (with OCR fallback) or the single-image OCR path based on
        the validated file_kind ("pdf" | "image") from file_validation.
        """
        if file_kind == "image":
            return self.process_image(file_path)
        return self.process_document(file_path)


document_processor = DocumentProcessor()
