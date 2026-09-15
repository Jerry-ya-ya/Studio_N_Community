"""add project recruitment github url

Revision ID: 029_recruit_github_url
Revises: 028_form_settlement
Create Date: 2026-09-15
"""

from alembic import op
import sqlalchemy as sa


revision = '029_recruit_github_url'
down_revision = '028_form_settlement'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    column_names = {
        column['name'] for column in inspector.get_columns('project_recruitment')
    }
    if 'github_url' not in column_names:
        op.add_column(
            'project_recruitment',
            sa.Column('github_url', sa.String(length=2048), nullable=True),
        )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    column_names = {
        column['name'] for column in inspector.get_columns('project_recruitment')
    }
    if 'github_url' in column_names:
        op.drop_column('project_recruitment', 'github_url')
