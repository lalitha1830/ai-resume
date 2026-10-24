"""
extensions.py — Shared Flask extension instances.

Flask extensions (SQLAlchemy, LoginManager, CSRFProtect) need to be
created BEFORE the Flask app object exists, so they can be registered
onto the app later.  This pattern is called the "Application Factory"
pattern and avoids circular import problems.

In simple terms:
  1. We create the extension objects HERE (no app attached yet).
  2. app.py creates the Flask app and calls db.init_app(app), etc.
  3. Now every module can import db from extensions without circular imports.
"""

from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect

# ── Database ORM ──────────────────────────────────────────────────────────────
db = SQLAlchemy()

# ── Authentication manager ────────────────────────────────────────────────────
login_manager = LoginManager()

# Tell Flask-Login which route to redirect to when an unauthenticated user
# tries to access a @login_required page.
login_manager.login_view = "auth.login"
login_manager.login_message = "Please sign in to continue."
login_manager.login_message_category = "info"

# ── CSRF protection ───────────────────────────────────────────────────────────
csrf = CSRFProtect()
