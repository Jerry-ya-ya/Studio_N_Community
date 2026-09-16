"""user PM and review levels

Revision ID: 034_user_levels
Revises: 033_todo_requests
Create Date: 2026-09-16
"""

from alembic import op
import sqlalchemy as sa


revision = '034_user_levels'
down_revision = '033_todo_requests'
branch_labels = None
depends_on = None


def has_column(inspector, table_name, column_name):
    return column_name in {
        column['name'] for column in inspector.get_columns(table_name)
    }


def upgrade():
    inspector = sa.inspect(op.get_bind())
    for level_column, experience_column in (
        ('pm_level', 'pm_experience'),
        ('review_level', 'review_experience'),
    ):
        if has_column(inspector, 'user', level_column):
            continue

        op.add_column(
            'user',
            sa.Column(level_column, sa.Integer(), nullable=True, server_default='1'),
        )
        op.execute(
            sa.text(
                f'UPDATE "user" SET {level_column} = '
                f'(COALESCE({experience_column}, 0) / 100) + 1'
            )
        )
        with op.batch_alter_table('user') as batch_op:
            batch_op.alter_column(
                level_column,
                existing_type=sa.Integer(),
                nullable=False,
                server_default=None,
            )
        inspector = sa.inspect(op.get_bind())


def downgrade():
    inspector = sa.inspect(op.get_bind())
    for column_name in ('review_level', 'pm_level'):
        if has_column(inspector, 'user', column_name):
            op.drop_column('user', column_name)
