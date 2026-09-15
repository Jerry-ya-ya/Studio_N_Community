"""add user activity status

Revision ID: 030_user_activity_status
Revises: 029_recruit_github_url
Create Date: 2026-09-15
"""

from alembic import op
import sqlalchemy as sa


revision = '030_user_activity_status'
down_revision = '029_recruit_github_url'
branch_labels = None
depends_on = None


def has_column(inspector, table_name, column_name):
    return column_name in [column['name'] for column in inspector.get_columns(table_name)]


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not has_column(inspector, 'user', 'is_active'):
        op.add_column(
            'user',
            sa.Column(
                'is_active',
                sa.Boolean(),
                nullable=False,
                server_default=sa.true(),
            ),
        )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if has_column(inspector, 'user', 'is_active'):
        op.drop_column('user', 'is_active')
