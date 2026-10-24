"""
tests/test_routes.py — Route-level integration tests.

Tests:
  1.  /analyze requires login
  2.  /analyze GET loads for logged-in user
  3.  /analyze POST — missing file returns error
  4.  /analyze POST — unsupported file type rejected
  5.  /analyze POST — missing job description rejected
  6.  /analysis/<id> requires login
  7.  /analysis/<id> returns 404 for non-existent ID
  8.  /analysis/<id> returns 403 if owned by another user
  9.  /analysis/<id> returns 200 for owner
 10.  /analysis/<id>/delete GET shows confirmation page
 11.  /analysis/<id>/delete POST deletes the record
 12.  /analysis/<id>/delete POST forbidden for non-owner
 13.  /history requires login
 14.  /history shows only current user's analyses
 15.  /profile requires login
 16.  /profile shows current user info
"""

import io
import json
import pytest

from models.user import Analysis


# ─────────────────────────────────────────────────────────────────────────────
# 1. /analyze requires login
# ─────────────────────────────────────────────────────────────────────────────

def test_analyze_requires_login(client):
    """Unauthenticated GET /analyze should redirect to login."""
    response = client.get("/analyze", follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


# ─────────────────────────────────────────────────────────────────────────────
# 2. /analyze GET loads for logged-in user
# ─────────────────────────────────────────────────────────────────────────────

def test_analyze_get_loads(logged_in_client):
    """Authenticated GET /analyze should return 200."""
    response = logged_in_client.get("/analyze")
    assert response.status_code == 200
    assert b"Analyze" in response.data or b"Resume" in response.data


# ─────────────────────────────────────────────────────────────────────────────
# 3. /analyze POST — missing file
# ─────────────────────────────────────────────────────────────────────────────

def test_analyze_post_no_file(logged_in_client):
    """Submitting the form without a file should show a validation error."""
    response = logged_in_client.post(
        "/analyze",
        data={
            "job_description": "Looking for a Python developer with 3 years experience.",
            "analysis_title": "Test",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    # Should show an error about the file
    assert b"upload" in response.data.lower() or b"resume" in response.data.lower()


# ─────────────────────────────────────────────────────────────────────────────
# 4. /analyze POST — unsupported file type
# ─────────────────────────────────────────────────────────────────────────────

def test_analyze_post_unsupported_file_type(logged_in_client):
    """A .txt file should be rejected."""
    data = {
        "job_description": "Looking for a Python developer with 3 years experience.",
        "resume_file": (io.BytesIO(b"Plain text file"), "resume.txt"),
    }
    response = logged_in_client.post(
        "/analyze",
        data=data,
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Unsupported" in response.data or b"PDF" in response.data


# ─────────────────────────────────────────────────────────────────────────────
# 5. /analyze POST — missing job description
# ─────────────────────────────────────────────────────────────────────────────

def test_analyze_post_empty_job_description(logged_in_client):
    """An empty job description should be rejected with a validation error."""
    from tests.conftest import make_pdf_bytes
    pdf_bytes = make_pdf_bytes()
    data = {
        "job_description": "",  # empty
        "resume_file": (io.BytesIO(pdf_bytes), "resume.pdf"),
    }
    response = logged_in_client.post(
        "/analyze",
        data=data,
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"job description" in response.data.lower()


# ─────────────────────────────────────────────────────────────────────────────
# 6. /analysis/<id> requires login
# ─────────────────────────────────────────────────────────────────────────────

def test_view_analysis_requires_login(client):
    """Unauthenticated access to /analysis/1 should redirect to login."""
    response = client.get("/analysis/1", follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


# ─────────────────────────────────────────────────────────────────────────────
# 7. /analysis/<id> 404 for missing ID
# ─────────────────────────────────────────────────────────────────────────────

def test_view_analysis_not_found(logged_in_client):
    """Requesting an analysis ID that doesn't exist should return 404."""
    response = logged_in_client.get("/analysis/99999")
    assert response.status_code == 404


# ─────────────────────────────────────────────────────────────────────────────
# 8. /analysis/<id> 403 for wrong user
# ─────────────────────────────────────────────────────────────────────────────

def test_view_analysis_forbidden_for_other_user(client, db, sample_user, second_user, sample_analysis):
    """
    second_user should get 403 when trying to view sample_user's analysis.
    """
    # Log in as second_user
    client.post(
        "/login",
        data={"email": "other@example.com", "password": "OtherPassword123!"},
        follow_redirects=True,
    )

    response = client.get(f"/analysis/{sample_analysis.id}")
    assert response.status_code == 403


# ─────────────────────────────────────────────────────────────────────────────
# 9. /analysis/<id> 200 for owner
# ─────────────────────────────────────────────────────────────────────────────

def test_view_analysis_success_for_owner(logged_in_client, sample_analysis):
    """The owner should be able to view their analysis (200 OK)."""
    response = logged_in_client.get(f"/analysis/{sample_analysis.id}")
    assert response.status_code == 200
    assert b"Test Analysis" in response.data or b"Software Engineer" in response.data


# ─────────────────────────────────────────────────────────────────────────────
# 10. Delete confirmation page
# ─────────────────────────────────────────────────────────────────────────────

def test_delete_confirmation_page(logged_in_client, sample_analysis):
    """GET /analysis/<id>/delete should show a confirmation page."""
    response = logged_in_client.get(f"/analysis/{sample_analysis.id}/delete")
    assert response.status_code == 200
    assert b"Delete" in response.data
    assert b"cannot be undone" in response.data


# ─────────────────────────────────────────────────────────────────────────────
# 11. Delete succeeds for owner
# ─────────────────────────────────────────────────────────────────────────────

def test_delete_analysis_success(logged_in_client, sample_analysis, db):
    """POST /analysis/<id>/delete should delete the record and redirect."""
    analysis_id = sample_analysis.id

    response = logged_in_client.post(
        f"/analysis/{analysis_id}/delete",
        follow_redirects=True,
    )
    assert response.status_code == 200
    # Should redirect to history and show a success flash
    assert b"deleted" in response.data.lower() or b"History" in response.data

    # Verify it's gone from the database
    deleted = db.session.get(Analysis, analysis_id)
    assert deleted is None


# ─────────────────────────────────────────────────────────────────────────────
# 12. Delete forbidden for non-owner
# ─────────────────────────────────────────────────────────────────────────────

def test_delete_analysis_forbidden_for_other_user(client, db, sample_user, second_user, sample_analysis):
    """second_user should get 403 when trying to delete sample_user's analysis."""
    # Log in as second_user
    client.post(
        "/login",
        data={"email": "other@example.com", "password": "OtherPassword123!"},
        follow_redirects=True,
    )

    response = client.post(f"/analysis/{sample_analysis.id}/delete")
    assert response.status_code == 403

    # The analysis should still exist
    still_exists = db.session.get(Analysis, sample_analysis.id)
    assert still_exists is not None


# ─────────────────────────────────────────────────────────────────────────────
# 13. /history requires login
# ─────────────────────────────────────────────────────────────────────────────

def test_history_requires_login(client):
    """Unauthenticated /history should redirect to login."""
    response = client.get("/history", follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


# ─────────────────────────────────────────────────────────────────────────────
# 14. /history shows only current user's analyses
# ─────────────────────────────────────────────────────────────────────────────

def test_history_shows_only_own_analyses(client, db, sample_user, second_user, sample_analysis):
    """
    second_user's history page should NOT show sample_user's analysis.
    """
    # Log in as second_user
    client.post(
        "/login",
        data={"email": "other@example.com", "password": "OtherPassword123!"},
        follow_redirects=True,
    )

    response = client.get("/history")
    assert response.status_code == 200
    # sample_analysis title should NOT appear
    assert b"Test Analysis" not in response.data


# ─────────────────────────────────────────────────────────────────────────────
# 15. /profile requires login
# ─────────────────────────────────────────────────────────────────────────────

def test_profile_requires_login(client):
    """Unauthenticated /profile should redirect to login."""
    response = client.get("/profile", follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


# ─────────────────────────────────────────────────────────────────────────────
# 16. /profile shows current user info
# ─────────────────────────────────────────────────────────────────────────────

def test_profile_shows_user_info(logged_in_client, sample_user):
    """The profile page should display the logged-in user's name and email."""
    response = logged_in_client.get("/profile")
    assert response.status_code == 200
    assert b"Test User" in response.data
    assert b"test@example.com" in response.data
