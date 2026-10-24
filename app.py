"""
app.py — ResumeAI Flask application entry point.

This file:
  1. Creates the Flask application using the Application Factory pattern.
  2. Initialises all extensions (database, login manager, CSRF).
  3. Creates the database tables if they don't already exist.
  4. Registers URL blueprints (auth routes, main routes, analysis routes).
  5. Configures error handlers.
  6. Starts the development server when run directly.

HOW TO RUN (in your terminal):
  python app.py
  # Then open http://127.0.0.1:5000 in your browser
"""

import os
import logging
from datetime import datetime, timezone

from flask import Flask, render_template, flash, redirect, url_for

from config import get_config
from extensions import db, login_manager, csrf


# ── Logging setup ──────────────────────────────────────────────────────────────
# This sends log messages to the terminal so you can see what is happening.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def create_app(config_class=None):
    """
    Application Factory: create and configure the Flask app.

    Using a factory function (instead of creating the app at module level)
    makes it easy to create different app instances for testing vs production.
    """
    app = Flask(__name__)

    # ── Load configuration ────────────────────────────────────────────────────
    if config_class is None:
        config_class = get_config()
    app.config.from_object(config_class)

    # Ensure the instance/ folder exists so SQLite can create the database file
    os.makedirs(app.instance_path, exist_ok=True)

    # ── Initialise extensions ─────────────────────────────────────────────────
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    # ── Register the user loader ──────────────────────────────────────────────
    # Flask-Login calls this function to load the user from the session.
    from models.user import User

    @login_manager.user_loader
    def load_user(user_id: str):
        """Load user by primary key — called on every request for logged-in users."""
        return db.session.get(User, int(user_id))

    # ── Register blueprints (route groups) ────────────────────────────────────
    from routes.auth import auth_bp
    from routes.main import main_bp
    from routes.analysis import analysis_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(analysis_bp)

    # ── Create database tables ────────────────────────────────────────────────
    with app.app_context():
        db.create_all()
        logger.info("Database tables created/verified.")

    # ── Template context processor ────────────────────────────────────────────
    @app.context_processor
    def inject_globals():
        """Make 'now' available in all templates for footer copyright year."""
        return {"now": datetime.now(timezone.utc)}

    # ── Error handlers ────────────────────────────────────────────────────────
    @app.errorhandler(403)
    def forbidden(e):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def page_not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(413)
    def file_too_large(e):
        flash("The uploaded file is too large. Maximum size is 5 MB.", "error")
        return redirect(url_for("analysis.new_analysis")), 302

    @app.errorhandler(500)
    def internal_error(e):
        logger.error("Internal server error: %s", e)
        db.session.rollback()  # Roll back any failed database transaction
        return render_template("errors/500.html"), 500

    # ── Security headers ──────────────────────────────────────────────────────
    @app.after_request
    def add_security_headers(response):
        """Add basic HTTP security headers to every response."""
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response

    return app


# ── Development server entry point ────────────────────────────────────────────
app = create_app()

if __name__ == "__main__":
    port = 5000

    # ── ngrok tunnel (only when NGROK_ENABLED=true) ───────────────────────────
    if app.config.get("NGROK_ENABLED"):
        try:
            from pyngrok import ngrok, conf

            authtoken = app.config.get("NGROK_AUTHTOKEN", "")
            if not authtoken:
                logger.warning("NGROK_AUTHTOKEN is not set — skipping tunnel.")
            else:
                conf.get_default().auth_token = authtoken
                tunnel = ngrok.connect(port, "http")
                public_url = tunnel.public_url
                # Upgrade to HTTPS
                if public_url.startswith("http://"):
                    public_url = public_url.replace("http://", "https://", 1)
                logger.info("╔════════════════════════════════════════════════════╗")
                logger.info("║  🌐 ngrok public URL : %s", public_url)
                logger.info("╚════════════════════════════════════════════════════╝")
        except ImportError:
            logger.warning(
                "pyngrok is not installed. Run: pip install pyngrok  — skipping tunnel."
            )

    app.run(
        host="127.0.0.1",
        port=port,
        debug=app.config.get("DEBUG", True),
    )
