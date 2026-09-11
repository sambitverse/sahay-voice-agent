import pytest
from app.websocket.client_ws import ClientAudioSession

def test_echo_detection_for_greetings():
    session = ClientAudioSession("test_call_echo_1")
    assert session._is_echo_of_agent_speech("Namaskar. NHAA 14566 helpline re apananku swagata.") is True
    assert session._is_echo_of_agent_speech("Namaskar. Rashtriya Helpline 14566 mein aapka swagat hai.") is True
    assert session._is_echo_of_agent_speech("samasya batayein") is True
    assert session._is_echo_of_agent_speech("apananku swagata daya kari") is True
    assert session._is_echo_of_agent_speech("14566 helpline") is True

def test_echo_detection_for_agent_history():
    session = ClientAudioSession("test_call_echo_2")
    session.conversation_history.append({
        "role": "agent",
        "content": "Aap bilkul chinta mat karein, police aur ambulance turant bhej rahe hain."
    })
    assert session._is_echo_of_agent_speech("chinta mat karein police aur ambulance") is True
    assert session._is_echo_of_agent_speech("Aap bilkul chinta mat karein") is True

def test_echo_detection_allows_real_user_speech():
    session = ClientAudioSession("test_call_echo_3")
    session.conversation_history.append({
        "role": "agent",
        "content": "Namaskar, main Sahay agent bol raha hoon. Aap safe hain?"
    })
    assert session._is_echo_of_agent_speech("Mera accident ho gaya hai highway par") is False
    assert session._is_echo_of_agent_speech("Mate asubidha re padichhi maribaku asichhanti") is False
    assert session._is_echo_of_agent_speech("Severe bleeding head injury near market") is False
    assert session._is_echo_of_agent_speech("Haji vespa accident aane botor") is False
