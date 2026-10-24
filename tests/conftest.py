"""
tests/conftest.py — Shared test fixtures for ResumeAI.

pytest looks for conftest.py automatically and makes its fixtures available
to every test file in the same directory.

What this file sets up:
  • A test Flask application (using in-memory SQLite, CSRF disabled)
  • A test client (simulates browser requests without a real browser)
  • Helper functions for creating test users and logging in/out
"""

import io
import pytest

from app import create_app
from config import TestingConfig
from extensions import db as _db
from models.user import User, Analysis


# ── App + client fixtures ──────────────────────────────────────────────────────

@pytest.fixture(scope="function")
def app():
    """
    Create a fresh Flask app instance for each test function.

    Uses TestingConfig which:
      • Points to an in-memory SQLite database (reset after each test)
      • Disables CSRF so tests can POST forms without tokens
      • Enables TESTING mode (cleaner error messages)
    """
    flask_app = create_app(TestingConfig)

    with flask_app.app_context():
        _db.create_all()
        yield flask_app
        _db.session.remove()
        _db.drop_all()


@pytest.fixture(scope="function")
def client(app):
    """
    A test client that simulates browser requests.

    With use_cookies=True the client maintains session state between requests,
    just like a real browser does.
    """
    return app.test_client()


@pytest.fixture(scope="function")
def db(app):
    """Expose the database session to tests that need to query it directly."""
    return _db


# ── Helper fixtures ────────────────────────────────────────────────────────────

@pytest.fixture
def sample_user(db):
    """Create and return a saved test user."""
    user = User(full_name="Test User", email="test@example.com")
    user.set_password("TestPassword123!")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def second_user(db):
    """A second user to test access isolation between users."""
    user = User(full_name="Other User", email="other@example.com")
    user.set_password("OtherPassword123!")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def logged_in_client(client, sample_user):
    """
    A test client that is already logged in as sample_user.

    CSRF is disabled in tests so we can POST forms freely.
    """
    client.post(
        "/login",
        data={"email": "test@example.com", "password": "TestPassword123!"},
        follow_redirects=True,
    )
    return client


@pytest.fixture
def sample_analysis(db, sample_user):
    """Create and return a saved test analysis belonging to sample_user."""
    import json
    analysis_data = {
        "summary": "Test summary.",
        "skills": {"matching": ["Python"], "missing": ["Docker"], "uncertain": []},
        "experience_alignment": ["Good experience in backend development."],
        "strengths": ["Strong Python skills"],
        "improvements": ["Add Docker to skillset"],
        "keywords": {"present": ["Python"], "missing_or_weak": ["Kubernetes"]},
        "components": {"skills": 7.0, "experience": 6.0, "qualifications": 8.0},
        "recommendations": ["Learn Docker basics"],
    }
    analysis = Analysis(
        user_id=sample_user.id,
        analysis_title="Test Analysis",
        job_title="Software Engineer",
        match_score=69.0,
        analysis_result_json=json.dumps(analysis_data),
    )
    db.session.add(analysis)
    db.session.commit()
    return analysis


# ── File helpers ───────────────────────────────────────────────────────────────

def make_pdf_bytes() -> bytes:
    """
    Create a minimal valid PDF in memory.

    This is a real (but very small) PDF that PyMuPDF can open and from which
    it can extract the text "Test resume content for automated testing."
    """
    # Minimal hand-crafted PDF with one text stream
    pdf_content = b"""%PDF-1.4
1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj
2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj
3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]
  /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj
4 0 obj << /Length 120 >>
stream
BT
/F1 12 Tf
72 720 Td
(Test resume content for automated testing. Python SQL Machine Learning Data Science.) Tj
ET
endstream
endobj
5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj
xref
0 6
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000274 00000 n 
0000000445 00000 n 
trailer << /Size 6 /Root 1 0 R >>
startxref
528
%%EOF"""
    return pdf_content


def make_docx_bytes() -> bytes:
    """
    Create a minimal valid DOCX file in memory using python-docx.
    Returns the raw bytes of the DOCX file.
    """
    from docx import Document
    doc = Document()
    doc.add_paragraph(
        "Test resume content for automated testing. "
        "Skills: Python, SQL, Machine Learning, Data Science."
    )
    doc.add_paragraph("Experience: 3 years as a software engineer.")
    buffer = io.BytesIO()
    doc.save(buffer)
    return buffer.getvalue()
