from app.extensions import db
from app.models import Answer, Question, QuestionOption, Response, UsabilityTest, User


def login(client, email="owner@example.com", password="strong-test-password"):
    return client.post("/auth/login", data={"email": email, "password": password})


def test_registration_hashes_password_and_protects_dashboard(client, app):
    response = client.post("/auth/register", data={"email": "new@example.com", "password": "long-secure-password"})
    assert response.status_code == 302
    with app.app_context():
        user = db.session.scalar(db.select(User).where(User.email == "new@example.com"))
        assert user.password_hash != "long-secure-password"
        assert user.check_password("long-secure-password")
    client.post("/auth/logout")
    assert client.get("/dashboard").status_code == 302


def test_bad_login(client):
    assert b"incorrect" in login(client, password="wrong-password").data


def test_health_and_assets(client):
    assert client.get("/health").json == {"status": "ok", "database": "ok"}
    assert client.get("/style.css").status_code == 200
    assert client.get("/app.css").status_code == 200


def test_create_publish_submit_and_results(client, app, user):
    assert client.get("/").status_code == 200
    login(client)
    client.post("/tests/new", data={"title": "Checkout flow", "description": ""})
    assert client.get("/dashboard").status_code == 200
    with app.app_context():
        test = db.session.scalar(db.select(UsabilityTest))
        q = Question(test_id=test.id, prompt="Which design?", question_type="preference", position=0)
        db.session.add(q)
        db.session.flush()
        first = QuestionOption(question_id=q.id, label="A", position=0)
        second = QuestionOption(question_id=q.id, label="B", position=1)
        db.session.add_all([first, second])
        db.session.flush()
        test_id, token, option_id, question_id = test.id, test.public_token, first.id, q.id
        db.session.commit()
    assert client.get(f"/tests/{test_id}/edit").status_code == 200
    assert client.get(f"/tests/{test_id}/preview").status_code == 200
    assert client.post(f"/tests/{test_id}/publish").status_code == 302
    invalid = client.post(f"/p/{token}", data={f"q_{question_id}": "999999"})
    assert invalid.status_code == 200
    with app.app_context():
        assert db.session.scalar(db.select(db.func.count(Response.id))) == 0
    participant_result = client.post(f"/p/{token}", data={f"q_{question_id}": str(option_id)})
    assert b"RESPONSE RECORDED" in participant_result.data
    assert b"RESPONSE RECORDED" in client.post(f"/p/{token}", data={f"q_{question_id}": str(option_id)}).data
    with app.app_context():
        assert db.session.scalar(db.select(db.func.count(Response.id))) == 2
        assert db.session.scalar(db.select(db.func.count(Answer.id))) == 2
    assert b"2 total responses" in client.get(f"/tests/{test_id}/results").data
    assert b"response_id" in client.get(f"/tests/{test_id}/export.csv").data
    client.post(f"/tests/{test_id}/delete")
    with app.app_context():
        assert db.session.get(UsabilityTest, test_id) is not None


def test_authorization_and_unpublished_rejected(client, app, user):
    login(client)
    client.post("/tests/new", data={"title": "Private", "description": ""})
    with app.app_context():
        test = db.session.scalar(db.select(UsabilityTest))
        test_id, token = test.id, test.public_token
        outsider = User(email="other@example.com")
        outsider.set_password("other-password-123")
        db.session.add(outsider)
        db.session.commit()
    assert client.post(f"/p/{token}").status_code == 404
    client.post("/auth/logout")
    login(client, "other@example.com", "other-password-123")
    assert client.get(f"/tests/{test_id}/results").status_code == 404
    assert client.get(f"/tests/{test_id}/export.csv").status_code == 404
    assert client.post(f"/tests/{test_id}/delete").status_code == 404
    assert client.post(f"/tests/{test_id}/edit", data={"action": "details", "title": "Stolen", "description": ""}).status_code == 404
