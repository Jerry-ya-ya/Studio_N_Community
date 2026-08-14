"""add user soft delete fields

Revision ID: 016_user_soft_delete
Revises: 015_post_like
Create Date: 2026-08-14
"""

from alembic import op
import sqlalchemy as sa


revision = '016_user_soft_delete'
down_revision = '015_post_like'
branch_labels = None
depends_on = None


def has_column(inspector, table_name, column_name):
    return column_name in [column['name'] for column in inspector.get_columns(table_name)]


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not has_column(inspector, 'user', 'is_deleted'):
        op.add_column('user', sa.Column('is_deleted', sa.Boolean(), nullable=True))
        op.execute(sa.text('UPDATE "user" SET is_deleted = false WHERE is_deleted IS NULL'))
        op.alter_column('user', 'is_deleted', nullable=False)

    if not has_column(inspector, 'user', 'deleted_at'):
        op.add_column('user', sa.Column('deleted_at', sa.DateTime(), nullable=True))


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if has_column(inspector, 'user', 'deleted_at'):
        op.drop_column('user', 'deleted_at')

    if has_column(inspector, 'user', 'is_deleted'):
        op.drop_column('user', 'is_deleted')
