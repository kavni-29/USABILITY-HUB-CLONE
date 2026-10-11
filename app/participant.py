import secrets

from flask import Blueprint, abort, flash, render_template, request
from sqlalchemy.exc import IntegrityError

from .extensions import db
from .models import Answer, Response, UsabilityTest
from .validation import normalize_text_answer

bp = Blueprint("participant", __name__, url_prefix="/p")


def participant_template(test, submission_key):
    return render_template("participant.html", test=test, submission_key=submission_key)


@bp.route("/<token>", methods=["GET", "POST"])
def participate(token):
    test = db.session.scalar(
        db.select(UsabilityTest).where(UsabilityTest.public_token == token, UsabilityTest.status == "published")
    )
    if not test:
        abort(404)
    if request.method == "POST":
        key = request.form.get("submission_key", "")
        if len(key) != 43 or not key.isascii() or not all(character.isalnum() or character in "_-" for character in key):
            abort(400)
        prior = db.session.scalar(
            db.select(Response).where(Response.test_id == test.id, Response.submission_key == key)
        )
        if prior:
            return render_template("complete.html")
        answers = []
        for question in test.questions:
            values = [value.strip() for value in request.form.getlist(f"q_{question.id}")]
            if not values or values == [""]:
                if question.required:
                    flash("Please answer every required question.", "error")
                    return participant_template(test, key)
                continue
            if question.question_type in {"single_choice", "preference", "yes_no", "multiple_choice"}:
                allowed = {str(option.id): option for option in question.options}
                if question.question_type != "multiple_choice" and len(values) != 1:
                    flash("Choose exactly one option for each single-choice question.", "error")
                    return participant_template(test, key)
                if len(set(values)) != len(values) or any(value not in allowed for value in values):
                    flash("One or more selections are invalid. Please try again.", "error")
                    return participant_template(test, key)
                answers.extend((question, allowed[value], None) for value in values)
            elif question.question_type == "rating":
                if len(values) != 1:
                    flash("Enter one valid rating.", "error")
                    return participant_template(test, key)
                try:
                    rating = int(values[0])
                except ValueError:
                    rating = -1
                if not question.rating_min <= rating <= question.rating_max:
                    flash("A rating is outside its allowed range.", "error")
                    return participant_template(test, key)
                answers.append((question, None, str(rating)))
            elif question.question_type == "text_response":
                if len(values) != 1:
                    flash("Enter one text response.", "error")
                    return participant_template(test, key)
                try:
                    text = normalize_text_answer(values[0])
                except ValueError as error:
                    flash(str(error), "error")
                    return participant_template(test, key)
                if text:
                    answers.append((question, None, text))
                elif question.required:
                    flash("Please answer every required question.", "error")
                    return participant_template(test, key)
            else:
                abort(400)
        response = Response(test=test, submission_key=key)
        db.session.add(response)
        for question, option, value in answers:
            db.session.add(Answer(response=response, question=question, option=option, value=value))
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            prior = db.session.scalar(
                db.select(Response).where(Response.test_id == test.id, Response.submission_key == key)
            )
            if prior:
                return render_template("complete.html")
            raise
        return render_template("complete.html")
    return participant_template(test, secrets.token_urlsafe(32))
