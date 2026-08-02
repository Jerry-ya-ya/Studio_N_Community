"""avatar source

Revision ID: 010_avatar_src
Revises: 009_checkin
Create Date: 2026-08-02
"""
from alembic import op
import sqlalchemy as sa


revision = "010_avatar_src"
down_revision = "009_checkin"
branch_labels = None
depends_on = None


def has_column(inspector, table_name, column_name):
    return column_name in [column["name"] for column in inspector.get_columns(table_name)]


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not has_column(inspector, "user", "avatar_source"):
        op.add_column(
            "user",
            sa.Column("avatar_source", sa.String(length=20), nullable=True),
        )
        op.execute("UPDATE \"user\" SET avatar_source = 'github' WHERE avatar_source IS NULL")
        op.alter_column("user", "avatar_source", nullable=False)


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if has_column(inspector, "user", "avatar_source"):
        op.drop_column("user", "avatar_source")
