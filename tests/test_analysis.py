"""
tests/test_analysis.py — AI analysis and scoring tests.

Tests:
  1.  Score calculation: correct result
  2.  Score calculation: missing component handled
  3.  Score calculation: out-of-range component clamped
  4.  Score calculation: empty input returns None
  5.  Score clamped to 0–100
  6.  Missing API key raises ConfigurationError
  7.  Gemini response validation — valid structure passes
  8.  Gemini response validation — missing field fails
  9.  Gemini response validation — invalid score range fails
 10.  analyze_resume with mocked API returns correct structure
 11.  Score description categories correct
"""

import json
import pytest

from services.scoring import calculate_match_score, validate_component_scores, get_score_description
from services.resume_analyzer import (
    analyze_resume,
    _validate_response,
    _extract_json_from_response,
    ConfigurationError,
    AnalysisError,
)


# ─────────────────────────────────────────────────────────────────────────────
# 1. Score calculation — correct weighted result
# ─────────────────────────────────────────────────────────────────────────────

def test_score_calculation_correct():
    """
    skills=7/10 * 50 = 35
    experience=6/10 * 30 = 18
    qualifications=8/10 * 20 = 16
    total = 69.0
    """
    components = {"skills": 7, "experience": 6, "qualifications": 8}
    score = calculate_match_score(components)
    assert score == 69.0


def test_score_calculation_perfect():
    """All components at 10 should give 100.0."""
    components = {"skills": 10, "experience": 10, "qualifications": 10}
    score = calculate_match_score(components)
    assert score == 100.0


def test_score_calculation_zero():
    """All components at 0 should give 0.0."""
    components = {"skills": 0, "experience": 0, "qualifications": 0}
    score = calculate_match_score(components)
    assert score == 0.0


# ─────────────────────────────────────────────────────────────────────────────
# 2. Missing component handled gracefully
# ─────────────────────────────────────────────────────────────────────────────

def test_score_missing_component():
    """Missing component should not crash — score is scaled proportionally."""
    components = {"skills": 8, "experience": 7}  # no 'qualifications'
    score = calculate_match_score(components)
    # Should be a valid float between 0 and 100
    assert score is not None
    assert 0.0 <= score <= 100.0


# ─────────────────────────────────────────────────────────────────────────────
# 3. Out-of-range component clamped
# ─────────────────────────────────────────────────────────────────────────────

def test_score_out_of_range_clamped():
    """Components outside [0, 10] should be clamped, not crash."""
    components = {"skills": 15, "experience": -2, "qualifications": 8}
    score = calculate_match_score(components)
    assert 0.0 <= score <= 100.0


# ─────────────────────────────────────────────────────────────────────────────
# 4. Empty input returns None
# ─────────────────────────────────────────────────────────────────────────────

def test_score_empty_input():
    """Empty dict should return None."""
    score = calculate_match_score({})
    assert score is None


def test_score_none_input():
    """None input should return None."""
    score = calculate_match_score(None)
    assert score is None


# ─────────────────────────────────────────────────────────────────────────────
# 5. Final score clamped to 0–100
# ─────────────────────────────────────────────────────────────────────────────

def test_score_always_in_range():
    """Any valid component dict should produce a score in [0, 100]."""
    for val in [0, 5, 10]:
        components = {"skills": val, "experience": val, "qualifications": val}
        score = calculate_match_score(components)
        assert 0.0 <= score <= 100.0


# ─────────────────────────────────────────────────────────────────────────────
# 6. Missing API key raises ConfigurationError
# ─────────────────────────────────────────────────────────────────────────────

def test_missing_api_key_raises():
    """analyze_resume with no API key should raise ConfigurationError."""
    with pytest.raises(ConfigurationError):
        analyze_resume(
            resume_text="This is a test resume with Python SQL experience.",
            job_description="Looking for a Python developer with SQL skills.",
            api_key="",        # empty → no key
            model_name="gemini-2.0-flash",
        )


# ─────────────────────────────────────────────────────────────────────────────
# 7. Validate response — valid structure passes
# ─────────────────────────────────────────────────────────────────────────────

def test_validate_response_valid():
    """A correctly structured dict should pass validation."""
    valid = {
        "summary": "Good match.",
        "skills": {"matching": ["Python"], "missing": ["Docker"], "uncertain": []},
        "experience_alignment": ["Relevant experience"],
        "strengths": ["Strong coder"],
        "improvements": ["Learn Docker"],
        "keywords": {"present": ["Python"], "missing_or_weak": ["AWS"]},
        "components": {"skills": 7.0, "experience": 6.0, "qualifications": 8.0},
    }
    is_valid, msg = _validate_response(valid)
    assert is_valid is True
    assert msg == ""


# ─────────────────────────────────────────────────────────────────────────────
# 8. Validate response — missing required field fails
# ─────────────────────────────────────────────────────────────────────────────

def test_validate_response_missing_field():
    """A dict missing 'summary' should fail validation."""
    invalid = {
        # "summary" is missing
        "skills": {"matching": [], "missing": [], "uncertain": []},
        "experience_alignment": [],
        "strengths": [],
        "improvements": [],
        "keywords": {"present": [], "missing_or_weak": []},
        "components": {"skills": 5, "experience": 5, "qualifications": 5},
    }
    is_valid, msg = _validate_response(invalid)
    assert is_valid is False
    assert "summary" in msg


# ─────────────────────────────────────────────────────────────────────────────
# 9. Validate response — score out of range
# ─────────────────────────────────────────────────────────────────────────────

def test_validate_response_score_out_of_range():
    """A component score of 11 (> 10) should fail validation."""
    invalid = {
        "summary": "Test.",
        "skills": {"matching": [], "missing": [], "uncertain": []},
        "experience_alignment": [],
        "strengths": [],
        "improvements": [],
        "keywords": {"present": [], "missing_or_weak": []},
        "components": {"skills": 11.0, "experience": 5.0, "qualifications": 5.0},  # 11 > 10
    }
    is_valid, msg = _validate_response(invalid)
    assert is_valid is False
    assert "range" in msg.lower() or "skills" in msg


# ─────────────────────────────────────────────────────────────────────────────
# 10. analyze_resume with mocked Gemini API
# ─────────────────────────────────────────────────────────────────────────────

def test_analyze_resume_mocked_api():
    """
    Tests the full JSON parsing and validation pipeline without a real API call.

    The google-genai import is deferred inside analyze_resume() so it gracefully
    handles the case where the package is missing.  We test the pipeline by calling
    the internal helper functions directly — this is the same code path that runs
    after a real API call returns a response.
    """
    mock_response_json = json.dumps({
        "summary": "Good match for this Python role.",
        "skills": {
            "matching": ["Python", "SQL"],
            "missing": ["Docker"],
            "uncertain": ["Kubernetes"]
        },
        "experience_alignment": ["Backend experience aligns with role requirements."],
        "strengths": ["Strong Python background"],
        "improvements": ["Add Docker experience"],
        "keywords": {
            "present": ["Python", "SQL"],
            "missing_or_weak": ["Docker", "AWS"]
        },
        "components": {
            "skills": 7.5,
            "experience": 6.0,
            "qualifications": 8.0
        },
        "recommendations": ["Take a Docker course", "Add a portfolio project"]
    })

    # ── Step 1: parse raw JSON text (as analyze_resume does after API call) ──
    data = _extract_json_from_response(mock_response_json)

    # ── Step 2: validate the parsed structure ──────────────────────────────────
    is_valid, msg = _validate_response(data)
    assert is_valid is True, f"Validation failed: {msg}"

    # ── Step 3: check key fields ───────────────────────────────────────────────
    assert data["summary"] == "Good match for this Python role."
    assert "Python" in data["skills"]["matching"]
    assert "Docker" in data["skills"]["missing"]
    assert data["components"]["skills"] == 7.5
    assert data["components"]["experience"] == 6.0

    # ── Step 4: verify score calculation works end-to-end ─────────────────────
    from services.scoring import calculate_match_score
    score = calculate_match_score(data["components"])
    # 7.5/10*50 + 6.0/10*30 + 8.0/10*20 = 37.5 + 18.0 + 16.0 = 71.5
    assert score == 71.5


# ─────────────────────────────────────────────────────────────────────────────
# 11. Score description categories
# ─────────────────────────────────────────────────────────────────────────────

def test_score_description_high():
    """Score >= 80 should give a positive description."""
    desc = get_score_description(85.0)
    assert "Strong" in desc or "strong" in desc.lower()


def test_score_description_medium():
    """Score 60–79 should indicate good match with room to grow."""
    desc = get_score_description(65.0)
    assert desc  # just check it returns something non-empty


def test_score_description_low():
    """Score < 40 should indicate a low match."""
    desc = get_score_description(25.0)
    assert "Low" in desc or "low" in desc.lower() or "gaps" in desc.lower()


def test_score_description_none():
    """None score should return 'unavailable' message."""
    desc = get_score_description(None)
    assert "unavailable" in desc.lower()


# ─────────────────────────────────────────────────────────────────────────────
# JSON extraction — handles markdown fences
# ─────────────────────────────────────────────────────────────────────────────

def test_extract_json_strips_markdown_fences():
    """_extract_json_from_response should handle ```json ... ``` wrapping."""
    wrapped = '```json\n{"key": "value"}\n```'
    result = _extract_json_from_response(wrapped)
    assert result == {"key": "value"}


def test_extract_json_plain():
    """Plain JSON should be extracted without modification."""
    plain = '{"key": "value"}'
    result = _extract_json_from_response(plain)
    assert result == {"key": "value"}


def test_extract_json_empty_raises():
    """Empty string should raise AnalysisError."""
    with pytest.raises(AnalysisError):
        _extract_json_from_response("")


def test_validate_component_scores_valid():
    """validate_component_scores should return True for valid input."""
    assert validate_component_scores({"skills": 7, "experience": 6, "qualifications": 8}) is True


def test_validate_component_scores_invalid():
    """validate_component_scores should return False for out-of-range input."""
    assert validate_component_scores({"skills": 11, "experience": 6, "qualifications": 8}) is False
