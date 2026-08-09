"""activity

Revision ID: 014_activity
Revises: 013_todo_settled
Create Date: 2026-08-09
"""
from alembic import op
import sqlalchemy as sa


revision = "014_activity"
down_revision = "013_todo_settled"
branch_labels = None
depends_on = None


def has_table(inspector, table_name):
    return table_name in inspector.get_table_names()


def has_index(inspector, table_name, index_name):
    return index_name in [index["name"] for index in inspector.get_indexes(table_name)]


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not has_table(inspector, "activity_promotion"):
        op.create_table(
            "activity_promotion",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("title", sa.String(length=120), nullable=False),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("visibility", sa.String(length=20), nullable=False, server_default="private"),
            sa.Column("target_filter", sa.String(length=160), nullable=False, server_default="all"),
            sa.Column("image_url", sa.String(length=255), nullable=True),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
            sa.Column("created_by_id", sa.Integer(), nullable=True),
            sa.CheckConstraint("visibility IN ('public', 'private')", name="ck_activity_promotion_visibility"),
            sa.ForeignKeyConstraint(["created_by_id"], ["user.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

        op.create_index(
            "ix_activity_promotion_visibility",
            "activity_promotion",
            ["visibility"],
            unique=False,
        )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if has_table(inspector, "activity_promotion"):
        if has_index(inspector, "activity_promotion", "ix_activity_promotion_visibility"):
            op.drop_index("ix_activity_promotion_visibility", table_name="activity_promotion")
        op.drop_table("activity_promotion")
