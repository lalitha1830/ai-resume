"""
models/user.py — Database models for ResumeAI.

Two tables:
  • User    — stores account information
  • Analysis — stores each resume-analysis result for a user

SQLAlchemy is the ORM (Object-Relational Mapper) that translates
Python classes into database tables automatically.

Flask-Login uses the UserMixin helpers so it can manage sessions.
"""

from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from extensions import db   # shared SQLAlchemy instance (see extensions.py)


class User(UserMixin, db.Model):
    """
    Represents a registered user.

    UserMixin adds is_authenticated, is_active, is_anonymous, and get_id()
    methods that Flask-Login requires — we don't have to write them ourselves.
    """

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(254), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    # One user can have many analyses.  'lazy=True' means the analyses are
    # fetched from the database only when you access user.analyses — not every
    # time you load the user object.
    analyses = db.relationship(
        "Analysis",
        back_populates="user",
        lazy=True,
        cascade="all, delete-orphan",  # deleting the user also deletes their analyses
        order_by="Analysis.created_at.desc()",
    )

    # ── Password helpers ───────────────────────────────────────────────────────

    def set_password(self, plaintext_password: str) -> None:
        """
        Hash the password and store it.  NEVER store the plaintext password.

        Werkzeug uses scrypt (or pbkdf2 as a fallback) — both are strong
        one-way hashing algorithms designed for passwords.
        """
        self.password_hash = generate_password_hash(plaintext_password)

    def check_password(self, plaintext_password: str) -> bool:
        """Return True if the supplied password matches the stored hash."""
        return check_password_hash(self.password_hash, plaintext_password)

    # ── Convenience properties ────────────────────────────────────────────────

    @property
    def first_name(self) -> str:
        """Return the first word of the user's full name for friendly greetings."""
        return self.full_name.split()[0] if self.full_name else "there"

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r}>"


class Analysis(db.Model):
    """
    Represents one resume-analysis session for a user.

    The full structured JSON returned by Gemini is stored in
    analysis_result_json so the results page can display every detail
    without calling the AI again.

    The uploaded resume file is NOT stored — only the analysis results.
    """

    __tablename__ = "analyses"

    id = db.Column(db.Integer, primary_key=True)

    # Foreign key links this row to the user who owns it.
    # ondelete="CASCADE" ensures the database also removes orphaned analyses
    # if the user row is deleted directly via SQL (not just through SQLAlchemy).
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Optional label the user provides (e.g. "Software Engineer at Acme")
    analysis_title = db.Column(db.String(200), nullable=True)

    # The job title extracted from the description or supplied by the user
    job_title = db.Column(db.String(200), nullable=True)

    # The match score (0–100).  We store it separately so the history
    # page can display scores quickly without parsing the full JSON.
    match_score = db.Column(db.Float, nullable=True)

    # Full structured analysis JSON returned by Gemini (validated before storing)
    analysis_result_json = db.Column(db.Text, nullable=True)

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Back-reference to the User model
    user = db.relationship("User", back_populates="analyses")

    # ── Convenience helpers ────────────────────────────────────────────────────

    @property
    def display_title(self) -> str:
        """Return a human-readable title for list views."""
        if self.analysis_title:
            return self.analysis_title
        if self.job_title:
            return self.job_title
        return f"Analysis #{self.id}"

    @property
    def score_label(self) -> str:
        """Return a colour-coded category based on the score."""
        if self.match_score is None:
            return "unknown"
        if self.match_score >= 75:
            return "high"
        if self.match_score >= 50:
            return "medium"
        return "low"

    @property
    def formatted_date(self) -> str:
        """Return a readable date string for templates."""
        if self.created_at:
            return self.created_at.strftime("%b %d, %Y · %I:%M %p")
        return "Unknown date"

    def __repr__(self) -> str:
        return f"<Analysis id={self.id} user_id={self.user_id} score={self.match_score}>"
