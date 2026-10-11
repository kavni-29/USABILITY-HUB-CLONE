from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from .extensions import db
from .models import Question, QuestionOption, Response, UsabilityTest

bp = Blueprint("dashboard", __name__)
VALID_TYPES = {"multiple_choice", "preference", "rating"}


@bp.get("/dashboard")
@login_required
def index():
    tests = db.session.scalars(db.select(UsabilityTest).where(UsabilityTest.owner_id == current_user.id).order_by(UsabilityTest.created_at.desc())).all()
    return render_template("dashboard.html", tests=tests)


def owned_test(test_id):
    test = db.session.get(UsabilityTest, test_id)
    if not test or test.owner_id != current_user.id:
        abort(404)
    return test


@bp.route("/tests/new", methods=["GET", "POST"])
@login_required
def create():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        if not title or len(title) > 120 or len(description) > 1000:
            flash("Provide a title up to 120 characters and description up to 1,000 characters.", "error")
        else:
            test = UsabilityTest(owner_id=current_user.id, title=title, description=description)
            db.session.add(test)
            db.session.commit()
            return redirect(url_for("dashboard.edit", test_id=test.id))
    return render_template("test_form.html", test=None)


@bp.route("/tests/<int:test_id>/edit", methods=["GET", "POST"])
@login_required
def edit(test_id):
    test = owned_test(test_id)
    if request.method == "POST":
        action = request.form.get("action")
        if action == "details":
            title = request.form.get("title", "").strip()
            description = request.form.get("description", "").strip()
            if not title or len(title) > 120 or len(description) > 1000:
                flash("Check the title and description length.", "error")
            else:
                test.title, test.description = title, description
                db.session.commit()
                flash("Test details saved.", "success")
        elif action == "question":
            prompt = request.form.get("prompt", "").strip()
            kind = request.form.get("question_type", "")
            options = [item.strip() for item in request.form.get("options", "").splitlines() if item.strip()]
            try:
                low, high = int(request.form.get("rating_min", "1")), int(request.form.get("rating_max", "5"))
            except ValueError:
                low, high = 1, 5
            valid = bool(prompt) and len(prompt) <= 500 and kind in VALID_TYPES
            valid = valid and (kind == "rating" and 1 <= low < high <= 10 or kind != "rating" and 2 <= len(options) <= 10 and all(len(o) <= 160 for o in options))
            if test.responses:
                flash("Questions are locked after the first response to protect existing results.", "error")
            elif not valid:
                flash("Check the question text, type, options (2–10) or rating range (1–10).", "error")
            else:
                q = Question(test=test, prompt=prompt, question_type=kind, position=len(test.questions), required=request.form.get("required") == "on", rating_min=low if kind == "rating" else None, rating_max=high if kind == "rating" else None)
                db.session.add(q)
                for position, label in enumerate(options if kind != "rating" else []):
                    db.session.add(QuestionOption(question=q, label=label, position=position))
                db.session.commit()
                flash("Question added.", "success")
        elif action == "update_question":
            q = db.session.get(Question, request.form.get("question_id", type=int))
            if test.responses:
                flash("Questions are locked after the first response to protect existing results.", "error")
            elif q and q.test_id == test.id:
                prompt = request.form.get("prompt", "").strip()
                kind = request.form.get("question_type", "")
                options = [item.strip() for item in request.form.get("options", "").splitlines() if item.strip()]
                try:
                    low, high = int(request.form.get("rating_min", "1")), int(request.form.get("rating_max", "5"))
                except ValueError:
                    low, high = 1, 5
                valid = bool(prompt) and len(prompt) <= 500 and kind in VALID_TYPES
                valid = valid and (kind == "rating" and 1 <= low < high <= 10 or kind != "rating" and 2 <= len(options) <= 10 and all(len(o) <= 160 for o in options))
                if not valid:
                    flash("Check the question text, type, options (2–10) or rating range (1–10).", "error")
                else:
                    q.prompt, q.question_type = prompt, kind
                    q.required = request.form.get("required") == "on"
                    q.rating_min, q.rating_max = (low, high) if kind == "rating" else (None, None)
                    q.options.clear()
                    for position, label in enumerate(options if kind != "rating" else []):
                        q.options.append(QuestionOption(label=label, position=position))
                    db.session.commit()
                    flash("Question updated.", "success")
        elif action == "delete_question":
            q = db.session.get(Question, request.form.get("question_id", type=int))
            if test.responses:
                flash("Questions are locked after responses arrive.", "error")
            elif q and q.test_id == test.id:
                db.session.delete(q)
                db.session.commit()
        return redirect(url_for("dashboard.edit", test_id=test.id))
    return render_template("test_form.html", test=test)


@bp.get("/tests/<int:test_id>/preview")
@login_required
def preview(test_id):
    test = owned_test(test_id)
    return render_template("preview.html", test=test)


@bp.post("/tests/<int:test_id>/publish")
@login_required
def publish(test_id):
    test = owned_test(test_id)
    if not test.is_published and not test.questions:
        flash("Add at least one question before publishing.", "error")
    else:
        test.is_published = not test.is_published
        db.session.commit()
    return redirect(url_for("dashboard.index"))


@bp.post("/tests/<int:test_id>/delete")
@login_required
def delete(test_id):
    test = owned_test(test_id)
    if test.responses:
        flash("Tests with responses cannot be deleted, preserving the research record.", "error")
    else:
        db.session.delete(test)
        db.session.commit()
        flash("Test deleted.", "success")
    return redirect(url_for("dashboard.index"))
