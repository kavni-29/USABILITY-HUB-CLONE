"""Add scheduled close time to studies.

Revision ID: bf2c34918a71
Revises: 7ac41fdd6240
"""
from alembic import op
import sqlalchemy as sa


revision = "bf2c34918a71"
down_revision = "7ac41fdd6240"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("usability_test", sa.Column("scheduled_close_at", sa.DateTime(timezone=True), nullable=True))


def downgrade():
    op.drop_column("usability_test", "scheduled_close_at")
