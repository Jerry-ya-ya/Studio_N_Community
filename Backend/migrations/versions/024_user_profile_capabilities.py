"""user public profile capabilities

Revision ID: 024_user_profile_capabilities
Revises: 023_user_pm_experience
Create Date: 2026-09-13
"""

from alembic import op
import sqlalchemy as sa


revision = '024_user_profile_capabilities'
down_revision = '023_user_pm_experience'
branch_labels = None
depends_on = None


CAPABILITY_COLUMNS = {
    'capability_direction': 'both',
    'capability_stack': 'fullstack',
    'capability_focus': 'game-systems',
    'capability_style': 'professional',
}


def has_column(inspector, table_name, column_name):
    return column_name in [column['name'] for column in inspector.get_columns(table_name)]


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    for column_name, default_value in CAPABILITY_COLUMNS.items():
        if not has_column(inspector, 'user', column_name):
            op.add_column(
                'user',
                sa.Column(
                    column_name,
                    sa.String(length=32),
                    nullable=False,
                    server_default=default_value,
                ),
            )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    for column_name in reversed(CAPABILITY_COLUMNS):
        if has_column(inspector, 'user', column_name):
            op.drop_column('user', column_name)
