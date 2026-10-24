"""
routes/analysis.py — Resume analysis routes.

Routes:
  GET  /analyze              — show the analysis form
  POST /analyze              — process the uploaded resume and job description
  GET  /analysis/<id>        — view individual analysis results
  GET  /analysis/<id>/delete — show delete confirmation page
  POST /analysis/<id>/delete — delete the analysis

Security:
  • All routes require login.
  • Ownership is verified before showing or deleting any analysis.
  • Files are read into memory and not stored on disk.
  • Job description length is validated server-side.
  • Uploaded files are validated for extension (no size limit).
  • CSRF tokens protect all state-changing forms.
"""

import json
import logging

from flask import (
    Blueprint,
    abort,
    flash,
    redirect,
    render_template,
    request,
    url_for,
    current_app,
)
from flask_login import current_user, login_required

from extensions import db
from models.user import Analysis
from services.resume_parser import parse_resume, ResumeParseError
from services.resume_analyzer import analyze_resume, AnalysisError, ConfigurationError
from services.scoring import calculate_match_score, get_score_description

logger = logging.getLogger(__name__)

analysis_bp = Blueprint("analysis", __name__)

ALLOWED_EXTENSIONS = {"pdf", "docx", "json"}


def allowed_file(filename: str) -> bool:
    """Return True if the filename has a supported extension."""
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


# ── New analysis form ──────────────────────────────────────────────────────────

@analysis_bp.route("/analyze", methods=["GET", "POST"])
@login_required
def new_analysis():
    """
    GET  — Show the analysis form.
    POST — Process the uploaded resume and job description.
    """

    if request.method == "POST":
        # ── Read form fields ──────────────────────────────────────────────────
        analysis_title = request.form.get("analysis_title", "").strip()
        job_title = request.form.get("job_title", "").strip()
        job_description = request.form.get("job_description", "").strip()
        uploaded_file = request.files.get("resume_file")

        logger.info(
            "POST /analyze — user_id=%d jd_len=%d file=%s",
            current_user.id,
            len(job_description),
            uploaded_file.filename if uploaded_file else "(none)",
        )

        max_jd_length = current_app.config.get("MAX_JOB_DESCRIPTION_LENGTH", 8000)

        # ── Validate job description ──────────────────────────────────────────
        if not job_description or len(job_description) < 30:
            flash("Please provide a meaningful job description (at least 30 characters).", "error")
            return render_template(
                "analyze.html",
                form_data={
                    "analysis_title": analysis_title,
                    "job_title": job_title,
                    "job_description": job_description,
                },
            )

        if len(job_description) > max_jd_length:
            flash(
                f"Job description is too long (maximum {max_jd_length} characters). "
                "Please shorten it.",
                "error",
            )
            return render_template(
                "analyze.html",
                form_data={
                    "analysis_title": analysis_title,
                    "job_title": job_title,
                    "job_description": job_description[:max_jd_length],
                },
            )

        # ── Validate file upload ──────────────────────────────────────────────
        if not uploaded_file or uploaded_file.filename == "":
            logger.warning("Upload rejected: no file selected (user_id=%d)", current_user.id)
            flash("Please upload your resume (PDF, DOCX, or JSON).", "error")
            return render_template(
                "analyze.html",
                form_data={
                    "analysis_title": analysis_title,
                    "job_title": job_title,
                    "job_description": job_description,
                },
            )

        if not allowed_file(uploaded_file.filename):
            logger.warning(
                "Upload rejected: bad extension '%s' (user_id=%d)",
                uploaded_file.filename, current_user.id,
            )
            flash(
                "Unsupported file type. Please upload a PDF (.pdf), "
                "Word document (.docx), or JSON file (.json).",
                "error",
            )
            return render_template(
                "analyze.html",
                form_data={
                    "analysis_title": analysis_title,
                    "job_title": job_title,
                    "job_description": job_description,
                },
            )

        # ── Read file bytes (into memory — not saved to disk) ─────────────────
        try:
            file_bytes = uploaded_file.read()
        except Exception as exc:
            logger.warning("Could not read uploaded file: %s", exc)
            flash("We couldn't read the uploaded file. Please try again.", "error")
            return render_template("analyze.html", form_data={
                "analysis_title": analysis_title,
                "job_title": job_title,
                "job_description": job_description,
            })

        if len(file_bytes) == 0:
            flash("The uploaded file is empty.", "error")
            return render_template("analyze.html", form_data={
                "analysis_title": analysis_title,
                "job_title": job_title,
                "job_description": job_description,
            })

        # ── Extract text from resume ──────────────────────────────────────────
        try:
            resume_text = parse_resume(file_bytes, uploaded_file.filename)
            logger.info("Resume parsed OK: %d chars (user_id=%d)", len(resume_text), current_user.id)
        except ResumeParseError as exc:
            logger.warning("Resume parse failed (user_id=%d): %s", current_user.id, exc)
            flash(str(exc), "error")
            return render_template("analyze.html", form_data={
                "analysis_title": analysis_title,
                "job_title": job_title,
                "job_description": job_description,
            })

        # ── Run AI analysis ───────────────────────────────────────────────────
        try:
            analysis_data = analyze_resume(
                resume_text=resume_text,
                job_description=job_description,
                job_title=job_title or analysis_title or None,
                api_key=current_app.config.get("GEMINI_API_KEY"),
                model_name=current_app.config.get("GEMINI_MODEL"),
            )
        except ConfigurationError as exc:
            flash(str(exc), "error")
            return render_template("analyze.html", form_data={
                "analysis_title": analysis_title,
                "job_title": job_title,
                "job_description": job_description,
            })
        except AnalysisError as exc:
            flash(str(exc), "error")
            return render_template("analyze.html", form_data={
                "analysis_title": analysis_title,
                "job_title": job_title,
                "job_description": job_description,
            })

        # ── Calculate score ───────────────────────────────────────────────────
        components = analysis_data.get("components", {})
        match_score = calculate_match_score(components)

        # ── Save to database ──────────────────────────────────────────────────
        try:
            new_analysis = Analysis(
                user_id=current_user.id,
                analysis_title=analysis_title or None,
                job_title=job_title or None,
                match_score=match_score,
                analysis_result_json=json.dumps(analysis_data),
            )
            db.session.add(new_analysis)
            db.session.commit()
            logger.info(
                "Analysis saved: id=%d user_id=%d score=%.1f",
                new_analysis.id,
                current_user.id,
                match_score or 0,
            )
        except Exception as exc:
            db.session.rollback()
            logger.error("Database error saving analysis: %s", exc)
            flash(
                "Your analysis completed but we couldn't save the results. "
                "Please try again.",
                "error",
            )
            return render_template("analyze.html", form_data={
                "analysis_title": analysis_title,
                "job_title": job_title,
                "job_description": job_description,
            })

        flash("Your analysis has been completed successfully!", "success")
        return redirect(url_for("analysis.view_analysis", analysis_id=new_analysis.id))

    # GET — show empty form
    return render_template("analyze.html", form_data={})


# ── View individual analysis results ──────────────────────────────────────────

@analysis_bp.route("/analysis/<int:analysis_id>")
@login_required
def view_analysis(analysis_id: int):
    """
    Show the full results for a single analysis.

    Security: verify the analysis belongs to the current user before displaying.
    """
    analysis = db.session.get(Analysis, analysis_id)

    if analysis is None:
        abort(404)

    # Ownership check — NEVER show another user's analysis
    if analysis.user_id != current_user.id:
        logger.warning(
            "Unauthorized access attempt: user %d tried to view analysis %d (owner: %d)",
            current_user.id,
            analysis_id,
            analysis.user_id,
        )
        abort(403)

    # Parse the stored JSON
    analysis_data = {}
    if analysis.analysis_result_json:
        try:
            analysis_data = json.loads(analysis.analysis_result_json)
        except json.JSONDecodeError:
            flash("The analysis data appears to be corrupted.", "error")

    score_description = get_score_description(analysis.match_score)

    return render_template(
        "results.html",
        analysis=analysis,
        analysis_data=analysis_data,
        score_description=score_description,
    )


# ── Delete analysis ────────────────────────────────────────────────────────────

@analysis_bp.route("/analysis/<int:analysis_id>/delete", methods=["GET", "POST"])
@login_required
def delete_analysis(analysis_id: int):
    """
    GET  — Show a confirmation page before deleting.
    POST — Actually delete the analysis.

    We use a server-rendered confirmation page instead of a JavaScript dialog.
    The POST form includes a CSRF token for security.
    """
    analysis = db.session.get(Analysis, analysis_id)

    if analysis is None:
        abort(404)

    # Ownership check
    if analysis.user_id != current_user.id:
        logger.warning(
            "Unauthorized delete attempt: user %d tried to delete analysis %d",
            current_user.id,
            analysis_id,
        )
        abort(403)

    if request.method == "POST":
        try:
            db.session.delete(analysis)
            db.session.commit()
            logger.info("Analysis deleted: id=%d by user=%d", analysis_id, current_user.id)
            flash("Analysis deleted successfully.", "success")
        except Exception as exc:
            db.session.rollback()
            logger.error("Error deleting analysis: %s", exc)
            flash("We couldn't delete this analysis. Please try again.", "error")

        return redirect(url_for("main.history"))

    # GET — show confirmation page
    return render_template("delete_confirmation.html", analysis=analysis)
