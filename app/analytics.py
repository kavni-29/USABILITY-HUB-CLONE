import csv
import io
from collections import Counter

from flask import Blueprint, Response as FlaskResponse, abort, render_template
from flask_login import current_user, login_required

from .extensions import db
from .models import Answer, Response, UsabilityTest

bp = Blueprint("analytics", __name__, url_prefix="/tests")


def owned(test_id):
    test = db.session.get(UsabilityTest, test_id)
    if not test or test.owner_id != current_user.id:
        abort(404)
    return test


def safe_csv_cell(value):
    value = str(value or "")
    if value[:1] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + value
    return value


@bp.get("/<int:test_id>/results")
@login_required
def results(test_id):
    test = owned(test_id)
    responses = db.session.scalars(db.select(Response).where(Response.test_id == test.id).order_by(Response.submitted_at)).all()
    summaries = []
    for question in test.questions:
        answers = [a for response in responses for a in response.answers if a.question_id == question.id]
        if question.question_type == "rating":
            values = [int(a.value) for a in answers if a.value and a.value.isdigit()]
            summary = {"average": sum(values) / len(values) if values else None, "count": len(values)}
        else:
            counts = Counter(a.option_id for a in answers)
            summary = {"options": [(option, counts[option.id], (counts[option.id] / len(answers) * 100 if answers else 0)) for option in question.options]}
        summaries.append((question, summary))
    return render_template("results.html", test=test, responses=responses, summaries=summaries)


@bp.get("/<int:test_id>/export.csv")
@login_required
def export(test_id):
    test = owned(test_id)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["response_id", "submitted_at", "question", "answer"])
    responses = db.session.scalars(db.select(Response).where(Response.test_id == test.id).order_by(Response.submitted_at)).all()
    for response in responses:
        for answer in response.answers:
            value = answer.option.label if answer.option else answer.value or ""
            writer.writerow([response.id, response.submitted_at.isoformat(), safe_csv_cell(answer.question.prompt), safe_csv_cell(value)])
    return FlaskResponse(output.getvalue(), mimetype="text/csv", headers={"Content-Disposition": f'attachment; filename="test-{test.id}-results.csv"'})
