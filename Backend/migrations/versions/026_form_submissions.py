"""add versioned user form submissions

Revision ID: 026_form_submissions
Revises: 025_form_templates
Create Date: 2026-09-13
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = '026_form_submissions'
down_revision = '025_form_templates'
branch_labels = None
depends_on = None


def upgrade():
    json_type = sa.JSON().with_variant(postgresql.JSONB(), 'postgresql')
    op.create_table(
        'form_submission',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('form_version', sa.Integer(), nullable=False),
        sa.Column('form_snapshot', json_type, nullable=False),
        sa.Column('answers', json_type, nullable=False),
        sa.Column('submitted_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('form_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['form_id'], ['form_template.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'form_id', 'user_id', 'form_version',
            name='uq_form_submission_form_user_version',
        ),
    )
    op.create_index('ix_form_submission_form_id', 'form_submission', ['form_id'])
    op.create_index('ix_form_submission_user_id', 'form_submission', ['user_id'])


def downgrade():
    op.drop_index('ix_form_submission_user_id', table_name='form_submission')
    op.drop_index('ix_form_submission_form_id', table_name='form_submission')
    op.drop_table('form_submission')
