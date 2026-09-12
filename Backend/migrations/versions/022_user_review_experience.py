"""user review experience

Revision ID: 022_user_review_experience
Revises: 021_project_levels
Create Date: 2026-09-12
"""

from alembic import op
import sqlalchemy as sa


revision = '022_user_review_experience'
down_revision = '021_project_levels'
branch_labels = None
depends_on = None


def has_column(inspector, table_name, column_name):
    return column_name in [column['name'] for column in inspector.get_columns(table_name)]


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not has_column(inspector, 'user', 'review_experience'):
        op.add_column(
            'user',
            sa.Column('review_experience', sa.Integer(), nullable=True, server_default='0'),
        )
        op.execute(sa.text(
            'UPDATE "user" SET review_experience = 0 WHERE review_experience IS NULL'
        ))
        op.alter_column(
            'user',
            'review_experience',
            existing_type=sa.Integer(),
            nullable=False,
            server_default='0',
        )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if has_column(inspector, 'user', 'review_experience'):
        op.drop_column('user', 'review_experience')
