"""Frozen initial schema snapshot. Later schema changes belong in later revisions."""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('career_roles',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('slug', sa.String(length=96), nullable=False),
    sa.Column('name', sa.String(length=160), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('education', sa.String(length=160), nullable=False),
    sa.Column('tools', sa.JSON(), nullable=False),
    sa.Column('typical_projects', sa.JSON(), nullable=False),
    sa.Column('industries', sa.JSON(), nullable=False),
    sa.Column('min_experience', sa.String(length=24), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_career_roles_name'), 'career_roles', ['name'], unique=False)
    op.create_index(op.f('ix_career_roles_slug'), 'career_roles', ['slug'], unique=True)
    op.create_table('evaluation_runs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=160), nullable=False),
    sa.Column('method', sa.String(length=64), nullable=False),
    sa.Column('dataset_name', sa.String(length=160), nullable=False),
    sa.Column('sample_count', sa.Integer(), nullable=False),
    sa.Column('metrics', sa.JSON(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_evaluation_runs_created_at'), 'evaluation_runs', ['created_at'], unique=False)
    op.create_table('interests',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('category', sa.String(length=64), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_interests_name'), 'interests', ['name'], unique=True)
    op.create_table('scoring_settings',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=64), nullable=False),
    sa.Column('weights', sa.JSON(), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name')
    )
    op.create_table('skills',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('category', sa.String(length=64), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_skills_name'), 'skills', ['name'], unique=True)
    op.create_table('users',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('email', sa.String(length=320), nullable=False),
    sa.Column('name', sa.String(length=160), nullable=False),
    sa.Column('password_hash', sa.String(length=512), nullable=False),
    sa.Column('role', sa.String(length=24), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_role'), 'users', ['role'], unique=False)
    op.create_table('career_skills',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('career_id', sa.Integer(), nullable=False),
    sa.Column('skill_id', sa.Integer(), nullable=False),
    sa.Column('importance', sa.Float(), nullable=False),
    sa.Column('required', sa.Boolean(), nullable=False),
    sa.Column('required_level', sa.String(length=24), nullable=False),
    sa.ForeignKeyConstraint(['career_id'], ['career_roles.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['skill_id'], ['skills.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('career_id', 'skill_id', name='uq_career_skill')
    )
    op.create_index(op.f('ix_career_skills_career_id'), 'career_skills', ['career_id'], unique=False)
    op.create_index(op.f('ix_career_skills_skill_id'), 'career_skills', ['skill_id'], unique=False)
    op.create_table('chat_history',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('role', sa.String(length=24), nullable=False),
    sa.Column('content', sa.Text(), nullable=False),
    sa.Column('ai_generated', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_chat_history_user_id'), 'chat_history', ['user_id'], unique=False)
    op.create_table('password_resets',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('token_hash', sa.String(length=64), nullable=False),
    sa.Column('expires_at', sa.DateTime(), nullable=False),
    sa.Column('used_at', sa.DateTime(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_password_resets_expires_at'), 'password_resets', ['expires_at'], unique=False)
    op.create_index(op.f('ix_password_resets_token_hash'), 'password_resets', ['token_hash'], unique=True)
    op.create_index(op.f('ix_password_resets_user_id'), 'password_resets', ['user_id'], unique=False)
    op.create_table('profiles',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('education', sa.String(length=120), nullable=False),
    sa.Column('degree', sa.String(length=160), nullable=False),
    sa.Column('branch', sa.String(length=160), nullable=False),
    sa.Column('graduation_year', sa.Integer(), nullable=True),
    sa.Column('experience_level', sa.String(length=24), nullable=False),
    sa.Column('target_role', sa.String(length=160), nullable=False),
    sa.Column('preferred_industry', sa.String(length=160), nullable=False),
    sa.Column('soft_skills', sa.JSON(), nullable=False),
    sa.Column('certifications', sa.JSON(), nullable=False),
    sa.Column('onboarding_complete', sa.Boolean(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_profiles_user_id'), 'profiles', ['user_id'], unique=True)
    op.create_table('projects',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=160), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('technologies', sa.JSON(), nullable=False),
    sa.Column('domain', sa.String(length=100), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_projects_user_id'), 'projects', ['user_id'], unique=False)
    op.create_table('recommendations',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('career_id', sa.Integer(), nullable=False),
    sa.Column('score', sa.Float(), nullable=False),
    sa.Column('factors', sa.JSON(), nullable=False),
    sa.Column('evidence', sa.JSON(), nullable=False),
    sa.Column('readiness', sa.Float(), nullable=False),
    sa.Column('coverage', sa.Float(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['career_id'], ['career_roles.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_recommendation_user_career_created', 'recommendations', ['user_id', 'career_id', 'created_at'], unique=False)
    op.create_index(op.f('ix_recommendations_career_id'), 'recommendations', ['career_id'], unique=False)
    op.create_index(op.f('ix_recommendations_created_at'), 'recommendations', ['created_at'], unique=False)
    op.create_index(op.f('ix_recommendations_user_id'), 'recommendations', ['user_id'], unique=False)
    op.create_table('resumes',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('filename', sa.String(length=255), nullable=False),
    sa.Column('extracted', sa.JSON(), nullable=False),
    sa.Column('accepted_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_resumes_user_id'), 'resumes', ['user_id'], unique=False)
    op.create_table('roadmaps',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('career_id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['career_id'], ['career_roles.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_roadmaps_career_id'), 'roadmaps', ['career_id'], unique=False)
    op.create_index(op.f('ix_roadmaps_user_id'), 'roadmaps', ['user_id'], unique=False)
    op.create_table('user_interests',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('interest_id', sa.Integer(), nullable=False),
    sa.Column('source', sa.String(length=24), nullable=False),
    sa.Column('score', sa.Float(), nullable=False),
    sa.ForeignKeyConstraint(['interest_id'], ['interests.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', 'interest_id', name='uq_user_interest')
    )
    op.create_index(op.f('ix_user_interests_interest_id'), 'user_interests', ['interest_id'], unique=False)
    op.create_index(op.f('ix_user_interests_user_id'), 'user_interests', ['user_id'], unique=False)
    op.create_table('user_sessions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('token_hash', sa.String(length=64), nullable=False),
    sa.Column('csrf_hash', sa.String(length=64), nullable=False),
    sa.Column('expires_at', sa.DateTime(), nullable=False),
    sa.Column('revoked_at', sa.DateTime(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_sessions_expires_at'), 'user_sessions', ['expires_at'], unique=False)
    op.create_index(op.f('ix_user_sessions_token_hash'), 'user_sessions', ['token_hash'], unique=True)
    op.create_index(op.f('ix_user_sessions_user_id'), 'user_sessions', ['user_id'], unique=False)
    op.create_table('user_skills',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('skill_id', sa.Integer(), nullable=False),
    sa.Column('level', sa.String(length=24), nullable=False),
    sa.Column('source', sa.String(length=24), nullable=False),
    sa.ForeignKeyConstraint(['skill_id'], ['skills.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', 'skill_id', name='uq_user_skill')
    )
    op.create_index(op.f('ix_user_skills_skill_id'), 'user_skills', ['skill_id'], unique=False)
    op.create_index(op.f('ix_user_skills_user_id'), 'user_skills', ['user_id'], unique=False)
    op.create_table('roadmap_progress',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('roadmap_id', sa.Integer(), nullable=False),
    sa.Column('phase', sa.String(length=64), nullable=False),
    sa.Column('title', sa.String(length=160), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('status', sa.String(length=24), nullable=False),
    sa.Column('skill', sa.String(length=100), nullable=True),
    sa.ForeignKeyConstraint(['roadmap_id'], ['roadmaps.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_roadmap_progress_roadmap_id'), 'roadmap_progress', ['roadmap_id'], unique=False)
    op.create_table('skill_gaps',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('recommendation_id', sa.Integer(), nullable=False),
    sa.Column('skill_id', sa.Integer(), nullable=False),
    sa.Column('current_level', sa.String(length=24), nullable=False),
    sa.Column('required_level', sa.String(length=24), nullable=False),
    sa.Column('severity', sa.String(length=24), nullable=False),
    sa.ForeignKeyConstraint(['recommendation_id'], ['recommendations.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['skill_id'], ['skills.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_skill_gaps_recommendation_id'), 'skill_gaps', ['recommendation_id'], unique=False)
    op.create_index(op.f('ix_skill_gaps_skill_id'), 'skill_gaps', ['skill_id'], unique=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    raise RuntimeError("The initial application schema cannot be downgraded without an explicit data-retention decision.")
