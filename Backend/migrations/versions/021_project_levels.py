"""project levels

Revision ID: 021_project_levels
Revises: 020_user_achievements
Create Date: 2026-09-10
"""

from alembic import op
import sqlalchemy as sa


revision = '021_project_levels'
down_revision = '020_user_achievements'
branch_labels = None
depends_on = None


def has_column(inspector, table_name, column_name):
    return column_name in [column['name'] for column in inspector.get_columns(table_name)]


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not has_column(inspector, 'project_recruitment', 'level'):
        op.add_column(
            'project_recruitment',
            sa.Column('level', sa.Integer(), nullable=True, server_default='1'),
        )
        op.execute(sa.text(
            'UPDATE project_recruitment '
            'SET level = CAST(COALESCE(token_used, 0) / 100 AS INTEGER) + 1'
        ))
        op.alter_column(
            'project_recruitment',
            'level',
            existing_type=sa.Integer(),
            nullable=False,
            server_default='1',
        )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if has_column(inspector, 'project_recruitment', 'level'):
        op.drop_column('project_recruitment', 'level')
