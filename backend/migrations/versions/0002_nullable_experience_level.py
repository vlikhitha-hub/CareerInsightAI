"""Preserve unprovided experience as unknown rather than Beginner."""

from alembic import op
import sqlalchemy as sa

revision = "0002_nullable_experience_level"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("profiles") as batch_op:
        batch_op.alter_column(
            "experience_level",
            existing_type=sa.String(length=24),
            nullable=True,
        )


def downgrade() -> None:
    raise RuntimeError(
        "This migration cannot be downgraded safely: unknown experience values must not be converted to Beginner."
    )
