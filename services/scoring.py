"""
services/scoring.py — Transparent match-score calculation.

This module calculates a numerical "Estimated Resume–Job Match" score
using component scores returned by the Gemini AI model.

WHY a separate scoring module?
  • Keeps scoring logic testable without needing the AI or Flask.
  • Makes the methodology transparent and easy to adjust.
  • Prevents the AI from fabricating an arbitrary percentage.

HOW the score is calculated:
  The AI returns component scores (0–10 scale) for:
    • skills        — how many relevant required skills are demonstrated
    • experience    — how well the experience matches job responsibilities
    • qualifications — how well education/certs match requirements

  We convert each component to a percentage contribution:
    • skills:         weight 50%
    • experience:     weight 30%
    • qualifications: weight 20%

  Final score = (skills/10 * 50) + (experience/10 * 30) + (qualifications/10 * 20)
  Clamped to 0–100.

These weights are configurable project defaults, NOT universal hiring standards.
"""

import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# ── Scoring weights ────────────────────────────────────────────────────────────
# Must add up to 100.  Change these if you want to experiment with different weights.
WEIGHTS = {
    "skills": 50,          # % contribution from skills component
    "experience": 30,      # % contribution from experience component
    "qualifications": 20,  # % contribution from qualifications component
}

# The AI returns component scores on a 0–10 scale
COMPONENT_MAX = 10


def calculate_match_score(components: Dict[str, float]) -> Optional[float]:
    """
    Convert component scores (0–10 each) into a final percentage score (0–100).

    Args:
        components: Dictionary with keys 'skills', 'experience', 'qualifications'
                    and float values between 0 and 10.

    Returns:
        A float between 0.0 and 100.0 representing the overall match.
        Returns None if the input is invalid.

    Example:
        components = {"skills": 7, "experience": 6, "qualifications": 8}
        score = calculate_match_score(components)
        # skills:         7/10 * 50  = 35.0
        # experience:     6/10 * 30  = 18.0
        # qualifications: 8/10 * 20  = 16.0
        # total                      = 69.0
    """
    if not components or not isinstance(components, dict):
        logger.warning("calculate_match_score: received empty or non-dict components")
        return None

    total_score = 0.0
    total_weight_applied = 0

    for component_name, weight in WEIGHTS.items():
        raw_value = components.get(component_name)

        if raw_value is None:
            logger.warning("Component '%s' missing from AI response", component_name)
            # We cannot score this component — skip it but note the limitation
            continue

        # Validate the component is a number in the expected range
        try:
            value = float(raw_value)
        except (TypeError, ValueError):
            logger.warning(
                "Component '%s' has non-numeric value: %r", component_name, raw_value
            )
            continue

        # Clamp to valid range
        value = max(0.0, min(COMPONENT_MAX, value))

        # Convert to percentage contribution: (value / max) * weight
        contribution = (value / COMPONENT_MAX) * weight
        total_score += contribution
        total_weight_applied += weight

    if total_weight_applied == 0:
        logger.warning("No valid components found; cannot calculate score")
        return None

    # If some components were missing, scale proportionally so we don't
    # artificially penalise candidates for incomplete AI responses.
    if total_weight_applied < sum(WEIGHTS.values()):
        scale_factor = sum(WEIGHTS.values()) / total_weight_applied
        total_score *= scale_factor
        logger.info(
            "Score scaled by %.2f because some components were missing", scale_factor
        )

    # Clamp final score to [0, 100]
    final_score = max(0.0, min(100.0, total_score))

    logger.info(
        "Score calculated: %.1f (components=%s, weights=%s)",
        final_score,
        components,
        WEIGHTS,
    )

    return round(final_score, 1)


def validate_component_scores(components: Dict) -> bool:
    """
    Check that all component scores are present and within range.

    Returns True if valid, False otherwise.
    """
    if not isinstance(components, dict):
        return False

    required_keys = set(WEIGHTS.keys())
    present_keys = set(components.keys())

    if not required_keys.issubset(present_keys):
        missing = required_keys - present_keys
        logger.warning("Missing component keys: %s", missing)
        return False

    for key in required_keys:
        val = components.get(key)
        try:
            fval = float(val)
            if not (0 <= fval <= COMPONENT_MAX):
                logger.warning("Component '%s' value %r out of range [0, %d]", key, val, COMPONENT_MAX)
                return False
        except (TypeError, ValueError):
            logger.warning("Component '%s' is not numeric: %r", key, val)
            return False

    return True


def get_score_description(score: Optional[float]) -> str:
    """Return a plain-English description of the score range."""
    if score is None:
        return "Score unavailable"
    if score >= 80:
        return "Strong match — your resume aligns well with this job description."
    if score >= 60:
        return "Good match — there are clear alignments and some areas to strengthen."
    if score >= 40:
        return "Moderate match — consider tailoring your resume more closely to this role."
    return "Low match — significant gaps detected. Consider developing missing skills or applying to better-fitting roles."
