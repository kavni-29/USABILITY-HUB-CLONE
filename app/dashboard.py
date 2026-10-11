from datetime import datetime, timezone

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import func

from .extensions import db
from .models import Question, QuestionOption, Response, UsabilityTest
from .validation import METHODOLOGIES, validate_question_form

bp = Blueprint("dashboard", __name__)


@bp.get("/dashboard")
@login_required
def index():
    query = db.select(UsabilityTest).where(UsabilityTest.owner_id == current_user.id)
    search = request.args.get("q", "").strip()[:120]
    status = request.args.get("status", "all")
    if search:
        query = query.where(UsabilityTest.title.ilike(f"%{search}%"))
    if status in {"draft", "published", "closed", "archived"}:
        query = query.where(UsabilityTest.status == status)
    tests = db.session.scalars(query.order_by(UsabilityTest.updated_at.desc())).all()
    totals = db.session.execute(
        db.select(
            func.count(UsabilityTest.id),
            func.sum(db.case((UsabilityTest.status == "draft", 1), else_=0)),
            func.sum(db.case((UsabilityTest.status == "published", 1), else_=0)),
            func.sum(db.case((UsabilityTest.status == "closed", 1), else_=0)),
            func.sum(db.case((UsabilityTest.status == "archived", 1), else_=0)),
        ).where(UsabilityTest.owner_id == current_user.id)
    ).one()
    response_count = db.session.scalar(
        db.select(func.count(Response.id)).join(UsabilityTest).where(UsabilityTest.owner_id == current_user.id)
    ) or 0
    stats = {"total": totals[0] or 0, "draft": totals[1] or 0, "published": totals[2] or 0, "closed": totals[3] or 0, "archived": totals[4] or 0, "responses": response_count}
    return render_template("dashboard.html", tests=tests, stats=stats, search=search, selected_status=status)


def owned_test(test_id):
    test = db.session.get(UsabilityTest, test_id)
    if not test or test.owner_id != current_user.id:
        abort(404)
    return test


def valid_test_details(form):
    title = form.get("title", "").strip()
    description = form.get("description", "").strip()
    methodology = form.get("methodology", "general").strip()
    if not title or len(title) > 120 or len(description) > 1000 or methodology not in METHODOLOGIES:
        raise ValueError("Check the title, description, and methodology.")
    return title, description, methodology


@bp.route("/tests/new", methods=["GET", "POST"])
@login_required
def create():
    if request.method == "POST":
        try:
            title, description, methodology = valid_test_details(request.form)
            test = UsabilityTest(owner_id=current_user.id, title=title, description=description, methodology=methodology)
            db.session.add(test)
            db.session.commit()
            return redirect(url_for("dashboard.edit", test_id=test.id))
        except ValueError as error:
            flash(str(error), "error")
    return render_template("test_form.html", test=None)


@bp.route("/tests/<int:test_id>/edit", methods=["GET", "POST"])
@login_required
def edit(test_id):
    test = owned_test(test_id)
    if request.method == "POST":
        action = request.form.get("action")
        if action == "details":
            try:
                test.title, test.description, test.methodology = valid_test_details(request.form)
                db.session.commit()
                flash("Study details saved.", "success")
            except ValueError as error:
                flash(str(error), "error")
        elif action in {"question", "update_question"}:
            existing_question = None
            if action == "update_question":
                existing_question = db.session.get(Question, request.form.get("question_id", type=int))
            if test.responses:
                flash("Question structure is locked after the first response to protect existing results.", "error")
            elif action == "update_question" and (not existing_question or existing_question.test_id != test.id):
                abort(404)
            else:
                try:
                    data = validate_question_form(request.form)
                    question = existing_question or Question(test=test, position=len(test.questions))
                    question.prompt = data["prompt"]
                    question.question_type = data["question_type"]
                    question.helper_text = data["helper_text"]
                    question.required = data["required"]
                    question.rating_min, question.rating_max = data["rating_min"], data["rating_max"]
                    question.options.clear()
                    for position, label in enumerate(data["options"]):
                        question.options.append(QuestionOption(label=label, position=position))
                    db.session.add(question)
                    db.session.commit()
                    flash("Question saved.", "success")
                except ValueError as error:
                    flash(str(error), "error")
        elif action == "delete_question":
            question = db.session.get(Question, request.form.get("question_id", type=int))
            if test.responses:
                flash("Question structure is locked after responses arrive.", "error")
            elif not question or question.test_id != test.id:
                abort(404)
            else:
                db.session.delete(question)
                db.session.commit()
                resequence(test)
        elif action == "reorder":
            question = db.session.get(Question, request.form.get("question_id", type=int))
            if test.responses:
                flash("Questions cannot be reordered after responses arrive.", "error")
            elif not question or question.test_id != test.id:
                abort(404)
            else:
                direction = request.form.get("direction")
                target_position = question.position + (-1 if direction == "up" else 1 if direction == "down" else 0)
                adjacent = next((item for item in test.questions if item.position == target_position), None)
                if adjacent:
                    question.position, adjacent.position = adjacent.position, question.position
                    db.session.commit()
        return redirect(url_for("dashboard.edit", test_id=test.id))
    return render_template("test_form.html", test=test)


def resequence(test):
    for position, question in enumerate(test.questions):
        question.position = position
    db.session.commit()


@bp.get("/tests/<int:test_id>/preview")
@login_required
def preview(test_id):
    return render_template("preview.html", test=owned_test(test_id))


@bp.post("/tests/<int:test_id>/publish")
@login_required
def publish(test_id):
    test = owned_test(test_id)
    if test.status not in {"draft", "published"}:
        flash("Only a draft or published study can be toggled.", "error")
    elif not test.is_published and not test.questions:
        flash("Add at least one question before publishing.", "error")
    elif test.is_published:
        test.is_published = False
        test.status = "draft"
        db.session.commit()
    else:
        test.is_published = True
        test.status = "published"
        test.published_at = datetime.now(timezone.utc)
        db.session.commit()
    return redirect(url_for("dashboard.index"))


@bp.post("/tests/<int:test_id>/close")
@login_required
def close(test_id):
    test = owned_test(test_id)
    if test.status != "published":
        flash("Only published studies can be closed.", "error")
    else:
        test.status, test.is_published = "closed", False
        test.closed_at = datetime.now(timezone.utc)
        db.session.commit()
    return redirect(url_for("dashboard.index"))


@bp.post("/tests/<int:test_id>/reopen")
@login_required
def reopen(test_id):
    test = owned_test(test_id)
    if test.status != "closed":
        flash("Only closed studies can be reopened.", "error")
    else:
        test.status, test.is_published, test.closed_at = "published", True, None
        test.published_at = datetime.now(timezone.utc)
        db.session.commit()
    return redirect(url_for("dashboard.index"))


@bp.post("/tests/<int:test_id>/archive")
@login_required
def archive(test_id):
    test = owned_test(test_id)
    if test.status == "published":
        flash("Close a published study before archiving it.", "error")
    elif test.status == "archived":
        flash("Study is already archived.", "error")
    else:
        test.status, test.is_published = "archived", False
        db.session.commit()
    return redirect(url_for("dashboard.index"))


@bp.post("/tests/<int:test_id>/delete")
@login_required
def delete(test_id):
    test = owned_test(test_id)
    if test.responses:
        flash("Studies with responses cannot be deleted. Archive the study to retain its research record.", "error")
    else:
        db.session.delete(test)
        db.session.commit()
        flash("Study deleted.", "success")
    return redirect(url_for("dashboard.index"))
