from datetime import datetime, timezone
from uuid import uuid4

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db, login_manager


def now_utc():
    return datetime.now(timezone.utc)


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(254), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=now_utc)
    tests = db.relationship("UsabilityTest", back_populates="owner", cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class UsabilityTest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True)
    title = db.Column(db.String(120), nullable=False)
    description = db.Column(db.String(1000), nullable=False, default="")
    public_token = db.Column(db.String(64), unique=True, nullable=False, default=lambda: uuid4().hex + uuid4().hex)
    is_published = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=now_utc)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=now_utc, onupdate=now_utc)
    owner = db.relationship("User", back_populates="tests")
    questions = db.relationship("Question", back_populates="test", cascade="all, delete-orphan", order_by="Question.position")
    responses = db.relationship("Response", back_populates="test", cascade="all, delete-orphan")


class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    test_id = db.Column(db.Integer, db.ForeignKey("usability_test.id", ondelete="CASCADE"), nullable=False, index=True)
    prompt = db.Column(db.String(500), nullable=False)
    question_type = db.Column(db.String(20), nullable=False)
    required = db.Column(db.Boolean, nullable=False, default=True)
    position = db.Column(db.Integer, nullable=False, default=0)
    rating_min = db.Column(db.Integer, nullable=True)
    rating_max = db.Column(db.Integer, nullable=True)
    test = db.relationship("UsabilityTest", back_populates="questions")
    options = db.relationship("QuestionOption", back_populates="question", cascade="all, delete-orphan", order_by="QuestionOption.position")
    __table_args__ = (
        db.CheckConstraint("question_type IN ('multiple_choice', 'preference', 'rating')", name="ck_question_type"),
        db.CheckConstraint("(question_type = 'rating' AND rating_min IS NOT NULL AND rating_max IS NOT NULL AND rating_min >= 1 AND rating_max <= 10 AND rating_min < rating_max) OR (question_type != 'rating' AND rating_min IS NULL AND rating_max IS NULL)", name="ck_question_rating_range"),
    )


class QuestionOption(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey("question.id", ondelete="CASCADE"), nullable=False, index=True)
    label = db.Column(db.String(160), nullable=False)
    position = db.Column(db.Integer, nullable=False, default=0)
    question = db.relationship("Question", back_populates="options")


class Response(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    test_id = db.Column(db.Integer, db.ForeignKey("usability_test.id", ondelete="CASCADE"), nullable=False, index=True)
    submitted_at = db.Column(db.DateTime(timezone=True), nullable=False, default=now_utc)
    test = db.relationship("UsabilityTest", back_populates="responses")
    answers = db.relationship("Answer", back_populates="response", cascade="all, delete-orphan")


class Answer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    response_id = db.Column(db.Integer, db.ForeignKey("response.id", ondelete="CASCADE"), nullable=False, index=True)
    question_id = db.Column(db.Integer, db.ForeignKey("question.id", ondelete="CASCADE"), nullable=False, index=True)
    option_id = db.Column(db.Integer, db.ForeignKey("question_option.id", ondelete="SET NULL"), nullable=True)
    value = db.Column(db.String(500), nullable=True)
    response = db.relationship("Response", back_populates="answers")
    question = db.relationship("Question")
    option = db.relationship("QuestionOption")
    __table_args__ = (db.UniqueConstraint("response_id", "question_id", name="uq_answer_response_question"),)


@login_manager.user_loader
def load_user(user_id):
    try:
        return db.session.get(User, int(user_id))
    except (TypeError, ValueError):
        return None
