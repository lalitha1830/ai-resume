"""
routes/auth.py — Authentication routes: register, login, logout.

A Flask Blueprint groups related routes together.  This blueprint handles
everything related to user accounts.

Routes:
  GET  /register  — show registration form
  POST /register  — process registration form
  GET  /login     — show login form
  POST /login     — process login form
  GET  /logout    — log out the current user

Security measures applied here:
  • Password hashing via Werkzeug (never stored in plaintext)
  • CSRF tokens on all forms (managed by Flask-WTF)
  • Generic error message for failed logins (prevents user enumeration)
  • Email normalisation (lowercase, strip whitespace)
  • Safe redirect after login (prevents open redirect attacks)
  • Flask-Login session management
"""

import logging
import re

from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required, login_user, logout_user
from werkzeug.security import generate_password_hash

from extensions import db
from models.user import User

logger = logging.getLogger(__name__)

# Create the blueprint — all routes below are prefixed with nothing extra
auth_bp = Blueprint("auth", __name__)

# Minimum acceptable password length
MIN_PASSWORD_LENGTH = 12


def normalize_email(email: str) -> str:
    """Lowercase and strip the email address."""
    return email.strip().lower()


def is_valid_email(email: str) -> bool:
    """Basic email format check using a regular expression."""
    pattern = r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


def is_safe_redirect_url(url: str) -> bool:
    """
    Ensure the redirect URL is relative (starts with /) so we cannot be
    tricked into redirecting to a malicious external site.
    """
    return url and url.startswith("/") and not url.startswith("//")


# ── Registration ───────────────────────────────────────────────────────────────

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    """Show and process the registration form."""

    # Redirect already-logged-in users to the dashboard
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        # ── Read form data ────────────────────────────────────────────────────
        full_name = request.form.get("full_name", "").strip()
        email = normalize_email(request.form.get("email", ""))
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        # ── Server-side validation ────────────────────────────────────────────
        errors = []

        if not full_name or len(full_name) < 2:
            errors.append("Please enter your full name (at least 2 characters).")

        if not email:
            errors.append("Email address is required.")
        elif not is_valid_email(email):
            errors.append("Please enter a valid email address.")

        if not password:
            errors.append("Password is required.")
        elif len(password) < MIN_PASSWORD_LENGTH:
            errors.append(
                f"Password must be at least {MIN_PASSWORD_LENGTH} characters long."
            )

        if password and confirm_password != password:
            errors.append("Passwords do not match. Please try again.")

        if errors:
            for error in errors:
                flash(error, "error")
            # Re-render form with the values they entered (except passwords)
            return render_template(
                "register.html",
                form_data={"full_name": full_name, "email": email},
            )

        # ── Check for duplicate email ─────────────────────────────────────────
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash(
                "An account with that email address already exists. "
                "Please sign in or use a different email.",
                "error",
            )
            return render_template(
                "register.html",
                form_data={"full_name": full_name, "email": email},
            )

        # ── Create and save new user ──────────────────────────────────────────
        try:
            new_user = User(full_name=full_name, email=email)
            new_user.set_password(password)  # hashes the password
            db.session.add(new_user)
            db.session.commit()
            logger.info("New user registered: id=%d", new_user.id)
        except Exception as exc:
            db.session.rollback()
            logger.error("Database error during registration: %s", exc)
            flash(
                "We couldn't create your account right now. Please try again.",
                "error",
            )
            return render_template(
                "register.html",
                form_data={"full_name": full_name, "email": email},
            )

        # ── Log the user in automatically and go to dashboard ─────────────────
        login_user(new_user)
        flash("Welcome to ResumeAI! Your account has been created.", "success")
        return redirect(url_for("main.dashboard"))

    # GET request — show empty form
    return render_template("register.html", form_data={})


# ── Login ──────────────────────────────────────────────────────────────────────

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Show and process the login form."""

    # Already logged in — go to dashboard
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        email = normalize_email(request.form.get("email", ""))
        password = request.form.get("password", "")
        remember_me = bool(request.form.get("remember_me"))

        # ── Validate input ────────────────────────────────────────────────────
        if not email or not password:
            flash("Please enter your email address and password.", "error")
            return render_template("login.html", form_data={"email": email})

        # ── Look up user ──────────────────────────────────────────────────────
        user = User.query.filter_by(email=email).first()

        # IMPORTANT: Use a GENERIC error message whether the email or password
        # is wrong.  Specific messages like "email not found" allow attackers
        # to discover which emails are registered (user enumeration).
        if user is None or not user.check_password(password):
            flash(
                "Incorrect email address or password. Please try again.",
                "error",
            )
            logger.info("Failed login attempt for email: %s", email)
            return render_template("login.html", form_data={"email": email})

        # ── Success: create session ───────────────────────────────────────────
        login_user(user, remember=remember_me)
        logger.info("User logged in: id=%d", user.id)

        # Safe redirect: only redirect to relative URLs
        next_page = request.args.get("next")
        if next_page and is_safe_redirect_url(next_page):
            return redirect(next_page)

        return redirect(url_for("main.dashboard"))

    # GET request
    return render_template("login.html", form_data={})


# ── Logout ─────────────────────────────────────────────────────────────────────

@auth_bp.route("/logout")
@login_required
def logout():
    """Log out the current user and redirect to the home page."""
    user_id = current_user.id
    logout_user()
    logger.info("User logged out: id=%d", user_id)
    flash("You have been signed out successfully.", "success")
    return redirect(url_for("main.index"))
