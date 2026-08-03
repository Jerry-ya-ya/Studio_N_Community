"""todo levels

Revision ID: 011_todo_levels
Revises: 010_avatar_src
Create Date: 2026-08-03
"""
from alembic import op
import sqlalchemy as sa


revision = "011_todo_levels"
down_revision = "010_avatar_src"
branch_labels = None
depends_on = None


def has_column(inspector, table_name, column_name):
    return column_name in [column["name"] for column in inspector.get_columns(table_name)]


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not has_column(inspector, "todo", "difficulty"):
        op.add_column("todo", sa.Column("difficulty", sa.Integer(), nullable=True))
        op.execute("UPDATE todo SET difficulty = 5 WHERE difficulty IS NULL")
        op.alter_column("todo", "difficulty", nullable=False)

    if not has_column(inspector, "todo", "duration"):
        op.add_column("todo", sa.Column("duration", sa.Integer(), nullable=True))
        op.execute("UPDATE todo SET duration = 5 WHERE duration IS NULL")
        op.alter_column("todo", "duration", nullable=False)


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if has_column(inspector, "todo", "duration"):
        op.drop_column("todo", "duration")

    if has_column(inspector, "todo", "difficulty"):
        op.drop_column("todo", "difficulty")
