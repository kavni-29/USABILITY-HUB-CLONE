from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from .extensions import db
from .models import Answer, Response, UsabilityTest

bp = Blueprint("participant", __name__, url_prefix="/p")


@bp.route("/<token>", methods=["GET", "POST"])
def participate(token):
    test = db.session.scalar(db.select(UsabilityTest).where(UsabilityTest.public_token == token, UsabilityTest.is_published.is_(True)))
    if not test:
        abort(404)
    if request.method == "POST":
        answers = []
        for question in test.questions:
            raw = request.form.get(f"q_{question.id}", "").strip()
            if question.required and not raw:
                flash("Please answer every required question.", "error")
                return render_template("participant.html", test=test)
            if not raw:
                continue
            if question.question_type in ("multiple_choice", "preference"):
                option = next((o for o in question.options if str(o.id) == raw), None)
                if not option:
                    flash("One of your selections is invalid. Please try again.", "error")
                    return render_template("participant.html", test=test)
                answers.append((question, option, None))
            else:
                try:
                    rating = int(raw)
                except ValueError:
                    rating = -1
                if not question.rating_min <= rating <= question.rating_max:
                    flash("A rating is outside its allowed range.", "error")
                    return render_template("participant.html", test=test)
                answers.append((question, None, str(rating)))
        response = Response(test=test)
        db.session.add(response)
        for question, option, value in answers:
            db.session.add(Answer(response=response, question=question, option=option, value=value))
        db.session.commit()
        return render_template("complete.html")
    return render_template("participant.html", test=test)
