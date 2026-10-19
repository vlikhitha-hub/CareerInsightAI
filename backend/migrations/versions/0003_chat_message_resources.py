"""Persist curated resource links attached to AI coach replies."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0003_chat_message_resources"
down_revision = "0002_nullable_experience_level"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if "resources" not in {column["name"] for column in inspect(bind).get_columns("chat_history")}:
        op.add_column("chat_history", sa.Column("resources", sa.JSON(), nullable=True))


def downgrade() -> None:
    raise RuntimeError(
        "This migration cannot be downgraded safely because the bootstrap schema may already have created this column."
    )
