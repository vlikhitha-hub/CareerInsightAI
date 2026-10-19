"""Persist skill assessment attempts and GitHub repository analysis reports."""
from alembic import op
import sqlalchemy as sa

revision = "0004_evidence_features"
down_revision = "0003_chat_message_resources"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        "skill_assessment_attempts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("skill_name", sa.String(100), nullable=False),
        sa.Column("questions", sa.JSON(), nullable=False),
        sa.Column("answers", sa.JSON(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("level", sa.String(24), nullable=False, server_default="insufficient_evidence"),
        sa.Column("attempted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_skill_assessment_attempts_user_id", "skill_assessment_attempts", ["user_id"])
    op.create_index("ix_skill_assessment_attempts_skill_name", "skill_assessment_attempts", ["skill_name"])
    op.create_index("ix_skill_assessment_attempts_created_at", "skill_assessment_attempts", ["created_at"])
    op.create_table(
        "repository_analyses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("repository_url", sa.String(500), nullable=False),
        sa.Column("repository_name", sa.String(200), nullable=False),
        sa.Column("summary", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_repository_analyses_user_id", "repository_analyses", ["user_id"])
    op.create_index("ix_repository_analyses_created_at", "repository_analyses", ["created_at"])

def downgrade() -> None:
    op.drop_table("repository_analyses")
    op.drop_table("skill_assessment_attempts")
