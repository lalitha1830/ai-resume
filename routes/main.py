"""
routes/main.py — Main application routes: landing page, dashboard, history, profile.

Routes:
  GET /           — public landing page
  GET /dashboard  — authenticated dashboard
  GET /history    — analysis history list
  GET /profile    — user profile page
"""

import logging
from datetime import timezone

from flask import Blueprint, render_template, redirect, url_for
from flask_login import current_user, login_required

from extensions import db
from models.user import User, Analysis

logger = logging.getLogger(__name__)

main_bp = Blueprint("main", __name__)


# ── Landing page ───────────────────────────────────────────────────────────────

@main_bp.route("/")
def index():
    """
    Public landing page.

    Authenticated users who visit the root URL are NOT automatically
    redirected — they see the landing page.  The "Get Started" button
    in the template handles the redirect logic.
    """
    return render_template("index.html")


# ── Dashboard ──────────────────────────────────────────────────────────────────

@main_bp.route("/dashboard")
@login_required   # Unauthenticated users are redirected to /login
def dashboard():
    """
    Authenticated user dashboard showing summary stats and recent analyses.

    We query ONLY the current user's analyses — never all users' analyses.
    """
    # Most recent 5 analyses for the "Recent Analyses" section
    recent_analyses = (
        Analysis.query
        .filter_by(user_id=current_user.id)
        .order_by(Analysis.created_at.desc())
        .limit(5)
        .all()
    )

    # Summary statistics from the current user's data
    all_analyses = (
        Analysis.query
        .filter_by(user_id=current_user.id)
        .all()
    )

    total_count = len(all_analyses)
    scores = [a.match_score for a in all_analyses if a.match_score is not None]
    average_score = round(sum(scores) / len(scores), 1) if scores else None
    latest_analysis = recent_analyses[0] if recent_analyses else None

    return render_template(
        "dashboard.html",
        recent_analyses=recent_analyses,
        total_count=total_count,
        average_score=average_score,
        latest_analysis=latest_analysis,
    )


# ── History ────────────────────────────────────────────────────────────────────

@main_bp.route("/history")
@login_required
def history():
    """
    Full analysis history for the current user, sorted newest first.
    """
    analyses = (
        Analysis.query
        .filter_by(user_id=current_user.id)
        .order_by(Analysis.created_at.desc())
        .all()
    )

    return render_template("history.html", analyses=analyses)


# ── Profile ────────────────────────────────────────────────────────────────────

@main_bp.route("/profile")
@login_required
def profile():
    """
    User profile page — shows account information.
    """
    # Count total analyses for the profile summary
    total_analyses = Analysis.query.filter_by(user_id=current_user.id).count()

    return render_template("profile.html", total_analyses=total_analyses)
