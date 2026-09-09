from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_contact_inquiry_submission():
    payload = {
        "name": "Sambit Moharana",
        "contact": "+91 9876543210",
        "category": "Legal Rights",
        "message": "Need information regarding PoA witness protection."
    }
    response = client.post("/api/v1/website/contact", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "ticket_id" in data
    assert data["ticket_id"].startswith("INQ-")

def test_portal_login_user_and_operator():
    user_res = client.post("/api/v1/auth/login", json={"role": "user", "identifier": "+919876543210", "code": "1234"})
    assert user_res.status_code == 200
    assert user_res.json()["role"] == "user"

    op_res = client.post("/api/v1/auth/login", json={"role": "operator", "identifier": "OP-14566", "code": "9999"})
    assert op_res.status_code == 200
    assert op_res.json()["role"] == "operator"

def test_send_otp_endpoint():
    # Valid phone
    res = client.post("/api/v1/auth/send-otp", json={"phone": "+91 94371-88210"})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["otp"] == "14566"

    # Invalid short phone
    bad_res = client.post("/api/v1/auth/send-otp", json={"phone": "123"})
    assert bad_res.status_code == 400

def test_grounded_chat_message_wilderness_pursuit():
    payload = {
        "message": "ମୋତେ ମାରିବାକୁ ଗୋଡ଼ାଉଛନ୍ତି, ମୁଁ ଏବେ ଜଙ୍ଗଲରେ ଲୁଚିକି ଅଛି।",
        "language": "or-IN"
    }
    response = client.post("/api/v1/chat/message", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["risk_level"] == "CRITICAL"
    # Grounding check: never advise door locking in forest
    assert "କବାଟ" not in data["text"]
    assert "ଘର ଭିତରେ" not in data["text"]
    assert "PCR 112" in data["text"]

def test_user_logs_endpoint():
    response = client.get("/api/v1/user/citizen_9924/logs")
    assert response.status_code == 200
    data = response.json()
    assert "logs" in data
    assert len(data["logs"]) >= 1


def test_out_of_scope_chat_message_interception():
    # Coding query
    payload_coding = {
        "message": "Can you write a python script to reverse a linked list?",
        "language": "en"
    }
    response = client.post("/api/v1/chat/message", json=payload_coding)
    assert response.status_code == 200
    data = response.json()
    assert "14566" in data["text"]
    assert "cannot answer out-of-scope" in data["text"].lower() or "out-of-scope" in data["text"].lower()

    # Cricket query in Hindi
    payload_sports = {
        "message": "Kal cricket match kaun jeeta tha?",
        "language": "hi"
    }
    res_sports = client.post("/api/v1/chat/message", json=payload_sports)
    assert res_sports.status_code == 200
    data_sports = res_sports.json()
    assert "14566" in data_sports["text"]
    assert "कार्यक्षेत्र से बाहर" in data_sports["text"]


def test_desia_and_broken_odia_chat_message():
    # Desia dialect distress
    payload_desia = {
        "message": "mor pache padila godauche dada banchao bana dongar re nuchi achhe",
        "language": "des-IN"
    }
    response = client.post("/api/v1/chat/message", json=payload_desia)
    assert response.status_code == 200
    data = response.json()
    # It should identify pursuit/wilderness and elevate to CRITICAL
    assert data["risk_level"] == "CRITICAL"
    assert "PCR 112" in data["text"]

