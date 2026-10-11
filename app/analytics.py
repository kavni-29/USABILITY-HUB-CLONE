import csv
import io
from collections import Counter, defaultdict

from flask import Blueprint, Response as FlaskResponse, abort, render_template
from flask_login import current_user, login_required

from .extensions import db
from .insights import generate_question_insights
from .models import Response, UsabilityTest

bp = Blueprint("analytics", __name__, url_prefix="/tests")


def owned(test_id):
    test = db.session.get(UsabilityTest, test_id)
    if not test or test.owner_id != current_user.id:
        abort(404)
    return test


def safe_csv_cell(value):
    value = str(value or "")
    if value.lstrip(" \t\r\n")[:1] in ("=", "+", "-", "@") or value[:1] in ("\t", "\r"):
        return "'" + value
    return value


@bp.get("/<int:test_id>/results")
@login_required
def results(test_id):
    test = owned(test_id)
    responses = db.session.scalars(
        db.select(Response).where(Response.test_id == test.id).order_by(Response.submitted_at)
    ).all()
    summaries = []
    all_insights = []
    for question in test.questions:
        answers = [answer for response in responses for answer in response.answers if answer.question_id == question.id]
        respondents = len({answer.response_id for answer in answers})
        insight_items = generate_question_insights(question, answers)
        all_insights.extend((question.prompt, item) for item in insight_items)
        if question.question_type == "rating":
            values = [int(answer.value) for answer in answers if answer.value and answer.value.isdigit()]
            counts = Counter(values)
            summary = {
                "count": len(values),
                "average": sum(values) / len(values) if values else None,
                "distribution": [(value, counts[value], counts[value] / len(values) * 100 if values else 0) for value in range(question.rating_min, question.rating_max + 1)],
            }
        elif question.question_type == "text_response":
            text_answers = [answer for answer in answers if answer.value and answer.value.strip()]
            summary = {"count": len(text_answers), "answers": list(reversed(text_answers[-100:]))}
        else:
            counts = Counter(answer.option_id for answer in answers if answer.option_id is not None)
            summary = {
                "respondents": respondents,
                "options": [
                    (option, counts[option.id], counts[option.id] / respondents * 100 if respondents else 0)
                    for option in question.options
                ],
            }
        summaries.append((question, summary, insight_items))
    daily = defaultdict(int)
    for response in responses:
        daily[response.submitted_at.date().isoformat()] += 1
    trend = sorted(daily.items())[-30:]
    period = (responses[0].submitted_at, responses[-1].submitted_at) if responses else None
    return render_template(
        "results.html", test=test, responses=responses, summaries=summaries,
        trend=trend, period=period, all_insights=all_insights,
    )


@bp.get("/<int:test_id>/export.csv")
@login_required
def export(test_id):
    test = owned(test_id)
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(["submission_id", "submitted_at", "question", "question_type", "answer"])
    responses = db.session.scalars(
        db.select(Response).where(Response.test_id == test.id).order_by(Response.submitted_at)
    ).all()
    for response in responses:
        for answer in response.answers:
            value = answer.option.label if answer.option else answer.value or ""
            writer.writerow([
                response.id,
                response.submitted_at.isoformat(),
                safe_csv_cell(answer.question.prompt),
                answer.question.question_type,
                safe_csv_cell(value),
            ])
    return FlaskResponse(
        output.getvalue(),
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="study-{test.id}-results.csv"'},
    )
