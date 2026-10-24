"""
tests/test_auth.py — Authentication tests.

Tests:
  1.  Landing page loads (200 OK)
  2.  Login page loads
  3.  Successful registration
  4.  Duplicate email registration rejected
  5.  Short password rejected
  6.  Mismatched passwords rejected
  7.  Missing name rejected
  8.  Password is hashed (never stored in plaintext)
  9.  Successful login
  10. Wrong password rejected
  11. Unknown email rejected
  12. Logout works
  13. Protected dashboard redirects unauthenticated users
"""

import pytest


# ─────────────────────────────────────────────────────────────────────────────
# 1. Landing page
# ─────────────────────────────────────────────────────────────────────────────

def test_landing_page_loads(client):
    """The public home page should return 200 OK."""
    response = client.get("/")
    assert response.status_code == 200
    assert b"ResumeAI" in response.data
    assert b"Build a Better Resume" in response.data


# ─────────────────────────────────────────────────────────────────────────────
# 2. Login page
# ─────────────────────────────────────────────────────────────────────────────

def test_login_page_loads(client):
    """The login page should return 200 OK."""
    response = client.get("/login")
    assert response.status_code == 200
    assert b"Sign In" in response.data


# ─────────────────────────────────────────────────────────────────────────────
# 3. Successful registration
# ─────────────────────────────────────────────────────────────────────────────

def test_registration_success(client, db):
    """A new user with valid details should be registered and redirected."""
    response = client.post(
        "/register",
        data={
            "full_name": "Alice Smith",
            "email": "alice@example.com",
            "password": "SecurePassword123!",
            "confirm_password": "SecurePassword123!",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    # After successful registration, the user is auto-logged in and redirected to dashboard
    assert b"Dashboard" in response.data or b"Welcome" in response.data

    from models.user import User
    user = User.query.filter_by(email="alice@example.com").first()
    assert user is not None
    assert user.full_name == "Alice Smith"


# ─────────────────────────────────────────────────────────────────────────────
# 4. Duplicate email
# ─────────────────────────────────────────────────────────────────────────────

def test_registration_duplicate_email(client, sample_user):
    """Registering with an already-used email should show an error."""
    response = client.post(
        "/register",
        data={
            "full_name": "Duplicate User",
            "email": "test@example.com",  # same as sample_user
            "password": "SecurePassword123!",
            "confirm_password": "SecurePassword123!",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"already exists" in response.data


# ─────────────────────────────────────────────────────────────────────────────
# 5. Short password
# ─────────────────────────────────────────────────────────────────────────────

def test_registration_short_password(client):
    """Password shorter than 12 characters should be rejected."""
    response = client.post(
        "/register",
        data={
            "full_name": "Bob Jones",
            "email": "bob@example.com",
            "password": "short",
            "confirm_password": "short",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"12" in response.data  # error message mentions the minimum length


# ─────────────────────────────────────────────────────────────────────────────
# 6. Mismatched passwords
# ─────────────────────────────────────────────────────────────────────────────

def test_registration_password_mismatch(client):
    """Non-matching passwords should be rejected."""
    response = client.post(
        "/register",
        data={
            "full_name": "Carol White",
            "email": "carol@example.com",
            "password": "SecurePassword123!",
            "confirm_password": "DifferentPassword123!",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"match" in response.data


# ─────────────────────────────────────────────────────────────────────────────
# 7. Missing name
# ─────────────────────────────────────────────────────────────────────────────

def test_registration_missing_name(client):
    """Empty full name should be rejected."""
    response = client.post(
        "/register",
        data={
            "full_name": "",
            "email": "dave@example.com",
            "password": "SecurePassword123!",
            "confirm_password": "SecurePassword123!",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"full name" in response.data.lower()


# ─────────────────────────────────────────────────────────────────────────────
# 8. Password hashing
# ─────────────────────────────────────────────────────────────────────────────

def test_password_is_hashed(sample_user):
    """The stored password hash must not equal the plaintext password."""
    plaintext = "TestPassword123!"
    assert sample_user.password_hash != plaintext
    assert len(sample_user.password_hash) > 20  # hashes are long strings
    assert sample_user.check_password(plaintext) is True
    assert sample_user.check_password("wrongpassword") is False


# ─────────────────────────────────────────────────────────────────────────────
# 9. Successful login
# ─────────────────────────────────────────────────────────────────────────────

def test_login_success(client, sample_user):
    """Valid credentials should log the user in and redirect to dashboard."""
    response = client.post(
        "/login",
        data={"email": "test@example.com", "password": "TestPassword123!"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Dashboard" in response.data


# ─────────────────────────────────────────────────────────────────────────────
# 10. Wrong password
# ─────────────────────────────────────────────────────────────────────────────

def test_login_wrong_password(client, sample_user):
    """Wrong password should show a generic error without revealing which field was wrong."""
    response = client.post(
        "/login",
        data={"email": "test@example.com", "password": "WrongPassword999!"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    # Generic error — should NOT say "password incorrect" specifically
    assert b"Incorrect" in response.data or b"incorrect" in response.data
    assert b"Dashboard" not in response.data


# ─────────────────────────────────────────────────────────────────────────────
# 11. Unknown email
# ─────────────────────────────────────────────────────────────────────────────

def test_login_unknown_email(client):
    """Unknown email should produce the same generic error as a wrong password."""
    response = client.post(
        "/login",
        data={"email": "nobody@example.com", "password": "AnyPassword123!"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Incorrect" in response.data or b"incorrect" in response.data


# ─────────────────────────────────────────────────────────────────────────────
# 12. Logout
# ─────────────────────────────────────────────────────────────────────────────

def test_logout(logged_in_client):
    """Logging out should redirect to the home page."""
    response = logged_in_client.get("/logout", follow_redirects=True)
    assert response.status_code == 200
    # After logout, going to dashboard should redirect to login
    response2 = logged_in_client.get("/dashboard", follow_redirects=True)
    assert b"Sign In" in response2.data or b"login" in response2.data.lower()


# ─────────────────────────────────────────────────────────────────────────────
# 13. Protected dashboard redirect
# ─────────────────────────────────────────────────────────────────────────────

def test_dashboard_requires_login(client):
    """Unauthenticated request to /dashboard should redirect to /login."""
    response = client.get("/dashboard", follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]
