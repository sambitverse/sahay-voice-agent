import pytest
from app.trauma.state_machine import ConversationStateManager, ConversationState
from app.safety.validator import SafetyValidator


def test_wilderness_pursuit_environment_detection():
    manager = ConversationStateManager()

    caller_text = "mate maribaku godauchanti mu ebe jangala re nuchiki achi"
    env = manager.detect_environment(caller_text)

    assert env["wilderness"] is True
    assert env["pursuit"] is True
    assert env["indoors"] is False


def test_wilderness_prompt_bans_door_locking():
    manager = ConversationStateManager()

    caller_text = "mate maribaku godauchanti mu ebe jangala re nuchiki achi"
    prompt = manager.get_system_prompt_for_state(
        state=ConversationState.PROBLEM_ASSESSMENT,
        language_code="or-IN",
        risk_level="CRITICAL",
        latest_transcript=caller_text
    )

    # Must contain wilderness survival mandate
    assert "CRITICAL SPATIAL MANDATE — CALLER IS OUTDOORS IN JUNGLE/WILDERNESS" in prompt
    assert "ABSOLUTE BAN: NEVER tell the caller to lock house doors" in prompt
    assert "SILENT" in prompt


def test_safety_validator_blocks_indoor_hallucination_in_forest():
    caller_text = "mate maribaku godauchanti mu ebe jangala re nuchiki achi"

    # Suppose Gemini hallucinated door-locking advice:
    hallucinated_response = "Apan bilkul chinta karantu nahi, ghara kabata band kariki basantu."

    validated_text, is_clean = SafetyValidator.validate(
        text=hallucinated_response,
        language_code="or-IN",
        caller_transcript=caller_text
    )

    # Must be intercepted and replaced with safe outdoor survival directive
    assert is_clean is False
    assert "kabata band" not in validated_text
    assert "ghara" not in validated_text
    assert "jangala re nuchiki ruhantu" in validated_text
    assert "phone silent" in validated_text


def test_wilderness_fallback_phrase():
    manager = ConversationStateManager()

    caller_text = "mate maribaku godauchanti mu ebe jangala re nuchiki achi"
    fallback = manager.get_fallback_phrase(
        language_code="or-IN",
        state=ConversationState.PROBLEM_ASSESSMENT,
        latest_transcript=caller_text
    )

    assert "ghara" not in fallback
    assert "kabata" not in fallback
    assert "phone silent" in fallback
    assert "jangala re nuchiki" in fallback


def test_assault_and_violence_fallback_phrase():
    manager = ConversationStateManager()

    caller_text = "ghare dhuki lathi re maruchhanti mo matha phatigala"
    fallback = manager.get_fallback_phrase(
        language_code="or-IN",
        state=ConversationState.PROBLEM_ASSESSMENT,
        latest_transcript=caller_text
    )

    # Must acknowledge attack and confirm PCR 112 / medical dispatch, not generic 'are you safe'
    assert "112" in fallback
    assert "medical" in fallback or "police" in fallback


def test_police_inquiry_fallback_phrase():
    manager = ConversationStateManager()

    caller_text = "police ku jaldi dakantu police kebe asiba"
    fallback = manager.get_fallback_phrase(
        language_code="or-IN",
        state=ConversationState.PROBLEM_ASSESSMENT,
        latest_transcript=caller_text
    )

    assert "112" in fallback
    assert "baharigalaani" in fallback or "suchana" in fallback


def test_boycott_and_water_denial_fallback_phrase():
    manager = ConversationStateManager()

    caller_text = "pani nebaku mana kale o samaja ru bahiskara kale"
    fallback = manager.get_fallback_phrase(
        language_code="or-IN",
        state=ConversationState.PROBLEM_ASSESSMENT,
        latest_transcript=caller_text
    )

    assert "aparadha" in fallback
    assert "DLSA" in fallback or "surakshya" in fallback
