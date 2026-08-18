"""activity time

Revision ID: 017_activity_time
Revises: 016_user_soft_delete
Create Date: 2026-08-18
"""

from alembic import op
import sqlalchemy as sa


revision = '017_activity_time'
down_revision = '016_user_soft_delete'
branch_labels = None
depends_on = None


def has_column(inspector, table_name, column_name):
    return column_name in [column['name'] for column in inspector.get_columns(table_name)]


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not has_column(inspector, 'activity_promotion', 'start_at'):
        op.add_column('activity_promotion', sa.Column('start_at', sa.DateTime(), nullable=True))

    if not has_column(inspector, 'activity_promotion', 'end_at'):
        op.add_column('activity_promotion', sa.Column('end_at', sa.DateTime(), nullable=True))


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if has_column(inspector, 'activity_promotion', 'end_at'):
        op.drop_column('activity_promotion', 'end_at')

    if has_column(inspector, 'activity_promotion', 'start_at'):
        op.drop_column('activity_promotion', 'start_at')
