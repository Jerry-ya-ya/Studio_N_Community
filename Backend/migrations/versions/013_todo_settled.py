"""todo settled

Revision ID: 013_todo_settled
Revises: 012_project_review
Create Date: 2026-08-05
"""
from alembic import op
import sqlalchemy as sa


revision = "013_todo_settled"
down_revision = "012_project_review"
branch_labels = None
depends_on = None


def has_column(inspector, table_name, column_name):
    return column_name in [column["name"] for column in inspector.get_columns(table_name)]


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not has_column(inspector, "todo", "settled"):
        op.add_column(
            "todo",
            sa.Column("settled", sa.Boolean(), nullable=True, server_default=sa.false()),
        )
        op.execute("UPDATE todo SET settled = false WHERE settled IS NULL")
        op.alter_column("todo", "settled", nullable=False, server_default=None)


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if has_column(inspector, "todo", "settled"):
        op.drop_column("todo", "settled")
