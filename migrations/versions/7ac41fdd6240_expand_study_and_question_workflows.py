"""Expand study lifecycle, question types, and idempotent submissions.

Revision ID: 7ac41fdd6240
Revises: bd6f43a874be
"""
from alembic import op
import sqlalchemy as sa


revision = "7ac41fdd6240"
down_revision = "bd6f43a874be"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("usability_test") as batch:
        batch.add_column(sa.Column("methodology", sa.String(length=40), server_default="general", nullable=False))
        batch.add_column(sa.Column("status", sa.String(length=20), server_default="draft", nullable=False))
        batch.add_column(sa.Column("published_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True))
        batch.create_check_constraint("ck_test_status", "status IN ('draft', 'published', 'closed', 'archived')")
        batch.create_check_constraint("ck_test_methodology", "methodology IN ('general', 'first_click', 'preference', 'concept_test', 'survey')")
        batch.create_index("ix_usability_test_status", ["status"], unique=False)
    op.execute("UPDATE usability_test SET status = CASE WHEN is_published THEN 'published' ELSE 'draft' END")
    op.execute("UPDATE usability_test SET published_at = CURRENT_TIMESTAMP WHERE is_published")

    with op.batch_alter_table("question") as batch:
        batch.add_column(sa.Column("helper_text", sa.String(length=300), server_default="", nullable=False))
        batch.drop_constraint("ck_question_type", type_="check")
        batch.create_check_constraint(
            "ck_question_type",
            "question_type IN ('single_choice', 'multiple_choice', 'preference', 'rating', 'text_response', 'yes_no')",
        )
    # Before this revision, `multiple_choice` rendered radio buttons. Preserve that meaning.
    op.execute("UPDATE question SET question_type = 'single_choice' WHERE question_type = 'multiple_choice'")

    with op.batch_alter_table("answer") as batch:
        batch.drop_constraint("uq_answer_response_question", type_="unique")

    with op.batch_alter_table("response") as batch:
        batch.add_column(sa.Column("submission_key", sa.String(length=64), nullable=True))
        batch.create_unique_constraint("uq_response_submission_key", ["test_id", "submission_key"])

    with op.batch_alter_table("answer") as batch:
        batch.create_check_constraint(
            "ck_answer_one_value",
            "(option_id IS NULL AND value IS NOT NULL) OR (option_id IS NOT NULL AND value IS NULL)",
        )


def downgrade():
    raise RuntimeError(
        "This migration expands question types and multi-select answer storage. "
        "Restore a database backup instead of downgrading and silently losing new-format data."
    )
