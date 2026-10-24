"""
tests/test_resume_parser.py — Resume text extraction tests.

Tests:
  1.  PDF text extraction succeeds
  2.  DOCX text extraction succeeds
  3.  Empty file rejected
  4.  Unsupported extension rejected
  5.  Corrupted/truncated PDF handled gracefully
  6.  Corrupted/truncated DOCX handled gracefully
  7.  PDF with no extractable text gives a clear error
"""

import io
import pytest

from services.resume_parser import (
    parse_resume,
    extract_text_from_pdf,
    extract_text_from_docx,
    ResumeParseError,
)
from tests.conftest import make_pdf_bytes, make_docx_bytes


# ─────────────────────────────────────────────────────────────────────────────
# 1. PDF extraction
# ─────────────────────────────────────────────────────────────────────────────

def test_pdf_extraction_success(app):
    """A well-formed PDF with text should return the extracted text."""
    with app.app_context():
        pdf_bytes = make_pdf_bytes()
        text = extract_text_from_pdf(pdf_bytes)
        assert isinstance(text, str)
        assert len(text) >= 50
        # Our test PDF contains the word "Python"
        assert "Python" in text or "resume" in text.lower()


# ─────────────────────────────────────────────────────────────────────────────
# 2. DOCX extraction
# ─────────────────────────────────────────────────────────────────────────────

def test_docx_extraction_success(app):
    """A well-formed DOCX with text should return the extracted text."""
    with app.app_context():
        docx_bytes = make_docx_bytes()
        text = extract_text_from_docx(docx_bytes)
        assert isinstance(text, str)
        assert len(text) >= 50
        assert "Python" in text or "resume" in text.lower()


# ─────────────────────────────────────────────────────────────────────────────
# 3. Empty file
# ─────────────────────────────────────────────────────────────────────────────

def test_empty_file_rejected(app):
    """An empty byte string should raise ResumeParseError."""
    with app.app_context():
        with pytest.raises(ResumeParseError, match="empty"):
            parse_resume(b"", "resume.pdf")


# ─────────────────────────────────────────────────────────────────────────────
# 4. Unsupported extension
# ─────────────────────────────────────────────────────────────────────────────

def test_unsupported_extension_rejected(app):
    """A .txt or .jpg file should raise ResumeParseError about unsupported format."""
    with app.app_context():
        with pytest.raises(ResumeParseError, match="Unsupported"):
            parse_resume(b"Some text content here", "resume.txt")

        with pytest.raises(ResumeParseError, match="Unsupported"):
            parse_resume(b"\xff\xd8\xff", "photo.jpg")


# ─────────────────────────────────────────────────────────────────────────────
# 5. Corrupted PDF
# ─────────────────────────────────────────────────────────────────────────────

def test_corrupted_pdf_handled(app):
    """Random bytes with a .pdf extension should raise ResumeParseError."""
    with app.app_context():
        corrupted = b"This is definitely not a real PDF file %PDF-"
        with pytest.raises(ResumeParseError):
            extract_text_from_pdf(corrupted)


# ─────────────────────────────────────────────────────────────────────────────
# 6. Corrupted DOCX
# ─────────────────────────────────────────────────────────────────────────────

def test_corrupted_docx_handled(app):
    """Random bytes with a .docx extension should raise ResumeParseError."""
    with app.app_context():
        corrupted = b"This is definitely not a real Word document."
        with pytest.raises(ResumeParseError):
            extract_text_from_docx(corrupted)


# ─────────────────────────────────────────────────────────────────────────────
# 7. PDF with no extractable text (image-only)
# ─────────────────────────────────────────────────────────────────────────────

def test_image_only_pdf_gives_clear_error(app):
    """
    A PDF that contains only images (no machine-readable text) should raise
    ResumeParseError with a message explaining that text could not be extracted.

    We simulate this by creating a valid PDF with an empty text stream.
    """
    with app.app_context():
        # Minimal PDF with an empty content stream (no text at all)
        empty_text_pdf = b"""%PDF-1.4
1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj
2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj
3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]
  /Contents 4 0 R /Resources << >> >> endobj
4 0 obj << /Length 0 >>
stream
endstream
endobj
xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000243 00000 n 
trailer << /Size 5 /Root 1 0 R >>
startxref
296
%%EOF"""
        with pytest.raises(ResumeParseError, match="readable text|extract"):
            extract_text_from_pdf(empty_text_pdf)
