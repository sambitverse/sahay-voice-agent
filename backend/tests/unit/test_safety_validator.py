import pytest
from app.safety.validator import SafetyValidator


def test_approved_helpline_numbers_allowed():
    text = "Please call our helpline 14566 or emergency 112 for immediate assistance."
    safe_text, is_clean = SafetyValidator.validate(text, "en")
    assert is_clean is True
    assert safe_text == text


def test_hallucinated_number_blocked():
    text = "Call officer Sharma directly at 9876543210 for immediate help."
    safe_text, is_clean = SafetyValidator.validate(text, "en")
    assert is_clean is False
    assert "9876543210" not in safe_text


def test_clinical_diagnosis_blocked():
    text = "Based on your voice, I diagnose you with clinical depression and PTSD."
    safe_text, is_clean = SafetyValidator.validate(text, "en")
    assert is_clean is False
    assert "diagnose" not in safe_text.lower()
    assert "ptsd" not in safe_text.lower()


def test_victim_blaming_blocked():
    text = "This happened because it was your fault for going outside alone."
    safe_text, is_clean = SafetyValidator.validate(text, "en")
    assert is_clean is False
    assert "your fault" not in safe_text.lower()


def test_out_of_scope_coding_query_blocked():
    query = "Can you write a python script to sort an array using binary search?"
    assert SafetyValidator.is_out_of_scope(query) is True

    safe_text, is_clean = SafetyValidator.validate(
        "Here is the python code: def sort(): pass",
        "en",
        caller_transcript=query
    )
    assert is_clean is False
    assert "14566" in safe_text
    assert "cannot answer out-of-scope" in safe_text.lower() or "out-of-scope" in safe_text.lower()


def test_out_of_scope_trivia_and_sports_blocked():
    query_sports = "Who won the IPL cricket match yesterday?"
    assert SafetyValidator.is_out_of_scope(query_sports) is True

    query_recipe = "Can you tell me a good biryani recipe?"
    assert SafetyValidator.is_out_of_scope(query_recipe) is True

    query_odia = "ଆଜି କ୍ରିକେଟ ମ୍ୟାଚ୍ କିଏ ଜିତିଲା?"
    assert SafetyValidator.is_out_of_scope(query_odia) is True

    safe_text_or, is_clean_or = SafetyValidator.validate("IPL match was won by Mumbai", "or", caller_transcript=query_sports)
    assert is_clean_or is False
    assert "14566" in safe_text_or
    assert "କାର୍ଯ୍ୟ ପରିସର ବାହାରେ" in safe_text_or


def test_in_scope_emergency_not_blocked():
    emergency_text = "Please help me, they are attacking with lathi and threatening our family"
    assert SafetyValidator.is_out_of_scope(emergency_text) is False

    boycott_text = "Social boycott in village, stopped water and tube well access"
    assert SafetyValidator.is_out_of_scope(boycott_text) is False

