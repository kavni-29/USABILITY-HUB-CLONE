import csv
import io
import re

from app.analytics import safe_csv_cell
from app.extensions import db
from app.models import Question, QuestionOption, Response, UsabilityTest


def sign_in(client):
    return client.post("/auth/login", data={"email": "owner@example.com", "password": "strong-test-password"})


def add_question(client, test_id, kind, prompt, options="", **fields):
    data = {
        "action": "question", "question_type": kind, "prompt": prompt,
        "helper_text": fields.pop("helper_text", ""), "options": options,
        "rating_min": fields.pop("rating_min", "1"), "rating_max": fields.pop("rating_max", "5"),
        "required": "on", **fields,
    }
    return client.post(f"/tests/{test_id}/edit", data=data)


def test_question_builder_types_submission_analytics_and_states(client, app, user):
    sign_in(client)
    created = client.post("/tests/new", data={"title": "Navigation study", "description": "Which path is clear?", "methodology": "first_click"})
    test_id = int(re.search(r"/tests/(\d+)/edit", created.location).group(1))
    add_question(client, test_id, "single_choice", "Choose one", "A\nB")
    add_question(client, test_id, "multiple_choice", "Choose all", "Red\nBlue\nGreen")
    add_question(client, test_id, "text_response", "What would you change?")
    add_question(client, test_id, "rating", "Rate this", rating_min="2", rating_max="8")
    add_question(client, test_id, "yes_no", "Was this clear?")
    add_question(client, test_id, "made_up", "Invalid type", "A\nB")
    add_question(client, test_id, "single_choice", "Duplicate options", "Same\nSame")

    with app.app_context():
        test = db.session.get(UsabilityTest, test_id)
        assert test.methodology == "first_click"
        assert [question.question_type for question in test.questions] == ["single_choice", "multiple_choice", "text_response", "rating", "yes_no"]
        question_ids = {question.question_type: question.id for question in test.questions}
        option_ids = {question.question_type: [option.id for option in question.options] for question in test.questions}
        token = test.public_token

    client.post(f"/tests/{test_id}/edit", data={"action": "reorder", "question_id": question_ids["yes_no"], "direction": "up"})
    with app.app_context():
        assert [question.question_type for question in db.session.get(UsabilityTest, test_id).questions] == ["single_choice", "multiple_choice", "text_response", "yes_no", "rating"]
    assert client.get(f"/tests/{test_id}/preview").status_code == 200
    client.post(f"/tests/{test_id}/publish")
    participant_url = f"/p/{token}"
    form_html = client.get(participant_url).get_data(as_text=True)
    key = re.search(r'name="submission_key" value="([^"]+)"', form_html).group(1)
    assert 'type="checkbox"' in form_html
    assert 'textarea id=' in form_html
    post_data = {
        f"q_{question_ids['single_choice']}": str(option_ids["single_choice"][0]),
        f"q_{question_ids['multiple_choice']}": [str(option_ids["multiple_choice"][0]), str(option_ids["multiple_choice"][2])],
        f"q_{question_ids['text_response']}": "<script>alert(1)</script>, path B",
        f"q_{question_ids['rating']}": "8",
        f"q_{question_ids['yes_no']}": str(option_ids["yes_no"][0]),
        "submission_key": key,
    }
    assert b"RESPONSE RECORDED" in client.post(participant_url, data=post_data).data
    # Replaying a failed or successful submit with the same key is idempotent.
    assert b"RESPONSE RECORDED" in client.post(participant_url, data=post_data).data
    with app.app_context():
        assert db.session.scalar(db.select(db.func.count(Response.id)).where(Response.test_id == test_id)) == 1
    results = client.get(f"/tests/{test_id}/results")
    assert results.status_code == 200
    assert b"Answer distribution" in results.data
    assert b"Rating distribution" in results.data
    assert b"Research insights" not in results.data
    assert b"&lt;script&gt;" in results.data
    csv_rows = list(csv.reader(io.StringIO(client.get(f"/tests/{test_id}/export.csv").get_data(as_text=True))))
    assert csv_rows[0] == ["submission_id", "submitted_at", "question", "question_type", "answer"]
    assert any(row[-1] == "<script>alert(1)</script>, path B" for row in csv_rows)
    assert safe_csv_cell("=SUM(1,2)") == "'=SUM(1,2)"

    client.post(f"/tests/{test_id}/close")
    assert client.get(participant_url).status_code == 404
    client.post(f"/tests/{test_id}/reopen")
    assert client.get(participant_url).status_code == 200
    client.post(f"/tests/{test_id}/close")
    client.post(f"/tests/{test_id}/archive")
    assert client.get(participant_url).status_code == 404


def test_dashboard_search_and_status_metrics(client, app, user):
    sign_in(client)
    client.post("/tests/new", data={"title": "Homepage study", "description": ""})
    dashboard = client.get("/dashboard?q=Home&status=draft")
    assert b"Homepage study" in dashboard.data
    assert b"Total studies" in dashboard.data
    assert b"Drafts" in dashboard.data
    assert b"No matching studies" in client.get("/dashboard?status=archived").data


def test_scheduled_close_is_saved_in_utc_and_closes_public_study(client, app, user):
    from datetime import datetime, timedelta, timezone

    sign_in(client)
    created = client.post("/tests/new", data={"title": "Timed study", "description": ""})
    test_id = int(re.search(r"/tests/(\d+)/edit", created.location).group(1))
    with app.app_context():
        test = db.session.get(UsabilityTest, test_id)
        token = test.public_token
    add_question(client, test_id, "text_response", "Share a thought")
    deadline = datetime.now(timezone.utc) + timedelta(minutes=2)
    client.post(f"/tests/{test_id}/edit", data={
        "action": "details", "title": "Timed study", "description": "", "methodology": "general",
        "scheduled_close_at": deadline.strftime("%Y-%m-%dT%H:%M"), "timezone_offset": "0",
    })
    with app.app_context():
        test = db.session.get(UsabilityTest, test_id)
        assert test.scheduled_close_at is not None
        assert test.scheduled_close_at.replace(tzinfo=timezone.utc) > datetime.now(timezone.utc)
    client.post(f"/tests/{test_id}/publish")
    assert b"Scheduled to close" in client.get("/dashboard").data
    with app.app_context():
        test = db.session.get(UsabilityTest, test_id)
        test.scheduled_close_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        db.session.commit()
    assert client.get(f"/p/{token}").status_code == 404
    with app.app_context():
        assert db.session.get(UsabilityTest, test_id).status == "closed"
