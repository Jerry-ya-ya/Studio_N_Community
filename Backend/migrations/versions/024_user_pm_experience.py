"""user PM experience

Revision ID: 024_user_pm_experience
Revises: 023_refresh_token_rotation
Create Date: 2026-09-12
"""

from alembic import op
import sqlalchemy as sa


revision = '024_user_pm_experience'
down_revision = '023_refresh_token_rotation'
branch_labels = None
depends_on = None


def has_column(inspector, table_name, column_name):
    return column_name in [column['name'] for column in inspector.get_columns(table_name)]


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not has_column(inspector, 'user', 'pm_experience'):
        op.add_column(
            'user',
            sa.Column('pm_experience', sa.Integer(), nullable=True, server_default='0'),
        )
        op.execute(sa.text(
            'UPDATE "user" SET pm_experience = 0 WHERE pm_experience IS NULL'
        ))
        op.alter_column(
            'user',
            'pm_experience',
            existing_type=sa.Integer(),
            nullable=False,
            server_default='0',
        )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if has_column(inspector, 'user', 'pm_experience'):
        op.drop_column('user', 'pm_experience')
